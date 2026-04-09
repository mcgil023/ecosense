import os, json
from pathlib import Path
from datetime import datetime
from collections import deque
import requests
from flask import Flask, request, jsonify, render_template
import numpy as np
import pandas as pd

# ── Gemini ─────────────────────────────────────────────────────
try:
    from google import genai as ggenai
    GENAI_OK = True
except ImportError:
    GENAI_OK = False

GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
WEATHER_CITY    = os.environ.get("WEATHER_CITY", "Tiruchirappalli")

app = Flask(__name__)

# ── Gemini client ───────────────────────────────────────────────
gemini_client = None
if GENAI_OK and GEMINI_API_KEY:
    try:
        gemini_client = ggenai.Client(api_key=GEMINI_API_KEY)
        print("✅ Gemini (google-genai) ready — gemini-2.0-flash")
    except Exception as e:
        print(f"❌ Gemini init failed: {e}")
else:
    print("⚠️  No GEMINI_API_KEY set — offline mode")

# ── ML Models ───────────────────────────────────────────────────
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

# ── Crop config ─────────────────────────────────────────────────
CROP_CONFIG = {
    "rice":      {"stages": ["germination","tillering","flowering","harvest"],      "moist_min": 60, "moist_opt": 75, "tds_max": 800},
    "maize":     {"stages": ["germination","vegetative","tasseling","harvest"],     "moist_min": 50, "moist_opt": 70, "tds_max": 700},
    "groundnut": {"stages": ["germination","vegetative","flowering","harvest"],     "moist_min": 45, "moist_opt": 65, "tds_max": 600},
    "sugarcane": {"stages": ["germination","tillering","grand_growth","harvest"],   "moist_min": 65, "moist_opt": 80, "tds_max": 900},
    "coconut":   {"stages": ["seedling","vegetative","flowering","harvest"],        "moist_min": 50, "moist_opt": 70, "tds_max": 750},
}

# ── State ───────────────────────────────────────────────────────
esp32_data = {}
history = {k: deque(maxlen=20) for k in ["soil_moisture","tds_ppm","air_temp_c","mq135_ammonia"]}

# ── Weather ─────────────────────────────────────────────────────
_weather_cache = {}
def get_weather():
    global _weather_cache
    if _weather_cache.get("ts") and (datetime.now() - _weather_cache["ts"]).seconds < 600:
        return _weather_cache
    if not WEATHER_API_KEY:
        return {"enabled": False, "temp": 30, "humidity": 60, "rain": 0, "wind": 2, "city": WEATHER_CITY}
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": WEATHER_CITY, "appid": WEATHER_API_KEY, "units": "metric"},
            timeout=8
        )
        d = r.json()
        _weather_cache = {
            "enabled":  True,
            "temp":     round(d["main"]["temp"], 1),
            "humidity": d["main"]["humidity"],
            "rain":     d.get("rain", {}).get("1h", 0),
            "wind":     round(d["wind"]["speed"], 1),
            "city":     WEATHER_CITY,
            "ts":       datetime.now()
        }
        return _weather_cache
    except Exception as e:
        print(f"⚠️  Weather API error: {e}")
        return {"enabled": False, "temp": 30, "humidity": 60, "rain": 0, "wind": 2, "city": WEATHER_CITY}

# ── Predict ─────────────────────────────────────────────────────
CRITICAL_STAGES = ["flowering", "tasseling", "grand_growth"]

