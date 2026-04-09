import os, json, pickle, threading
from pathlib import Path
from datetime import datetime
from collections import deque
import requests
from flask import Flask, request, jsonify, render_template

# Heavy imports wrapped — startup never crashes
np = pd = None
try:
    import numpy as np
    import pandas as pd
except Exception as e:
    print(f"⚠️ numpy/pandas: {e}")

app = Flask(__name__)

GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY",  "")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
WEATHER_CITY    = os.environ.get("WEATHER_CITY",    "Tiruchirappalli")

# Gemini
gemini_client = None
try:
    if GEMINI_API_KEY:
        from google import genai as _genai
        _gc = _genai.Client(api_key=GEMINI_API_KEY)
        class _W:
            def __init__(self,c): self._c=c
            def generate_content(self,p):
                r=self._c.models.generate_content(model="gemini-2.0-flash",contents=p)
                class _R:
                    def __init__(self,t): self.text=t
                return _R(r.text)
        gemini_client = _W(_gc)
        print("✅ Gemini ready")
except Exception as e:
    print(f"⚠️ Gemini: {e}")

# ML Models
models = {}
try:
    for f in Path("models").glob("*.pkl"):
        with open(f,"rb") as fh: models[f.stem]=pickle.load(fh)
        print(f"✅ Model: {f.stem}")
except Exception as e:
    print(f"⚠️ Models: {e}")

CROP_CONFIG = {
    "rice":      {"stages":["germination","tillering","flowering","harvest"],    "moist_min":60,"moist_opt":75,"tds_max":800},
    "maize":     {"stages":["germination","vegetative","tasseling","harvest"],   "moist_min":50,"moist_opt":70,"tds_max":700},
    "groundnut": {"stages":["germination","vegetative","flowering","harvest"],   "moist_min":45,"moist_opt":65,"tds_max":600},
    "sugarcane": {"stages":["germination","tillering","grand_growth","harvest"], "moist_min":65,"moist_opt":80,"tds_max":900},
    "coconut":   {"stages":["seedling","vegetative","flowering","harvest"],      "moist_min":50,"moist_opt":70,"tds_max":750},
}
CRITICAL_STAGES = ["flowering","tasseling","grand_growth"]
esp32_data = {}
history = {k: deque(maxlen=20) for k in ["soil_moisture","tds_ppm","air_temp_c","mq135_ammonia"]}

def get_weather():
    try:
        if not WEATHER_API_KEY:
            return {"enabled":False,"temp":30,"humidity":60,"rain":0,"wind":2,"city":WEATHER_CITY}
        r=requests.get("https://api.openweathermap.org/data/2.5/weather",
            params={"q":WEATHER_CITY,"appid":WEATHER_API_KEY,"units":"metric"},timeout=8)
        d=r.json()
        return {"enabled":True,"temp":round(d["main"]["temp"],1),
                "humidity":d["main"]["humidity"],"rain":d.get("rain",{}).get("1h",0),
                "wind":round(d["wind"]["speed"],1),"city":WEATHER_CITY}
    except:
        return {"enabled":False,"temp":30,"humidity":60,"rain":0,"wind":2,"city":WEATHER_CITY}

def get_forecast():
    try:
        if not WEATHER_API_KEY:
            return {"enabled":False,"next24h":[],"rain_coming":False,"heat_coming":False,
                    "total_rain_mm":0,"max_temp":30,"summary":"Forecast unavailable"}
        r=requests.get("https://api.openweathermap.org/data/2.5/forecast",
            params={"q":WEATHER_CITY,"appid":WEATHER_API_KEY,"units":"metric","cnt":8},timeout=8)
        d=r.json()
        slots=[{"time":i["dt_txt"][11:16],"temp":round(i["main"]["temp"],1),
                "humidity":i["main"]["humidity"],"rain":round(i.get("rain",{}).get("3h",0),1),
                "desc":i["weather"][0]["main"]} for i in d.get("list",[])[:8]]
        rc=any(s["rain"]>1 for s in slots); hc=any(s["temp"]>36 for s in slots)
        mt=max((s["temp"] for s in slots),default=30)
        tr=round(sum(s["rain"] for s in slots),1)
        sm=(f"🌧 Heavy rain {tr}mm — skip irrigation" if rc and tr>5 else
            f"🌦 Light rain expected" if rc else
            f"🌡️ Heat {mt}°C ahead — irrigate early" if hc else "🌤 Stable weather")
        return {"enabled":True,"next24h":slots,"rain_coming":rc,"heat_coming":hc,
                "total_rain_mm":tr,"max_temp":mt,"summary":sm}
    except Exception as e:
        return {"enabled":False,"next24h":[],"rain_coming":False,"heat_coming":False,
                "total_rain_mm":0,"max_temp":30,"summary":"Forecast unavailable"}

