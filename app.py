import os, json, math, warnings, pickle
from pathlib import Path
from collections import deque
import requests
from flask import Flask, request, jsonify, render_template, Response
from queue import Queue, Empty
import threading as _th

import ai_engine

warnings.filterwarnings("ignore")

np = pd = None
try:
    import numpy as np
except Exception as e:
    print(f"numpy: {e}")

joblib = None
try:
    import joblib
except Exception as e:
    print(f"joblib: {e}")

app = Flask(__name__)

# ── Environment ─────────────────────────────────────────────────
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
WEATHER_CITY = os.environ.get("WEATHER_CITY", "Tiruchirappalli")

# ── Crop configuration (single source of truth) ─────────────────
CROP_CONFIG = {}
try:
    with open("crop_config.json", encoding="utf-8") as f:
        CROP_CONFIG = json.load(f)
except Exception as e:
    print(f"crop_config: {e}")

# Frontend-facing dict: stages as array of names (+ tds_max for reference)
CROPS = {}
for _c, _cfg in CROP_CONFIG.items():
    _stages = _cfg.get("stages", {})
    _stage_list = list(_stages.keys()) if isinstance(_stages, dict) else (_stages or [])
    CROPS[_c] = {"stages": _stage_list, "tds_max": _cfg.get("tds_max")}

# Critical stages derived from config
CRITICAL_STAGES = set()
for _c, _cfg in CROP_CONFIG.items():
    for _st, _sc in _cfg.get("stages", {}).items():
        if isinstance(_sc, dict) and _sc.get("critical"):
            CRITICAL_STAGES.add(_st)
CRITICAL_STAGES = sorted(CRITICAL_STAGES)


def get_crop_cfg(crop, stage):
    """Return flat per-crop+stage thresholds from crop_config.json."""
    crop_cfg = CROP_CONFIG.get(crop) or CROP_CONFIG.get("rice") or {}
    stage_cfg = (crop_cfg.get("stages") or {}).get(stage) or {}
    if not isinstance(stage_cfg, dict):
        stage_cfg = {}
    return {
        "tds_max": crop_cfg.get("tds_max", 800),
        "moist_min": stage_cfg.get("moist_min", 50),
        "moist_opt": stage_cfg.get("moist_opt", 70),
        "critical": stage_cfg.get("critical", False),
    }


# ── ML models (joblib format, project root) ─────────────────────
MODELS = {}
ENCODERS = {}
FEATURE_ORDER = []
try:
    with open("feature_list.json", encoding="utf-8") as f:
        FEATURE_ORDER = json.load(f)
except Exception as e:
    print(f"feature_list: {e}")

if joblib:
    for _name, _fname in [
        ("health_status", "model_health_status.pkl"),
        ("irrigate_now", "model_irrigate_now.pkl"),
        ("pump_lock", "model_pump_lock.pkl"),
        ("gas_alert", "model_gas_alert.pkl"),
    ]:
        try:
            MODELS[_name] = joblib.load(_fname)
            print(f"loaded model: {_fname}")
        except Exception as e:
            print(f"model {_fname}: {e}")
    for _name, _fname in [
        ("crop", "encoder_crop.pkl"),
        ("stage", "encoder_stage.pkl"),
        ("health", "encoder_health.pkl"),
    ]:
        try:
            ENCODERS[_name] = joblib.load(_fname)
            print(f"loaded encoder: {_fname}")
        except Exception as e:
            print(f"encoder {_fname}: {e}")

ML_READY = len(MODELS) == 4 and len(ENCODERS) == 3


def build_feature_vector(crop, stage, sd, cfg):
    """Build the 15-feature row in feature_list.json order."""
    crop_enc = int(ENCODERS["crop"].transform([crop])[0])
    stage_enc = int(ENCODERS["stage"].transform([stage])[0])
    is_crit = 1 if stage in CRITICAL_STAGES else 0
    return [[crop_enc, stage_enc, is_crit,
             float(sd.get("soil_moisture", 0)),
             float(sd.get("tds_ppm", 0)),
             float(sd.get("air_temp_c", 0)),
             float(sd.get("soil_temp_c", 0)),
             float(sd.get("humidity_pct", 0)),
             float(sd.get("mq135_ammonia", 0)),
             float(sd.get("mq4_methane", 0)),
             float(sd.get("mq7_co", 0)),
             float(sd.get("mq2_smoke", 0)),
             float(cfg["moist_min"]),
             float(cfg["moist_opt"]),
             float(cfg["tds_max"])]]