def predict(crop, stage, sensors, weather):
    cfg = CROP_CONFIG.get(crop, CROP_CONFIG["rice"])
    sc  = {"moist_min": cfg["moist_min"], "moist_opt": cfg["moist_opt"]}

    sd = {
        "soil_moisture": float(sensors.get("soil_moisture", 72)),
        "tds_ppm":       float(sensors.get("tds_ppm", 350)),
        "air_temp_c":    float(sensors.get("air_temp_c", 28)),
        "soil_temp_c":   float(sensors.get("soil_temp_c", 24)),
        "humidity_pct":  float(sensors.get("humidity_pct", 65)),
        "mq135_ammonia": float(sensors.get("mq135_ammonia", 50)),
        "mq4_methane":   float(sensors.get("mq4_methane", 200)),
        "mq7_co":        float(sensors.get("mq7_co", 10)),
    }

    # Auto-fill temp/humidity from live weather if not from ESP32
    if not sensors.get("air_temp_c") and weather.get("enabled"):
        sd["air_temp_c"]   = float(weather.get("temp", 28))
        sd["humidity_pct"] = float(weather.get("humidity", 65))

    for k in ["soil_moisture","tds_ppm","air_temp_c","mq135_ammonia"]:
        history[k].append(sd[k])

    score = 100
    if sd["soil_moisture"] < sc["moist_min"]:
        score -= min(40, (sc["moist_min"] - sd["soil_moisture"]) * 1.2)
    elif sd["soil_moisture"] > 90:
        score -= 15

    tds_safe = sd["tds_ppm"] <= cfg["tds_max"]
    if not tds_safe:
        score -= min(30, (sd["tds_ppm"] - cfg["tds_max"]) / 30)

    if sd["air_temp_c"] > 38:
        score -= min(25, (sd["air_temp_c"] - 38) * 3)
    elif sd["air_temp_c"] < 15:
        score -= 20

    gas_alert = (sd["mq135_ammonia"] > 200 or sd["mq4_methane"] > 1000 or sd["mq7_co"] > 100)
    if gas_alert:
        score -= 30

    if sd["humidity_pct"] > 90:
        score -= 10
    elif sd["humidity_pct"] < 30:
        score -= 15

    # Weather penalty
    rain = weather.get("rain", 0) if isinstance(weather.get("rain"), (int, float)) else 0
    if rain > 20:
        score -= 10

    score = max(0, min(100, round(score)))
    if   score >= 75: hs = "GOOD"
    elif score >= 50: hs = "MODERATE"
    elif score >= 25: hs = "POOR"
    else:             hs = "CRITICAL"

    if crop in models:
        try:
            feat_names = ["soil_moisture","tds_ppm","air_temp_c","soil_temp_c",
                          "humidity_pct","mq135_ammonia","mq4_methane","mq7_co",
                          "moist_min_threshold","moist_opt_threshold","tds_max_threshold"]
            row = pd.DataFrame([[
                sd["soil_moisture"], sd["tds_ppm"], sd["air_temp_c"], sd["soil_temp_c"],
                sd["humidity_pct"], sd["mq135_ammonia"], sd["mq4_methane"], sd["mq7_co"],
                sc["moist_min"], sc["moist_opt"], cfg["tds_max"]
            ]], columns=feat_names)
            pred  = models[crop].predict(row)[0]
            proba = models[crop].predict_proba(row)[0]
            score = round(max(proba) * 100)
            hs    = str(pred)
        except Exception as e:
            print(f"⚠️  ML predict failed: {e} — rule-based used")

    irrigate_now = sd["soil_moisture"] < sc["moist_min"] and not gas_alert
    pump_locked  = gas_alert or hs == "CRITICAL"
    pump_on      = irrigate_now and not pump_locked

    hist_m = list(history["soil_moisture"])
    if len(hist_m) >= 3:
        trend = "rising" if hist_m[-1] > hist_m[-3] + 2 else "falling" if hist_m[-1] < hist_m[-3] - 2 else "stable"
    else:
        trend = "stable"

    aqi = 100
    if sd["mq135_ammonia"] > 100: aqi -= 20
    if sd["mq4_methane"]   > 500: aqi -= 25
    if sd["mq7_co"]        > 35:  aqi -= 20
    aqi     = max(0, aqi)
    aqi_lbl = "Excellent" if aqi > 80 else "Good" if aqi > 60 else "Moderate" if aqi > 40 else "Poor"
    conf    = min(99, max(70, score + (5 if crop in models else -5)))

    return {
        "health_score":      score,
        "health_status":     hs,
        "irrigate_now":      bool(irrigate_now),
        "pump_on":           bool(pump_on),
        "pump_locked":       bool(pump_locked),
        "gas_alert":         bool(gas_alert),
        "tds_safe":          bool(tds_safe),
        "trend_moisture":    trend,
        "field_aqi":         aqi,
        "field_aqi_label":   aqi_lbl,
        "confidence_pct":    conf,
        "is_critical_stage": stage in CRITICAL_STAGES,
        "sensors_used":      sd,
        "weather":           {"temp": weather.get("temp"), "humidity": weather.get("humidity"),
                               "rain": weather.get("rain"), "wind": weather.get("wind")}
    }

