# -*- coding: utf-8 -*-
"""
Automated Self-Test Suite for EcoSense Enterprise Agronomic System.
Validates:
1. Crop configuration parsing and FAO-56 Kc loading.
2. Evapotranspiration calculation under heat/wind variations.
3. Trend regression calculation across a 20-sample window.
4. API endpoints (/predict, /esp32, /crops) with assertion checks for 200 OK.
"""

import sys
import json
import math
import numpy as np

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import app

client = app.app.test_client()

print("=" * 70)
print("RUNNING ECOSENSE ENTERPRISE REFACTORING & AGRONOMIC VERIFICATION")
print("=" * 70)

# ==============================================================================
# TEST 1: Crop Configuration & FAO-56 Kc Loading
# ==============================================================================
print("\n[TEST 1] Validating crop_config.json and FAO-56 Kc loading...")
with open("crop_config.json", encoding="utf-8") as f:
    cfg = json.load(f)

expected_crops = ["rice", "maize", "groundnut", "sugarcane", "coconut"]
for crop in expected_crops:
    assert crop in cfg, f"Missing crop {crop} in crop_config.json"
    stages = cfg[crop]["stages"]
    assert len(stages) >= 4, f"Crop {crop} should have at least 4 stages"
    for st_name, st_data in stages.items():
        assert "kc" in st_data, f"Stage {st_name} in {crop} missing 'kc'"
        assert isinstance(st_data["kc"], (int, float)), f"Kc in {crop}:{st_name} must be numeric"
        assert st_data["kc"] > 0, f"Kc in {crop}:{st_name} must be positive"
        assert "moist_min" in st_data
        assert "moist_opt" in st_data
        assert "critical" in st_data

# Test get_crop_cfg helper
rice_germ = app.get_crop_cfg("rice", "germination")
assert rice_germ["kc"] == 1.05, f"Expected Kc 1.05 for rice germination, got {rice_germ['kc']}"
assert rice_germ["moist_min"] == 70

maize_emergence = app.get_crop_cfg("maize", "emergence")
assert maize_emergence["kc"] == 0.40, f"Expected Kc 0.40 for maize emergence, got {maize_emergence['kc']}"

print("✓ Crop configuration and FAO-56 Kc factors validated successfully!")

# ==============================================================================
# TEST 2: Evapotranspiration Calculation (FAO-56 Penman-Monteith)
# ==============================================================================
print("\n[TEST 2] Validating FAO-56 Evapotranspiration calculation...")

# Base conditions: 28°C, 65% humidity, 1.5 m/s wind, Kc=1.15
base_weather = {"temp": 28.0, "humidity": 65.0, "wind": 1.5}
base_etc = app.calculate_fao56_evapotranspiration(base_weather, kc_factor=1.15)
print("  Base Weather ETc:", base_etc)

assert "et0_reference_mm_day" in base_etc
assert "etc_crop_demand_mm_day" in base_etc
assert "vapor_pressure_deficit_kpa" in base_etc
assert base_etc["etc_crop_demand_mm_day"] > 0
assert base_etc["vapor_pressure_deficit_kpa"] > 0
# ETc must equal Kc * ET0 (rounded to 2 decimal places)
expected_etc = round(base_etc["et0_reference_mm_day"] * 1.15, 2)
assert abs(base_etc["etc_crop_demand_mm_day"] - expected_etc) <= 0.02

# Heat & Wind Variation: 40°C, 25% humidity, 4.0 m/s wind, Kc=1.15
extreme_weather = {"temp": 40.0, "humidity": 25.0, "wind": 4.0}
extreme_etc = app.calculate_fao56_evapotranspiration(extreme_weather, kc_factor=1.15)
print("  Extreme Heat/Wind ETc:", extreme_etc)

assert extreme_etc["et0_reference_mm_day"] > base_etc["et0_reference_mm_day"], "Extreme heat/wind should increase ET0"
assert extreme_etc["vapor_pressure_deficit_kpa"] > base_etc["vapor_pressure_deficit_kpa"], "Dry heat should elevate VPD"
assert extreme_etc["etc_crop_demand_mm_day"] > base_etc["etc_crop_demand_mm_day"], "Crop water demand should spike under heat"

print("✓ Evapotranspiration calculations and physics response verified!")

# ==============================================================================
# TEST 3: Trend Regression Calculation Across 20-Sample Sliding Window
# ==============================================================================
print("\n[TEST 3] Validating Linear Regression Slope Trend (trend_from_hist)...")

# Rising sequence
rising_samples = [50.0 + i * 0.6 for i in range(20)]
rising_trend = app.trend_from_hist(rising_samples)
print(f"  Rising window (slope ~ +0.6): trend = {rising_trend}")
assert rising_trend == "rising", f"Expected 'rising', got {rising_trend}"

# Falling sequence
falling_samples = [70.0 - i * 0.5 for i in range(20)]
falling_trend = app.trend_from_hist(falling_samples)
print(f"  Falling window (slope ~ -0.5): trend = {falling_trend}")
assert falling_trend == "falling", f"Expected 'falling', got {falling_trend}"

