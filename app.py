import os,json,pickle
import math
from pathlib import Path
from datetime import datetime
from collections import deque
import requests
from flask import Flask,request,jsonify,render_template
np=pd=None
try:
    import numpy as np
    import pandas as pd
except Exception as e: print(f"numpy/pandas: {e}")
app=Flask(__name__)
GEMINI_API_KEY=os.environ.get("GEMINI_API_KEY","")
WEATHER_API_KEY=os.environ.get("WEATHER_API_KEY","")
WEATHER_CITY=os.environ.get("WEATHER_CITY","Tiruchirappalli")
gemini_model=None
try:
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model=genai.GenerativeModel("gemini-1.5-flash")
        print("Gemini ready")
except Exception as e: print(f"Gemini: {e}")
models={}
try:
    for f in Path("models").glob("*.pkl"):
        with open(f,"rb") as fh: models[f.stem]=pickle.load(fh)
except Exception as e: print(f"Models: {e}")
CROPS={"rice":{"stages":["germination","tillering","flowering","harvest"],"moist_min":60,"moist_opt":75,"tds_max":800},"maize":{"stages":["germination","vegetative","tasseling","harvest"],"moist_min":50,"moist_opt":70,"tds_max":700},"groundnut":{"stages":["germination","vegetative","flowering","harvest"],"moist_min":45,"moist_opt":65,"tds_max":600},"sugarcane":{"stages":["germination","tillering","grand_growth","harvest"],"moist_min":65,"moist_opt":80,"tds_max":900},"coconut":{"stages":["seedling","vegetative","flowering","harvest"],"moist_min":50,"moist_opt":70,"tds_max":750}}
CRITICAL_STAGES=["flowering","tasseling","grand_growth"]
esp32_data={}
hist={k:deque(maxlen=20) for k in ["soil_moisture","tds_ppm","air_temp_c","mq135_ammonia"]}
def get_weather():
    try:
        if not WEATHER_API_KEY:
            return {"enabled":False,"temp":None,"humidity":None,"rain":None,"wind":None,"city":WEATHER_CITY,"error":"Weather API is not configured"}
        r=requests.get("https://api.openweathermap.org/data/2.5/weather",params={"q":WEATHER_CITY,"appid":WEATHER_API_KEY,"units":"metric"},timeout=8)
        r.raise_for_status()
        d=r.json()
        return {"enabled":True,"temp":round(d["main"]["temp"],1),"humidity":d["main"]["humidity"],"rain":d.get("rain",{}).get("1h",0),"wind":round(d["wind"]["speed"],1),"city":WEATHER_CITY}
    except Exception as e:
        app.logger.warning("Weather request failed: %s", e)
        return {"enabled":False,"temp":None,"humidity":None,"rain":None,"wind":None,"city":WEATHER_CITY,"error":"Weather data is unavailable"}
def get_forecast():
    try:
        if not WEATHER_API_KEY:
            return {"enabled":False,"next24h":[],"rain_coming":False,"heat_coming":False,"total_rain_mm":0,"max_temp":None,"summary":"Weather data unavailable"}
        r=requests.get("https://api.openweathermap.org/data/2.5/forecast",params={"q":WEATHER_CITY,"appid":WEATHER_API_KEY,"units":"metric","cnt":8},timeout=8)
        r.raise_for_status()
        d=r.json()
        slots=[{"time":i["dt_txt"][11:16],"temp":round(i["main"]["temp"],1),"humidity":i["main"]["humidity"],"rain":round(i.get("rain",{}).get("3h",0),1),"desc":i["weather"][0]["main"]} for i in d.get("list",[])[:8]]
        rc=any(s["rain"]>1 for s in slots); hc=any(s["temp"]>36 for s in slots)
        mt=max((s["temp"] for s in slots),default=30); tr=round(sum(s["rain"] for s in slots),1)
        sm=("Heavy rain "+str(tr)+"mm - skip irrigation" if rc and tr>5 else "Light rain expected - reduce irrigation" if rc else "Heat "+str(mt)+"C ahead - irrigate early morning" if hc else "Stable weather next 24h")
        return {"enabled":True,"next24h":slots,"rain_coming":rc,"heat_coming":hc,"total_rain_mm":tr,"max_temp":mt,"summary":sm}
    except Exception as e:
        app.logger.warning("Forecast request failed: %s", e)
        return {"enabled":False,"next24h":[],"rain_coming":False,"heat_coming":False,"total_rain_mm":0,"max_temp":None,"summary":"Weather data unavailable"}
