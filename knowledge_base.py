# -*- coding: utf-8 -*-
"""
EcoSense Agricultural Knowledge Base & Offline Domain Engine.
Provides deep agronomy, plant pathology, fertilizer nutrition,
water salinity, and sensor diagnostic intelligence in English and Tamil.
"""

from typing import Dict, Any, List

CROP_NAMES = {
    "rice": {"en": "Rice (Paddy)", "ta": "நெல்"},
    "maize": {"en": "Maize (Corn)", "ta": "மக்காச்சோளம்"},
    "groundnut": {"en": "Groundnut (Peanut)", "ta": "நிலக்கடலை"},
    "sugarcane": {"en": "Sugarcane", "ta": "கரும்பு"},
    "coconut": {"en": "Coconut Palm", "ta": "தென்னை"}
}

# 1. Extensive Crop Disease & Pest Database
DISEASE_PEST_DB = {
    "blast": {
        "crops": ["rice"],
        "keywords": ["blast", "pyricularia", "spindle", "கருகல்", "குலை நோய்", "குலைநோய்"],
        "en": (
            "🌾 **Rice Blast Disease (*Pyricularia oryzae*)**\n"
            "- **Symptoms**: Spindle-shaped lesions with grey centres and brown margins on leaves; rotting neck/nodes during flowering.\n"
            "- **Organic Control**: Spray 5% Neem seed kernel extract (NSKE) or *Pseudomonas fluorescens* @ 10g/Litre.\n"
            "- **Chemical Control**: Spray Tricyclazole 75% WP @ 0.6 g/L or Kasugamycin @ 1.5 ml/L at first sign of lesions.\n"
            "- **Agronomic Tip**: Avoid excessive Nitrogen (Urea) application during active tillering and cloudy weather."
        ),
        "ta": (
            "🌾 **நெல் குலை நோய் (Blast Disease)**\n"
            "- **அறிகுறிகள்**: இலைகளில் கண் வடிவிலான அல்லது கதிர் போன்ற புள்ளிகள், சாம்பல் நிற மையம், பழுப்பு நிற விளிம்புகள்.\n"
            "- **இயற்கை கட்டுப்பாடு**: வேப்பங்கொட்டை சாறு 5% அல்லது *சூடோமோனாஸ் புளோரசன்ஸ்* (Pseudomonas) லிட்டருக்கு 10 கிராம் தெளிக்கவும்.\n"
            "- **ரசாயன கட்டுப்பாடு**: டிரைசைக்ளசோல் 75% WP (Tricyclazole) லிட்டருக்கு 0.6 கிராம் வீதம் தெளிக்கவும்.\n"
            "- **முக்கிய குறிப்பு**: தழைச்சத்து (Urea) உரங்களை அதிகமாக இடுவதைத் தவிர்க்கவும்."
        )
    },
    "sheath_blight": {
        "crops": ["rice"],
        "keywords": ["sheath", "blight", "rhizoctonia", "உறை கருகல்", "உறையழுகல்", "தாளழுகல்"],
        "en": (
            "🌾 **Rice Sheath Blight (*Rhizoctonia solani*)**\n"
            "- **Symptoms**: Snake-skin like greenish-grey oval lesions on leaf sheaths near the water level.\n"
            "- **Control**: Spray Validamycin 3% L @ 2.5 ml/L or Hexaconazole 5% EC @ 2 ml/L.\n"
            "- **Cultural Practice**: Maintain proper spacing; avoid excessive dense planting and drain excess stagnant water."
        ),
        "ta": (
            "🌾 **நெல் உறை அழுகல் / உறை கருகல் நோய்**\n"
            "- **அறிகுறிகள்**: நீர் மட்டத்திற்கு மேல் உள்ள தாள் உறைகளில் பாம்பு தோல் போன்ற சாம்பல் பச்சை புள்ளிகள்.\n"
            "- **கட்டுப்பாடு**: வேலிடமைசின் 3% L (Validamycin) லிட்டருக்கு 2.5 மிலி அல்லது ஹெக்ஸாகோனசோல் லிட்டருக்கு 2 மிலி தெளிக்கவும்.\n"
            "- **குறிப்பு**: அதிக அடர்த்தியாக நடவு செய்வதைத் தவிர்க்கவும், தேங்கிய நீரை வடிக்கவும்."
        )
    },
    "stem_borer": {
        "crops": ["rice"],
        "keywords": ["stem borer", "borer", "dead heart", "white ear", "தண்டு துளைப்பான்", "குருத்து பூச்சி"],
        "en": (
            "🌾 **Rice Yellow Stem Borer (*Scirpophaga incertulas*)**\n"
            "- **Symptoms**: 'Dead heart' in vegetative stage (drying of central shoot); 'White earhead' with chaffy grains during reproductive stage.\n"
            "- **Biological**: Install pheromone traps @ 5 per acre; release *Trichogramma japonicum* egg parasitoids.\n"
            "- **Chemical**: Apply Chlorantraniliprole 18.5% SC @ 0.3 ml/L or Cartap hydrochloride 4G @ 10 kg/acre."
        ),
        "ta": (
            "🌾 **நெல் தண்டு துளைப்பான் (Yellow Stem Borer)**\n"
            "- **அறிகுறிகள்**: பயிர் வளர்ச்சிப் பருவத்தில் நடுக்குருத்து காய்ந்து போதல் (Dead Heart), பால் பிடிக்கும் பருவத்தில் வெண்கதிர் தோன்றுதல்.\n"
            "- **இயற்கை முறை**: ஏக்கருக்கு 5 இனக்கவர்ச்சி பொறிகள் வைக்கவும்; டிரைக்கோடெர்மா முட்டை ஒட்டுண்ணிகளை கட்டவும்.\n"
            "- **கட்டுப்பாடு**: குளோரான்ட்ரானிலிப்ரோல் (Coragen) லிட்டருக்கு 0.3 மிலி தெளிக்கவும்."
        )
    },
    "fall_armyworm": {
        "crops": ["maize"],
        "keywords": ["armyworm", "fall army", "faw", "படைப்புழு", "மக்காச்சோள படைப்புழு"],
        "en": (
            "🌽 **Maize Fall Armyworm (*Spodoptera frugiperda*)**\n"
            "- **Symptoms**: Ragged leaf feeding holes with large amounts of sawdust-like fecal matter inside the whorl.\n"
            "- **Biological**: Apply *Bacillus thuringiensis* (Bt) @ 2g/L or Metarhizium anisopliae @ 5g/L into leaf whorls.\n"
            "- **Chemical**: Spray Emamectin benzoate 5% SG @ 0.4 g/L or Spinetoram 11.7% SC @ 0.5 ml/L directed into the whorl."
        ),
        "ta": (
            "🌽 **மக்காச்சோள படைப்புழு (Fall Armyworm)**\n"
            "- **அறிகுறிகள்**: இலைகளில் ஒழுங்கற்ற துளைகள், சுருண்ட இலைகளுக்குள் மரத்தூள் போன்ற புழுக்களின் கழிவு.\n"
            "- **இயற்கை முறை**: பேசிலஸ் துரிஞ்சியென்சிஸ் (Bt) லிட்டருக்கு 2 கிராம் அல்லது வேப்ப எண்ணெய் தெளிக்கவும்.\n"
            "- **ரசாயன முறை**: எமாமெக்டின் பென்சோயேட் (Emamectin Benzoate 5% SG) லிட்டருக்கு 0.4 கிராம் வீதம் பயிரின் குருத்துப் பகுதியில் நன்கு படும்படி தெளிக்கவும்."
        )
    },
    "tikka_disease": {
        "crops": ["groundnut"],
        "keywords": ["tikka", "cercospora", "leaf spot", "டிக்கா", "இலைப்புள்ளி"],
        "en": (
            "🥜 **Groundnut Tikka Leaf Spot (*Cercospora arachidicola*)**\n"
            "- **Symptoms**: Dark brown circular spots with bright yellow chlorotic halos on upper leaves, premature leaf fall.\n"
            "- **Control**: Spray Mancozeb 75% WP @ 2g/L or Carbendazim 50% WP @ 1g/L at 10-15 day intervals."
        ),
        "ta": (
            "🥜 **நிலக்கடலை டிக்கா இலைப்புள்ளி நோய் (Tikka Disease)**\n"
            "- **அறிகுறிகள்**: இலைகளின் மேல் பகுதியில் மஞ்சள் வளையத்துடன் கூடிய அடர் பழுப்பு நிற வட்டப்புள்ளிகள், இலைகள் உதிர்தல்.\n"
            "- **கட்டுப்பாடு**: மேன்கோசெப் (Mancozeb) லிட்டருக்கு 2 கிராம் அல்லது கார்பென்டாசிம் லிட்டருக்கு 1 கிராம் தெளிக்கவும்."
        )
    },
    "red_rot": {
        "crops": ["sugarcane"],
        "keywords": ["red rot", "colletotrichum", "செவ்வழுகல்", "கரும்பு அழுகல்"],
        "en": (
            "🎋 **Sugarcane Red Rot (*Colletotrichum falcatum*)**\n"
            "- **Symptoms**: Discoloration of 3rd and 4th leaves; longitudinal reddening of internal stalk with distinct white transverse bands and alcoholic odor.\n"
            "- **Remedy**: Remove and burn affected clumps immediately. Treat seed setts with hot water (52°C for 30 mins) or Carbendazim @ 1g/L prior to planting."
        ),
        "ta": (
            "🎋 **கரும்பு செவ்வழுகல் நோய் (Red Rot)**\n"
            "- **அறிகுறிகள்**: கரும்பு தண்டின் உட்பகுதி சிவந்து குறுக்குவெட்டு வெள்ளை பட்டைகளுடன் சாராய வாசனை அடித்தல், இலைகள் காய்ந்து போதல்.\n"
            "- **கட்டுப்பாடு**: பாதிக்கப்பட்ட கரும்புகளை உடனே வேரோடு பிடுங்கி எரிக்கவும். விதைக்கரணைகளை கார்பென்டாசிம் (1g/L) அல்லது வெந்நீர் நேர்த்தி (52°C 30 நிமிடம்) செய்து நடவும்."
        )
    },
    "rhinoceros_beetle": {
        "crops": ["coconut"],
        "keywords": ["rhinoceros", "beetle", "v cut", "வண்டு", "காண்டாமிருக வண்டு"],
        "en": (
            "🌴 **Coconut Rhinoceros Beetle (*Oryctes rhinoceros*)**\n"
            "- **Symptoms**: Characteristic 'V' shaped geometric cuts on newly opened fronds; bored holes in the crown.\n"
            "- **Remedy**: Place a mixture of sand and Neem cake (1:1) in leaf axils. Use pheromone traps (Oryctalure) @ 1 per 2 acres."
        ),
        "ta": (
            "🌴 **தென்னை காண்டாமிருக வண்டு (Rhinoceros Beetle)**\n"
            "- **அறிகுறிகள்**: விரியும் தென்னை ஓலைகளில் 'V' வடிவ வெட்டுக்கள், குருத்து பகுதியில் துளைகள்.\n"
            "- **கட்டுப்பாடு**: மட்டைகளின் இடுக்குகளில் மணல் + வேப்பம்பிண்ணாக்கு சமஅளவு கலந்து வைக்கவும். ஏக்கருக்கு 1 இனக்கவர்ச்சி பொறி வைக்கவும்."
        )
    }
}