def run_ml(crop, stage, sd, cfg):
    """Run all 4 ML models. Returns dict or None on any failure."""
    if not ML_READY:
        return None
    X = build_feature_vector(crop, stage, sd, cfg)
    health_pred = int(MODELS["health_status"].predict(X)[0])
    health_status = ENCODERS["health"].inverse_transform([health_pred])[0]
    return {
        "health_status": health_status,
        "irrigate_now": bool(int(MODELS["irrigate_now"].predict(X)[0])),
        "pump_locked": bool(int(MODELS["pump_lock"].predict(X)[0])),
        "gas_alert": bool(int(MODELS["gas_alert"].predict(X)[0])),
    }


# ── State & historical sliding windows ──────────────────────────
SENSOR_DEFAULTS = {
    "soil_moisture": 72.0,
    "tds_ppm": 350.0,
    "air_temp_c": 28.0,
    "soil_temp_c": 24.0,
    "humidity_pct": 65.0,
    "mq135_ammonia": 50.0,
    "mq4_methane": 200.0,
    "mq7_co": 10.0,
    "mq2_smoke": 20.0,
}

esp32_data = {}
hist = {k: deque(maxlen=20) for k in ["soil_moisture", "tds_ppm", "air_temp_c", "mq135_ammonia"]}


def trend_from_hist(hm):
    if len(hm) < 3:
        return "stable"
    diff = hm[-1] - hm[-3]
    return "rising" if diff > 2 else "falling" if diff < -2 else "stable"


# ── Weather ─────────────────────────────────────────────────────
def get_weather():
    try:
        if not WEATHER_API_KEY:
            return {"enabled": False, "temp": None, "humidity": None, "rain": None,
                    "wind": None, "city": WEATHER_CITY, "error": "Weather API is not configured"}
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": WEATHER_CITY, "appid": WEATHER_API_KEY, "units": "metric"},
            timeout=8,
        )
        r.raise_for_status()
        d = r.json()
        return {
            "enabled": True,
            "temp": round(d["main"]["temp"], 1),
            "humidity": d["main"]["humidity"],
            "rain": d.get("rain", {}).get("1h", 0),
            "wind": round(d["wind"]["speed"], 1),
            "city": WEATHER_CITY,
        }
    except Exception as e:
        app.logger.warning("Weather request failed: %s", e)
        return {"enabled": False, "temp": None, "humidity": None, "rain": None,
                "wind": None, "city": WEATHER_CITY, "error": "Weather data is unavailable"}


def get_forecast():
    try:
        if not WEATHER_API_KEY:
            return {"enabled": False, "next24h": [], "rain_coming": False, "heat_coming": False,
                    "total_rain_mm": 0, "max_temp": None, "summary": "Weather data unavailable"}
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"q": WEATHER_CITY, "appid": WEATHER_API_KEY, "units": "metric", "cnt": 8},
            timeout=8,
        )
        r.raise_for_status()
        d = r.json()
        slots = [
            {
                "time": i["dt_txt"][11:16],
                "temp": round(i["main"]["temp"], 1),
                "humidity": i["main"]["humidity"],
                "rain": round(i.get("rain", {}).get("3h", 0), 1),
                "desc": i["weather"][0]["main"],
            }
            for i in d.get("list", [])[:8]
        ]
        rc = any(s["rain"] > 1 for s in slots)
        hc = any(s["temp"] > 36 for s in slots)
        mt = max((s["temp"] for s in slots), default=30)
        tr = round(sum(s["rain"] for s in slots), 1)
        sm = (
            f"Heavy rain {tr}mm - skip irrigation" if rc and tr > 5
            else "Light rain expected - reduce irrigation" if rc
            else f"Heat {mt}C ahead - irrigate early morning" if hc
            else "Stable weather next 24h"
        )
        return {"enabled": True, "next24h": slots, "rain_coming": rc, "heat_coming": hc,
                "total_rain_mm": tr, "max_temp": mt, "summary": sm}
    except Exception as e:
        app.logger.warning("Forecast request failed: %s", e)
        return {"enabled": False, "next24h": [], "rain_coming": False, "heat_coming": False,
                "total_rain_mm": 0, "max_temp": None, "summary": "Weather data unavailable"}


