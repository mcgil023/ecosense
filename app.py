from flask import Flask, render_template, request, jsonify
import joblib, json, os
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import deque

import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
gemini_ready = False
gemini_model = None
try:
    if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        gemini_ready = True
        print("✅ Gemini AI loaded")
    else:
        print("⚠️  No Gemini API key — using offline chatbot")
except Exception as e:
    print(f"⚠️  Gemini error: {e}")

app  = Flask(__name__)
BASE = Path(__file__).parent

model_health   = joblib.load(BASE/"model_health_status.pkl")
model_irrigate = joblib.load(BASE/"model_irrigate_now.pkl")
model_lock     = joblib.load(BASE/"model_pump_lock.pkl")
model_gas      = joblib.load(BASE/"model_gas_alert.pkl")
le_crop        = joblib.load(BASE/"encoder_crop.pkl")
le_stage       = joblib.load(BASE/"encoder_stage.pkl")
le_health      = joblib.load(BASE/"encoder_health.pkl")
with open(BASE/"crop_config.json") as f:
    CC = json.load(f)

FEATURES = ["crop_enc","stage_enc","is_critical_stage",
            "soil_moisture","tds_ppm","air_temp_c","soil_temp_c",
            "humidity_pct","mq135_ammonia","mq4_methane","mq7_co","mq2_smoke",
            "moist_min_threshold","moist_opt_threshold","tds_max_threshold"]

history    = {k: deque(maxlen=20) for k in ["soil_moisture","tds_ppm","air_temp_c","mq135_ammonia"]}
pump_state = {"on": False, "locked": False}
esp32_data = {}

def predict(crop, stage, sd):
    cfg = CC[crop]; sc = cfg["stages"][stage]
    row = pd.DataFrame([[
        le_crop.transform([crop])[0], le_stage.transform([stage])[0],
        1 if sc.get("critical") else 0,
        sd["soil_moisture"], sd["tds_ppm"], sd["air_temp_c"], sd["soil_temp_c"],
        sd["humidity_pct"], sd["mq135_ammonia"], sd["mq4_methane"],
        sd["mq7_co"], sd["mq2_smoke"],
        sc["moist_min"], sc["moist_opt"], cfg["tds_max"]
    ]], columns=FEATURES)

    health_label = le_health.inverse_transform([model_health.predict(row)[0]])[0]
    irrigate_now = int(model_irrigate.predict(row)[0])
    pump_lock    = int(model_lock.predict(row)[0])
    gas_alert    = int(model_gas.predict(row)[0])
    confidence   = round(float(max(model_health.predict_proba(row)[0]))*100, 1)

    aqi = 100
    if sd["mq135_ammonia"]>200: aqi-=30
    elif sd["mq135_ammonia"]>100: aqi-=15
    if sd["mq7_co"]>100: aqi-=35
    elif sd["mq7_co"]>35: aqi-=20
    if sd["mq4_methane"]>1000: aqi-=25
    if sd["mq2_smoke"]>400: aqi-=25
    aqi = max(0, aqi)
    aqi_lbl = ("Excellent" if aqi>=80 else "Good" if aqi>=60 else "Moderate" if aqi>=40 else "Poor" if aqi>=20 else "Critical")

    for k in history:
        if k in sd: history[k].append(sd[k])

    trend = "stable"
    if len(history["soil_moisture"])>=5:
        d=list(history["soil_moisture"]); h=len(d)//2
        delta = sum(d[h:])/len(d[h:]) - sum(d[:h])/len(d[:h])
        trend = "falling" if delta<-1 else "rising" if delta>1 else "stable"

    pump_lock_bool = bool(pump_lock)
    pump_on_bool   = bool(irrigate_now) and not pump_lock_bool
    hs = {"GOOD":90,"MODERATE":65,"POOR":40,"CRITICAL":15}
    return {
        "health_status": health_label, "health_score": hs[health_label],
        "confidence_pct": confidence, "irrigate_now": bool(irrigate_now),
        "pump_locked": pump_lock_bool, "pump_on": pump_on_bool,
        "gas_alert": bool(gas_alert), "field_aqi": aqi, "field_aqi_label": aqi_lbl,
        "tds_safe": sd["tds_ppm"]<=cfg["tds_max"],
        "is_critical_stage": bool(sc.get("critical",False)),
        "moist_min": sc["moist_min"], "moist_opt": sc["moist_opt"],
        "tds_max": cfg["tds_max"], "trend_moisture": trend,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }

def build_gemini_prompt(crop, stage, sd, result, lang, msg):
    lang_line = "Reply ONLY in Tamil language." if lang=="ta" else "Reply in simple English."
    return f"""You are EcoSense, an expert AI farming assistant for Tamil Nadu farmers.
{lang_line}
Keep answers SHORT (2-4 sentences), practical, and directly based on the numbers below.
Never say "I don't know" — always give a specific, helpful answer.

=== LIVE SENSOR DATA ===
Crop: {crop.capitalize()} | Stage: {stage.replace('_',' ').title()} {"(CRITICAL STAGE)" if result.get('is_critical_stage') else ""}
Soil Moisture : {sd.get('soil_moisture',0):.0f}%  (Min: {result.get('moist_min')}%, Optimal: {result.get('moist_opt')}%)
TDS (Salinity): {sd.get('tds_ppm',0):.0f} ppm (Safe limit: {result.get('tds_max')} ppm) — {"UNSAFE ⚠️" if not result.get('tds_safe') else "SAFE ✅"}
Air Temp      : {sd.get('air_temp_c',0):.0f}°C | Soil Temp: {sd.get('soil_temp_c',0):.0f}°C | Humidity: {sd.get('humidity_pct',0):.0f}%
Ammonia(MQ135): {sd.get('mq135_ammonia',0):.0f} ppm | Methane(MQ4): {sd.get('mq4_methane',0):.0f} ppm
CO(MQ7)       : {sd.get('mq7_co',0):.0f} ppm | Smoke(MQ2): {sd.get('mq2_smoke',0):.0f}
=== AI DECISIONS ===
Health: {result.get('health_status')} ({result.get('health_score')}/100) | Irrigate: {"YES" if result.get('irrigate_now') else "NO"}
Pump: {"LOCKED" if result.get('pump_locked') else "ON" if result.get('pump_on') else "OFF"} | Gas: {"DANGER ⚠️" if result.get('gas_alert') else "Clear"}
AQI: {result.get('field_aqi')}/100 — {result.get('field_aqi_label')} | Trend: {result.get('trend_moisture')}
========================
Farmer asks: "{msg}"
Your answer:"""