# 2. Comprehensive Fertilizer & Soil Nutrition Guide
FERTILIZER_GUIDE = {
    "rice": {
        "en": (
            "🌾 **Fertilizer Recommendation for Rice (Paddy)**\n"
            "- **Basal Dose**: Apply 50% P (DAP/Super Phosphate), 25% N (Urea), and 33% K (Potash) before final leveling.\n"
            "- **Active Tillering (20-25 DAT)**: Top dress 50% N (Urea) with Zinc Sulphate (25 kg/acre if deficient).\n"
            "- **Panicle Initiation (40-45 DAT)**: Apply remaining 25% N and 33% Potash for plump grain formation.\n"
            "- **Organic Booster**: Apply Panchakavya (3% spray) or Jeevamrutham (200L/acre via irrigation water)."
        ),
        "ta": (
            "🌾 **நெல்லுக்கான உரப் பரிந்துரை (Fertilizer Schedule)**\n"
            "- **அடி உரம் (Basal)**: நடவுக்கு முன் DAP / சூப்பர் பாஸ்பேட், பொட்டாஷ் 33% மற்றும் தழைச்சத்து 25% இடவும்.\n"
            "- **தூர்கட்டும் பருவம் (20-25 நாட்கள்)**: தழைச்சத்து (Urea) 50% மற்றும் ஜிங்க் சல்பேட் 25 கிலோ/ஏக்கர் இடவும்.\n"
            "- **கதிர் உருவாகும் பருவம் (40-45 நாட்கள்)**: மீதமுள்ள 25% யூரியா மற்றும் 33% பொட்டாஷ் இடவும் (மணிகள் திரட்சியாக வளர உதவும்).\n"
            "- **இயற்கை உரம்**: பாசன நீரில் ஜீவாமிர்தம் (ஏக்கருக்கு 200 லிட்டர்) அல்லது பஞ்சகாவ்யா 3% தெளிக்கவும்."
        )
    },
    "maize": {
        "en": (
            "🌽 **Fertilizer Recommendation for Maize**\n"
            "- **Basal**: Apply full dose of Phosphorus (DAP) and Potash (MOP), plus 25% Nitrogen.\n"
            "- **Knee-High Stage (30 DAS)**: Top dress 50% Nitrogen (Urea) along with earthing-up.\n"
            "- **Tasseling / Silking Stage**: Top dress remaining 25% Nitrogen to enhance cob size.\n"
            "- **Micronutrient**: Apply Zinc Sulphate 10 kg/acre to prevent white bud disease."
        ),
        "ta": (
            "🌽 **மக்காச்சோளத்திற்கான உரப் பரிந்துரை**\n"
            "- **அடி உரம்**: முழு அளவு மணிச்சத்து (DAP), சாம்பல் சத்து (Potash) மற்றும் 25% தழைச்சத்து (Urea) இடவும்.\n"
            "- **முழங்கால் உயர பருவம் (30 நாட்கள்)**: 50% யூரியா உரம் இட்டு மண் அணைக்கவும்.\n"
            "- **பூக்கும்/கதிர் வரும் பருவம்**: மீதமுள்ள 25% யூரியா இட்டு கதிர்கள் பெரிதாக வளர உதவவும்.\n"
            "- **நுண்ணூட்டம்**: வெண்குருத்து நோய் வராமல் தடுக்க ஜிங்க் சல்பேட் 10 கிலோ/ஏக்கர் இடவும்."
        )
    },
    "groundnut": {
        "en": (
            "🥜 **Fertilizer Recommendation for Groundnut**\n"
            "- **Basal**: 10:40:40 kg NPK per acre + 200 kg Gypsum at flowering/pegging (40-45 DAS).\n"
            "- **Importance of Gypsum**: Calcium is vital for proper pod development and preventing pops (empty shells).\n"
            "- **Biofertilizers**: Seed treatment with *Rhizobium* culture enhances nitrogen fixation."
        ),
        "ta": (
            "🥜 **நிலக்கடலைக்கான உரப் பரிந்துரை**\n"
            "- **அடி உரம்**: ஏக்கருக்கு 10:40:40 கிலோ NPK இடவும்.\n"
            "- **ஜிப்சம் இடுதல்**: பூத்து விழுது இறங்கும் பருவத்தில் (40-45 நாட்கள்) ஏக்கருக்கு 200 கிலோ ஜிப்சம் இடவும் (காய் திரட்சியாகவும் சப்பைகள் இல்லாமலும் இருக்க கால்சியம் மிக முக்கியம்).\n"
            "- **உயிர் உரம்**: விதைக்கும் முன் ரைசோபியம் (Rhizobium) கொண்டு விதை நேர்த்தி செய்யவும்."
        )
    },
    "sugarcane": {
        "en": (
            "🎋 **Fertilizer Recommendation for Sugarcane**\n"
            "- **Basal**: 25% N, 100% P, and 33% K at planting.\n"
            "- **Tillering (30-45 days)**: 25% N with light earthing up.\n"
            "- **Grand Growth (90-120 days)**: Remaining 50% N and 67% K with final earthing-up to prevent lodging."
        ),
        "ta": (
            "🎋 **கரும்புக்கான உரப் பரிந்துரை**\n"
            "- **அடி உரம்**: நடவின் போது 25% தழைச்சத்து, 100% மணிச்சத்து மற்றும் 33% சாம்பல் சத்து இடவும்.\n"
            "- **தூர்கட்டும் பருவம் (30-45 நாட்கள்)**: 25% யூரியா இட்டு லேசான மண் அணைக்கவும்.\n"
            "- **துரித வளர்ச்சிப் பருவம் (90-120 நாட்கள்)**: மீதி 50% யூரியா மற்றும் 67% பொட்டாஷ் இட்டு பெரிய மண் அணைப்பு செய்யவும்."
        )
    },
    "coconut": {
        "en": (
            "🌴 **Nutrient Management for Coconut**\n"
            "- **Per Tree / Year**: 1.3 kg Urea, 2 kg Super Phosphate, 2 kg Muriate of Potash in two splits (May-June & Sept-Oct).\n"
            "- **Organic**: Apply 50 kg Farm Yard Manure (FYM) or green manure per palm annually.\n"
            "- **Micronutrients**: Apply 500g Magnesium Sulphate and 100g Borax around the drip circle."
        ),
        "ta": (
            "🌴 **தென்னைக்கான உர மேலாண்மை**\n"
            "- **மரம் ஒன்றுக்கு ஆண்டுதோறும்**: 1.3 கிலோ யூரியா, 2 கிலோ சூப்பர் பாஸ்பேட், 2 கிலோ பொட்டாஷ் இரண்டு தவணைகளாக (மே-ஜூன் & செப்-அக்) இடவும்.\n"
            "- **இயற்கை உரம்**: ஆண்டுக்கு 50 கிலோ தொழு உரம் அல்லது பசுந்தாள் உரம் வட்டப்பாத்தியில் இடவும்.\n"
            "- **நுண்ணூட்டம்**: மரத்திற்கு 500 கிராம் மெக்னீசியம் சல்பேட் மற்றும் 100 கிராம் போராக்ஸ் இடவும்."
        )
    }
}