# ── Core inference: ML first, rule-based hybrid fallback ────────
def heuristic(crop, stage, sd, cfg):
    """Rule-based scoring (also provides the calibrated health_score number)."""
    score = 100
    if sd["soil_moisture"] < cfg["moist_min"]:
        score -= min(40, (cfg["moist_min"] - sd["soil_moisture"]) * 1.2)
    elif sd["soil_moisture"] > 90:
        score -= 15
    tds_safe = sd["tds_ppm"] <= cfg["tds_max"]
    if not tds_safe:
        score -= min(30, (sd["tds_ppm"] - cfg["tds_max"]) / 30)
    if sd["air_temp_c"] > 38:
        score -= min(25, (sd["air_temp_c"] - 38) * 3)
    elif sd["air_temp_c"] < 15:
        score -= 20
    gas = sd["mq135_ammonia"] > 200 or sd["mq4_methane"] > 1000 or sd["mq7_co"] > 100 or sd.get("mq2_smoke", 0) > 100
    if gas:
        score -= 30
    if sd["humidity_pct"] > 90:
        score -= 10
    elif sd["humidity_pct"] < 30:
        score -= 15
    score = max(0, min(100, round(score)))
    hs = "GOOD" if score >= 75 else "MODERATE" if score >= 50 else "POOR" if score >= 25 else "CRITICAL"
    pump_locked = gas or hs == "CRITICAL" or not tds_safe
    irrigate = sd["soil_moisture"] < cfg["moist_min"] and not pump_locked
    return {"health_status": hs, "irrigate_now": bool(irrigate), "pump_locked": bool(pump_locked),
            "gas_alert": bool(gas), "tds_safe": tds_safe, "health_score": score}