def predict(crop,stage,sensors,w):
    cfg=CROPS.get(crop,CROPS["rice"])
    sd={k:float(sensors.get(k,v)) for k,v in [("soil_moisture",72),("tds_ppm",350),("air_temp_c",28),("soil_temp_c",24),("humidity_pct",65),("mq135_ammonia",50),("mq4_methane",200),("mq7_co",10)]}
    for k in ["soil_moisture","tds_ppm","air_temp_c","mq135_ammonia"]: hist[k].append(sd[k])
    score=100
    if sd["soil_moisture"]<cfg["moist_min"]: score-=min(40,(cfg["moist_min"]-sd["soil_moisture"])*1.2)
    elif sd["soil_moisture"]>90: score-=15
    tds_safe=sd["tds_ppm"]<=cfg["tds_max"]
    if not tds_safe: score-=min(30,(sd["tds_ppm"]-cfg["tds_max"])/30)
    if sd["air_temp_c"]>38: score-=min(25,(sd["air_temp_c"]-38)*3)
    elif sd["air_temp_c"]<15: score-=20
    gas=(sd["mq135_ammonia"]>200 or sd["mq4_methane"]>1000 or sd["mq7_co"]>100)
    if gas: score-=30
    if sd["humidity_pct"]>90: score-=10
    elif sd["humidity_pct"]<30: score-=15
    score=max(0,min(100,round(score)))
    hs=("GOOD" if score>=75 else "MODERATE" if score>=50 else "POOR" if score>=25 else "CRITICAL")
    pump_locked=gas or hs=="CRITICAL" or not tds_safe
    irrigate=sd["soil_moisture"]<cfg["moist_min"] and not pump_locked
    pump_on=irrigate and not pump_locked
    fc=get_forecast()
    if w.get("enabled") and (w.get("rain") or 0)>2 and pump_on: pump_on=False; irrigate=False
    if fc.get("enabled") and fc.get("rain_coming") and fc.get("total_rain_mm",0)>5 and pump_on: pump_on=False; irrigate=False
    if fc.get("heat_coming") and sd["soil_moisture"]<(cfg["moist_opt"]-5) and not pump_locked: irrigate=True; pump_on=True
    hm=list(hist["soil_moisture"])
    trend=("rising" if len(hm)>=3 and hm[-1]>hm[-3]+2 else "falling" if len(hm)>=3 and hm[-1]<hm[-3]-2 else "stable")
    aqi=max(0,100-(20 if sd["mq135_ammonia"]>100 else 0)-(25 if sd["mq4_methane"]>500 else 0)-(20 if sd["mq7_co"]>35 else 0))
    return {"health_score":score,"health_status":hs,"irrigate_now":bool(irrigate),"pump_on":bool(pump_on),"pump_locked":bool(pump_locked),"gas_alert":bool(gas),"tds_safe":bool(tds_safe),"trend_moisture":trend,"field_aqi":aqi,"field_aqi_label":("Excellent" if aqi>80 else "Good" if aqi>60 else "Moderate" if aqi>40 else "Poor"),"confidence_pct":min(99,max(70,score+(5 if crop in models else -5))),"is_critical_stage":stage in CRITICAL_STAGES,"weather_note":fc.get("summary","Stable weather next 24h"),"sensors_used":sd}