def predict(crop, stage, sensors, weather):
    try:
        cfg=CROP_CONFIG.get(crop,CROP_CONFIG["rice"])
        sd={"soil_moisture":float(sensors.get("soil_moisture",72)),
            "tds_ppm":float(sensors.get("tds_ppm",350)),
            "air_temp_c":float(sensors.get("air_temp_c",28)),
            "soil_temp_c":float(sensors.get("soil_temp_c",24)),
            "humidity_pct":float(sensors.get("humidity_pct",65)),
            "mq135_ammonia":float(sensors.get("mq135_ammonia",50)),
            "mq4_methane":float(sensors.get("mq4_methane",200)),
            "mq7_co":float(sensors.get("mq7_co",10))}
        for k in ["soil_moisture","tds_ppm","air_temp_c","mq135_ammonia"]:
            history[k].append(sd[k])
        score=100
        if sd["soil_moisture"]<cfg["moist_min"]:
            score-=min(40,(cfg["moist_min"]-sd["soil_moisture"])*1.2)
        elif sd["soil_moisture"]>90: score-=15
        tds_safe=sd["tds_ppm"]<=cfg["tds_max"]
        if not tds_safe: score-=min(30,(sd["tds_ppm"]-cfg["tds_max"])/30)
        if sd["air_temp_c"]>38: score-=min(25,(sd["air_temp_c"]-38)*3)
        elif sd["air_temp_c"]<15: score-=20
        gas_alert=(sd["mq135_ammonia"]>200 or sd["mq4_methane"]>1000 or sd["mq7_co"]>100)
        if gas_alert: score-=30
        if sd["humidity_pct"]>90: score-=10
        elif sd["humidity_pct"]<30: score-=15
        score=max(0,min(100,round(score)))
        hs=("GOOD" if score>=75 else "MODERATE" if score>=50 else "POOR" if score>=25 else "CRITICAL")
        if crop in models and np is not None and pd is not None:
            try:
                feat=["soil_moisture","tds_ppm","air_temp_c","soil_temp_c","humidity_pct",
                      "mq135_ammonia","mq4_methane","mq7_co",
                      "moist_min_threshold","moist_opt_threshold","tds_max_threshold"]
                row=pd.DataFrame([[sd["soil_moisture"],sd["tds_ppm"],sd["air_temp_c"],
                    sd["soil_temp_c"],sd["humidity_pct"],sd["mq135_ammonia"],
                    sd["mq4_methane"],sd["mq7_co"],
                    cfg["moist_min"],cfg["moist_opt"],cfg["tds_max"]]],columns=feat)
                score=round(max(models[crop].predict_proba(row)[0])*100)
                hs=str(models[crop].predict(row)[0])
            except Exception as e: print(f"⚠️ ML: {e}")
        # pump logic
        pump_locked=(gas_alert or hs=="CRITICAL" or not tds_safe)
        irrigate_now=(sd["soil_moisture"]<cfg["moist_min"] and not pump_locked)
        pump_on=irrigate_now and not pump_locked
        fc=get_forecast()
        if weather.get("rain",0)>2 and pump_on: pump_on=False; irrigate_now=False
        if fc.get("rain_coming") and fc.get("total_rain_mm",0)>5 and pump_on:
            pump_on=False; irrigate_now=False
        if fc.get("heat_coming") and sd["soil_moisture"]<(cfg["moist_opt"]-5) and not pump_locked:
            irrigate_now=True; pump_on=True
        wn=fc.get("summary","🌤 Weather normal.")
        hm=list(history["soil_moisture"])
        trend=("rising" if len(hm)>=3 and hm[-1]>hm[-3]+2 else
               "falling" if len(hm)>=3 and hm[-1]<hm[-3]-2 else "stable")
        aqi=100
        if sd["mq135_ammonia"]>100: aqi-=20
        if sd["mq4_methane"]>500:   aqi-=25
        if sd["mq7_co"]>35:         aqi-=20
        aqi=max(0,aqi)
        return {"health_score":score,"health_status":hs,
                "irrigate_now":bool(irrigate_now),"pump_on":bool(pump_on),
                "pump_locked":bool(pump_locked),"gas_alert":bool(gas_alert),
                "tds_safe":bool(tds_safe),"trend_moisture":trend,
                "field_aqi":max(0,aqi),
                "field_aqi_label":("Excellent" if aqi>80 else "Good" if aqi>60 else "Moderate" if aqi>40 else "Poor"),
                "confidence_pct":min(99,max(70,score+(5 if crop in models else -5))),
                "is_critical_stage":stage in CRITICAL_STAGES,
                "weather_note":wn,"sensors_used":sd}
    except Exception as e:
        print(f"❌ predict: {e}")
        return {"health_score":50,"health_status":"MODERATE","irrigate_now":False,
                "pump_on":False,"pump_locked":False,"gas_alert":False,"tds_safe":True,
                "trend_moisture":"stable","field_aqi":80,"field_aqi_label":"Good",
                "confidence_pct":70,"is_critical_stage":False,"weather_note":"","sensors_used":{}}

