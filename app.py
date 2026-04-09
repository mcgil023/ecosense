import os, json, pickle, threading
from pathlib import Path
from datetime import datetime
from collections import deque
from queue import Queue, Empty
from flask import Flask, request, jsonify, render_template, Response
import requests

# ── Heavy imports — wrapped so startup never crashes ──────────
np = pd = None
try:
    import numpy as np
    import pandas as pd
except Exception as e:
    print(f"⚠️ numpy/pandas not available: {e}")

app = Flask(__name__)

# ── SSE ───────────────────────────────────────────────────────
_sse_clients = []
_sse_lock    = threading.Lock()

# ── Config ────────────────────────────────────────────────────
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY",  "")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
WEATHER_CITY    = os.environ.get("WEATHER_CITY",    "Tiruchirappalli")

# ── Gemini ────────────────────────────────────────────────────
gemini_client = None
try:
    if GEMINI_API_KEY:
        from google import genai as _genai
        _gc = _genai.Client(api_key=GEMINI_API_KEY)
        class _W:
            def __init__(self,c): self._c=c
            def generate_content(self,prompt):
                r = self._c.models.generate_content(model="gemini-2.0-flash",contents=prompt)
                class _R:
                    def __init__(self,t): self.text=t
                return _R(r.text)
        gemini_client = _W(_gc)
        print("✅ Gemini ready")
except Exception as e:
    print(f"⚠️ Gemini unavailable: {e}")

# ── ML Models ─────────────────────────────────────────────────
models = {}
try:
    for f in Path("models").glob("*.pkl"):
        with open(f,"rb") as fh:
            models[f.stem] = pickle.load(fh)
        print(f"✅ Model: {f.stem}")
except Exception as e:
    print(f"⚠️ Model load: {e}")

# ── Crop Config ───────────────────────────────────────────────
CROP_CONFIG = {
    "rice":      {"stages":["germination","tillering","flowering","harvest"],    "moist_min":60,"moist_opt":75,"tds_max":800},
    "maize":     {"stages":["germination","vegetative","tasseling","harvest"],   "moist_min":50,"moist_opt":70,"tds_max":700},
    "groundnut": {"stages":["germination","vegetative","flowering","harvest"],   "moist_min":45,"moist_opt":65,"tds_max":600},
    "sugarcane": {"stages":["germination","tillering","grand_growth","harvest"], "moist_min":65,"moist_opt":80,"tds_max":900},
    "coconut":   {"stages":["seedling","vegetative","flowering","harvest"],      "moist_min":50,"moist_opt":70,"tds_max":750},
}
CRITICAL_STAGES = ["flowering","tasseling","grand_growth"]

esp32_data = {}
history    = {k: deque(maxlen=20) for k in
              ["soil_moisture","tds_ppm","air_temp_c","mq135_ammonia"]}

# ── Weather ───────────────────────────────────────────────────
_weather_cache = {}
def get_weather():
    global _weather_cache
    try:
        if _weather_cache.get("ts") and            (datetime.now()-_weather_cache["ts"]).seconds < 600:
            return _weather_cache
        if not WEATHER_API_KEY:
            return {"enabled":False,"temp":30,"humidity":60,
                    "rain":0,"wind":2,"city":WEATHER_CITY}
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q":WEATHER_CITY,"appid":WEATHER_API_KEY,"units":"metric"},
            timeout=8)
        d = r.json()
        _weather_cache = {
            "enabled":True,"temp":round(d["main"]["temp"],1),
            "humidity":d["main"]["humidity"],
            "rain":d.get("rain",{}).get("1h",0),
            "wind":round(d["wind"]["speed"],1),
            "city":WEATHER_CITY,"ts":datetime.now()}
        return _weather_cache
    except:
        return {"enabled":False,"temp":30,"humidity":60,
                "rain":0,"wind":2,"city":WEATHER_CITY}

