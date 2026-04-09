import os, json
from pathlib import Path
from datetime import datetime
from collections import deque
import requests
from flask import Flask, request, jsonify, render_template
import numpy as np
import pandas as pd

# ── Gemini ──────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
gemini_client = None

if GEMINI_API_KEY:
    try:
        from google import genai as _genai
        _client = _genai.Client(api_key=GEMINI_API_KEY)
        class _GeminiWrapper:
            def __init__(self, c): self._c = c
            def generate_content(self, prompt):
                r = self._c.models.generate_content(
                    model="gemini-2.0-flash", contents=prompt)
                class _R:
                    def __init__(self, t): self.text = t
                return _R(r.text)
        gemini_client = _GeminiWrapper(_client)
        print("✅ Gemini ready (google-genai)")
    except Exception as e:
        print(f"❌ Gemini init failed: {e}")
else:
    print("⚠️  GEMINI_API_KEY not set — offline mode")

WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
WEATHER_CITY    = os.environ.get("WEATHER_CITY", "Tiruchirappalli")

app = Flask(__name__)

# ── ML Models ────────────────────────────────────────────────────
import pickle
models = {}
model_dir = Path("models")
if model_dir.exists():
    for f in model_dir.glob("*.pkl"):
        try:
            with open(f, "rb") as fh:
                models[f.stem] = pickle.load(fh)
            print(f"✅ Model loaded: {f.stem}")
        except Exception as e:
            print(f"⚠️  Model {f.stem} skipped: {e}")

# ── Crop config ──────────────────────────────────────────────────
CROP_CONFIG = {
    "rice":      {"stages":["germination","tillering","flowering","harvest"],   "moist_min":60,"moist_opt":75,"tds_max":800},
    "maize":     {"stages":["germination","vegetative","tasseling","harvest"],  "moist_min":50,"moist_opt":70,"tds_max":700},
    "groundnut": {"stages":["germination","vegetative","flowering","harvest"],  "moist_min":45,"moist_opt":65,"tds_max":600},
    "sugarcane": {"stages":["germination","tillering","grand_growth","harvest"],"moist_min":65,"moist_opt":80,"tds_max":900},
    "coconut":   {"stages":["seedling","vegetative","flowering","harvest"],     "moist_min":50,"moist_opt":70,"tds_max":750},
}

# ── State ────────────────────────────────────────────────────────
esp32_data = {}
history = {k: deque(maxlen=20) for k in ["soil_moisture","tds_ppm","air_temp_c","mq135_ammonia"]}

# ── Weather ──────────────────────────────────────────────────────
_weather_cache = {}
def get_weather():
    global _weather_cache
    if _weather_cache.get("ts") and (datetime.now()-_weather_cache["ts"]).seconds < 600:
        return _weather_cache
    if not WEATHER_API_KEY:
        return {"enabled":False,"temp":30,"humidity":60,"rain":0,"wind":2,"city":WEATHER_CITY}
    try:
        r = requests.get("https://api.openweathermap.org/data/2.5/weather",
            params={"q":WEATHER_CITY,"appid":WEATHER_API_KEY,"units":"metric"},timeout=8)
        d = r.json()
        _weather_cache = {"enabled":True,"temp":round(d["main"]["temp"],1),
            "humidity":d["main"]["humidity"],"rain":d.get("rain",{}).get("1h",0),
            "wind":round(d["wind"]["speed"],1),"city":WEATHER_CITY,"ts":datetime.now()}
        return _weather_cache
    except:
        return {"enabled":False,"temp":30,"humidity":60,"rain":0,"wind":2,"city":WEATHER_CITY}

# ── Core predict ─────────────────────────────────────────────────
CRITICAL_STAGES = ["flowering","tasseling","grand_growth"]

