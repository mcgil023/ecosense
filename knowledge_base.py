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
                f"🚨 **உயர் TDS உப்புத்தன்மை எச்சரிக்கை!**\n"
                f"- **தற்போதைய TDS**: {tds:.0f} ppm ({cta} பயிருக்கு அனுமதிக்கப்பட்ட உச்ச வரம்பு: {max_tds:.0f} ppm).\n"
                f"- **பாதிப்பு**: அதிக உப்பு வேர்களில் சவ்வூடுபரவல் அழுத்தத்தை (Osmotic Stress) உண்டாக்கி பயிரை கருக வைக்கும்.\n"
                f"- **தீர்வுகள்**:\n"
                f"  1. பம்ப் தானாக பூட்டப்பட்டுள்ளது. நன்னீர் கிடைக்கும் வரை இந்த நீரைப் பாய்ச்ச வேண்டாம்.\n"
                f"  2. நிலத்தில் ஏக்கருக்கு 200-500 கிலோ ஜிப்சம் இட்டு நிலத்தடி உப்பைக் குறைக்கவும்.\n"
                f"  3. மழை நீர் சேகரிப்பு அல்லது சுத்தமான நீருடன் கலந்து (Dilution) பாய்ச்சவும்.\n"
                f"  4. சொட்டு நீர் பாசனத்தில் அமில சிகிச்சை (Acid treatment) மூலம் உப்புகளைக் கரைக்கலாம்."
            )
        else:
            return (
                f"🚨 **High Salinity & TDS Warning!**\n"
                f"- **Current TDS**: {tds:.0f} ppm (Exceeds maximum safe limit of {max_tds:.0f} ppm for {cta}).\n"
                f"- **Crop Impact**: High salt concentration causes root osmotic shock and leaf tip scorching.\n"
                f"- **Remediation Steps**:\n"
                f"  1. Irrigation pump is locked to safeguard roots. Avoid pumping saline borehole water.\n"
                f"  2. Apply Gypsum @ 200-500 kg/acre to displace excess sodium ions from root zone.\n"
                f"  3. Dilute saline source with harvested rainwater where possible.\n"
                f"  4. Increase drainage channels to leach accumulated salts after irrigation."
            )
    else:
        if is_ta:
            return (
                f"✅ **நீர் தரம் பாதுகாப்பானது**\n"
                f"- **தற்போதைய TDS**: {tds:.0f} ppm (வரம்பு: <{max_tds:.0f} ppm).\n"
                f"- உப்பின் அளவு {cta} பயிரின் வேர்களுக்கு உகந்த வரம்பில் உள்ளது. பாசனத்திற்கு தாராளமாகப் பயன்படுத்தலாம்."
            )
        else:
            return (
                f"✅ **Water Quality is Safe & Optimal**\n"
                f"- **Current TDS**: {tds:.0f} ppm (Well within safe limit of {max_tds:.0f} ppm for {cta}).\n"
                f"- Salt levels pose no risk to root osmotic absorption. Safe for regular irrigation."
            )