# 3. Water Salinity & TDS Remediation Guide
def get_salinity_guide(tds: float, max_tds: float, crop: str, lang: str) -> str:
    is_ta = (lang == "ta")
    cta = CROP_NAMES.get(crop, {}).get("ta", crop) if is_ta else CROP_NAMES.get(crop, {}).get("en", crop)
    
    if tds > max_tds:
        if is_ta:
            return (
                f"⚠️ **பாசன நீர் தற்போது பாதுகாப்பாக இல்லை.** தண்ணீரில் உப்புத்தன்மை (TDS) {cta} பயிருக்கான உகந்த அளவை விட அதிகமாக உள்ளது. "
                "இது பயிரின் வேர்களை எரித்து வளர்ச்சியைப் பாதிக்கும் என்பதால் நல்ல நீருடன் கலந்து பயன்படுத்தவும் அல்லது ஜிப்சம் இட்டு உவர்த்தன்மையை குறைக்கவும்."
            )
        else:
            return (
                f"⚠️ **The water is not safe for irrigation right now.** Salinity (TDS) exceeds the safe limit for {cta}. "
                "Pumping this water will burn the roots and cause osmotic stress. Please dilute the water source with fresh rainwater or treat it before irrigating."
            )
    else:
        if is_ta:
            return f"✅ **பாசன நீர் பாதுகாப்பாக உள்ளது.** நீரின் உப்புத்தன்மை {cta} பயிரின் பாதுகாப்பான வரம்பிற்குள் உள்ளது. தாராளமாக பாசனம் செய்யலாம்."
        else:
            return f"✅ **The water is safe for irrigation!** Salinity (TDS) is well within the healthy limit for {cta}."