def offline_reply_en(result, sd, crop, cfg):
    """English offline reply with correct pump-lock awareness."""
    mst=round(sd.get("soil_moisture",0))
    tds=round(sd.get("tds_ppm",0))
    hs=result.get("health_status","MODERATE")
    if result["pump_locked"] and not result["tds_safe"]:
        return (f"⚠️ Pump is LOCKED — water TDS is {tds}ppm which exceeds safe limit "
                f"({cfg['tds_max']}ppm) for {crop}. Do NOT irrigate. Use fresh water.")
    if result["gas_alert"]:
        return "🚨 Gas alert active! Do NOT irrigate. Ventilate the field immediately."
    if result["irrigate_now"] and result["pump_on"]:
        return (f"💧 Yes, irrigate now. Soil moisture is {mst}% — below the "
                f"{cfg['moist_min']}% minimum needed for {crop}.")
    return (f"✅ No irrigation needed. Moisture {mst}% is adequate for {crop}. "
            f"Health: {hs}.")

def water_quality_reply_en(result, sd, crop, cfg):
    """Correct water quality reply — never says irrigate when TDS is high."""
    tds=round(sd.get("tds_ppm",0))
    if not result["tds_safe"]:
        return (f"❌ Water quality is UNSAFE. TDS is {tds}ppm — exceeds the "
                f"{cfg['tds_max']}ppm limit for {crop}. Pump is locked. "
                f"Source fresh water before irrigating.")
    return (f"✅ Water quality is safe. TDS is {tds}ppm — within the "
            f"{cfg['tds_max']}ppm limit for {crop}. Safe to irrigate if soil needs it.")

