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
    weather = get_weather()
    if not stage:
        return jsonify({"reply":"Please select a crop and growth stage first.","source":"system"})
    result = predict(crop,stage,sd,weather)
    if gemini_ready and gemini_client:
        try:
            prompt = (f"You are EcoSense, a smart farming assistant. "
                      f"Crop: {crop}, Stage: {stage}. "
                      f"Moisture: {sd.get('soil_moisture',0):.0f}%, TDS: {sd.get('tds_ppm',0):.0f}ppm, "
                      f"Temp: {sd.get('air_temp_c',0):.1f}C, Humidity: {sd.get('humidity_pct',0):.0f}%. "
                      f"Health: {result['health_status']} ({result['health_score']}/100). "
                      f"Irrigate: {result['irrigate_now']}, Pump locked: {result['pump_locked']}, Gas alert: {result['gas_alert']}. "
                      f"Farmer asks: {msg}. "
                      f"Reply in 1-2 short simple sentences only. Be direct. No technical jargon.")
            resp = gemini_client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            return jsonify({"reply":resp.text.strip(),"source":"gemini"})
        except Exception as e:
            print(f"Gemini chat error: {e}")
    hs = result["health_status"]; sc = result["health_score"]
    tips = {"GOOD":"Crop looks healthy. Keep monitoring.", "MODERATE":"Crop needs attention. Check moisture and nutrients.", "POOR":"Crop is struggling. Take action soon.", "CRITICAL":"Urgent! Crop is in critical condition."}
    offline = f"{tips.get(hs,'')} Moisture: {sd.get('soil_moisture',0):.0f}%. {'Irrigate now.' if result['irrigate_now'] else ''} {'Gas danger!' if result['gas_alert'] else ''}"
    return jsonify({"reply":offline.strip(),"source":"offline"})

@app.route("/status")
def status():
    return jsonify({"gemini_ready":gemini_ready,"models_loaded":True,
                    "weather_enabled":bool(WEATHER_API_KEY),
                    "telegram_enabled":bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID),"callmebot_enabled":bool(CALLMEBOT_PHONE and CALLMEBOT_APIKEY)})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