def chat_reply(msg,result,sd,crop,cfg,lang):
    ml=msg.lower(); is_ta=(lang=="ta")
    mst=round(sd.get("soil_moisture",0)); tds=round(sd.get("tds_ppm",0)); tmp=round(sd.get("air_temp_c",0),1)
    hs=result["health_status"]; sc=result["health_score"]
    cta={"rice":"நெல்","maize":"மக்காச்சோளம்","groundnut":"நிலக்கடலை","sugarcane":"கரும்பு","coconut":"தேங்காய்"}.get(crop,crop)
    hta={"GOOD":"நல்லது","MODERATE":"நடுத்தரம்","POOR":"மோசம்","CRITICAL":"அவசரம்"}.get(hs,hs)
    if any(w in ml for w in ["water safe","water quality","tds","saline","salt","நீர் தரம்","உப்பு"]):
        if not result["tds_safe"]:
            return (f"நீர் தரம் பாதுகாப்பற்றது. TDS {tds}ppm — {cta}க்கு அனுமதிக்கப்பட்ட {cfg['tds_max']}ppm ஐ தாண்டியது. பம்ப் தடுக்கப்பட்டுள்ளது." if is_ta else f"Water UNSAFE. TDS {tds}ppm exceeds {cfg['tds_max']}ppm limit for {crop}. Pump locked.")
        return (f"நீர் தரம் பாதுகாப்பானது. TDS {tds}ppm." if is_ta else f"Water safe. TDS {tds}ppm within {cfg['tds_max']}ppm limit.")
    if any(w in ml for w in ["irrigat","pump","water","பாசன","நீர்","பம்ப்"]):
        if result["pump_locked"] and not result["tds_safe"]:
            return (f"பம்ப் தடுக்கப்பட்டுள்ளது — TDS {tds}ppm அதிகம். சுத்தமான நீர் பயன்படுத்துங்கள்." if is_ta else f"Pump LOCKED — TDS {tds}ppm too high. Use fresh water.")
        if result["gas_alert"]:
            return ("வாயு எச்சரிக்கை! நீர் பாய்ச்சாதீர்கள்." if is_ta else "Gas alert! Do NOT irrigate.")
        if result["irrigate_now"]:
            return (f"இப்போது நீர் பாய்ச்சுங்கள்! ஈரப்பதம் {mst}% — {cta}க்கு {cfg['moist_min']}% தேவை." if is_ta else f"Irrigate now! Moisture {mst}% below {cfg['moist_min']}% for {crop}.")
        return (f"நீர்ப்பாசனம் தேவையில்லை. ஈரப்பதம் {mst}% போதுமானது." if is_ta else f"No irrigation needed. Moisture {mst}% adequate.")
    if any(w in ml for w in ["gas","ammonia","methane","air quality","air safe","aqi","is air","காற்று","வாயு","காற்று தரம்"]):
        if result["gas_alert"]: return (f"வாயு எச்சரிக்கை! NH3:{round(sd.get('mq135_ammonia',0))}ppm. வெளியேறுங்கள்!" if is_ta else f"Gas alert! NH3:{round(sd.get('mq135_ammonia',0))}ppm. Evacuate!")
        return ("காற்று தரம் நல்லது." if is_ta else "Air quality safe.")
    if any(w in ml for w in ["health","score","ஆரோக்கிய"]):
        return (f"{cta} ஆரோக்கியம்: {sc}/100 ({hta}). ஈரப்பதம்:{mst}%." if is_ta else f"{crop} health: {sc}/100 ({hs}). Moisture:{mst}%.")
    irr=("நீர் பாய்ச்சுங்கள்! " if result["irrigate_now"] else ""); gas_t=("வாயு எச்சரிக்கை!" if result["gas_alert"] else "நல்லது.")
    irr_e=("Irrigate now! " if result["irrigate_now"] else ""); gas_e=("Gas alert!" if result["gas_alert"] else "All clear.")
    return (f"{cta}: {sc}/100({hta}). {irr}{gas_t}" if is_ta else f"{crop}: {sc}/100({hs}). {irr_e}{gas_e}")
@app.route("/healthz")
def healthz(): return "ok",200
@app.route("/")
def index(): return render_template("index.html")
@app.route("/crops")
def crops_r(): return jsonify(CROPS)
@app.route("/predict",methods=["POST"])
def predict_r():
    try:
        d=request.json or {}; w=get_weather(); s=dict(d.get("sensors",{}))
        if esp32_data and d.get("mode","live") != "sim": s.update(esp32_data)  # sim fix
        return jsonify(predict(d.get("crop","rice"),d.get("stage","germination"),s,w))
    except Exception as e: return jsonify({"error":str(e)}),500
@app.route("/weather")
def weather_r(): return jsonify(get_weather())
@app.route("/forecast")
def forecast_r(): return jsonify(get_forecast())