def predict(crop, stage, sensors, w, mode="live"):
    cfg = get_crop_cfg(crop, stage)
    sd = {k: float(sensors.get(k, v)) for k, v in SENSOR_DEFAULTS.items()}
    for k in hist:
        hist[k].append(sd[k])

    # ML inference with rule-based fallback
    ml = None
    try:
        ml = run_ml(crop, stage, sd, cfg)
    except Exception as e:
        app.logger.warning("ML inference failed, using heuristic: %s", e)
    base = ml if ml else heuristic(crop, stage, sd, cfg)

    # Calibrated score & agronomic status
    score = heuristic(crop, stage, sd, cfg)["health_score"]
    health_status = base.get("health_status", "GOOD")
    tds_safe = sd["tds_ppm"] <= cfg["tds_max"]
    is_drought = sd["soil_moisture"] < cfg["moist_min"]
    is_waterlogged = sd["soil_moisture"] > 88

    # Gas alert from ML or direct MQ sensor thresholds
    gas_alert = bool(base.get("gas_alert") or (
        sd["mq135_ammonia"] > 100 or sd["mq4_methane"] > 500 or sd["mq7_co"] > 35 or sd.get("mq2_smoke", 0) > 80
    ))

    # Safety Pump Lock: Must lock if water salinity is high OR hazardous gas is present
    pump_locked = bool(base.get("pump_locked") or not tds_safe or gas_alert)

    # Irrigation need: Crop needs water if ML says irrigate OR soil moisture is in drought
    irrigate_needed = bool((base.get("irrigate_now") or is_drought) and not is_waterlogged)

    # Physical pump action:
    pump_on = irrigate_needed and not pump_locked

    # Weather-aware pump delay (ONLY in LIVE mode, NEVER in SIM mode!)
    fc = get_forecast()
    weather_delayed = False
    if mode != "sim":
        current_rain = (w.get("rain") or 0) if w.get("enabled") else 0
        total_rain = fc.get("total_rain_mm", 0) if fc.get("enabled") else 0
        if (current_rain > 2 or (fc.get("rain_coming") and total_rain > 5)) and pump_on:
            pump_on = False
            weather_delayed = True

    # High temperature boost in live mode
    if mode != "sim" and fc.get("heat_coming") and sd["soil_moisture"] < (cfg["moist_opt"] - 5) and not pump_locked:
        irrigate_needed = True
        pump_on = True

    # Generate clear agronomic advisory message:
    if pump_locked:
        lock_reasons = []
        if not tds_safe:
            lock_reasons.append(f"High Water Salinity ({sd['tds_ppm']:.0f} ppm)")
        if gas_alert:
            lock_reasons.append("Hazardous Gas Spikes")
        reason_str = " & ".join(lock_reasons) or "Safety Interlock"
        if is_drought:
            advisory = f"Soil needs water, but pump is locked due to {reason_str}. Treat water/ventilate area before irrigating."
        else:
            advisory = f"Pump locked due to {reason_str}."
    elif weather_delayed:
        advisory = f"Soil moisture is low ({sd['soil_moisture']:.0f}%), but incoming rainfall will irrigate naturally. Pump kept on standby."
    elif irrigate_needed:
        advisory = f"Soil moisture is low ({sd['soil_moisture']:.0f}%). Irrigation recommended immediately."
    elif is_waterlogged:
        advisory = f"Excessive soil moisture ({sd['soil_moisture']:.0f}%). Pause irrigation to prevent root rot."
    else:
        advisory = f"Soil moisture is optimal ({sd['soil_moisture']:.0f}%). No irrigation needed."

    trend = trend_from_hist(hist["soil_moisture"])
    aqi = max(0, 100 - (20 if sd["mq135_ammonia"] > 100 else 0)
              - (25 if sd["mq4_methane"] > 500 else 0)
              - (20 if sd["mq7_co"] > 35 else 0)
              - (15 if sd.get("mq2_smoke", 0) > 100 else 0))
    conf = 95 if ml else min(99, max(70, score - 5))

    weather_note = "Simulation Mode Active" if mode == "sim" else fc.get("summary", "Stable weather next 24h")

    return {
        "health_score": score,
        "health_status": health_status,
        "irrigate_now": bool(irrigate_needed),
        "pump_on": bool(pump_on),
        "pump_locked": bool(pump_locked),
        "gas_alert": bool(gas_alert),
        "tds_safe": bool(tds_safe),
        "is_drought": bool(is_drought),
        "trend_moisture": trend,
        "field_aqi": aqi,
        "field_aqi_label": "Excellent" if aqi > 80 else "Good" if aqi > 60 else "Moderate" if aqi > 40 else "Poor",
        "confidence_pct": conf,
        "is_critical_stage": cfg["critical"],
        "weather_note": weather_note,
        "advisory": advisory,
        "sensors_used": sd,
        "inference_source": "ml" if ml else "heuristic",
    }


# ── Routes ──────────────────────────────────────────────────────
@app.route("/healthz")
def healthz():
    return "ok", 200


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/crops")
def crops_r():
    return jsonify(CROPS)


@app.route("/predict", methods=["POST"])
def predict_r():
    try:
        d = request.json or {}
        w = get_weather()
        s = dict(d.get("sensors", {}))
        mode = d.get("mode", "live")
        if esp32_data and mode != "sim":
            s.update(esp32_data)
        return jsonify(predict(d.get("crop", "rice"), d.get("stage", "germination"), s, w, mode=mode))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/weather")
def weather_r():
    return jsonify(get_weather())


@app.route("/forecast")
def forecast_r():
    return jsonify(get_forecast())


# SSE push for instant ESP32->browser
_sse_q = []
_sse_lock = _th.Lock()


