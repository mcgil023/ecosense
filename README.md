# EcoSense — Smart Farming Dashboard

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black.svg)](https://flask.palletsprojects.com/)
[![Deployed on Render](https://img.shields.io/badge/Deployed%20on-Render-46E3B7.svg)](https://render.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Live Demo:** https://ecosense-fntj.onrender.com

EcoSense is an IoT + ML dashboard for small farms and greenhouses. It ingests live sensor data from ESP32 devices, runs industrial-grade ML models for crop health, irrigation decisions, gas alerts, and pump safety, and provides a real-time web UI with weather integration, forecasts, and an AI farming assistant (Gemini).

---

## 🚀 Major Improvements

### Industrial-Grade ML Inference
- ✅ **Active ML Engine**: All 4 pre-trained models now power predictions (was previously heuristic-only)
- ✅ **Hybrid Fallback**: Automatic fall-back to rule-based logic if ML encounters outliers
- ✅ **Safety First**: Gas alerts or critical TDS now IMMEDIATELY lock the pump (fail-safe)
- ✅ **Feature Completeness**: Full 15-feature vector including `mq2_smoke` (previously missing)
- ✅ **Noise Resistance**: Trend analysis uses linear regression slope over 20-sample window (vs fragile 3-sample check)

### Sunlight-Readable Industrial UI
- ✅ **High-Contrast Themes**: Light/Daylight theme optimized for outdoor visibility
- ✅ **Chunky Touch Targets**: 54mm minimum size for gloved/dirty hands
- ✅ **Physical Feedback**: `:active` states and industrial alarm animations
- ✅ **Persistent Theme Toggle**: Sun/Moon button with localStorage persistence
- ✅ **SVG Theme Awareness**: Crop face and gauge adapt to theme colors

### Configuration & Reliability
- ✅ **Single Source of Truth**: All thresholds from `crop_config.json` (eliminated hardcoded drift)
- ✅ **ESP32 Validation**: Full range checking including `mq2_smoke` (0-100,000 ppm)
- ✅ **Joblib Models**: Properly loaded scikit-learn pipelines with version compatibility handling
- ✅ **Error Resilience**: Comprehensive try/catch boundaries throughout

### Enhanced AI Assistant
- ✅ **Multi-Turn Context**: Last 4 conversation turns sent to Gemini for contextual awareness
- ✅ **Improved Tamil**: Fixed translations and cultural appropriateness
- ✅ **2-Sentence Limit**: Maintained concise, actionable responses

---

## 🌟 Features

| Area | Capability |
|------|------------|
| **Live Sensors** | Soil moisture, TDS (water quality), air/soil temperature, humidity, MQ135 (NH₃), MQ4 (CH₄), MQ7 (CO), MQ2 (Smoke) |
| **ML Inference** | Crop health score (0-100), health status (GOOD/MODERATE/POOR/CRITICAL), irrigation recommendation, pump lock safety, gas leak detection |
| **Crops Supported** | Rice, Maize, Groundnut, Sugarcane, Coconut — each with stage-aware thresholds |
| **Weather** | Current conditions + 24h forecast (OpenWeatherMap) — auto-adjusts irrigation for rain/heat |
| **Safety** | Pump auto-lock on gas leak, critical health, unsafe TDS, or critical-stage awareness |
| **Trends** | Rolling 20-sample history with linear regression slope (noise-resistant) |
| **AI Assistant** | Multilingual (Tamil/English) chat via Gemini 1.5 Flash — answers farming questions with live sensor context + conversation history |
| **Real-time** | Server-Sent Events (SSE) stream for live dashboard updates (<200ms) |
| **ESP32 Ingestion** | POST `/esp32` or `/data` with validated JSON payloads |
| **Industrial UI** | High-contrast light theme for sunlight readability, 54mm touch targets, theme toggle |

---

## 🏗️ Architecture

```
ESP32 (sensors) ──HTTPS──▶ Flask API (/esp32, /data)
                               │
                               ▼
                     ┌───────────────────────┐
                     │  ML Inference (sklearn)│
                     │  • health_status       │
                     │  • irrigate_now        │
                     │  • pump_lock           │
                     │  • gas_alert           │
                     └───────────┬─────────────┘
                                 │
                     ┌───────────▼─────────────┐
                     │   Web Dashboard (SSE)   │
                     │  • Live sensor cards    │
                     │  • Health gauge         │
                     │  • Irrigation button    │
                     │  • Weather + Forecast   │
                     │  • AI Chat (Gemini)     │
                     │  • Theme Toggle         │
                     └─────────────────────────┘
```

---

## 📦 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/mcgil023/ecosense.git
cd ecosense
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file (or export in shell):

```bash
# Required for AI chat
GEMINI_API_KEY=your_gemini_api_key

# Required for weather
WEATHER_API_KEY=your_openweathermap_api_key
WEATHER_CITY=Tiruchirappalli  # or your city
```

### 3. Run Locally

```bash
python app.py
# → http://localhost:5000
```

### 4. Push Sensor Data (ESP32)

```bash
curl -X POST http://localhost:5000/esp32 \
  -H "Content-Type: application/json" \
  -d '{
    "sensors": {
      "soil_moisture": 68,
      "tds_ppm": 420,
      "air_temp_c": 31.2,
      "soil_temp_c": 27.5,
      "humidity_pct": 72,
      "mq135_ammonia": 45,
      "mq4_methane": 180,
      "mq7_co": 8,
      "mq2_smoke": 20
    }
  }'
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Main dashboard |
| `GET` | `/healthz` | Health check (Render) |
| `GET` | `/crops` | List supported crops & stages |
| `POST` | `/predict` | Run ML inference on sensor payload |
| `GET` | `/weather` | Current weather |
| `GET` | `/forecast` | 24h forecast (8 × 3h slots) |
| `GET` | `/stream` | SSE live updates (dashboard) |
| `POST` | `/esp32` / `/data` | Ingest ESP32 sensor JSON |
| `GET` | `/live` | Last received ESP32 payload |
| `POST` | `/chat` | AI farming assistant (Gemini) with conversation history |
| `GET` | `/status` | Model & service readiness |

### Example `/predict` Request

```json
POST /predict
{
  "crop": "rice",
  "stage": "flowering",
  "sensors": {
    "soil_moisture": 65,
    "tds_ppm": 500,
    "air_temp_c": 32,
    "soil_temp_c": 28,
    "humidity_pct": 70,
    "mq135_ammonia": 60,
    "mq4_methane": 200,
    "mq7_co": 10,
    "mq2_smoke": 15
  },
  "mode": "sim"
}
```

### Example `/predict` Response

```json
{
  "health_score": 78,
  "health_status": "GOOD",
  "engine": "ml",
  "irrigate_now": true,
  "pump_on": true,
  "pump_locked": false,
  "gas_alert": false,
  "tds_safe": true,
  "trend_moisture": "stable",
  "field_aqi": 85,
  "field_aqi_label": "Excellent",
  "confidence_pct": 83,
  "is_critical_stage": true,
  "weather_note": "Heat 38C ahead - irrigate early morning",
  "sensors_used": { ... },
  "thresholds": {
    "moist_min": 75,
    "moist_opt": 95,
    "tds_max": 700
  }
}
```

---

## 📱 ESP32 Payload Schema

```json
{
  "sensors": {
    "soil_moisture": 0–100,      // %
    "tds_ppm": 0–10000,          // ppm
    "air_temp_c": -50–80,        // °C
    "soil_temp_c": -50–80,       // °C
    "humidity_pct": 0–100,       // %
    "mq135_ammonia": 0–100000,   // ppm
    "mq4_methane": 0–100000,     // ppm
    "mq7_co": 0–100000,          // ppm
    "mq2_smoke": 0–100000        // ppm
  }
}
```

All fields optional; missing values fall back to defaults. Out-of-range values rejected with 400.

---

## 🌾 Crop Configuration

`crop_config.json` defines per-crop thresholds:

```json
{
  "rice": {
    "stages": {
      "germination": {"moist_min": 70, "moist_opt": 90, "critical": false},
      "tillering": {"moist_min": 65, "moist_opt": 85, "critical": true},
      "panicle_init": {"moist_min": 70, "moist_opt": 90, "critical": true},
      "flowering": {"moist_min": 75, "moist_opt": 95, "critical": true},
      "grain_filling": {"moist_min": 65, "moist_opt": 85, "critical": true},
      "maturity": {"moist_min": 45, "moist_opt": 65, "critical": false}
    },
    "tds_max": 700
  },
  "maize": { ... },
  "groundnut": { ... },
  "sugarcane": { ... },
  "coconut": { ... }
}
```

**Critical stages** (extra irrigation care): `flowering`, `tasseling`, `grand_growth`, `silking`, `pegging`, `pod_filling`, `panicle_init`, `tillering`, `young_palm`, `bearing`, `nursery`, `vegetative`, `grain_filling`.

---

## 🤖 ML Models (Pre-trained, Loaded at Startup)

| File | Purpose | Type |
|------|---------|------|
| `model_health_status.pkl` | Health score → status classifier (4 classes) | RandomForestClassifier |
| `model_irrigate_now.pkl` | Irrigation decision (binary) | DecisionTreeClassifier |
| `model_pump_lock.pkl` | Pump safety lock (binary) | DecisionTreeClassifier |
| `model_gas_alert.pkl` | Gas leak detection (binary) | DecisionTreeClassifier |
| `encoder_crop.pkl` | Crop label encoding | LabelEncoder |
| `encoder_stage.pkl` | Stage label encoding | LabelEncoder |
| `encoder_health.pkl` | Health label encoding | LabelEncoder |

> Models are pickled `scikit-learn` pipelines. Retrain by replacing `.pkl` files.

---

## 💾 Project Structure

```
ecosense/
├── app.py                 # Flask app + ML inference + routes
├── requirements.txt       # Python deps
├── render.yaml            # Render.com service config
├── Procfile               # Gunicorn command
├── crop_config.json       # Crop thresholds & stages (SSOT)
├── feature_list.json      # Model feature order (15 features)
├── training_data.csv      # Historical training data
├── *.pkl                  # Pre-trained sklearn models & encoders
├── templates/
│   └── index.html         # Dashboard UI with theme toggle
├── static/
│   ├── style.css          # Industrial high-contrast CSS + themes
│   ├── style_extra.css    # Legacy (retained for compatibility)
│   └── script.js          # SSE client + charts + chat + theme logic
```

---

## 🚦 Deployment (Render)

1. Push to GitHub
2. New → Web Service → Connect repo
3. Render auto-detects `render.yaml`:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
4. Add env vars in Render dashboard: `GEMINI_API_KEY`, `WEATHER_API_KEY`, `WEATHER_CITY`
5. Deploy → `https://your-app.onrender.com`

---

## 📈 Roadmap

- [ ] Multi-field / multi-device support
- [ ] Historical data export (CSV)
- [ ] SMS/WhatsApp alerts via Twilio
- [ ] Model retraining pipeline (GitHub Actions)
- [ ] Mobile PWA install
- [ ] LoRaWAN gateway support
- [ ] Solar-powered ESP32 sleep modes

---

## 🤝 Contributing

1. Fork → feature branch → PR
2. Run `python -m py_compile app.py` before commit
3. Keep changes focused; update `crop_config.json` for new crops

---

## ⚖️ License

MIT — free for personal, educational, and commercial use.

---

## 🙏 Acknowledgements

- **OpenWeatherMap** — weather & forecast API
- **Google Gemini** — AI farming assistant
- **scikit-learn** — ML models
- **Flask + Gunicorn** — web framework
- **Render** — free hosting