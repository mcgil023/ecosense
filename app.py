from flask import Flask, render_template, request, jsonify
import joblib, json, os, requests
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import deque

# NEW google-genai package
try:
    from google import genai as ggenai
    GENAI_OK = True
except ImportError:
    GENAI_OK = False

GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY","")
CALLMEBOT_PHONE  = os.environ.get("CALLMEBOT_PHONE","")   # kept for backward compat
CALLMEBOT_APIKEY = os.environ.get("CALLMEBOT_APIKEY","")  # kept for backward compat
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN","")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID","")
WEATHER_API_KEY  = os.environ.get("WEATHER_API_KEY","")
WEATHER_CITY     = os.environ.get("WEATHER_CITY","Tiruchirappalli")

app  = Flask(__name__)
BASE = Path(__file__).parent

# ── Gemini init ──────────────────────────────────────────────
gemini_ready  = False
gemini_client = None
try:
    if GEMINI_API_KEY and GENAI_OK:
        gemini_client = ggenai.Client(api_key=GEMINI_API_KEY)
        gemini_ready  = True
        print("✅ Gemini (google-genai) ready")
except Exception as e:
    print(f"⚠️  Gemini init error: {e}")

# ── Models ──────────────────────────────────────────────────
model_health   = joblib.load(BASE/"model_health_status.pkl")
model_irrigate = joblib.load(BASE/"model_irrigate_now.pkl")
model_lock     = joblib.load(BASE/"model_pump_lock.pkl")
model_gas      = joblib.load(BASE/"model_gas_alert.pkl")
le_crop        = joblib.load(BASE/"encoder_crop.pkl")
le_stage       = joblib.load(BASE/"encoder_stage.pkl")
le_health      = joblib.load(BASE/"encoder_health.pkl")
with open(BASE/"crop_config.json") as f:
    CC = json.load(f)

FEATURES = ["crop_enc","stage_enc","is_critical_stage","soil_moisture","tds_ppm",
            "air_temp_c","soil_temp_c","humidity_pct","mq135_ammonia","mq4_methane",
            "mq7_co","mq2_smoke","moist_min_threshold","moist_opt_threshold","tds_max_threshold"]
history  = {k: deque(maxlen=20) for k in ["soil_moisture","tds_ppm","air_temp_c","mq135_ammonia"]}
esp32_data = {}

# ── Helpers ─────────────────────────────────────────────────
def get_weather(city=WEATHER_CITY):
    if not WEATHER_API_KEY:
        return {"enabled":False}
    try:
        r = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric",
            timeout=10).json()
        return {"enabled":True,"city":city,"temp":r["main"]["temp"],
                "humidity":r["main"]["humidity"],"rain":r.get("rain",{}).get("1h",0),
                "wind":r["wind"]["speed"],"desc":r["weather"][0]["main"]}
    except Exception as e:
        return {"enabled":False,"error":str(e)}