@app.route("/stream")
def stream_r():
    def gen():
        q = Queue(maxsize=5)
        with _sse_lock:
            _sse_q.append(q)
        try:
            while True:
                try:
                    yield f"data: {q.get(timeout=20)}\n\n"
                except Empty:
                    yield "data: {}\n\n"
        finally:
            with _sse_lock:
                if q in _sse_q:
                    _sse_q.remove(q)

    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/esp32", methods=["POST"])
@app.route("/data", methods=["POST"])
def esp32_r():
    global esp32_data
    raw = request.json or {}
    candidate = raw.get("sensors", raw) if isinstance(raw, dict) else raw
    if not isinstance(candidate, dict):
        return jsonify({"error": "Sensor payload must be a JSON object"}), 400

    sensor_ranges = {
        "soil_moisture": (0, 100),
        "tds_ppm": (0, 10000),
        "air_temp_c": (-50, 80),
        "soil_temp_c": (-50, 80),
        "humidity_pct": (0, 100),
        "mq135_ammonia": (0, 100000),
        "mq4_methane": (0, 100000),
        "mq7_co": (0, 100000),
        "mq2_smoke": (0, 100000),
    }

    for key, value in candidate.items():
        if key not in sensor_ranges:
            continue
        if isinstance(value, bool):
            return jsonify({"error": f"{key} must be numeric"}), 400
        try:
            number = float(value)
        except (TypeError, ValueError):
            return jsonify({"error": f"{key} must be numeric"}), 400
        low, high = sensor_ranges[key]
        if not math.isfinite(number) or not low <= number <= high:
            return jsonify({"error": f"{key} is outside the allowed range"}), 400

    esp32_data = candidate
    payload = json.dumps(esp32_data)
    with _sse_lock:
        dead = []
        for q in _sse_q:
            try:
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
        for q in dead:
            _sse_q.remove(q)
    return jsonify({"status": "ok"})


@app.route("/live")
def live_r():
    return jsonify(esp32_data if esp32_data else {"status": "no_data"})


@app.route("/chat", methods=["POST"])
def chat_r():
    try:
        d = request.json or {}
        msg = d.get("message", "").strip()
        crop = d.get("crop", "rice")
        stg = d.get("stage", "germination")
        lang = d.get("lang", "en")
        history = d.get("history", [])

        s = dict(d.get("sensors", {}))
        if esp32_data:
            s.update(esp32_data)

        mode = d.get("mode", "live")
        w = get_weather()
        fc = get_forecast()
        weather_ctx = {
            "enabled": bool(w.get("enabled") or fc.get("enabled")),
            "city": w.get("city", WEATHER_CITY),
            "temp": w.get("temp"),
            "humidity": w.get("humidity"),
            "current_rain": w.get("rain") or 0,
            "rain_coming": bool(fc.get("rain_coming")),
            "heat_coming": bool(fc.get("heat_coming")),
            "total_rain_mm": fc.get("total_rain_mm", 0),
            "max_temp": fc.get("max_temp"),
            "summary": fc.get("summary", "Stable weather next 24h"),
        }
        res = predict(crop, stg, s, w, mode=mode)
        sd = res.get("sensors_used", {})
        cfg = get_crop_cfg(crop, stg)

        reply_data = ai_engine.generate_chat_reply(
            message=msg,
            history=history,
            crop=crop,
            stage=stg,
            sensors=sd,
            pred_result=res,
            crop_cfg=cfg,
            weather=weather_ctx,
            lang=lang,
        )
        return jsonify(reply_data)
    except Exception as e:
        app.logger.error("Chat route error: %s", e)
        return jsonify({"reply": f"Chat Error: {e}", "source": "error"}), 500


@app.route("/status")
def status_r():
    return jsonify({
        "gemini_ready": ai_engine.is_gemini_available(),
        "model_name": ai_engine.get_active_model_name(),
        "ml_ready": ML_READY,
        "models": list(MODELS.keys()),
        "encoders": list(ENCODERS.keys()),
        "esp32": bool(esp32_data),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