def offline_reply_ta(result, sd, crop, cfg):
    """Tamil offline reply with correct pump-lock awareness."""
    mst=round(sd.get("soil_moisture",0))
    tds=round(sd.get("tds_ppm",0))
    hs=result.get("health_status","MODERATE")
    cta={"rice":"நெல்","maize":"மக்காச்சோளம்","groundnut":"நிலக்கடலை",
         "sugarcane":"கரும்பு","coconut":"தேங்காய்"}.get(crop,crop)
    hta={"GOOD":"நல்லது","MODERATE":"நடுத்தரம்","POOR":"மோசம்","CRITICAL":"அவசரம்"}.get(hs,hs)
    if result["pump_locked"] and not result["tds_safe"]:
        return (f"⚠️ பம்ப் தடுக்கப்பட்டுள்ளது — நீரில் TDS {tds}ppm, "
                f"{cta}க்கு அனுமதிக்கப்பட்ட {cfg['tds_max']}ppm ஐ தாண்டியது. "
                f"நீர் பாய்ச்சாதீர்கள். சுத்தமான நீர் பயன்படுத்துங்கள்.")
    if result["gas_alert"]:
        return "🚨 வாயு எச்சரிக்கை! நீர் பாய்ச்சாதீர்கள். வயலை காற்றோட்டம் செய்யுங்கள்."
    if result["irrigate_now"] and result["pump_on"]:
        return (f"💧 இப்போது நீர் பாய்ச்சுங்கள். மண் ஈரப்பதம் {mst}% — "
                f"{cta}க்கு தேவையான {cfg['moist_min']}% ஐ விட குறைவாக உள்ளது.")
    return (f"✅ நீர்ப்பாசனம் தேவையில்லை. ஈரப்பதம் {mst}% போதுமானது. "
            f"ஆரோக்கியம்: {hta}.")

def water_quality_reply_ta(result, sd, crop, cfg):
    tds=round(sd.get("tds_ppm",0))
    cta={"rice":"நெல்","maize":"மக்காச்சோளம்","groundnut":"நிலக்கடலை",
         "sugarcane":"கரும்பு","coconut":"தேங்காய்"}.get(crop,crop)
    if not result["tds_safe"]:
        return (f"❌ நீர் தரம் பாதுகாப்பற்றது. TDS {tds}ppm — {cta}க்கு "
                f"அனுமதிக்கப்பட்ட {cfg['tds_max']}ppm ஐ தாண்டியது. "
                f"பம்ப் தடுக்கப்பட்டுள்ளது. சுத்தமான நீர் தேடுங்கள்.")
    return (f"✅ நீர் தரம் பாதுகாப்பானது. TDS {tds}ppm — {cta}க்கு "
            f"உள்ள {cfg['tds_max']}ppm வரம்புக்கு உட்பட்டது.")

@app.route("/healthz")
def healthz(): return "ok", 200

@app.route("/")
def index(): return render_template("index.html")

@app.route("/crops")
def crops_route(): return jsonify(CROP_CONFIG)

@app.route("/predict", methods=["POST"])
def predict_route():
    try:
        d=request.json or {}
        w=get_weather(); s=dict(d.get("sensors",{}))
        if esp32_data: s.update(esp32_data)
        return jsonify(predict(d.get("crop","rice"),d.get("stage","germination"),s,w))
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route("/weather")
def weather_route(): return jsonify(get_weather())

@app.route("/forecast")
def forecast_route(): return jsonify(get_forecast())

@app.route("/esp32", methods=["POST"])
@app.route("/data",  methods=["POST"])
def receive_esp32():
    global esp32_data
    raw=request.json or {}
    esp32_data=raw.get("sensors",raw)
    print(f"📡 ESP32: {list(esp32_data.keys())}")
    return jsonify({"status":"ok","received":list(esp32_data.keys())})

@app.route("/live")
def live(): return jsonify(esp32_data if esp32_data else {"status":"no_data"})

