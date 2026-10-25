# -*- coding: utf-8 -*-
"""
EcoSense Hybrid AI Engine.
Integrates Google Gemini Large Language Model with multi-turn chat memory,
deep project knowledge, real-time farm sensor telemetry,
and fallback to the local Agricultural Knowledge Base.
Operates strictly using server-side environment variables for security.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import knowledge_base

# Cascade of Gemini models to attempt
MODEL_CASCADE = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]

# Load local .env if present
def load_dotenv():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip('"\'')
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            print("Error reading .env:", e)

load_dotenv()

_active_model_name = None

def get_api_key() -> str:
    # Always read from server environment / local .env
    return os.environ.get("GEMINI_API_KEY", "").strip()

def is_gemini_available() -> bool:
    return bool(get_api_key())

def get_active_model_name() -> str:
    return _active_model_name or ("gemini-2.0-flash" if is_gemini_available() else "Offline KB")

def build_system_prompt(crop: str, stage: str, sensors: Dict[str, Any], pred_result: Dict[str, Any], crop_cfg: Dict[str, Any], weather: Dict[str, Any], lang: str) -> str:
    sm = float(sensors.get("soil_moisture", 0))
    tds = float(sensors.get("tds_ppm", 0))
    at = float(sensors.get("air_temp_c", 0))
    st = float(sensors.get("soil_temp_c", 0))
    hum = float(sensors.get("humidity_pct", 0))
    nh3 = float(sensors.get("mq135_ammonia", 0))
    ch4 = float(sensors.get("mq4_methane", 0))
    co = float(sensors.get("mq7_co", 0))
    
    score = pred_result.get("health_score", 100)
    status = pred_result.get("health_status", "GOOD")
    pump_locked = pred_result.get("pump_locked", False)
    irrigate_now = pred_result.get("irrigate_now", False)
    gas_alert = pred_result.get("gas_alert", False)
    tds_safe = pred_result.get("tds_safe", True)
    weather_note = pred_result.get("weather_note", "Stable weather")
    
    max_tds = crop_cfg.get("tds_max", 800)
    opt_moist = crop_cfg.get("moist_opt", 75)
    min_moist = crop_cfg.get("moist_min", 60)
    
    lang_instruction = (
        "Respond in fluent, natural, grammatically correct Tamil (தமிழ்). Use appropriate agricultural terminology."
        if lang == "ta"
        else "Respond in clear, professional English."
    )
    
    return f"""You are EcoSense AI, the intelligent companion and agronomic brain of the EcoSense Smart Precision Agriculture system.
You are intimately familiar with the EcoSense project architecture, sensors, machine learning models, and automation logic.
You also possess complete, unrestricted general AI intelligence: you can answer ANY question (whether about the EcoSense project, agriculture, plant pathology, computer science, or general topics) accurately, intelligently, and politely.

ABOUT THE ECOSENSE PROJECT:
- Purpose: An AI & IoT smart agriculture platform designed to monitor crop health, automate precision irrigation, detect toxic field gases, and prevent crop loss from salinity shock.
- Hardware & IoT: ESP32 microcontroller publishing real-time telemetry over Wi-Fi via HTTP POST to /esp32; Capacitive Soil Moisture Sensor v1.2 (0-100%); Gravity Analog TDS sensor measuring water salinity in ppm; MQ-135 (Ammonia NH3 & air quality); MQ-4 (Methane CH4); MQ-7 (Carbon Monoxide CO); DHT11/DHT22 ambient temperature & humidity sensors; 5V Relay module controlling irrigation pump actuator.
- Automated Safety Interlocks:
  1. High Salinity Lock: If water TDS exceeds the crop's threshold, the pump is automatically locked to prevent osmotic shock and root burning.
  2. Gas Hazard Lock: If MQ-135 (NH3 > 200ppm), MQ-4 (CH4 > 1000ppm), or MQ-7 (CO > 100ppm) exceed safety limits, pump is locked to eliminate spark hazards and workers are warned to evacuate.
- Machine Learning Models: Pre-trained scikit-learn models (Random Forest) for Crop Health Status (GOOD/MODERATE/POOR/CRITICAL), Urgent Irrigation Need (True/False), and Pump Lockout.
- Crops Supported: Rice (Paddy), Maize (Corn), Groundnut (Peanut), Sugarcane, Coconut, plus general crops.