def get_gas_safety_guide(sensors: Dict[str, Any], lang: str) -> str:
    is_ta = (lang == "ta")
    nh3 = float(sensors.get("mq135_ammonia", 0))
    ch4 = float(sensors.get("mq4_methane", 0))
    co = float(sensors.get("mq7_co", 0))
    smoke = float(sensors.get("mq2_smoke", 0))
    
    has_hazard = (nh3 > 100 or ch4 > 500 or co > 35 or smoke > 80)
    
    if has_hazard:
        if is_ta:
            return "⚠️ **எச்சரிக்கை: வயலில் வாயு அபாயம் உள்ளது!** அம்மோனியா அல்லது மீத்தேன் வாயு அதிகரித்துள்ளது. பாதுகாப்புக்காக பம்ப் பூட்டப்பட்டுள்ளது. வயலில் காற்றோட்டத்தை சரிசெய்யவும்."
        else:
            return "⚠️ **Warning: Hazardous gas spikes detected in the field!** Elevated Ammonia or Methane levels can harm crop roots. The irrigation pump is locked for safety. Please check compost areas and field aeration."
    else:
        if is_ta:
            return "✅ **வயலில் காற்றுத்தரம் சீராகவும் பாதுகாப்பாகவும் உள்ளது.** தீங்கு விளைவிக்கும் வாயுக்கள் ஏதுமில்லை."
        else:
            return "✅ **Air quality around the field is safe and normal.** Gas levels are well within healthy limits."