# ── SSE push for instant ESP32→browser ───────────────────────
from flask import Response
from queue import Queue, Empty
import threading as _th
_sse_q    = []
_sse_lock = _th.Lock()

@app.route("/stream")
def stream_r():
    def gen():
        q = Queue(maxsize=5)
        with _sse_lock: _sse_q.append(q)
        try:
            while True:
                try:    yield f"data: {q.get(timeout=20)}\n\n"
                except Empty: yield "data: {}\n\n"
        finally:
            with _sse_lock:
                if q in _sse_q: _sse_q.remove(q)
    return Response(gen(), mimetype="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.route("/esp32",methods=["POST"])
@app.route("/data",methods=["POST"])
def esp32_r():
    global esp32_data
    import json as _j
    raw=request.json or {}
    candidate=raw.get("sensors",raw) if isinstance(raw,dict) else raw
    if not isinstance(candidate, dict):
        return jsonify({"error":"Sensor payload must be a JSON object"}),400
    sensor_ranges={
        "soil_moisture":(0,100),"tds_ppm":(0,10000),"air_temp_c":(-50,80),
        "soil_temp_c":(-50,80),"humidity_pct":(0,100),"mq135_ammonia":(0,100000),
        "mq4_methane":(0,100000),"mq7_co":(0,100000)
    }
    for key,value in candidate.items():
        if key not in sensor_ranges:
            continue
        if isinstance(value,bool):
            return jsonify({"error":f"{key} must be numeric"}),400
        try:
            number=float(value)
        except (TypeError,ValueError):
            return jsonify({"error":f"{key} must be numeric"}),400
        low,high=sensor_ranges[key]
        if not math.isfinite(number) or not low <= number <= high:
            return jsonify({"error":f"{key} is outside the allowed range"}),400
    esp32_data=candidate
    payload = _j.dumps(esp32_data)
    with _sse_lock:
        dead=[]
        for q in _sse_q:
            try: q.put_nowait(payload)
            except: dead.append(q)
        for q in dead: _sse_q.remove(q)
    return jsonify({"status":"ok"})
@app.route("/live")
def live_r(): return jsonify(esp32_data if esp32_data else {"status":"no_data"})
@app.route("/chat",methods=["POST"])
def chat_r():
    try:
        d=request.json or {}; msg=d.get("message","").strip(); crop=d.get("crop","rice"); stg=d.get("stage","germination"); lang=d.get("lang","ta")
        s=dict(d.get("sensors",{}))
        if esp32_data: s.update(esp32_data)
        res=predict(crop,stg,s,get_weather()); sd=res.get("sensors_used",{}); cfg=CROPS.get(crop,CROPS["rice"])
        off=chat_reply(msg,res,sd,crop,cfg,lang)
        if gemini_model:
            try:
                li=("Reply ONLY in Tamil." if lang=="ta" else "Reply in simple English.")
                prompt=(f"EcoSense AI Crop:{crop} Stage:{stg} Moisture:{sd.get('soil_moisture',0):.0f}% TDS:{sd.get('tds_ppm',0):.0f}ppm(max:{cfg['tds_max']}) AirTemp:{sd.get('air_temp_c',0):.1f}C Humidity:{sd.get('humidity_pct',0):.0f}% NH3:{sd.get('mq135_ammonia',0):.0f}ppm CH4:{sd.get('mq4_methane',0):.0f}ppm CO:{sd.get('mq7_co',0):.0f}ppm GasAlert:{res['gas_alert']} PumpLocked:{res['pump_locked']} TDSSafe:{res['tds_safe']} Health:{res['health_score']}/100 Status:{res['health_status']}. Q:{msg}. {li} 2 sentences max.")
                r=gemini_model.generate_content(prompt)
                return jsonify({"reply":r.text.strip(),"source":"gemini"})
            except Exception as e: print(f"Gemini: {e}")
        return jsonify({"reply":off,"source":"offline"})
    except Exception as e: return jsonify({"reply":"Error.","source":"error"}),500
@app.route("/status")
def status_r(): return jsonify({"gemini_ready":bool(gemini_model),"models":list(models.keys()),"esp32":bool(esp32_data)})
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