@app.route("/chat", methods=["POST"])
def chat():
    try:
        d=request.json or {}
        msg=d.get("message","").strip()
        crop=d.get("crop","rice")
        stage=d.get("stage","germination")
        lang=d.get("lang","ta")
        sensors=dict(d.get("sensors",{}))
        if esp32_data: sensors.update(esp32_data)
        result=predict(crop,stage,sensors,get_weather())
        sd=result.get("sensors_used",{})
        cfg=CROP_CONFIG.get(crop,CROP_CONFIG["rice"])
        ml=msg.lower()
        is_ta=(lang=="ta")

        # Keyword routing — water quality checked BEFORE irrigate
        if any(w in ml for w in ["water safe","water quality","tds","saline","salt",
                                   "நீர் தரம்","உப்பு","tds"]):
            off=(water_quality_reply_ta(result,sd,crop,cfg) if is_ta
                 else water_quality_reply_en(result,sd,crop,cfg))
        elif any(w in ml for w in ["irrigat","water","pump","பாசன","நீர்","பம்ப்"]):
            off=(offline_reply_ta(result,sd,crop,cfg) if is_ta
                 else offline_reply_en(result,sd,crop,cfg))
        elif any(w in ml for w in ["gas","ammonia","methane","co ","வாயு","நச்சு"]):
            if result["gas_alert"]:
                off=("வாயு எச்சரிக்கை! NH3:{:.0f}ppm CH4:{:.0f}ppm. உடனே வெளியேறுங்கள்!".format(
                     sd.get("mq135_ammonia",0),sd.get("mq4_methane",0)) if is_ta else
                     "Gas alert! NH3:{:.0f}ppm CH4:{:.0f}ppm. Keep workers away!".format(
                     sd.get("mq135_ammonia",0),sd.get("mq4_methane",0)))
            else:
                off=("காற்று தரம் பாதுகாப்பானது. அனைத்து வாயு அளவுகளும் சாதாரணம்." if is_ta
                     else "Air quality safe. All gas levels normal.")
        elif any(w in ml for w in ["health","status","score","ஆரோக்கிய","நிலை"]):
            sc=result["health_score"]; hs=result["health_status"]
            mst=round(sd.get("soil_moisture",0))
            hta={"GOOD":"நல்லது","MODERATE":"நடுத்தரம்","POOR":"மோசம்","CRITICAL":"அவசரம்"}.get(hs,hs)
            off=(f"{crop} ஆரோக்கியம்: {sc}/100 ({hta}). மண் ஈரப்பதம்: {mst}%." if is_ta
                 else f"{crop} health: {sc}/100 ({hs}). Moisture: {mst}%.")
        elif any(w in ml for w in ["rain","forecast","weather","மழை","வானிலை"]):
            off=result.get("weather_note","🌤 Weather normal.")
        elif any(w in ml for w in ["fertilize","fertil","உரம்"]):
            off=("பயிர் ஆரோக்கியமாக இருந்தால் மட்டும் உரமிடலாம். வாயு எச்சரிக்கை இல்லாதபோது." if is_ta
                 else "Fertilize only when crop is healthy and no gas alerts are active.")
        else:
            off=(offline_reply_ta(result,sd,crop,cfg) if is_ta
                 else offline_reply_en(result,sd,crop,cfg))

        if gemini_client:
            try:
                lang_inst=("Reply ONLY in Tamil language. தமிழில் மட்டும் பதில் சொல்லுங்கள்." if is_ta
                           else "Reply in simple English.")
                prompt=(f"EcoSense AI for Indian farmers. Crop:{crop} Stage:{stage}. "
                        f"Moisture:{sd.get('soil_moisture',0):.0f}% TDS:{sd.get('tds_ppm',0):.0f}ppm "
                        f"(max allowed:{cfg['tds_max']}ppm) Temp:{sd.get('air_temp_c',0):.1f}°C "
                        f"NH3:{sd.get('mq135_ammonia',0):.0f}ppm. "
                        f"Health:{result['health_score']}/100 ({result['health_status']}). "
                        f"Pump locked:{result['pump_locked']} TDS safe:{result['tds_safe']} "
                        f"Gas alert:{result['gas_alert']} Irrigate:{result['irrigate_now']}. "
                        f"Forecast:{result.get('weather_note','')}. "
                        f"Farmer asks:\"{msg}\". "
                        f"{lang_inst} 2 sentences max. No jargon.")
                resp=gemini_client.generate_content(prompt)
                return jsonify({"reply":resp.text.strip(),"source":"gemini"})
            except Exception as e: print(f"⚠️ Gemini: {e}")
        return jsonify({"reply":off,"source":"offline"})
    except Exception as e:
        print(f"❌ /chat: {e}")
        return jsonify({"reply":"Sorry, error occurred.","source":"error"}),500

@app.route("/status")
def status():
    return jsonify({"gemini_ready":bool(gemini_client),
                    "models_loaded":list(models.keys()),
                    "esp32_connected":bool(esp32_data),
                    "crops":list(CROP_CONFIG.keys())})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