LIVE FARM SENSORS & STATUS CONTEXT:
- Selected Crop: {crop} | Growth Stage: {stage}
- Soil Moisture: {sm:.1f}% (Minimum threshold: {min_moist}%, Optimal: {opt_moist}%)
- Water Salinity (TDS): {tds:.0f} ppm (Maximum safe limit for {crop}: {max_tds} ppm | Safe: {tds_safe})
- Climate: Air Temp {at:.1f}°C, Soil Temp {st:.1f}°C, Humidity {hum:.0f}%
- Air Quality / Hazardous Gas Sensors: NH3 (Ammonia): {nh3:.0f} ppm, CH4 (Methane): {ch4:.0f} ppm, CO: {co:.0f} ppm (Gas Alert: {gas_alert})
- Irrigation Actuator Status: Pump Locked: {pump_locked}, Irrigation Needed: {irrigate_now}
- Crop Health Score: {score}/100 ({status})
- Meteorological Outlook: {weather_note}

GUIDELINES:
1. When answering farm/crop questions, ground your advice in the live sensor values above. For example, explain why the pump is locked (high TDS or gas hazard) or if soil moisture is deficient.
2. When answering questions about the EcoSense project, explain its hardware, ML models, and safety features accurately.
3. When answering general questions, answer comprehensively like a complete, helpful AI assistant.
4. Formatting: Use rich GitHub Markdown with bold headings, bullet points, and numbered steps.
5. Language Requirement: {lang_instruction}
"""

def generate_chat_reply(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    crop: str = "rice",
    stage: str = "germination",
    sensors: Optional[Dict[str, Any]] = None,
    pred_result: Optional[Dict[str, Any]] = None,
    crop_cfg: Optional[Dict[str, Any]] = None,
    weather: Optional[Dict[str, Any]] = None,
    lang: str = "en"
) -> Dict[str, Any]:
    global _active_model_name
    
    sensors = sensors or {}
    pred_result = pred_result or {}
    crop_cfg = crop_cfg or {}
    weather = weather or {}
    history = history or []
    
    api_key = get_api_key()
    
    if api_key:
        sys_prompt = build_system_prompt(crop, stage, sensors, pred_result, crop_cfg, weather, lang)
        
        # 1. Try google.genai (new official SDK)
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=api_key)
            
            # Format contents from history
            contents = []
            for item in history[-6:]:  # Keep last 6 turns for memory
                role = "user" if item.get("role") == "user" else "model"
                text = item.get("text", "").strip()
                if text:
                    contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
            
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))
            
            for m_name in MODEL_CASCADE:
                try:
                    config = types.GenerateContentConfig(
                        system_instruction=sys_prompt,
                        temperature=0.7,
                        max_output_tokens=1024
                    )
                    resp = client.models.generate_content(
                        model=m_name,
                        contents=contents,
                        config=config
                    )
                    if resp and resp.text:
                        _active_model_name = m_name
                        return {
                            "reply": resp.text.strip(),
                            "source": "gemini",
                            "model": m_name,
                            "status": "ok"
                        }
                except Exception as inner_e:
                    continue
        except Exception as genai_err:
            pass

        # 2. Try google.generativeai (legacy SDK fallback)
        try:
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=api_key)
            
            for m_name in MODEL_CASCADE:
                try:
                    model = genai_legacy.GenerativeModel(
                        model_name=m_name,
                        system_instruction=sys_prompt
                    )
                    
                    chat_hist = []
                    for item in history[-6:]:
                        role = "user" if item.get("role") == "user" else "model"
                        text = item.get("text", "").strip()
                        if text:
                            chat_hist.append({"role": role, "parts": [text]})
                    
                    chat = model.start_chat(history=chat_hist)
                    resp = chat.send_message(message)
                    if resp and resp.text:
                        _active_model_name = m_name
                        return {
                            "reply": resp.text.strip(),
                            "source": "gemini",
                            "model": m_name,
                            "status": "ok"
                        }
                except Exception as inner_e:
                    continue
        except Exception as legacy_err:
            pass

    # 3. Fallback to Local Knowledge Base Engine
    _active_model_name = "Offline KB"
    kb_reply = knowledge_base.query_knowledge_base(
        query=message,
        crop=crop,
        stage=stage,
        sensors=sensors,
        pred_result=pred_result,
        crop_cfg=crop_cfg,
        lang=lang
    )
    
    return {
        "reply": kb_reply,
        "source": "offline",
        "model": "offline-kb",
        "status": "ok"
    }