def query_knowledge_base(
    query: str,
    crop: str,
    stage: str,
    sensors: Dict[str, Any],
    pred_result: Dict[str, Any],
    crop_cfg: Dict[str, Any],
    lang: str = "en",
    weather: Optional[Dict[str, Any]] = None
) -> str:
    weather = weather or {}
    city = weather.get("city", "Tiruchirappalli")
    w_temp = weather.get("temp")
    w_hum = weather.get("humidity")
    rain_mm = weather.get("total_rain_mm", 0)
    rain_coming = bool(weather.get("rain_coming"))
    heat_coming = bool(weather.get("heat_coming"))
    w_summary = weather.get("summary", "Stable weather next 24h")
    w_enabled = bool(weather.get("enabled", False))
    q = query.lower().strip()
    is_ta = (lang == "ta")
    moist = float(sensors.get("soil_moisture", 0))
    tds = float(sensors.get("tds_ppm", 0))
    cta = CROP_NAMES.get(crop, {}).get("ta", crop) if is_ta else CROP_NAMES.get(crop, {}).get("en", crop)
    max_tds = crop_cfg.get("tds_max", 800)
    min_moist = crop_cfg.get("moist_min", 60)
    
    is_drought = (moist < min_moist) or bool(pred_result.get("is_drought")) or (moist < 40)
    pump_locked = bool(pred_result.get("pump_locked"))
    gas_alert = bool(pred_result.get("gas_alert"))
    tds_safe = bool(pred_result.get("tds_safe", tds <= max_tds))
    irrigate_now = bool(pred_result.get("irrigate_now")) or is_drought

    # 1. Project & Hardware Queries
    if any(k in q for k in ["ecosense", "project", "hardware", "esp32", "sensor", "iot", "architecture", "திட்டம்", "சென்சார்"]):
        if is_ta:
            return (
                "🌱 **EcoSense** என்பது ESP32 IoT சாதனம் மற்றும் AI/ML மூலம் பாசனத்தை தானியங்கி முறையில் கட்டுப்படுத்தி "
                "பயிர்களைப் பாதுகாக்கும் நவீன ஸ்மார்ட் விவசாய அமைப்பாகும். இதில் மண் ஈரப்பதம், நீரின் உப்புத்தன்மை (TDS) "
                "மற்றும் வாயு சென்சார்கள் இணைக்கப்பட்டுள்ளன."
            )
        else:
            return (
                "🌱 **EcoSense** is an autonomous precision agriculture system. It connects an ESP32 microcontroller with "
                "capacitive soil moisture, water salinity (TDS), and gas sensors to machine learning models, automating irrigation "
                "and locking pumps during salinity or gas hazards."
            )

    # 2. Specific Diseases & Pests FIRST
    for pest_key, data in DISEASE_PEST_DB.items():
        if any(kw in q for kw in data["keywords"]):
            return data["ta" if is_ta else "en"]

    # 3. Water Quality & Salinity
    if any(k in q for k in ["tds", "salin", "salt", "water safe", "water quality", "உப்புத்தன்மை", "உவர்நீர்"]):
        return get_salinity_guide(tds, max_tds, crop, lang)

    # 4. Irrigation & Pump status (Weather-Aware & Drought-Aware)
    if any(k in q for k in ["irrigat", "pump", "water", "பாசனம்", "தண்ணீர்", "பம்ப்"]):
        if pump_locked:
            reason_en = "High Water Salinity (TDS)" if not tds_safe else "Gas Hazard" if gas_alert else "Safety Lock"
            reason_ta = "அதிக உவர்தன்மை (TDS)" if not tds_safe else "வாயு அபாயம்" if gas_alert else "பாதுகாப்பு பூட்டு"
            if is_ta:
                return (
                    f"🛑 **இல்லை, இப்போது பாசனம் செய்ய வேண்டாம்.** {reason_ta} காரணமாக பம்ப் தானாக பூட்டப்பட்டுள்ளது. "
                    "பயிரின் வேர்கள் சேதமடைவதைத் தடுக்க நீரின் தரத்தை சரிசெய்த பின் பாசனம் செய்யவும்."
                )
            else:
                return (
                    f"🛑 **No, do not irrigate right now.** The irrigation pump is locked due to {reason_en}. "
                    f"Safety interlocks protect your {cta} roots from toxic water or hazards. Please resolve the issue before watering."
                )
        elif rain_coming and rain_mm > 4:
            if is_ta:
                return (
                    f"🌦️ **{city} பகுதியில் விரைவில் மழை பெய்ய வாய்ப்புள்ளது ({rain_mm:.1f}மிமீ)!** "
                    f"மண்ணில் ஈரப்பதம் குறைவாக இருந்தாலும், பம்பை இயக்காமல் மழைநீரை பாசனத்திற்கு பயன்படுத்துவது மின்சாரத்தையும் நீரையும் மிச்சப்படுத்தும்."
                )
            else:
                return (
                    f"🌦️ **Rain is coming soon in {city} (around {rain_mm:.1f}mm expected)!** "
                    f"Even if the soil is dry, keep the pump on standby and let the incoming rain irrigate your {cta} crops naturally to save water and electricity."
                )
        elif is_drought or irrigate_now:
            if heat_coming:
                if is_ta:
                    return (
                        f"💧 **ஆம், உடனடியாக பாசனம் செய்யவும்!** கடுமையான வெப்பம் மற்றும் வறட்சி ({cta} பயிருக்கு நீர் அழுத்தம்) உள்ளதால், "
                        "ஆவியாவதைத் தடுக்க அதிகாலையிலேயே தண்ணீர் பாய்ச்சி பயிரை பாதுகாக்கவும்."
                    )
                else:
                    return (
                        f"💧 **Yes, irrigate your farm right away!** High heat and drought are stressing your {cta} crops. "
                        "Water early in the morning to prevent evaporation and rehydrate the root zone."
                    )
            else:
                if is_ta:
                    return (
                        f"💧 **ஆம், உடனடியாக பாசனம் செய்யவும்!** மண்ணில் ஈரப்பதம் மிகவும் குறைவாக உள்ளது ({cta} பயிருக்கு வறட்சி அழுத்தம் ஏற்பட்டுள்ளது). "
                        "இப்போது தண்ணீர் பாய்ச்சுவது பயிரை வறட்சியிலிருந்து காப்பாற்றும்."
                    )
                else:
                    return (
                        f"💧 **Yes, irrigate your farm right away!** The soil is critically dry for your {cta} crops and no significant rain is expected. "
                        "Turning on the water now will rehydrate the roots and prevent yield loss."
                    )
        elif moist > 88:
            if is_ta:
                return f"🌿 **பாசனம் தேவையில்லை.** வயலில் ஏற்கனவே நீர் அதிகமாக உள்ளது. வேர் அழுகலைத் தடுக்க அதிகப்படியான தண்ணீரை வடிய வைக்கவும்."
            else:
                return f"🌿 **No irrigation needed.** The soil already has excess moisture. Ensure proper drainage to avoid root rot."
        else:
            if rain_coming:
                if is_ta:
                    return f"🌿 **இப்போது பாசனம் தேவையில்லை.** மண்ணில் நல்ல ஈரப்பதம் உள்ளது மற்றும் {city} பகுதியில் மழையும் எதிர்பார்க்கப்படுகிறது. வடிகால் வசதியை சரிபார்க்கவும்."
                else:
                    return f"🌿 **No need to irrigate right now.** The soil has good moisture, and rain is also expected in {city}. Ensure drainage channels are clear."
            else:
                if is_ta:
                    return f"🌿 **இப்போது பாசனம் தேவையில்லை.** மண்ணில் தேவையான ஈரப்பதம் சீராக உள்ளது. பம்பை நிறுத்தி வைப்பது நல்லது."
                else:
                    return f"🌿 **No need to water right now.** The soil has plenty of healthy moisture, so keeping the pump off will protect root health and save water."

    # 5. Gas / Air Quality
    if any(k in q for k in ["gas", "ammonia", "methane", "air quality", "air safe", "aqi", "காற்று", "வாயு"]):
        return get_gas_safety_guide(sensors, lang)

    # 6. Fertilizers & Nutrients (Weather-Aware)
    if any(k in q for k in ["fertiliz", "urea", "dap", "potash", "npk", "manure", "உரம்", "சாணம்", "ஊட்டச்சத்து", "யூரியா"]):
        guide = FERTILIZER_GUIDE.get(crop, FERTILIZER_GUIDE["rice"])
        base_resp = guide.get("ta" if is_ta else "en", "")
        if rain_coming:
            w_warn = (
                f"\n\n🌦️ **வானிலை எச்சரிக்கை ({city}):** விரைவில் மழை வர வாய்ப்புள்ளதால் ({rain_mm:.1f}மிமீ), "
                "உரம் மழைநீரில் அடித்துச் செல்லப்படாமல் இருக்க மழை நின்ற பின் இடவும்."
                if is_ta else
                f"\n\n🌦️ **Weather Alert for {city}:** Rain ({rain_mm:.1f}mm) is approaching! "
                "Delay applying top-dress fertilizers or foliar sprays until after the rain passes so nutrients aren't washed away."
            )
            return base_resp + w_warn
        return base_resp

    # 7. General pest/disease question
    if any(k in q for k in ["pest", "disease", "insect", "bug", "worm", "பூச்சி", "நோய்"]):
        matched_entries = [d["ta" if is_ta else "en"] for d in DISEASE_PEST_DB.values() if crop in d["crops"]]
        if matched_entries:
            header = f"🐛 **{cta} பயிருக்கான முக்கிய பூச்சி மற்றும் நோய் பாதுகாப்பு:**\n\n" if is_ta else f"🐛 **Key Pest & Disease Management for {cta}:**\n\n"
            return header + "\n\n".join(matched_entries[:2])

    # 8. Overall Health & Diagnostics
    if any(k in q for k in ["health", "score", "status", "condition", "ஆரோக்கிய", "நிலைமை"]):
        hs = pred_result.get("health_status", "GOOD")
        if hs == "CRITICAL" or is_drought:
            if is_ta:
                return f"🚨 **{cta} பயிர் தீவிர வறட்சி அழுத்தத்தில் உள்ளது!** வாடுவதைத் தடுக்க உடனடியாக தண்ணீர் பாய்ச்சவும்."
            else:
                return f"🚨 **Your {cta} crops are experiencing severe drought stress right now!** Immediate irrigation is recommended to prevent leaf wilting and yield damage."
        elif hs == "POOR":
            if is_ta:
                return f"⚠️ **பயிரின் நிலை சற்று பலவீனமாக உள்ளது.** மண் ஈரப்பதத்தை கவனித்து உரிய பாசனம் அளிக்கவும்."
            else:
                return f"⚠️ **Your {cta} crop condition is poor.** Check moisture and field conditions today to help your crops recover."
        elif hs == "MODERATE":
            if is_ta:
                return f"🌱 **பயிர் நிலை சுமாராக உள்ளது.** வழக்கமான பாசனம் மற்றும் உரமிடுதலைத் தொடரவும்."
            else:
                return f"🌱 **Your {cta} crop condition is moderate.** Maintain regular watering and nutrient schedules."
        else:
            if is_ta:
                return f"🌱 **{cta} பயிர்கள் மிக ஆரோக்கியமாக வளர்கின்றன!** தற்போதைய பராமரிப்பு முறையைத் தொடரவும்."
            else:
                return f"🌱 **Your {cta} crops are in great health and growing well!** Moisture and soil conditions are ideal."

    # 9. Weather Advice & Meteorological Outlook
    if any(k in q for k in ["weather", "rain", "forecast", "climate", "temperature", "மழை", "வானிலை", "வெப்பநிலை", "வெப்பம்", "குளிர்"]):
        if w_enabled and w_temp is not None:
            if is_ta:
                tip = "மழை எதிர்பார்க்கப்படுவதால் உரம் இடுவதையோ மருந்து தெளிப்பதையோ மழை நின்ற பின் செய்யவும்." if rain_coming else "வெப்பம் அதிகமாக இருப்பதால் அதிகாலையிலேயே பாசனம் செய்யவும்." if heat_coming else "வானிலை சீராக உள்ளதால் வழக்கமான பணிகளை மேற்கொள்ளலாம்."
                return f"🌦️ **{city} வானிலை நிலவரம்:** தற்போது வெப்பநிலை {w_temp}°C, ஈரப்பதம் {w_hum}%. முன்னறிவிப்பு: {w_summary}. {tip}"
            else:
                tip = "Rain is expected soon, so hold off on foliar sprays and fertilizer top-dressing to prevent runoff." if rain_coming else "High heat ahead, so water crops in the early morning to reduce moisture evaporation." if heat_coming else "Weather conditions are stable and favorable for regular farm maintenance."
                return f"🌦️ **Weather in {city}:** Currently {w_temp}°C with {w_hum}% humidity. Forecast: {w_summary}. {tip}"
        else:
            wnote = pred_result.get("weather_note", "Stable weather next 24h")
            if is_ta:
                return f"🌦️ **வானிலை ஆலோசனை ({city})**: {wnote}. மழை எதிர்பார்க்கப்பட்டால் பூச்சிக்கொல்லி தெளிப்பதையும் உரமிடுவதையும் தற்காலிகமாக ஒத்திவைக்கவும்."
            else:
                return f"🌦️ **Weather Advisory ({city})**: {wnote}. If heavy rainfall is approaching, hold off on fertilizer top-dressing to prevent nutrient runoff."

    # 10. General Conversational Fallback (Simple, non-value-based)
    if is_ta:
        return f"🌱 நான் உங்கள் EcoSense விவசாய வழிகாட்டி. பாசனம், உர அட்டவணை, பூச்சி/நோய் தடுப்பு மற்றும் வானிலை குறித்து என்னிடம் கேட்கலாம்!"
    else:
        return f"🌱 I am your EcoSense farming companion. Ask me any practical question about irrigating your farm, fertilizers, pest control, or crop care!"
