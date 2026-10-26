# EcoSense — Enterprise Precision Agronomy & IoT Dashboard

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black.svg)](https://flask.palletsprojects.com/)
[![Deployed on Render](https://img.shields.io/badge/Deployed%20on-Render-46E3B7.svg)](https://render.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Live Demo:** https://ecosense-fntj.onrender.com

EcoSense is an enterprise-grade IoT and Precision Agriculture Platform designed for smallholders, commercial fields, and precision greenhouses. It integrates multi-tenant ESP32 sensor telemetry, scientific **FAO-56 Penman-Monteith Evapotranspiration ($ET_c$) physics**, industrial **scikit-learn Machine Learning inference**, rural power grid scheduling (TNEB), borewell burnout safety interlocks, and a live multilingual **Gemini AI farming companion**.

---

## 🚀 Enterprise Agronomic Architecture

### 1. FAO-56 Penman-Monteith Evapotranspiration Model ($ET_c = K_c \times ET_0$)
- **Scientific Water Demand**: Calculates daily reference crop evapotranspiration ($ET_0$) using solar radiation approximations and Vapor Pressure Deficit ($VPD$).
- **Stage-Specific Crop Coefficients ($K_c$)**: All crop stages in `crop_config.json` map official FAO-56 $K_c$ factors (e.g., Rice tillering $K_c = 1.15$, panicle initiation $K_c = 1.35$) to compute exact daily crop water demand ($ET_c$ in mm/day).

### 2. Rural Borewell Dry-Run Protection & TNEB 3-Phase Grid Scheduling
- **Borewell Motor Burnout Protection**: Actively detects sudden water salinity (TDS) spikes (>40% consecutive jump caused by silt, cavitation, or air intrusion), immediately locking pump actuators to prevent catastrophic motor burnout.
- **Rural Three-Phase Grid Power Scheduling**: Synchronized with Indian rural agricultural power timing (e.g., TNEB daily slots: `06:00–12:00` and `21:00–03:00` IST) to ensure pump actuation aligns with available high-voltage supply.

### 3. Industrial ML Inference & Explainability Breakdown
- **Active Scikit-Learn Models**: Random Forest Crop Health Classifier, Decision Tree Irrigation Decision, Decision Tree Safety Interlock, and MQ Gas Hazard Alert.
- **Explainable Diagnostics (`factors_breakdown`)**: Eliminates "black-box" opacity by exposing exact penalty deductions for moisture deficit, salinity stress, thermal extremes, and toxic gas presence.
- **True Linear Regression Sloping**: Evaluates 20-sample sliding windows with NumPy linear slope fitting (`np.polyfit`) for noise-resistant trend detection.

### 4. Conversational Weather-Aware AI Assistant (Gemini)
- **Local & Meteorological Awareness**: Integrates live OpenWeatherMap conditions and 24-hour rainfall/heat forecasts directly into conversational guidance.
- **Zero Raw Data Dumps**: Provides human-friendly, actionable agricultural advice in English and Tamil (தமிழ்) without confusing farmers with raw data tables.

---

## 🏗️ System Architecture

```
ESP32 Telemetry ──HTTPS──▶ Flask Ingestion Engine (/esp32, /data)
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
    ┌─────────────────────────┐               ┌──────────────────────────────┐
    │   ML Decision Engine    │               │  Agronomic Physics Engine    │
    │  • RandomForest Health  │               │  • FAO-56 Penman-Monteith    │
    │  • DecisionTree Irrig   │               │    (ETc = Kc * ET0, VPD)     │
    │  • Safety Pump Lock     │               │  • Borewell Dry-Run Interlock│
    │  • MQ Gas Leak Alert    │               │  • TNEB 3-Phase Grid Timing  │
    └──────────┬──────────────┘               └──────────────┬───────────────┘
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      ▼
                      ┌──────────────────────────────┐
                      │    Precision Agronomy API    │
                      │   (Multi-Device Tenancy)     │
                      └───────────────┬──────────────┘
                                      ▼
                      ┌──────────────────────────────┐
                      │    Live Dashboard (SSE)      │
                      │  • Telemetry Cards & Gauges  │
                      │  • Explainable Diagnostics   │
                      │  • Weather-Aware Companion   │
                      │  • Server-Side Gemini AI     │
                      └──────────────────────────────┘
```

---

## 🌟 Core Feature Matrix

| Domain | Capability | Description |
|---|---|---|
| **Live Telemetry** | 9-Channel Sensing | Soil moisture, TDS salinity, ambient/soil temperature, humidity, MQ-135 (NH₃), MQ-4 (CH₄), MQ-7 (CO), MQ-2 (Smoke) |
| **Agronomic Physics** | FAO-56 Penman-Monteith | Reference evapotranspiration ($ET_0$), Crop water demand ($ET_c = K_c \times ET_0$), and Vapor Pressure Deficit ($VPD$) |
| **Pump Safety** | Multi-Layer Interlocks | Automatic lock on critical TDS, hazardous gas, or borewell cavitation/dry-run spike (>40%) |
| **Grid Management** | Three-Phase Scheduling | TNEB rural power synchronization (06:00–12:00 & 21:00–03:00 IST) |
| **Trend Analytics** | 20-Sample Regression | Mathematical linear slope fitting ($m = \text{Cov}(x,y)/\text{Var}(x)$) via `numpy.polyfit` |
| **Explainable ML** | Penalty Diagnostics | Quantitative `factors_breakdown` for moisture, salinity, heat, and gas penalties |
| **AI Companion** | Multilingual Generative AI | Natural English & Tamil agricultural guidance powered by Google Gemini |

---

## 🔌 API Specifications

### Example `/predict` Response (Extended Schema)

```json
POST /predict
{
  "health_score": 45,
  "health_status": "CRITICAL",
  "irrigate_now": true,
  "pump_on": true,
  "pump_locked": false,
  "gas_alert": false,
  "tds_safe": true,
  "is_drought": true,
  "trend_moisture": "falling",
  "field_aqi": 100,
  "field_aqi_label": "Excellent",
  "confidence_pct": 95,
  "is_critical_stage": true,
  "weather_note": "Heavy rain 18.2mm expected",
  "advisory": "Moisture stress detected (25%). Irrigation recommended immediately.",
  "sensors_used": {
    "soil_moisture": 25.0,
    "tds_ppm": 380.0,
    "air_temp_c": 38.0,
    "soil_temp_c": 34.0,
    "humidity_pct": 28.0,
    "mq135_ammonia": 55.0,
    "mq4_methane": 160.0,
    "mq7_co": 11.0,
    "mq2_smoke": 18.0
  },
  "inference_source": "ml",
  "agronomic_physics": {
    "fao56_kc_factor": 1.15,
    "etc_crop_water_demand_mm_day": 5.49,
    "et0_reference_mm_day": 4.77,
    "vpd_kpa": 5.53
  },
  "grid_power_status": {
    "three_phase_available": true,
    "active_slot": "Slot 1 (06:00-12:00)"
  },
  "factors_breakdown": {
    "moisture_penalty": 40.0,
    "salinity_penalty": 0.0,
    "thermal_penalty": 0.0,
    "toxic_gas_penalty": 0.0
  }
}
```

---

## 🌾 Crop Configuration (`crop_config.json`)

Thresholds and FAO-56 $K_c$ parameters for supported crops:

```json
{
  "rice": {
    "tds_max": 750,
    "stages": {
      "germination": { "moist_min": 70, "moist_opt": 90, "kc": 1.05, "critical": false },
      "tillering":   { "moist_min": 65, "moist_opt": 85, "kc": 1.15, "critical": true },
      "panicle":     { "moist_min": 70, "moist_opt": 90, "kc": 1.35, "critical": true },
      "ripening":    { "moist_min": 45, "moist_opt": 65, "kc": 0.90, "critical": false }
    }
  },
  "maize": { "tds_max": 800, "stages": { ... } },
  "groundnut": { "tds_max": 700, "stages": { ... } },
  "sugarcane": { "tds_max": 900, "stages": { ... } },
  "coconut": { "tds_max": 1200, "stages": { ... } }
}
```

---

## 📦 Automated Verification Suite

Run the enterprise test suite covering FAO-56 physics, linear regression slope fitting, and API endpoints:

```bash
python test_ecosense.py
```

Expected output:
```text
======================================================================
RUNNING ECOSENSE ENTERPRISE REFACTORING & AGRONOMIC VERIFICATION
======================================================================
[TEST 1] Validating crop_config.json and FAO-56 Kc loading...
✓ Crop configuration and FAO-56 Kc factors validated successfully!

[TEST 2] Validating FAO-56 Evapotranspiration calculation...
✓ Evapotranspiration calculations and physics response verified!

[TEST 3] Validating Linear Regression Slope Trend (trend_from_hist)...
✓ Linear regression slope trend over sliding window verified!

[TEST 4] Validating API Endpoints (/crops, /esp32, /predict)...
✓ GET /crops -> 200 OK
✓ POST /esp32 -> 200 OK (Tenancy verified)
✓ POST /predict -> 200 OK (Full extended schema verified)
✓ GET /healthz -> 200 OK
======================================================================
ALL 4 ENTERPRISE AGRONOMIC TESTS PASSED SUCCESSFULLY! 🚀
======================================================================
```

---

## ⚖️ License

MIT License — free for academic, personal, and commercial agricultural deployment.