# 4. Gas & Air Quality Safety Assessment
def get_gas_safety_guide(sensors: Dict[str, Any], lang: str) -> str:
    is_ta = (lang == "ta")
    nh3 = float(sensors.get("mq135_ammonia", 0))
    ch4 = float(sensors.get("mq4_methane", 0))
    co = float(sensors.get("mq7_co", 0))
    is_gas_alert = (nh3 > 200 or ch4 > 1000 or co > 100)
    
    if is_gas_alert:
        if is_ta:
            return (
                f"⚠️ **அபாயகரமான வாயு எச்சரிக்கை (Field Gas Alert)!**\n"
                f"- **அளவீடுகள்**: NH3 (அம்மோனியா): {nh3:.0f} ppm | CH4 (மீத்தேன்): {ch4:.0f} ppm | CO (கார்பன் மோனாக்சைடு): {co:.0f} ppm.\n"
                f"- **காரணங்கள்**: அதிக நீர் தேங்கி அழுகிய கரிமப் பொருட்கள், சாணக் கழிவு வாயுக்கள், அல்லது வயல் எரிப்பு.\n"
                f"- **பாதுகாப்பு வழிகாட்டல்**:\n"
                f"  1. விவசாயப் பணியாளர்கள் உடனடியாக அப்பகுதியிலிருந்து தற்காலிகமாக வெளியேறவும்.\n"
                f"  2. பாசன பம்ப் உடனடியாக பூட்டப்பட்டுள்ளது (மின்னணு தீப்பொறி அபாயத்தைத் தடுக்க).\n"
                f"  3. வயலில் தேங்கியுள்ள கழிவுநீரை வடித்து காற்றோட்டம் ஏற்படுத்தவும்."
            )
        else:
            return (
                f"⚠️ **Hazardous Field Gas Alert!**\n"
                f"- **Readings**: NH3: {nh3:.0f} ppm | CH4: {ch4:.0f} ppm | CO: {co:.0f} ppm.\n"
                f"- **Causes**: Anaerobic rotting in stagnant water, slurry accumulation, or nearby biomass burning.\n"
                f"- **Action Protocol**:\n"
                f"  1. Farm workers must vacate the sensor zone until ventilation improves.\n"
                f"  2. Irrigation pump is locked to eliminate any spark hazards.\n"
                f"  3. Aerate stagnant trenches and clear rotting organic sludge."
            )
    else:
        if is_ta:
            return (
                f"🍃 **வயல்வெளி காற்று தரம் சிறப்பானது**\n"
                f"- அம்மோனியா (NH3): {nh3:.0f} ppm | மீத்தேன் (CH4): {ch4:.0f} ppm | கார்பன் மோனாக்சைடு (CO): {co:.0f} ppm.\n"
                f"- நச்சு வாயுக்கள் எதுவும் இல்லை. பண்ணை சுற்றுச்சூழல் ஆரோக்கியமாக உள்ளது."
            )
        else:
            return (
                f"🍃 **Field Air Quality is Safe & Healthy**\n"
                f"- NH3: {nh3:.0f} ppm | CH4: {ch4:.0f} ppm | CO: {co:.0f} ppm.\n"
                f"- No toxic gas accumulation detected. Safe working environment."
            )