def predict(crop, stage, sensors, weather):
    cfg = CROP_CONFIG.get(crop, CROP_CONFIG["rice"])
    sc  = {"moist_min":cfg["moist_min"],"moist_opt":cfg["moist_opt"]}
    sd  = {
        "soil_moisture":  float(sensors.get("soil_moisture",72)),
        "tds_ppm":        float(sensors.get("tds_ppm",350)),
        "air_temp_c":     float(sensors.get("air_temp_c",28)),
        "soil_temp_c":    float(sensors.get("soil_temp_c",24)),
        "humidity_pct":   float(sensors.get("humidity_pct",65)),
        "mq135_ammonia":  float(sensors.get("mq135_ammonia",50)),
        "mq4_methane":    float(sensors.get("mq4_methane",200)),
        "mq7_co":         float(sensors.get("mq7_co",10)),
    }
    for k in ["soil_moisture","tds_ppm","air_temp_c","mq135_ammonia"]:
        history[k].append(sd[k])

    score = 100
    if sd["soil_moisture"] < sc["moist_min"]:
        score -= min(40,(sc["moist_min"]-sd["soil_moisture"])*1.2)
    elif sd["soil_moisture"] > 90:
        score -= 15
    tds_safe = sd["tds_ppm"] <= cfg["tds_max"]
    if not tds_safe:
        score -= min(30,(sd["tds_ppm"]-cfg["tds_max"])/30)
    if sd["air_temp_c"] > 38:
        score -= min(25,(sd["air_temp_c"]-38)*3)
    elif sd["air_temp_c"] < 15:
        score -= 20
    gas_alert = (sd["mq135_ammonia"]>200 or sd["mq4_methane"]>1000 or sd["mq7_co"]>100)
    if gas_alert: score -= 30
    if sd["humidity_pct"] > 90: score -= 10
    elif sd["humidity_pct"] < 30: score -= 15
    score = max(0,min(100,round(score)))
    hs = "GOOD" if score>=75 else "MODERATE" if score>=50 else "POOR" if score>=25 else "CRITICAL"

    if crop in models:
        try:
            feat_names = ["soil_moisture","tds_ppm","air_temp_c","soil_temp_c",
                          "humidity_pct","mq135_ammonia","mq4_methane","mq7_co",
                          "moist_min_threshold","moist_opt_threshold","tds_max_threshold"]
            row = pd.DataFrame([[sd["soil_moisture"],sd["tds_ppm"],sd["air_temp_c"],sd["soil_temp_c"],
                                  sd["humidity_pct"],sd["mq135_ammonia"],sd["mq4_methane"],sd["mq7_co"],
                                  sc["moist_min"],sc["moist_opt"],cfg["tds_max"]]], columns=feat_names)
            pred  = models[crop].predict(row)[0]
            proba = models[crop].predict_proba(row)[0]
            score = round(max(proba)*100)
            hs    = str(pred)
        except Exception as e:
            print(f"⚠️  ML predict failed: {e}")

    irrigate_now = sd["soil_moisture"] < sc["moist_min"] and not gas_alert
    pump_locked  = gas_alert or hs == "CRITICAL" or not tds_safe
    pump_on      = irrigate_now and not pump_locked

    # ── Weather + Forecast-Aware Pump Decision ─────────────────
    w_temp      = weather.get("temp",    30)
    w_humidity  = weather.get("humidity", 60)
    w_rain      = weather.get("rain",     0)
    fc          = get_forecast()
    rain_coming = fc.get("rain_coming", False)
    heat_coming = fc.get("heat_coming", False)
    total_rain  = fc.get("total_rain_mm", 0)
    fc_summary  = fc.get("summary", "")

    # Rain currently → skip
    if w_rain > 2 and pump_on:
        pump_on = False; irrigate_now = False

    # Heavy rain forecast in 24h → skip
    if rain_coming and total_rain > 5 and pump_on:
        pump_on = False; irrigate_now = False

    # Heat wave coming → irrigate early even if borderline
    if heat_coming and sd["soil_moisture"] < (sc["moist_opt"] - 5) and not pump_locked:
        irrigate_now = True
        pump_on      = True

    weather_note = fc_summary if fc_summary else (
        f"🌧 Rain {w_rain}mm now — skipped." if w_rain > 2 else
        f"🌡️ Hot {w_temp}°C — HIGH priority." if w_temp > 35 else
        f"💧 Humid {w_humidity}%."             if w_humidity > 80 else
        "🌤 Weather normal."
    )

    hist_m = list(history["soil_moisture"])
    trend  = "stable"
    if len(hist_m) >= 3:
        trend = "rising" if hist_m[-1]>hist_m[-3]+2 else "falling" if hist_m[-1]<hist_m[-3]-2 else "stable"

    aqi = 100
    if sd["mq135_ammonia"] > 100: aqi -= 20
    if sd["mq4_methane"]   > 500: aqi -= 25
    if sd["mq7_co"]        >  35: aqi -= 20
    aqi     = max(0, aqi)
    aqi_lbl = "Excellent" if aqi>80 else "Good" if aqi>60 else "Moderate" if aqi>40 else "Poor"

    return {
        "health_score": score, "health_status": hs,
        "irrigate_now": bool(irrigate_now), "pump_on": bool(pump_on),
        "pump_locked":  bool(pump_locked),  "gas_alert": bool(gas_alert),
        "tds_safe":     bool(tds_safe),     "trend_moisture": trend,
        "field_aqi":    aqi,                "field_aqi_label": aqi_lbl,
        "confidence_pct": min(99,max(70,score+(5 if crop in models else -5))),
        "is_critical_stage": stage in CRITICAL_STAGES,
        "weather_note": weather_note,
        "sensors_used": sd,
    }