# Stable sequence with noise
stable_samples = [55.0 + (0.05 if i % 2 == 0 else -0.05) for i in range(20)]
stable_trend = app.trend_from_hist(stable_samples)
print(f"  Stable window (slope ~ 0.0): trend = {stable_trend}")
assert stable_trend == "stable", f"Expected 'stable', got {stable_trend}"

# Short sequence (< 5 samples)
short_samples = [50.0, 52.0, 54.0]
assert app.trend_from_hist(short_samples) == "stable"

print("✓ Linear regression slope trend over sliding window verified!")

# ==============================================================================
# TEST 4: API Endpoints Verification (/crops, /esp32, /predict)
# ==============================================================================
print("\n[TEST 4] Validating API Endpoints (/crops, /esp32, /predict)...")

# 1. /crops endpoint
r_crops = client.get("/crops")
assert r_crops.status_code == 200, f"Expected 200, got {r_crops.status_code}"
crops_data = r_crops.get_json()
assert len(crops_data) == 5
assert "rice" in crops_data
assert "stages" in crops_data["rice"]
print("  ✓ GET /crops -> 200 OK")

# 2. /esp32 telemetry ingestion endpoint (with device tenancy)
esp32_payload = {
    "device_id": "esp32_field_alpha",
    "sensors": {
        "soil_moisture": 68.5,
        "tds_ppm": 340.0,
        "air_temp_c": 29.2,
        "soil_temp_c": 25.0,
        "humidity_pct": 62.0,
        "mq135_ammonia": 45.0,
        "mq4_methane": 180.0,
        "mq7_co": 8.0,
        "mq2_smoke": 15.0
    }
}
r_esp32 = client.post("/esp32", json=esp32_payload)
assert r_esp32.status_code == 200, f"Expected 200, got {r_esp32.status_code}"
esp32_res = r_esp32.get_json()
assert esp32_res.get("status") == "ok"
assert esp32_res.get("device_id") == "esp32_field_alpha"
print("  ✓ POST /esp32 -> 200 OK (Tenancy verified)")

# 3. /predict endpoint with extended schema validation
predict_payload = {
    "crop": "rice",
    "stage": "tillering",
    "sensors": {
        "soil_moisture": 25.0,  # drought
        "tds_ppm": 380.0,
        "air_temp_c": 38.0,
        "soil_temp_c": 34.0,
        "humidity_pct": 28.0,
        "mq135_ammonia": 55.0,
        "mq4_methane": 160.0,
        "mq7_co": 11.0,
        "mq2_smoke": 18.0
    },
    "mode": "sim",
    "device_id": "esp32_field_alpha"
}
r_predict = client.post("/predict", json=predict_payload)
assert r_predict.status_code == 200, f"Expected 200, got {r_predict.status_code}"
p = r_predict.get_json()

# Assert extended schema components
assert "health_score" in p
assert "health_status" in p
assert "irrigate_now" in p
assert "pump_on" in p
assert "pump_locked" in p
assert "gas_alert" in p
assert "tds_safe" in p
assert "is_drought" in p
assert "trend_moisture" in p
assert "field_aqi" in p
assert "advisory" in p

# Assert Agronomic Physics Block
assert "agronomic_physics" in p, "agronomic_physics block missing from /predict"
agri = p["agronomic_physics"]
assert "fao56_kc_factor" in agri
assert "etc_crop_water_demand_mm_day" in agri
assert "et0_reference_mm_day" in agri
assert "vpd_kpa" in agri
assert "et_c_mm_day" in agri
assert "kc_factor" in agri
assert agri["kc_factor"] == 1.15  # rice tillering Kc

# Assert Grid Power Status Block
assert "grid_power_status" in p, "grid_power_status block missing from /predict"
grid = p["grid_power_status"]
assert "three_phase_available" in grid
assert "three_phase_active" in grid
assert "active_slot" in grid
assert "current_slot" in grid
assert "next_window_ist" in grid

# Assert Borewell Protection Block
assert "borewell_protection" in p, "borewell_protection block missing from /predict"
bw = p["borewell_protection"]
assert "dry_run_detected" in bw
assert "alert" in bw


# Assert Factors Breakdown Block (Explainable ML/Heuristics)
assert "factors_breakdown" in p, "factors_breakdown block missing from /predict"
fb = p["factors_breakdown"]
assert "moisture_penalty" in fb
assert "salinity_penalty" in fb
assert "thermal_penalty" in fb
assert "toxic_gas_penalty" in fb
assert fb["moisture_penalty"] > 0, "Drought should impose moisture penalty"

# Verify Drought actuation
assert p["irrigate_now"] is True
assert p["pump_on"] is True
assert p["is_drought"] is True

print("  ✓ POST /predict -> 200 OK (Full extended schema verified)")

# 4. /healthz endpoint
r_healthz = client.get("/healthz")
assert r_healthz.status_code == 200
print("  ✓ GET /healthz -> 200 OK")

print("\n" + "=" * 70)
print("ALL 4 ENTERPRISE AGRONOMIC TESTS PASSED SUCCESSFULLY! 🚀")
print("=" * 70)