# ── Routes ──────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/crops")
def crops():
    return jsonify(CROP_CONFIG)

@app.route("/predict", methods=["POST"])
def predict_route():
    try:
        d       = request.json or {}
        weather = get_weather()
        sensors = dict(d.get("sensors", {}))
        if esp32_data:
            sensors.update(esp32_data)
        result  = predict(d.get("crop","rice"), d.get("stage","germination"), sensors, weather)
        return jsonify(result)
    except Exception as e:
        print(f"❌ /predict error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/weather")
def weather_route():
    return jsonify(get_weather())

@app.route("/esp32", methods=["POST"])
@app.route("/data",  methods=["POST"])
def receive_esp32():
    global esp32_data
    raw        = request.json or {}
    esp32_data = raw.get("sensors", raw)
    print(f"📡 ESP32 data received: {list(esp32_data.keys())}")
    return jsonify({"status": "ok", "received": list(esp32_data.keys())})

@app.route("/live")
def live():
    return jsonify(esp32_data if esp32_data else {"status": "no_data"})

@app.route("/chat", methods=["POST"])
def chat():
    try:
        d       = request.json or {}
        msg     = d.get("message","").strip()
        crop    = d.get("crop","rice")
        stage   = d.get("stage","germination")
        sensors = dict(d.get("sensors", {}))
        if esp32_data:
            sensors.update(esp32_data)
        weather = get_weather()
        result  = predict(crop, stage, sensors, weather)
        sd      = result["sensors_used"]

        tips    = {
            "GOOD":     "Crop looks healthy. Keep monitoring.",
            "MODERATE": "Crop needs attention. Check moisture.",
            "POOR":     "Crop is struggling. Take action soon.",
            "CRITICAL": "Urgent! Crop is in critical condition."
        }
        offline = (f"{tips.get(result['health_status'],'')} "
                   f"Moisture: {sd.get('soil_moisture',0):.0f}%. "
                   f"{'Irrigate now.' if result['irrigate_now'] else ''} "
                   f"{'Gas danger!' if result['gas_alert'] else ''}").strip()

        if gemini_client:
            try:
                w = weather
                prompt = (
                    f"You are EcoSense, a smart farming assistant. "
                    f"Crop: {crop}, Stage: {stage}. "
                    f"Moisture: {sd.get('soil_moisture',0):.0f}%, TDS: {sd.get('tds_ppm',0):.0f}ppm, "
                    f"Air Temp: {sd.get('air_temp_c',0):.1f}C, Humidity: {sd.get('humidity_pct',0):.0f}%. "
                    f"Weather: {w.get('temp','?')}C, Rain: {w.get('rain',0)}mm, Wind: {w.get('wind','?')}m/s. "
                    f"Health: {result['health_status']} ({result['health_score']}/100). "
                    f"Irrigate: {result['irrigate_now']}, Gas alert: {result['gas_alert']}. "
                    f"Farmer asks: {msg}. "
                    f"Reply in 1-2 short simple sentences. Be direct."
                )
                resp = gemini_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                return jsonify({"reply": resp.text.strip(), "source": "gemini"})
            except Exception as e:
                print(f"⚠️  Gemini error: {e}")

        return jsonify({"reply": offline, "source": "offline"})
    except Exception as e:
        print(f"❌ /chat error: {e}")
        return jsonify({"reply": "Sorry, an error occurred.", "source": "error"}), 500

@app.route("/status")
def status():
    return jsonify({
        "gemini_ready":    bool(gemini_client),
        "models_loaded":   list(models.keys()),
        "esp32_connected": bool(esp32_data),
        "crops":           list(CROP_CONFIG.keys())
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