# ── Forecast ──────────────────────────────────────────────────
_forecast_cache = {}
def get_forecast():
    global _forecast_cache
    try:
        if _forecast_cache.get("ts") and            (datetime.now()-_forecast_cache["ts"]).seconds < 1800:
            return _forecast_cache
        if not WEATHER_API_KEY:
            return {"enabled":False,"next24h":[],"rain_coming":False,
                    "heat_coming":False,"total_rain_mm":0,"max_temp":30,
                    "summary":"Forecast unavailable"}
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"q":WEATHER_CITY,"appid":WEATHER_API_KEY,
                    "units":"metric","cnt":8},timeout=8)
        d = r.json()
        slots=[]
        for item in d.get("list",[])[:8]:
            slots.append({"time":item["dt_txt"][11:16],
                "temp":round(item["main"]["temp"],1),
                "humidity":item["main"]["humidity"],
                "rain":round(item.get("rain",{}).get("3h",0),1),
                "desc":item["weather"][0]["main"]})
        rc  = any(s["rain"]>1  for s in slots)
        hc  = any(s["temp"]>36 for s in slots)
        mt  = max((s["temp"] for s in slots),default=30)
        tr  = round(sum(s["rain"] for s in slots),1)
        sm  = (f"🌧 Heavy rain {tr}mm — skip irrigation" if rc and tr>5 else
               f"🌦 Light rain expected — reduce irrigation" if rc else
               f"🌡️ Heat {mt}°C ahead — irrigate early morning" if hc else
               "🌤 Stable weather next 24h")
        _forecast_cache = {"enabled":True,"next24h":slots,
            "rain_coming":rc,"heat_coming":hc,"total_rain_mm":tr,
            "max_temp":mt,"summary":sm,"ts":datetime.now()}
        return _forecast_cache
    except Exception as e:
        print(f"⚠️ Forecast: {e}")
        return {"enabled":False,"next24h":[],"rain_coming":False,
                "heat_coming":False,"total_rain_mm":0,"max_temp":30,
                "summary":"Forecast unavailable"}