# ── Routes ───────────────────────────────────────────────────────
@app.route("/")
def index(): return render_template("index.html")

@app.route("/crops")
def crops(): return jsonify(CROP_CONFIG)

@app.route("/predict", methods=["POST"])
def predict_route():
    try:
        d       = request.json or {}
        sensors = dict(d.get("sensors", {}))
        if esp32_data: sensors.update(esp32_data)
        result  = predict(d.get("crop","rice"), d.get("stage","germination"), sensors, get_weather())
        return jsonify(result)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/weather")
def weather_route(): return jsonify(get_weather())

@app.route("/esp32", methods=["POST"])
@app.route("/data",  methods=["POST"])
def receive_esp32():
    global esp32_data
    raw        = request.json or {}
    esp32_data = raw.get("sensors", raw)
    print(f"📡 ESP32: {esp32_data}")
    return jsonify({"status":"ok","received":list(esp32_data.keys())})

@app.route("/live")
def live():
    return jsonify(esp32_data if esp32_data else {"status":"no_data"})

@app.route("/chat", methods=["POST"])
def chat():
    try:
        d       = request.json or {}
        msg     = d.get("message", "").strip()
        crop    = d.get("crop", "rice")
        stage   = d.get("stage", "germination")
        sensors = dict(d.get("sensors", {}))
        if esp32_data: sensors.update(esp32_data)
        result  = predict(crop, stage, sensors, get_weather())
        sd      = result["sensors_used"]
        cfg     = CROP_CONFIG.get(crop, CROP_CONFIG["rice"])
        msg_l   = msg.lower()

        # ── Smart rule-based offline ────────────────────────────
        if any(w in msg_l for w in ["irrigat","water","pump"]):
            if result["irrigate_now"]:
                offline = (f"Yes, irrigate now. Soil moisture is {sd['soil_moisture']:.0f}% — "
                           f"below the minimum {cfg['moist_min']}% needed for {crop} at {stage} stage.")
            elif result["gas_alert"]:
                offline = "Do not irrigate — gas alert active (NH3/CH4/CO high). Ventilate field first."
            else:
                offline = (f"No irrigation needed. Soil moisture is {sd['soil_moisture']:.0f}%, "
                           f"adequate for {crop} at {stage} stage.")

        elif any(w in msg_l for w in ["gas","ammonia","methane"," co ","toxic","air","smell"]):
            if result["gas_alert"]:
                offline = (f"⚠️ Gas alert! NH3: {sd['mq135_ammonia']:.0f}ppm, "
                           f"CH4: {sd['mq4_methane']:.0f}ppm, CO: {sd['mq7_co']:.0f}ppm. "
                           f"Keep workers away and ventilate immediately.")
            else:
                offline = (f"Air quality safe. NH3: {sd['mq135_ammonia']:.0f}ppm, "
                           f"CH4: {sd['mq4_methane']:.0f}ppm, CO: {sd['mq7_co']:.0f}ppm.")

        elif any(w in msg_l for w in ["tds","saline","salt","quality"]):
            if result["tds_safe"]:
                offline = (f"Water quality is good. TDS: {sd['tds_ppm']:.0f}ppm — "
                           f"within the safe {cfg['tds_max']}ppm limit for {crop}.")
            else:
                offline = (f"⚠️ TDS too high: {sd['tds_ppm']:.0f}ppm (limit: {cfg['tds_max']}ppm). "
                           f"Use filtered or fresh water for irrigation.")

        elif any(w in msg_l for w in ["temp","heat","hot","cold"]):
            t = sd['air_temp_c']
            note = "Too hot — increase irrigation frequency." if t > 38 else ("Too cold — protect seedlings." if t < 15 else "Temperature is normal.")
            offline = f"Air temp: {t:.1f}°C, Soil temp: {sd['soil_temp_c']:.1f}°C. {note}"

        elif any(w in msg_l for w in ["fertiliz","nutrient","npk","urea"]):
            if result["health_status"] in ["GOOD","MODERATE"]:
                offline = (f"Safe to fertilize. Moisture is {sd['soil_moisture']:.0f}% and no gas issues. "
                           f"Use nitrogen-based fertilizer for {crop} at {stage}.")
            else:
                offline = f"Fix health issues first (score: {result['health_score']}/100) before fertilizing."

        elif any(w in msg_l for w in ["health","status","condition","score"]):
            offline = (f"{crop.title()} at {stage}: health {result['health_score']}/100 ({result['health_status']}). "
                       f"Moisture: {sd['soil_moisture']:.0f}%, Temp: {sd['air_temp_c']:.1f}°C, "
                       f"Humidity: {sd['humidity_pct']:.0f}%.")

        elif any(w in msg_l for w in ["harvest","ready","when"]):
            offline = (f"{crop.title()} is at {stage} stage. "
                       f"Monitor until maturity. Health score: {result['health_score']}/100. "
                       f"Maintain moisture above {cfg['moist_min']}%.")
        else:
            offline = (f"{crop.title()} ({stage}) — Health: {result['health_score']}/100 ({result['health_status']}). "
                       f"Moisture: {sd['soil_moisture']:.0f}%, TDS: {sd['tds_ppm']:.0f}ppm, "
                       f"Temp: {sd['air_temp_c']:.1f}°C. "
                       f"{'Irrigate now. ' if result['irrigate_now'] else ''}"
                       f"{'⚠️ Gas alert!' if result['gas_alert'] else 'All systems clear.'}")

        # ── Gemini ──────────────────────────────────────────────
        if gemini_client:
            try:
                prompt = (
                    f"You are EcoSense, a smart farming assistant for Indian farmers. "
                    f"Crop: {crop}, Stage: {stage}. "
                    f"Sensor data — Moisture: {sd['soil_moisture']:.0f}% (min: {cfg['moist_min']}%), "
                    f"TDS: {sd['tds_ppm']:.0f}ppm (max: {cfg['tds_max']}ppm), "
                    f"Air temp: {sd['air_temp_c']:.1f}°C, Soil temp: {sd['soil_temp_c']:.1f}°C, "
                    f"Humidity: {sd['humidity_pct']:.0f}%, "
                    f"NH3: {sd['mq135_ammonia']:.0f}ppm, CH4: {sd['mq4_methane']:.0f}ppm, CO: {sd['mq7_co']:.0f}ppm. "
                    f"Health: {result['health_score']}/100 ({result['health_status']}). "
                    f"Irrigate: {result['irrigate_now']}, Gas alert: {result['gas_alert']}, Water safe: {result['tds_safe']}. "
                    f"Farmer asks: \"{msg}\". "
                    f"Give a very simple, friendly answer in 1-2 short sentences. Use plain farmer-friendly language. No technical jargon. No data dumps. Just clear advice."
                )
                resp = gemini_client.generate_content(prompt)
                return jsonify({"reply": resp.text.strip(), "source": "gemini"})
            except Exception as e:
                print(f"⚠️  Gemini chat error: {e}")

        return jsonify({"reply": offline.strip(), "source": "offline"})
    except Exception as e:
        print(f"❌ /chat error: {e}")
        return jsonify({"reply": "Sorry, an error occurred.", "source": "error"}), 500

@app.route("/forecast")
def forecast_route():
    return jsonify(get_forecast())

@app.route("/status")
def status():
    return jsonify({
        "gemini_ready":   bool(gemini_client),
        "models_loaded":  list(models.keys()),
        "esp32_connected":bool(esp32_data),
        "crops":          list(CROP_CONFIG.keys()),
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
