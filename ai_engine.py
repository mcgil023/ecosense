# -*- coding: utf-8 -*-
"""
EcoSense Hybrid AI Engine.
Integrates Google Gemini REST API (with SDK fallbacks) and Local Knowledge Base.
Provides simple, conversational, non-value-based agronomic guidance and general AI intelligence.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests

import knowledge_base

logger = logging.getLogger("ecosense.ai")

_active_key = ""
_active_model_name = ""

MODEL_CASCADE = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]

# Load local .env if present
def load_dotenv():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        try:
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip()
                        if k and not os.environ.get(k):
                            os.environ[k] = v.strip('"').strip("'")
        except Exception:
            pass

load_dotenv()


def get_api_key() -> str:
    global _active_key
    if _active_key:
        return _active_key
    return os.environ.get("GEMINI_API_KEY", "").strip()


def set_api_key(key: str) -> None:
    global _active_key
    _active_key = (key or "").strip()
    if _active_key:
        os.environ["GEMINI_API_KEY"] = _active_key
    elif "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]


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
    is_drought = pred_result.get("is_drought", sm < crop_cfg.get("moist_min", 60))
    weather_note = pred_result.get("weather_note", "Stable weather")
    
    max_tds = crop_cfg.get("tds_max", 800)
    opt_moist = crop_cfg.get("moist_opt", 75)
    min_moist = crop_cfg.get("moist_min", 60)
    
    lang_instruction = (
        "Respond in fluent, friendly, natural spoken Tamil (தமிழ்). Do NOT output English programming variables or raw tables."
        if lang == "ta"
        else "Respond in clear, friendly, conversational English."
    )
    
    return f"""You are EcoSense AI, the personal farming companion on the EcoSense Smart Agriculture dashboard.
You are an expert in agronomy, plant pathology, soil fertility, precision irrigation, and crop care.
You also possess complete general knowledge: you can answer any general question, science query, or user topic politely and intelligently.

CURRENT FIELD & CROP CONTEXT:
- Selected Crop: {crop} (Growth Stage: {stage})
- Soil Moisture Status: {"CRITICAL DROUGHT" if is_drought else "Optimal / Adequate"} (Current: {sm:.0f}%, Min Needed: {min_moist}%, Target: {opt_moist}%)
- Irrigation Pump: {"LOCKED FOR SAFETY (Salinity/Gas Hazard)" if pump_locked else "Available / Active" if irrigate_now else "Standby"}
- Water Salinity (TDS): {"DANGEROUSLY HIGH / SALINE" if not tds_safe else "Safe for irrigation"} ({tds:.0f} ppm, Max Safe: {max_tds} ppm)
- Air Quality: {"HAZARDOUS GAS SPIKE DETECTED" if gas_alert else "Safe and normal"}
- Crop Health: {status} ({score}/100)
- Meteorological Summary: {weather_note}

CRITICAL USER INSTRUCTIONS:
1. KEEP REPLIES SIMPLE, CONVERSATIONAL, DIRECT, AND ACTIONABLE.
2. DO NOT RECITE OR DUMP LISTS OF RAW SENSOR NUMBERS (e.g., NEVER write "Soil Moisture: {sm:.0f}%, TDS: {tds:.0f} ppm, Temp: {at:.1f}°C"). The user already sees all these sensor numbers and cards on the dashboard screen!
3. Provide direct answers in 2 to 4 friendly, practical sentences. Tell the farmer clearly what to do and why.
4. When asked about watering/irrigation:
   - If soil moisture is low or in drought ({is_drought}): Tell them clearly to IRRIGATE IMMEDIATELY to prevent crop loss (unless the pump is locked).
   - If the pump is locked due to high TDS or gas: Explain clearly that the pump is locked to protect root health from saline water or gas hazards.
   - If soil moisture is healthy: Reassure them that no watering is needed right now.
5. Language Requirement: {lang_instruction}
"""


def _call_gemini_rest(api_key: str, sys_prompt: str, message: str, history: List[Dict[str, str]]) -> Optional[str]:
    """Call Google Gemini using direct HTTP REST API."""
    contents = []
    for item in history[-6:]:
        role = "user" if item.get("role") == "user" else "model"
        text = (item.get("text") or "").strip()
        if text:
            contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    for m_name in MODEL_CASCADE:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": sys_prompt}]
            },
            "generationConfig": {
                "temperature": 0.6,
                "maxOutputTokens": 600
            }
        }
        try:
            r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
            if r.status_code == 200:
                data = r.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
            else:
                logger.warning("Gemini REST %s returned %s: %s", m_name, r.status_code, r.text[:200])
        except Exception as e:
            logger.warning("Gemini REST request error for %s: %s", m_name, e)
    return None


def generate_chat_reply(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    crop: str = "rice",
    stage: str = "germination",
    sensors: Optional[Dict[str, Any]] = None,
    pred_result: Optional[Dict[str, Any]] = None,
    crop_cfg: Optional[Dict[str, Any]] = None,
    weather: Optional[Dict[str, Any]] = None,
    lang: str = "en",
    custom_api_key: Optional[str] = None
) -> Dict[str, Any]:
    global _active_model_name
    
    sensors = sensors or {}
    pred_result = pred_result or {}
    crop_cfg = crop_cfg or {}
    weather = weather or {}
    history = history or []
    
    api_key = (custom_api_key or "").strip() or get_api_key()
    
    if api_key:
        sys_prompt = build_system_prompt(crop, stage, sensors, pred_result, crop_cfg, weather, lang)
        
        # 1. Primary: Direct Gemini REST API
        rest_reply = _call_gemini_rest(api_key, sys_prompt, message, history)
        if rest_reply:
            _active_model_name = "gemini-2.0-flash"
            return {
                "reply": rest_reply,
                "source": "gemini",
                "model": "gemini-2.0-flash",
                "status": "ok"
            }
        
        # 2. Secondary: Try official google.genai SDK
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=api_key)
            contents = []
            for item in history[-6:]:
                role = "user" if item.get("role") == "user" else "model"
                text = (item.get("text") or "").strip()
                if text:
                    contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))
            
            for m_name in MODEL_CASCADE:
                try:
                    config = types.GenerateContentConfig(
                        system_instruction=sys_prompt,
                        temperature=0.6,
                        max_output_tokens=600
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
                except Exception:
                    continue
        except Exception:
            pass

    # 3. Fallback to Local Knowledge Base Engine (Simple, conversational, non-value-based)
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
        "status": "ok",
        "has_gemini_key": bool(api_key)
    }