# ── Predict ───────────────────────────────────────────────────
def predict(crop, stage, sensors, weather):
    try:
        cfg = CROP_CONFIG.get(crop, CROP_CONFIG["rice"])
        sd  = {
            "soil_moisture": float(sensors.get("soil_moisture", 72)),
            "tds_ppm":       float(sensors.get("tds_ppm",       350)),
            "air_temp_c":    float(sensors.get("air_temp_c",    28)),
            "soil_temp_c":   float(sensors.get("soil_temp_c",   24)),
            "humidity_pct":  float(sensors.get("humidity_pct",  65)),
            "mq135_ammonia": float(sensors.get("mq135_ammonia", 50)),
            "mq4_methane":   float(sensors.get("mq4_methane",  200)),
            "mq7_co":        float(sensors.get("mq7_co",        10)),
        }
        for k in ["soil_moisture","tds_ppm","air_temp_c","mq135_ammonia"]:
            history[k].append(sd[k])

        score = 100
        if sd["soil_moisture"] < cfg["moist_min"]:
            score -= min(40,(cfg["moist_min"]-sd["soil_moisture"])*1.2)
        elif sd["soil_moisture"] > 90: score -= 15
        tds_safe = sd["tds_ppm"] <= cfg["tds_max"]
        if not tds_safe:
            score -= min(30,(sd["tds_ppm"]-cfg["tds_max"])/30)
        if sd["air_temp_c"] > 38: score -= min(25,(sd["air_temp_c"]-38)*3)
        elif sd["air_temp_c"] < 15: score -= 20
        gas_alert = (sd["mq135_ammonia"]>200 or
                     sd["mq4_methane"]>1000 or sd["mq7_co"]>100)
        if gas_alert: score -= 30
        if sd["humidity_pct"] > 90: score -= 10
        elif sd["humidity_pct"] < 30: score -= 15
        score = max(0,min(100,round(score)))
        hs = ("GOOD" if score>=75 else "MODERATE" if score>=50
              else "POOR" if score>=25 else "CRITICAL")

        if crop in models and np is not None and pd is not None:
            try:
                feat=["soil_moisture","tds_ppm","air_temp_c","soil_temp_c",
                      "humidity_pct","mq135_ammonia","mq4_methane","mq7_co",
                      "moist_min_threshold","moist_opt_threshold","tds_max_threshold"]
                row=pd.DataFrame([[sd["soil_moisture"],sd["tds_ppm"],
                    sd["air_temp_c"],sd["soil_temp_c"],sd["humidity_pct"],
                    sd["mq135_ammonia"],sd["mq4_methane"],sd["mq7_co"],
                    cfg["moist_min"],cfg["moist_opt"],cfg["tds_max"]]],
                    columns=feat)
                pred  = models[crop].predict(row)[0]
                proba = models[crop].predict_proba(row)[0]
                score = round(max(proba)*100)
                hs    = str(pred)
            except Exception as e:
                print(f"⚠️ ML: {e}")

        irrigate_now = (sd["soil_moisture"]<cfg["moist_min"] and not gas_alert)
        pump_locked  = (gas_alert or hs=="CRITICAL" or not tds_safe)
        pump_on      = irrigate_now and not pump_locked

        fc   = get_forecast()
        w_rain = weather.get("rain",0)
        if w_rain > 2 and pump_on:
            pump_on = False; irrigate_now = False
        if fc.get("rain_coming") and fc.get("total_rain_mm",0)>5 and pump_on:
            pump_on = False; irrigate_now = False
        if fc.get("heat_coming") and sd["soil_moisture"]<(cfg["moist_opt"]-5)            and not pump_locked:
            irrigate_now = True; pump_on = True

        wn = fc.get("summary","")
        if not wn:
            wn = (f"🌧 Rain {w_rain}mm — skipped." if w_rain>2 else
                  f"🌡️ Hot {weather.get('temp',30)}°C." if weather.get('temp',30)>35
                  else "🌤 Weather normal.")

        hm = list(history["soil_moisture"])
        trend = ("rising"  if len(hm)>=3 and hm[-1]>hm[-3]+2 else
                 "falling" if len(hm)>=3 and hm[-1]<hm[-3]-2 else "stable")

        aqi=100
        if sd["mq135_ammonia"]>100: aqi-=20
        if sd["mq4_methane"]>500:   aqi-=25
        if sd["mq7_co"]>35:         aqi-=20
        aqi=max(0,aqi)
        aqi_lbl=("Excellent" if aqi>80 else "Good" if aqi>60
                 else "Moderate" if aqi>40 else "Poor")

        return {"health_score":score,"health_status":hs,
                "irrigate_now":bool(irrigate_now),"pump_on":bool(pump_on),
                "pump_locked":bool(pump_locked),"gas_alert":bool(gas_alert),
                "tds_safe":bool(tds_safe),"trend_moisture":trend,
                "field_aqi":aqi,"field_aqi_label":aqi_lbl,
                "confidence_pct":min(99,max(70,score+(5 if crop in models else -5))),
                "is_critical_stage":stage in CRITICAL_STAGES,
                "weather_note":wn,"sensors_used":sd}
    except Exception as e:
        print(f"❌ predict: {e}")
        return {"health_score":50,"health_status":"MODERATE",
                "irrigate_now":False,"pump_on":False,"pump_locked":False,
                "gas_alert":False,"tds_safe":True,"trend_moisture":"stable",
                "field_aqi":80,"field_aqi_label":"Good","confidence_pct":70,
                "is_critical_stage":False,"weather_note":"","sensors_used":{}}