def telegram_send(text):
    """Send alert via Telegram Bot — instant setup, always reliable"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return {"ok":False,"reason":"TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set"}
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode":"HTML"},
            timeout=15)
        data = r.json()
        ok = r.status_code == 200 and data.get("ok", False)
        print(f"📲 Telegram → {'✅ sent' if ok else '❌ failed'} | {r.status_code}")
        return {"ok": ok, "status": r.status_code, "response": str(data)[:200]}
    except Exception as e:
        print(f"⚠️  Telegram error: {e}")
        return {"ok":False,"error":str(e)}

def callmebot_send(text):
    """Legacy WhatsApp via CallMeBot — use as fallback only"""
    if not CALLMEBOT_PHONE or not CALLMEBOT_APIKEY:
        return {"ok":False,"reason":"CALLMEBOT env vars not set"}
    from urllib.parse import quote
    phone = CALLMEBOT_PHONE.strip().replace(" ","")
    if not phone.startswith("+"): phone = "+91" + phone
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={quote(text)}&apikey={CALLMEBOT_APIKEY}"
    try:
        r = requests.get(url, timeout=20)
        print(f"📱 CallMeBot → status {r.status_code}")
        return {"ok": r.status_code==200, "status": r.status_code}
    except Exception as e:
        return {"ok":False,"error":str(e)}

def send_alert(text):
    """Try Telegram first; fall back to CallMeBot if configured"""
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return telegram_send(text)
    elif CALLMEBOT_PHONE and CALLMEBOT_APIKEY:
        return send_alert(text)
    else:
        print("⚠️  No alert channel configured (set TELEGRAM_TOKEN+TELEGRAM_CHAT_ID in Render env)")
        return {"ok":False,"reason":"no alert channel configured"}


def predict(crop, stage, sd, weather=None):
    cfg = CC[crop]; sc = cfg["stages"][stage]
    row = pd.DataFrame([[
        le_crop.transform([crop])[0], le_stage.transform([stage])[0],
        1 if sc.get("critical") else 0,
        sd["soil_moisture"],sd["tds_ppm"],sd["air_temp_c"],sd["soil_temp_c"],
        sd["humidity_pct"],sd["mq135_ammonia"],sd["mq4_methane"],sd["mq7_co"],sd["mq2_smoke"],
        sc["moist_min"],sc["moist_opt"],cfg["tds_max"]
    ]], columns=FEATURES)
    hl = le_health.inverse_transform([model_health.predict(row)[0]])[0]
    irr  = int(model_irrigate.predict(row)[0])
    lock = int(model_lock.predict(row)[0])
    gas  = int(model_gas.predict(row)[0])
    conf = round(float(max(model_health.predict_proba(row)[0]))*100,1)
    aqi  = 100
    if sd["mq135_ammonia"]>200: aqi-=30
    elif sd["mq135_ammonia"]>100: aqi-=15
    if sd["mq7_co"]>100: aqi-=35
    elif sd["mq7_co"]>35: aqi-=20
    if sd["mq4_methane"]>1000: aqi-=25
    if sd["mq2_smoke"]>400: aqi-=25
    aqi = max(0,aqi)
    aqi_lbl = ("Excellent" if aqi>=80 else "Good" if aqi>=60 else "Moderate" if aqi>=40 else "Poor" if aqi>=20 else "Critical")
    for k in history:
        if k in sd: history[k].append(sd[k])
    trend="stable"
    if len(history["soil_moisture"])>=5:
        d=list(history["soil_moisture"]); h=len(d)//2
        delta=sum(d[h:])/len(d[h:])-sum(d[:h])/len(d[:h])
        trend="falling" if delta<-1 else "rising" if delta>1 else "stable"
    hs={"GOOD":90,"MODERATE":65,"POOR":40,"CRITICAL":15}
    return {"health_status":hl,"health_score":hs.get(hl,50),"confidence_pct":conf,
            "irrigate_now":bool(irr),"pump_locked":bool(lock),
            "pump_on":bool(irr) and not bool(lock),
            "gas_alert":bool(gas),"field_aqi":aqi,"field_aqi_label":aqi_lbl,
            "tds_safe":sd["tds_ppm"]<=cfg["tds_max"],
            "is_critical_stage":bool(sc.get("critical",False)),
            "moist_min":sc["moist_min"],"moist_opt":sc["moist_opt"],"tds_max":cfg["tds_max"],
            "trend_moisture":trend,"timestamp":datetime.now().strftime("%H:%M:%S"),
            "weather":weather or {}}

def send_alert_if_needed(crop,stage,sd,result,weather):
    if result["gas_alert"] or result["pump_locked"] or result["health_status"]=="CRITICAL":
        w = f" Weather {weather.get('temp')}C, hum {weather.get('humidity')}%" if weather and weather.get("enabled") else ""
        text=(f"EcoSense Alert: {crop} {stage}. Health {result['health_status']} ({result['health_score']}/100). "
              f"Pump {'LOCKED' if result['pump_locked'] else 'OK'}. Gas {'DANGER' if result['gas_alert'] else 'CLEAR'}.{w}")
        return send_alert(text)
    return {"ok":False,"reason":"no alert"}

# ── Routes ──────────────────────────────────────────────────
@app.route("/")
def index():
    crops  = list(CC.keys())
    stages = {c:list(CC[c]["stages"].keys()) for c in crops}
    return render_template("index.html",crops=crops,stages=json.dumps(stages),gemini_ready=gemini_ready)

@app.route("/crops")
def crops_route():
    return jsonify({c:{"stages":list(CC[c]["stages"].keys())} for c in CC})

@app.route("/predict",methods=["POST"])
def predict_route():
    d=request.json; weather=get_weather()
    result=predict(d["crop"],d["stage"],d["sensors"],weather)
    send_alert_if_needed(d["crop"],d["stage"],d["sensors"],result,weather)
    return jsonify(result)

@app.route("/weather")
def weather_route():
    return jsonify(get_weather())

@app.route("/esp32",methods=["POST"])
def receive_esp32():
    global esp32_data; esp32_data=request.json
    return jsonify({"status":"ok"})

@app.route("/live")
def live():
    return jsonify(esp32_data if esp32_data else {"status":"no_data"})

@app.route("/chat",methods=["POST"])
def chat():
    msg   = request.json.get("message","").strip()
    crop  = request.json.get("crop","rice")
    stage = request.json.get("stage","")
    sd    = request.json.get("sensors",{})
    lang  = request.json.get("lang","en")
    weather = get_weather()
    if not stage:
        return jsonify({"reply":"Please select a crop and growth stage first.","source":"system"})
    result = predict(crop,stage,sd,weather)
    if gemini_ready and gemini_client:
        try:
            lang_str = "Tamil (தமிழ்)" if lang=="ta" else "simple English"
            lang_instruction = "நீங்கள் தமிழில் மட்டுமே பதில் சொல்ல வேண்டும். English பயன்படுத்தாதீர்கள்." if lang=="ta" else ""
            prompt = (f"IMPORTANT INSTRUCTION: {lang_instruction if lang=='ta' else 'Reply in simple English only.'} "
                      f"You are EcoSense, an expert smart farming AI assistant. "
                      f"Current crop: {crop}, growth stage: {stage}. "
                      f"Live sensor data: {sd}. "
                      f"Weather: {weather}. "
                      f"AI prediction: health={result['health_status']}({result['health_score']}/100), "
                      f"irrigate={result['irrigate_now']}, pump_locked={result['pump_locked']}, gas_alert={result['gas_alert']}. "
                      f"Farmer asks: {msg}. "
                      f"Give a concise, practical, actionable answer in 2-3 sentences. "
                      f"{'MUST reply in Tamil (தமிழ்) language only. Do not use English at all.' if lang=='ta' else ''}")
            resp = gemini_client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            return jsonify({"reply":resp.text.strip(),"source":"gemini"})
        except Exception as e:
            print(f"Gemini chat error: {e}")
    hs = result["health_status"]; sc = result["health_score"]
    offline = (f"Health: {hs} ({sc}/100). Moisture: {sd.get('soil_moisture',0):.0f}%. "
               f"TDS: {sd.get('tds_ppm',0):.0f} ppm ({'Safe' if result['tds_safe'] else 'High'}). "
               f"Pump: {'LOCKED' if result['pump_locked'] else ('ON' if result['pump_on'] else 'OFF')}. "
               f"Gas: {'DANGER' if result['gas_alert'] else 'Clear'}.")
    return jsonify({"reply":offline,"source":"offline"})

@app.route("/test-whatsapp")
def test_whatsapp():
    result = send_alert("🌱 EcoSense Alert Test\nYour smart farm is connected! ✅\nAll systems active.")
    return jsonify(result)

@app.route("/status")
def status():
    return jsonify({"gemini_ready":gemini_ready,"models_loaded":True,
                    "weather_enabled":bool(WEATHER_API_KEY),
                    "telegram_enabled":bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID),"callmebot_enabled":bool(CALLMEBOT_PHONE and CALLMEBOT_APIKEY)})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