def rule_reply(msg, crop, stage, sd, r, lang):
    m=msg.lower()
    moist=sd.get("soil_moisture",70); tds=sd.get("tds_ppm",300)
    at=sd.get("air_temp_c",28); hum=sd.get("humidity_pct",65)
    mq135=sd.get("mq135_ammonia",50); mq7=sd.get("mq7_co",10)
    mq4=sd.get("mq4_methane",200); mq2=sd.get("mq2_smoke",50)
    aqi=r.get("field_aqi",100); aqi_lbl=r.get("field_aqi_label","Good")
    pl=r.get("pump_locked",False); po=r.get("pump_on",False)
    ts=r.get("tds_safe",True); mm=r.get("moist_min",60); mo=r.get("moist_opt",75)
    tm=r.get("tds_max",800); ic=r.get("is_critical_stage",False)
    h=r.get("health_status","GOOD"); sc=r.get("health_score",70)
    tr=r.get("trend_moisture","stable")
    if any(x in m for x in ["can i water","should i water","need to water","irrigate now","water now","shall i water","shall i irrigate"]):
        if pl: en=f"No — do NOT irrigate. TDS is {tds:.0f} ppm, exceeds {tm} ppm safe limit for {crop}. Pump is locked. Use alternate water source."; ta=f"வேண்டாம். TDS {tds:.0f} ppm வரம்பை மீறுகிறது."
        elif moist<mm: en=f"Yes — irrigate {'immediately (critical stage!)' if ic else 'now'}. Moisture {moist:.0f}% is below the {mm}% minimum for {crop}."; ta=f"ஆம் — நீர்ப்பாசனம் செய்யுங்கள். ஈரப்பதம் {moist:.0f}%."
        elif moist>=mo: en=f"No — moisture {moist:.0f}% is already at optimal ({mo}%). Irrigation now will cause waterlogging."; ta=f"இல்லை. ஈரப்பதம் {moist:.0f}% உகந்த அளவை எட்டியுள்ளது."
        else: en=f"Moisture {moist:.0f}% is between min ({mm}%) and optimal ({mo}%). Trend is {tr}. You can wait a little longer."; ta=f"ஈரப்பதம் {moist:.0f}% — இடையில் உள்ளது. போக்கு: {tr}."
    elif any(x in m for x in ["water safe","tds","salinity","borewell"]):
        if not ts: en=f"No — water NOT safe. TDS {tds:.0f} ppm exceeds {tm} ppm limit. Pump locked."; ta=f"இல்லை. TDS {tds:.0f} ppm வரம்பை மீறுகிறது."
        else: en=f"Yes — water is safe. TDS {tds:.0f} ppm is within {tm} ppm limit."; ta=f"ஆம். TDS {tds:.0f} ppm பாதுகாப்பான அளவில்."
    elif any(x in m for x in ["health","how is my crop","crop status"]):
        issues=[]
        if moist<mm: issues.append(f"low moisture ({moist:.0f}%)")
        if not ts: issues.append(f"high TDS ({tds:.0f} ppm)")
        if aqi<60: issues.append("poor air quality")
        if at>38: issues.append(f"heat stress ({at:.0f}°C)")
        en=f"Crop health: {h} ({sc}/100). Stage: {stage.replace('_',' ').title()} {'⭐ CRITICAL' if ic else ''}. Issues: {', '.join(issues) if issues else 'None — all clear'}. Trend: {tr}."; ta=f"பயிர் ஆரோக்கியம்: {h} ({sc}/100). பிரச்சனைகள்: {', '.join(issues) if issues else 'இல்லை'}."
    elif any(x in m for x in ["fertiliz","urea","manure","nutrient"]):
        if mq135>200: en=f"Not recommended. Ammonia {mq135:.0f} ppm — nitrogen already high. Wait 48 hours."; ta=f"பரிந்துரைக்கப்படவில்லை. அம்மோனியா {mq135:.0f} ppm அதிகமாக உள்ளது."
        elif moist<mm: en=f"Wait — soil too dry ({moist:.0f}%). Irrigate first, then fertilize."; ta=f"காத்திருங்கள். மண் வறண்டுள்ளது. முதலில் நீர்ப்பாசனம்."
        else: en=f"OK to fertilize. AQI {aqi}/100 — {aqi_lbl}. Moisture {moist:.0f}% adequate."; ta=f"உரம் இடலாம். AQI {aqi}/100."
    elif any(x in m for x in ["air quality","gas","ammonia","co level","smoke","methane"]):
        danger=[]
        if mq7>35: danger.append(f"CO: {mq7:.0f} ppm")
        if mq4>1000: danger.append(f"Methane: {mq4:.0f} ppm")
        if mq2>400: danger.append(f"Smoke: {mq2:.0f}")
        if mq135>200: danger.append(f"Ammonia: {mq135:.0f} ppm")
        if danger: en=f"⚠️ Gas danger! {', '.join(danger)}. AQI {aqi}/100. Check field immediately."; ta=f"⚠️ வாயு ஆபத்து! {', '.join(danger)}."
        else: en=f"Air quality {aqi_lbl} (AQI {aqi}/100). All gas levels safe."; ta=f"காற்று தரம் {aqi_lbl} (AQI {aqi}/100). அனைத்தும் பாதுகாப்பு."
    elif any(x in m for x in ["pump","motor","pump status"]):
        if pl: en=f"Pump LOCKED. TDS {tds:.0f} ppm unsafe for {crop}."; ta=f"பம்ப் பூட்டப்பட்டுள்ளது. TDS {tds:.0f} ppm."
        elif po: en=f"Pump ON. Irrigation running. Auto-stops at {mo}% moisture."; ta=f"பம்ப் இயங்குகிறது. {mo}% எட்டியதும் நிற்கும்."
        else: en=f"Pump OFF. Moisture {moist:.0f}% within safe range."; ta=f"பம்ப் நிறுத்தம். ஈரப்பதம் {moist:.0f}% சரி."
    elif any(x in m for x in ["temperature","heat","hot"]):
        en=f"Air: {at:.0f}°C, Soil: {sd.get('soil_temp_c',24):.0f}°C, Humidity: {hum:.0f}%. {'⚠️ Heat stress!' if at>38 else 'Temperature safe for '+crop+'.'}"; ta=f"வெப்பம் {at:.0f}°C. {'வெப்ப எச்சரிக்கை!' if at>38 else 'பாதுகாப்பான அளவு.'}"
    elif any(x in m for x in ["help","hi","hello","vanakkam"]):
        en="Hello! I am EcoSense AI. Ask: Irrigate? | Water safe? | Crop health? | Fertilize? | Air quality? | Pump? | Temperature?"; ta="வணக்கம்! EcoSense AI. கேளுங்கள்: நீர்? TDS? ஆரோக்கியம்? உரம்? காற்று? பம்ப்?"
    else:
        issues=[]
        if moist<mm: issues.append(f"moisture low")
        if not ts: issues.append(f"TDS high")
        if aqi<60: issues.append("poor air")
        if at>38: issues.append("heat stress")
        en=f"{crop.capitalize()} health: {h} ({sc}/100). Issues: {', '.join(issues) if issues else 'None'}. Ask about irrigation, water, fertilizer, pump or air quality."; ta=f"{crop} ஆரோக்கியம்: {h}. பிரச்சனைகள்: {', '.join(issues) if issues else 'இல்லை'}."
    return ta if lang=="ta" else en