# ── Tamil offline reply ────────────────────────────────────────
def translate_offline_ta(msg, result, sd, crop, cfg):
    hs  = result.get("health_status","MODERATE")
    mst = round(sd.get("soil_moisture",0))
    tmp = round(sd.get("air_temp_c",0),1)
    tds = round(sd.get("tds_ppm",0))
    cta = {"rice":"நெல்","maize":"மக்காச்சோளம்",
           "groundnut":"நிலக்கடலை","sugarcane":"கரும்பு",
           "coconut":"தேங்காய்"}.get(crop,crop)
    hta = {"GOOD":"நல்லது","MODERATE":"நடுத்தரம்",
           "POOR":"மோசம்","CRITICAL":"அவசரம்"}.get(hs,hs)
    if result.get("irrigate_now"):
        return (f"இப்போது நீர் பாய்ச்சுங்கள்! மண் ஈரப்பதம் {mst}% — "
                f"{cta}க்கு தேவையான அளவை விட குறைவாக உள்ளது.")
    elif result.get("gas_alert"):
        return "வாயு எச்சரிக்கை! வயலில் இருந்து விலகி காற்றோட்டம் செய்யுங்கள்."
    elif not result.get("tds_safe"):
        return (f"பம்ப் தடுக்கப்பட்டுள்ளது — நீரில் TDS அளவு "
                f"அதிகம் ({tds} ppm). சுத்தமான நீர் பயன்படுத்துங்கள்.")
    elif tmp > 38:
        return f"வெப்பம் அதிகமாக உள்ளது ({tmp}°C). பயிரை கவனியுங்கள்."
    else:
        return (f"{cta} ஆரோக்கியம்: {result.get('health_score',50)}/100 "
                f"({hta}). மண் ஈரப்பதம்: {mst}%.")

# ── Routes ────────────────────────────────────────────────────
@app.route("/healthz")
def healthz(): return "ok", 200

@app.route("/")
def index(): return render_template("index.html")

@app.route("/crops")
def crops(): return jsonify(CROP_CONFIG)

@app.route("/predict", methods=["POST"])
def predict_route():
    try:
        d = request.json or {}
        w = get_weather()
        s = dict(d.get("sensors",{}))
        if esp32_data: s.update(esp32_data)
        return jsonify(predict(d.get("crop","rice"),
                               d.get("stage","germination"), s, w))
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/weather")
def weather_route(): return jsonify(get_weather())

@app.route("/forecast")
def forecast_route(): return jsonify(get_forecast())