# 5. Core Offline Engine Matcher
def query_knowledge_base(
    query: str,
    crop: str,
    stage: str,
    sensors: Dict[str, Any],
    pred_result: Dict[str, Any],
    crop_cfg: Dict[str, Any],
    lang: str = "en"
) -> str:
    q = query.lower().strip()
    is_ta = (lang == "ta")
    moist = float(sensors.get("soil_moisture", 0))
    tds = float(sensors.get("tds_ppm", 0))
    temp = float(sensors.get("air_temp_c", 0))
    hum = float(sensors.get("humidity_pct", 0))
    cta = CROP_NAMES.get(crop, {}).get("ta", crop) if is_ta else CROP_NAMES.get(crop, {}).get("en", crop)
    max_tds = crop_cfg.get("tds_max", 800)
    opt_moist = crop_cfg.get("moist_opt", 75)
    min_moist = crop_cfg.get("moist_min", 60)

    # 1. Check Specific Diseases & Pests FIRST (avoid accidental substring matches)
    for pest_key, data in DISEASE_PEST_DB.items():
        if any(kw in q for kw in data["keywords"]):
            return data["ta" if is_ta else "en"]

    # 2. Water Quality & Salinity
    if any(k in q for k in ["tds", "salin", "salt", "water safe", "water quality", "நீர் தரம்", "உப்பு"]):
        return get_salinity_guide(tds, max_tds, crop, lang)

    # 3. Irrigation & Pump status
    if any(k in q for k in ["irrigat", "pump", "water", "பாசன", "நீர்", "பம்ப்"]):
        if pred_result.get("pump_locked"):
            reason_en = "High Salinity (TDS)" if not pred_result.get("tds_safe") else "Gas Alert" if pred_result.get("gas_alert") else "Critical Crop Stress"
            reason_ta = "அதிக உப்புத்தன்மை (TDS)" if not pred_result.get("tds_safe") else "வாயு கசிவு எச்சரிக்கை" if pred_result.get("gas_alert") else "கடுமையான பயிர் அழுத்தம்"
            if is_ta:
                return (
                    f"🛑 **பம்ப் தானாகப் பூட்டப்பட்டுள்ளது (Pump Locked)!**\n"
                    f"- **காரணம்**: {reason_ta}.\n"
                    f"- **மண் ஈரப்பதம்**: {moist:.0f}% (தேவை: {min_moist}%).\n"
                    f"- பயிரின் வேர்கள் சேதமடையாமல் இருக்க பம்ப் பாதுகாப்பு முறையில் வைக்கப்பட்டுள்ளது."
                )
            else:
                return (
                    f"🛑 **Irrigation Pump is Automatically Locked!**\n"
                    f"- **Reason**: {reason_en}.\n"
                    f"- **Soil Moisture**: {moist:.0f}% (Optimal: {opt_moist}%).\n"
                    f"- Safety interlock prevents pumping damaged water into {cta} root zone."
                )
        if pred_result.get("irrigate_now"):
            if is_ta:
                return (
                    f"💧 **இப்போது பாசனம் செய்யவும் (Irrigate Now)!**\n"
                    f"- **தற்போதைய ஈரப்பதம்**: {moist:.0f}% (பரிந்துரை: {opt_moist}%, குறைந்தபட்சம்: {min_moist}%).\n"
                    f"- பயிர் பருவம்: **{stage}** — நீர் பற்றாக்குறை வளர்ச்சி மற்றும் விளைச்சலைப் பாதிக்கும்."
                )
            else:
                return (
                    f"💧 **Irrigation Recommended Now!**\n"
                    f"- **Current Moisture**: {moist:.0f}% (Target: {opt_moist}%, Minimum: {min_moist}%).\n"
                    f"- Growth Stage: **{stage}** — moisture stress at this stage will reduce yield."
                )
        else:
            if is_ta:
                return (
                    f"🌿 **தற்போது பாசனம் தேவையில்லை**\n"
                    f"- மண் ஈரப்பதம்: **{moist:.0f}%** போதுமான அளவில் உள்ளது (உகந்தது: {opt_moist}%).\n"
                    f"- அதிகப்படியான நீர் தேங்குவதைத் தவிர்க்கவும்."
                )
            else:
                return (
                    f"🌿 **No Irrigation Needed at Present**\n"
                    f"- Soil moisture is healthy at **{moist:.0f}%** (Optimal: {opt_moist}%).\n"
                    f"- Prevents waterlogging and root rot."
                )

    # 4. Gas / Air Quality
    if any(k in q for k in ["gas", "ammonia", "methane", "air quality", "air safe", "aqi", "காற்று", "வாயு"]):
        return get_gas_safety_guide(sensors, lang)

    # 5. Fertilizers & Nutrients
    if any(k in q for k in ["fertiliz", "urea", "dap", "potash", "npk", "manure", "உரம்", "சாணம்", "ஊட்டச்சத்து", "யூரியா"]):
        guide = FERTILIZER_GUIDE.get(crop, FERTILIZER_GUIDE["rice"])
        return guide.get("ta" if is_ta else "en", "")

    # 6. General pest/disease question
    if any(k in q for k in ["pest", "disease", "insect", "bug", "worm", "பூச்சி", "நோய்"]):
        matched_entries = [d["ta" if is_ta else "en"] for d in DISEASE_PEST_DB.values() if crop in d["crops"]]
        if matched_entries:
            header = f"🐛 **{cta} பயிருக்கான முக்கிய பூச்சி மற்றும் நோய் மேலாண்மை:**\n\n" if is_ta else f"🐛 **Key Pest & Disease Management for {cta}:**\n\n"
            return header + "\n\n".join(matched_entries[:2])

    # 7. Overall Health & Diagnostics
    if any(k in q for k in ["health", "score", "status", "condition", "ஆரோக்கிய", "நிலைமை"]):
        hs = pred_result.get("health_status", "GOOD")
        sc = pred_result.get("health_score", 85)
        aqi_label = pred_result.get("field_aqi_label", "Good")
        if is_ta:
            return (
                f"📊 **{cta} பயிர் ஆரோக்கிய சுருக்கம்**\n"
                f"- **ஆரோக்கிய மதிப்பெண்**: {sc}/100 ({hs})\n"
                f"- **பருவம்**: {stage}\n"
                f"- **மண் ஈரப்பதம்**: {moist:.0f}% | **மண் TDS**: {tds:.0f} ppm\n"
                f"- **வெப்பநிலை**: {temp:.1f}°C | **ஈரப்பதம்**: {hum:.0f}%\n"
                f"- **சுற்றுச்சூழல் AQI**: {aqi_label}"
            )
        else:
            return (
                f"📊 **{cta} Crop Health Diagnostic Summary**\n"
                f"- **Health Score**: {sc}/100 ({hs})\n"
                f"- **Current Stage**: {stage}\n"
                f"- **Soil Moisture**: {moist:.0f}% | **Salinity (TDS)**: {tds:.0f} ppm\n"
                f"- **Temperature**: {temp:.1f}°C | **Air Humidity**: {hum:.0f}%\n"
                f"- **Field AQI**: {aqi_label}"
            )

    # 8. Weather Advice
    if any(k in q for k in ["weather", "rain", "forecast", "climate", "மழை", "வானிலை"]):
        wnote = pred_result.get("weather_note", "Stable weather next 24h")
        if is_ta:
            return (
                f"🌦️ **வானிலை ஆலோசனை**\n"
                f"- **முன்னறிவிப்பு**: {wnote}\n"
                f"- **வெப்பநிலை**: {temp:.1f}°C | **ஈரப்பதம்**: {hum:.0f}%\n"
                f"- மழை எதிர்பார்க்கப்பட்டால் பூச்சிக்கொல்லி தெளிப்பதையும் உரமிடுவதையும் தற்காலிகமாக ஒத்திவைக்கவும்."
            )
        else:
            return (
                f"🌦️ **Weather & Agricultural Advisory**\n"
                f"- **Forecast**: {wnote}\n"
                f"- **Ambient Temp**: {temp:.1f}°C | **Air Humidity**: {hum:.0f}%\n"
                f"- If rain is forecasted, postpone foliar spraying and top-dress fertilizer applications to prevent runoff."
            )

    # 9. General AI Fallback
    safe_query = query.replace('"', "'")
    if is_ta:
        return (
            f"🌱 **EcoSense AI விவசாய வழிகாட்டி**\n\n"
            f"தங்களின் கேள்வி: *'{safe_query}'*\n"
            f"- **பயிர்**: {cta} (பருவம்: {stage})\n"
            f"- **கள நிலவரம்**: ஈரப்பதம் {moist:.0f}%, TDS {tds:.0f} ppm, வெப்பநிலை {temp:.1f}°C.\n\n"
            f"நீங்கள் என்னிடம் பாசனம், உர அட்டவணை, பூச்சி/நோய் தடுப்பு, மண் உப்புத்தன்மை மற்றும் வானிலை குறித்து கேட்கலாம்!\n\n"
            f"💡 *(முழுமையான திறந்தவெளி செயற்கை நுண்ணறிவை (Complete AI) இயக்க, தயவுசெய்து உங்கள் Google Gemini API Key ஐ Chat தலைப்பில் உள்ள '🔑 Key' பொத்தானில் இணைக்கவும்.)*"
        )
    else:
        return (
            f"🌱 **EcoSense Agricultural Intelligence Companion**\n\n"
            f"Regarding your query: *'{safe_query}'*\n"
            f"- **Crop**: {cta} (Growth Stage: {stage})\n"
            f"- **Live Conditions**: Soil Moisture {moist:.0f}%, TDS {tds:.0f} ppm, Temp {temp:.1f}°C.\n\n"
            f"You can ask me about irrigation timing, fertilizer schedules (NPK), pest/disease treatments, and water salinity!\n\n"
            f"💡 *(Tip: To unlock full general reasoning across any question, configure your Google Gemini API Key via the '🔑 Key' button in the chat header.)*"
        )