@app.route("/")
def index():
    crops = list(CC.keys())
    stages = {c: list(CC[c]["stages"].keys()) for c in crops}
    return render_template("index.html", crops=crops, stages=json.dumps(stages), gemini_ready=gemini_ready)

@app.route("/predict", methods=["POST"])
def predict_route():
    d = request.json
    return jsonify(predict(d["crop"], d["stage"], d["sensors"]))

@app.route("/crops")
def get_crops():
    return jsonify({c:{"stages":list(CC[c]["stages"].keys()),"tds_max":CC[c]["tds_max"],
                       "temp_min":CC[c]["temp_min"],"temp_max":CC[c]["temp_max"]} for c in CC})

@app.route("/esp32", methods=["POST"])
def receive_esp32():
    global esp32_data
    esp32_data = request.json
    print(f"📡 ESP32: moisture={esp32_data.get('soil_moisture')}% TDS={esp32_data.get('tds_ppm')}ppm")
    return jsonify({"status": "ok"})

@app.route("/live")
def live_data():
    return jsonify(esp32_data if esp32_data else {"status": "no_data"})

@app.route("/chat", methods=["POST"])
def chat():
    msg   = request.json.get("message","").strip()
    crop  = request.json.get("crop","rice")
    stage = request.json.get("stage","")
    sd    = request.json.get("sensors",{})
    lang  = request.json.get("lang","en")
    if not stage:
        return jsonify({"reply":"Please select a crop and growth stage first.","source":"system"})
    result = predict(crop, stage, sd)
    if gemini_ready:
        try:
            prompt = build_gemini_prompt(crop, stage, sd, result, lang, msg)
            resp   = gemini_model.generate_content(prompt)
            return jsonify({"reply": resp.text.strip(), "source":"gemini"})
        except Exception as e:
            print(f"Gemini error: {e}")
    reply = rule_reply(msg, crop, stage, sd, result, lang)
    return jsonify({"reply": reply, "source":"offline"})

@app.route("/status")
def status():
    return jsonify({"gemini_ready": gemini_ready, "models_loaded": True, "crops": list(CC.keys())})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