@app.route("/stream")
def stream():
    def generate():
        q = Queue(maxsize=10)
        with _sse_lock: _sse_clients.append(q)
        try:
            if esp32_data:
                yield f"data: {json.dumps(esp32_data)}\n\n"
            while True:
                try:
                    data = q.get(timeout=25)
                    yield f"data: {json.dumps(data)}\n\n"
                except Empty:
                    yield f"data: {json.dumps({'_ping':True})}\n\n"
        finally:
            with _sse_lock:
                if q in _sse_clients: _sse_clients.remove(q)
    return Response(generate(), mimetype="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.route("/esp32", methods=["POST"])
@app.route("/data",  methods=["POST"])
def receive_esp32():
    global esp32_data
    raw = request.json or {}
    esp32_data = raw.get("sensors", raw)
    with _sse_lock:
        dead=[]
        for q in _sse_clients:
            try: q.put_nowait(esp32_data)
            except: dead.append(q)
        for q in dead: _sse_clients.remove(q)
    return jsonify({"status":"ok"})

@app.route("/live")
def live(): return jsonify(esp32_data if esp32_data else {"status":"no_data"})

@app.route("/chat", methods=["POST"])
def chat():
    try:
        d       = request.json or {}
        msg     = d.get("message","").strip()
        crop    = d.get("crop","rice")
        stage   = d.get("stage","germination")
        lang    = d.get("lang","ta")
        sensors = dict(d.get("sensors",{}))
        if esp32_data: sensors.update(esp32_data)
        result  = predict(crop, stage, sensors, get_weather())
        sd      = result.get("sensors_used",{})
        cfg     = CROP_CONFIG.get(crop, CROP_CONFIG["rice"])
        ml      = msg.lower()

        if any(w in ml for w in ["irrigat","water","pump","நீர்","பாசன"]):
            if result["irrigate_now"]:
                off=f"Yes, irrigate now! Soil moisture {sd.get('soil_moisture',0):.0f}% below minimum {cfg['moist_min']}% for {crop}."
            elif result["gas_alert"]:
                off="Do not irrigate — gas alert active! Ventilate field first."
            elif not result["tds_safe"]:
                off=f"Pump locked — TDS too high ({sd.get('tds_ppm',0):.0f}ppm). Use fresh water."
            else:
                off=f"No irrigation needed. Moisture {sd.get('soil_moisture',0):.0f}% is adequate."
        elif any(w in ml for w in ["gas","ammonia","methane","வாயு","நச்சு"]):
            if result["gas_alert"]:
                off=f"Gas alert! NH3:{sd.get('mq135_ammonia',0):.0f}ppm CH4:{sd.get('mq4_methane',0):.0f}ppm. Keep workers away!"
            else:
                off="Air quality safe. All gas levels normal."
        elif any(w in ml for w in ["tds","saline","salt","quality","உப்பு"]):
            off=(f"TDS {sd.get('tds_ppm',0):.0f}ppm — {'safe' if result['tds_safe'] else 'TOO HIGH! Use fresh water'}.")
        elif any(w in ml for w in ["temp","heat","வெப்ப"]):
            off=f"Air temperature {sd.get('air_temp_c',0):.1f}°C. {'Too hot!' if sd.get('air_temp_c',0)>38 else 'Normal.'}"
        elif any(w in ml for w in ["health","status","score","ஆரோக்கிய"]):
            off=f"{crop} health {result['health_score']}/100 ({result['health_status']}). Moisture:{sd.get('soil_moisture',0):.0f}%"
        elif any(w in ml for w in ["rain","forecast","weather","மழை","வானிலை"]):
            off=result.get("weather_note","Check weather before irrigation.")
        else:
            off=(f"{crop} ({stage}): {result['health_score']}/100 ({result['health_status']}). "
                 f"Moisture:{sd.get('soil_moisture',0):.0f}%. "
                 f"{'Irrigate now! ' if result['irrigate_now'] else ''}"
                 f"{'Gas alert!' if result['gas_alert'] else 'All clear.'}")

        if lang == "ta":
            off = translate_offline_ta(msg, result, sd, crop, cfg)

        if gemini_client:
            try:
                lang_inst = ("Reply in Tamil (தமிழில் மட்டும் பதில் சொல்லுங்கள்)."
                             if lang=="ta" else "Reply in simple English.")
                prompt=(f"EcoSense AI for Indian farmers. Crop:{crop} Stage:{stage}. "
                        f"Moisture:{sd.get('soil_moisture',0):.0f}% TDS:{sd.get('tds_ppm',0):.0f}ppm "
                        f"Temp:{sd.get('air_temp_c',0):.1f}°C NH3:{sd.get('mq135_ammonia',0):.0f}ppm. "
                        f"Health:{result['health_score']}/100 ({result['health_status']}). "
                        f"Irrigate:{result['irrigate_now']} Gas:{result['gas_alert']}. "
                        f"Forecast:{result.get('weather_note','')}. "
                        f"Farmer asks: \"{msg}\". "
                        f"{lang_inst} 2 sentences max. No jargon.")
                resp = gemini_client.generate_content(prompt)
                return jsonify({"reply":resp.text.strip(),"source":"gemini"})
            except Exception as e:
                print(f"⚠️ Gemini: {e}")

        return jsonify({"reply":off.strip(),"source":"offline"})
    except Exception as e:
        print(f"❌ /chat: {e}")
        return jsonify({"reply":"Sorry, something went wrong.","source":"error"}),500

@app.route("/status")
def status():
    return jsonify({"gemini_ready":bool(gemini_client),
                    "models_loaded":list(models.keys()),
                    "esp32_connected":bool(esp32_data),
                    "crops":list(CROP_CONFIG.keys())})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
