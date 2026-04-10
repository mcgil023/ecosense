
function quickAsk(i) {
  const q = UI_STRINGS[uiLang].quickQuestions[i];
  if(q) { if(gid('chatInput')) gid('chatInput').value=q; sendChat(); }
}


// ── State ──────────────────────────────────────────────────────
let currentCrop = 'rice', cropStages = {};
let MODE = 'sim';
let liveInterval = null;

const SCENARIOS = {
  normal:   {soil_moisture:72,  tds_ppm:350,  air_temp_c:28, humidity_pct:65, soil_temp_c:24, mq135_ammonia:50,  mq4_methane:200,  mq7_co:10},
  dry:      {soil_moisture:28,  tds_ppm:420,  air_temp_c:34, humidity_pct:42, soil_temp_c:31, mq135_ammonia:60,  mq4_methane:220,  mq7_co:15},
  saline:   {soil_moisture:55,  tds_ppm:1200, air_temp_c:30, humidity_pct:58, soil_temp_c:27, mq135_ammonia:70,  mq4_methane:250,  mq7_co:20},
  gas:      {soil_moisture:68,  tds_ppm:360,  air_temp_c:29, humidity_pct:64, soil_temp_c:25, mq135_ammonia:260, mq4_methane:1400, mq7_co:140},
  heat:     {soil_moisture:48,  tds_ppm:500,  air_temp_c:41, humidity_pct:30, soil_temp_c:36, mq135_ammonia:80,  mq4_methane:300,  mq7_co:22},
  critical: {soil_moisture:18,  tds_ppm:1600, air_temp_c:43, humidity_pct:22, soil_temp_c:39, mq135_ammonia:320, mq4_methane:1800, mq7_co:170}
};

// Single source of truth for sensor values
let currentSensors = Object.assign({}, SCENARIOS.normal);

function gid(x)  { return document.getElementById(x); }
function setBar(id, p) { const el=gid(id); if(el) el.style.width = Math.max(4,Math.min(100,p))+'%'; }
function setText(id, t) { const el=gid(id); if(el) el.textContent = t; }

// ── Clock ───────────────────────────────────────────────────────
function clock() { if(gid('clock')) gid('clock').textContent = new Date().toLocaleTimeString(); }
setInterval(clock, 1000); clock();

// ── Mode Switch ─────────────────────────────────────────────────
function setMode(mode) {
  MODE = mode;
  const liveBtn = gid('btn-live'), simBtn = gid('btn-sim');
  const simBar  = gid('simbar'),   modeTag = gid('modeTag');

  if (MODE === 'live') {
    if(liveBtn) liveBtn.classList.add('active-mode');
    if(simBtn)  simBtn.classList.remove('active-mode');
    if(simBar)  simBar.style.opacity = '0.4';
    if(modeTag){ modeTag.textContent = '📡 LIVE'; modeTag.style.background='#1a4d1a'; }
    startLivePoll();
  } else {
    if(simBtn)  simBtn.classList.add('active-mode');
    if(liveBtn) liveBtn.classList.remove('active-mode');
    if(simBar)  simBar.style.opacity = '1';
    if(modeTag){ modeTag.textContent = '🎛️ SIM'; modeTag.style.background='#3a2a00'; }
    stopLivePoll();
    setScenario('normal');
  }
}

// ── Live Poll ───────────────────────────────────────────────────
function startLivePoll() {
  stopLivePoll();
  fetchLive();
  liveInterval = setInterval(fetchLive, 2000);
}
function stopLivePoll() {
  if (liveInterval) { clearInterval(liveInterval); liveInterval = null; }
}

async function fetchLive() {
  try {
    const r = await fetch('/live');
    const d = await r.json();
    const tag = gid('modeTag');
    if (d.status === 'no_data') {
      if(tag){ tag.textContent = '📡 LIVE — Waiting for ESP32...'; tag.style.background='#4d2a00'; }
      return;
    }
    // Merge live data into currentSensors
    Object.keys(d).forEach(k => { if(k !== 'status') currentSensors[k] = Number(d[k]); });
    renderSensors(currentSensors);
    await runPredict();
    if(tag){ tag.textContent = '📡 LIVE ✅'; tag.style.background='#1a4d1a'; }
  } catch(e) {
    const tag = gid('modeTag');
    if(tag){ tag.textContent = '📡 LIVE — Error'; tag.style.background='#4d0000'; }
  }
}

// ── Render sensor bars ──────────────────────────────────────────
function renderSensors(d) {
  setText('v-moist',    d.soil_moisture  + '%');
  setText('v-tds',      d.tds_ppm        + ' ppm');
  setText('v-air',      d.air_temp_c     + '°C');
  setText('v-hum',      d.humidity_pct   + '%');
  setText('v-soiltemp', d.soil_temp_c    + '°C');
  setText('v-mq135',    d.mq135_ammonia  + ' ppm');
  setText('v-mq4',      d.mq4_methane    + ' ppm');
  setText('v-mq7',      d.mq7_co         + ' ppm');
  setBar('b-moist',    d.soil_moisture);
  setBar('b-tds',      Math.min(100, d.tds_ppm / 20));
  setBar('b-air',      Math.min(100, d.air_temp_c * 2));
  setBar('b-hum',      d.humidity_pct);
  setBar('b-soiltemp', Math.min(100, d.soil_temp_c * 2));
}

// ── Scenario setter ─────────────────────────────────────────────
function setScenario(name) {
  currentSensors = Object.assign({}, SCENARIOS[name]);
  renderSensors(currentSensors);
  runPredict();
  // Highlight active scenario button
  document.querySelectorAll('.scenario-chips button').forEach(b => b.classList.remove('active-scene'));
  const sc = gid('sc-' + name);
  if (sc) sc.classList.add('active-scene');
}

// ── Run Predict ─────────────────────────────────────────────────
async function runPredict() {
  const stageEl = gid('stageSel');
  if (!stageEl) return;
  try {
    const r = await fetch('/predict', {
      method:  'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ crop: currentCrop, stage: stageEl.value, sensors: currentSensors })
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || 'Predict failed');

    const healthLabels = UI_STRINGS[uiLang].health;
    const adviceMap = UI_STRINGS[uiLang].advice;};

    // Update score
    setText('scoreText',  d.health_score);
    setText('adviceText', adviceMap[d.health_status] || 'Analyzing...');

    // Animate half-arc gauge
    const fill   = gid('gaugeFill');
    const needle = gid('gaugeNeedle');
    const pct    = Math.max(0, Math.min(100, d.health_score));
    const color  = pct >= 75 ? '#2ecc71' : pct >= 50 ? '#f1c40f' : pct >= 25 ? '#e67e22' : '#e74c3c';
    const arcLen = 188;
    if (fill) {
      fill.style.strokeDashoffset = arcLen - (pct / 100) * arcLen;
      fill.style.stroke = color;
    }
    // Move needle dot along the arc path (semicircle: cx=70, cy=75, r=60)
    if (needle) {
      const angle = Math.PI - (pct / 100) * Math.PI; // 180° to 0°
      const nx = 70 + 60 * Math.cos(angle);
      const ny = 75 - 60 * Math.sin(angle);
      needle.setAttribute('cx', nx.toFixed(1));
      needle.setAttribute('cy', ny.toFixed(1));
      needle.setAttribute('fill', color);
    }

    // Health tag with color class
    const tag = gid('healthTag');
    if (tag) {
      tag.textContent = healthLabels[d.health_status] || d.health_status;
      tag.className   = 'health-tag';
      if      (d.health_status === 'MODERATE') tag.classList.add('moderate');
      else if (d.health_status === 'POOR')     tag.classList.add('poor');
      else if (d.health_status === 'CRITICAL') tag.classList.add('critical');
    }

    // Animated crop face morph
    const face   = gid('cropFace');
    const eyeL   = gid('eye-l');
    const eyeR   = gid('eye-r');
    const mouth  = gid('mouth');
    const sparks = gid('sparkles');
    const svg    = gid('cropSvg');

    if (face) {
      face.className = 'crop-face';
      const s = d.health_status;

      // Face class for animation
      face.classList.add(
        s === 'GOOD'     ? 'face-good'     :
        s === 'MODERATE' ? 'face-moderate' :
        s === 'POOR'     ? 'face-poor'     : 'face-critical'
      );

      // Eye color
      const eyeColor = s==='GOOD' ? '#2ecc71' : s==='MODERATE' ? '#f1c40f' : s==='POOR' ? '#e67e22' : '#e74c3c';
      if(eyeL) eyeL.setAttribute('fill', eyeColor);
      if(eyeR) eyeR.setAttribute('fill', eyeColor);

      // Stem/head color
      svg?.querySelectorAll('line,ellipse:not(#eye-l):not(#eye-r)').forEach(el => {
        if(el.tagName==='line'||el.getAttribute('stroke'))
          el.setAttribute('stroke', eyeColor);
      });

      // Mouth shape
      if (mouth) {
        if      (s === 'GOOD')     mouth.setAttribute('d','M33 43 Q40 50 47 43'); // big smile
        else if (s === 'MODERATE') mouth.setAttribute('d','M33 44 Q40 46 47 44'); // slight smile
        else if (s === 'POOR')     mouth.setAttribute('d','M33 47 Q40 44 47 47'); // frown
        else                       mouth.setAttribute('d','M32 48 Q40 42 48 48'); // deep frown
        mouth.setAttribute('stroke', eyeColor);
      }

      // Eyes: X eyes for critical
      if (eyeL && eyeR) {
        if (s === 'CRITICAL') {
          eyeL.setAttribute('rx','3'); eyeL.setAttribute('ry','1.2');
          eyeR.setAttribute('rx','3'); eyeR.setAttribute('ry','1.2');
        } else {
          eyeL.setAttribute('r','2.8'); eyeR.setAttribute('r','2.8');
        }
      }
      // Hide sparkles if not good
      if (sparks) sparks.style.display = s==='GOOD' ? '' : 'none';
    }
    setText('d-irrigate', d.irrigate_now ? '✅ YES' : 'NO');
    setText('d-pump',     d.pump_locked  ? '🔒 LOCKED' : (d.pump_on ? '🟢 ON' : 'OFF'));
    setText('d-gas',   d.gas_alert ? '🚨 ALERT' : '✅ CLEAR');
    setText('d-stage', stageEl.value);
    setText('t-moist', d.trend_moisture || 'stable');
    setText('t-tds',   d.tds_safe ? '✅ Safe' : '⚠️ High');
    setText('t-aqi',   d.field_aqi_label || '--');
    if(gid('confText')) setText('confText', (uiLang==='ta'?'நம்பகத்தன்மை ':'Confidence ') + d.confidence_pct + '%');
    // WhatsApp alert button — activate on CRITICAL / gas alert
    const waBtn = gid('waBtn');
    if (waBtn) {
      if (d.gas_alert || d.health_status === 'CRITICAL' || d.health_status === 'POOR') {
        waBtn.classList.add('alert-active');
        waBtn.title = 'Alert condition detected — click to notify farmer';
      } else {
        waBtn.classList.remove('alert-active');
      }
    }
    // Weather note in advice box
    if (d.weather_note && gid('weatherNote')) {
      const _wm = UI_STRINGS[uiLang].weatherMap || {};
      let _wt = d.weather_note;
      if (uiLang === 'ta') {
        const _wmap = {
          'Stable weather next 24h': '🌤 அடுத்த 24 மணி நேரம் நிலையான வானிலை',
          'Light rain expected': '🌦 இலேசான மழை எதிர்பார்க்கப்படுகிறது — நீர்ப்பாசனம் குறைக்கவும்',
          'Heavy rain': '🌧 கனமழை வரும் — நீர்ப்பாசனம் தவிர்க்கவும்',
          'Stable weather': '🌤 நிலையான வானிலை',
          'Weather normal': '🌤 வானிலை சாதாரணம்',
          'Forecast unavailable': 'வானிலை கணிப்பு இல்லை',
          'Heat': '🌡️ வெப்பம்',
          'irrigate early': 'காலையில் நீர் பாய்ச்சுங்கள்',
          'skip irrigation': 'நீர்ப்பாசனம் தவிர்க்கவும்'
        };
        for (const [en, ta] of Object.entries(_wmap)) {
          if (_wt.includes(en)) { _wt = ta; break; }
        }
      }
      setText('weatherNote', _wt);
    }
  } catch(e) {
    console.error('Predict error:', e);
    setText('adviceText', 'Prediction error — server may be starting up. Retrying...');
    // Auto retry after 3s
    setTimeout(runPredict, 3000);
  }
}

// ── Weather ─────────────────────────────────────────────────────
async function loadWeather() {
  try {
    const d = await fetch('/weather').then(r => r.json());
    setText('weatherPill',  '☁️ ' + d.temp + '°C');
    setText('weatherStrip', `🌥 ${d.city}: ${d.temp}°C · Humidity ${d.humidity}% · Rain ${d.rain}mm · Wind ${d.wind}m/s`);
  } catch {}
}

// ── Status ──────────────────────────────────────────────────────
async function loadStatus() {
  try {
    const d = await fetch('/status').then(r => r.json());
    setText('aiBadge',    d.gemini_ready ? '🤖 Gemini ON' : '🤖 AI');
    setText('chatStatus', d.gemini_ready ? 'ONLINE' : 'OFFLINE');
    const dot = gid('chatDot');
    if (dot) { dot.className = d.gemini_ready ? 'dot online' : 'dot'; }
  } catch {}
}

// ── FillStages — BUG FIX: handle both array and object stages ───
function fillStages() {
  const s = gid('stageSel');
  if (!s) return;
  s.innerHTML = '';
  const crop = cropStages[currentCrop];
  let stages;
  if (!crop) {
    stages = ['germination'];
  } else if (Array.isArray(crop.stages)) {
    stages = crop.stages;                   // ✅ array → use directly
  } else if (crop.stages && typeof crop.stages === 'object') {
    stages = Object.keys(crop.stages);      // ✅ object → get keys
  } else {
    stages = ['germination'];
  }
  stages.forEach(v => {
    const o = document.createElement('option');
    o.value = v;
    o.textContent = v[0].toUpperCase() + v.slice(1).replace(/_/g,' ');
    s.appendChild(o);
  });
  runPredict();
}

// ── Crop tabs ───────────────────────────────────────────────────
async function boot() {
  try {
    const c = await fetch('/crops').then(r => r.json());
    cropStages = c;
    const tabs = gid('crop-tabs');
    if (tabs) {
      Object.keys(c).forEach((k, i) => {
        const b = document.createElement('button');
        b.textContent = '🌾 ' + k[0].toUpperCase() + k.slice(1);
        b.className   = 'crop-btn' + (i === 0 ? ' active' : '');
        b.onclick = () => {
          document.querySelectorAll('.crop-btn').forEach(x => x.classList.remove('active'));
          b.classList.add('active');
          currentCrop = k;
          fillStages();
        };
        tabs.appendChild(b);
      });
    }
  } catch(e) {
    console.error('Failed to load crops:', e);
    cropStages = { rice: { stages: ['germination','tillering','flowering','harvest'], moist_min:60, moist_opt:75, tds_max:800 } };
  }
  fillStages();
  await loadStatus();
  await loadWeather();
  await loadForecast();

  setInterval(loadWeather,   60000);
  setInterval(loadForecast,  1800000);  // refresh forecast every 30 min
  setMode('sim');
}

// ── Chat ─────────────────────────────────────────────────────────
function addMsg(cls, txt) {
  const box = gid('chatBox');
  if (!box) return;
  const div = document.createElement('div');
  div.className = cls; div.textContent = txt;
  box.appendChild(div); box.scrollTop = box.scrollHeight;
}
function quickAsk(q) { const i=gid('chatInput'); if(i){ i.value=q; sendChat(); } }

async function sendChat() {
  const input = gid('chatInput');
  if (!input) return;
  const msg = input.value.trim();
  if (!msg) return;
  addMsg('user', msg); input.value = '';
  try {
    const stageEl = gid('stageSel');
    const r = await fetch('/chat', {
      method:  'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        message: msg, crop: currentCrop,
        stage:   stageEl ? stageEl.value : 'germination',
        sensors: currentSensors,
        lang:    uiLang
      })
    });
    const d = await r.json();
    addMsg('bot', d.reply || 'No reply');
  } catch { addMsg('bot', 'Connection error — server may be restarting.'); }
}

const stageEl = gid('stageSel');
if (stageEl) stageEl.addEventListener('change', runPredict);
window.addEventListener('load', boot);

// ── WhatsApp Alert ──────────────────────────────────────────
function sendWhatsApp() {
  const stageEl = gid('stageSel');
  const score   = gid('scoreText')  ? gid('scoreText').textContent  : '--';
  const status  = gid('healthTag')  ? gid('healthTag').textContent  : '--';
  const gas     = gid('d-gas')      ? gid('d-gas').textContent      : '--';
  const pump    = gid('d-pump')     ? gid('d-pump').textContent     : '--';
  const stage   = stageEl           ? stageEl.value                 : '--';
  const moist   = gid('v-moist')    ? gid('v-moist').textContent    : '--';
  const temp    = gid('v-air')      ? gid('v-air').textContent      : '--';

  const msg =
    `🚨 *EcoSense Farm Alert*\n` +
    `Crop: ${currentCrop.toUpperCase()} (${stage})\n` +
    `Health: ${score}/100 — ${status}\n` +
    `Moisture: ${moist} | Temp: ${temp}\n` +
    `Gas: ${gas} | Pump: ${pump}\n` +
    `⚠️ Immediate attention required!\n` +
    `Dashboard: https://ecosense-fntj.onrender.com`;

  window.open('https://wa.me/?text=' + encodeURIComponent(msg), '_blank');
}

// ── Forecast Strip ──────────────────────────────────────────
async function loadForecast() {
  try {
    const d = await fetch('/forecast').then(r => r.json());
    const strip = gid('forecastStrip');
    if (!strip || !d.enabled || !d.next24h.length) {
      if (strip) strip.innerHTML = '<span style="font-size:11px;color:#4a6e4a;padding:4px 0;">Forecast unavailable</span>';
      return;
    }
    const icons = {
      'Rain':'🌧','Drizzle':'🌦','Thunderstorm':'⛈️',
      'Clouds':'☁️','Clear':'☀️','Mist':'🌫️','Haze':'🌫️','Snow':'❄️'
    };
    strip.innerHTML = d.next24h.map(s => `
      <div style="min-width:62px;background:#162118;border:1px solid #1e3320;
                  border-radius:8px;padding:5px 6px;text-align:center;flex-shrink:0;">
        <div style="font-size:10px;color:#7a9e7a">${s.time}</div>
        <div style="font-size:16px;margin:2px 0">${icons[s.desc]||'🌤'}</div>
        <div style="font-size:11px;font-weight:700;color:#e0f0e0">${s.temp}°</div>
        ${s.rain > 0 ? `<div style="font-size:10px;color:#4fc3f7">💧${s.rain}mm</div>` : ''}
      </div>
    `).join('');

    // Update forecast summary note
    if (gid('weatherNote')) {
      setText('weatherNote', d.summary);
    }
  } catch(e) {
    console.error('Forecast error:', e);
  }
}

// ── UI Language Toggle (EN ↔ TA) ────────────────────────────
// Only sensor labels, health status, advice, decisions toggle
// Sim menu, mode buttons always stay English

const UI_STRINGS = {
  en: {
    sensorPanel:   "LIVE SENSOR READINGS",
    gasPanel:      "GAS SENSORS",
    adviceTitle:   "🤖 AI Field Advice",
    chatHead:      "🌿 AI Farming Companion",
    chatPlaceholder: "Ask me anything about your farm...",
    gaugeLabel:    "HEALTH SCORE / 100",
    decisions:     ["Irrigate","Pump","Gas","Stage"],
    trendKeys:     ["Moisture Trend:","Water:","Air Quality:"],
    health: {GOOD:"🌱 GOOD",MODERATE:"⚠️ MODERATE",POOR:"😢 POOR",CRITICAL:"💀 CRITICAL"},
    advice: {
      GOOD:     "✅ Crop looks healthy. Keep monitoring.",
      MODERATE: "⚠️ Crop needs attention. Check moisture & temperature.",
      POOR:     "🔴 Crop is struggling. Irrigate and inspect field.",
      CRITICAL: "💀 CRITICAL — Immediate action required!"
    },
    langBtn: "🇮🇳 TA",
    waBtn:   "📲 Send WhatsApp Alert",
    trendVals:  {stable:"Stable", rising:"Rising", falling:"Falling"},
    tdsOk:      "✅ Safe",
    tdsHigh:    "⚠️ High",
    aqiLabels:  {Excellent:"Excellent", Good:"Good", Moderate:"Moderate", Poor:"Poor"},
    weatherMap: {},
    quickLabels: ["💧 Irrigate?","🧂 Water safe?","🌱 Health?","🌿 Fertilize?","☁️ Air quality?","⚙️ Pump status?"],
    quickQuestions: ["Should I irrigate now?","Is water quality safe?","How is crop health?",
                     "Can I fertilize now?","Is air quality safe?","What is pump status?"],
  },
  ta: {
    sensorPanel:   "நேரடி உணரி அளவீடுகள்",
    gasPanel:      "வாயு உணரிகள்",
    adviceTitle:   "🤖 AI வயல் ஆலோசனை",
    chatHead:      "🌿 AI வேளாண் உதவியாளர்",
    chatPlaceholder: "உங்கள் வயலைப் பற்றி கேளுங்கள்...",
    gaugeLabel:    "ஆரோக்கிய மதிப்பெண் / 100",
    decisions:     ["நீர்ப்பாசனம்","பம்ப்","வாயு","நிலை"],
    trendKeys:     ["ஈரப்பதம்:","நீர்:","காற்று தரம்:"],
    health: {GOOD:"🌱 நல்லது",MODERATE:"⚠️ நடுத்தரம்",POOR:"😢 மோசம்",CRITICAL:"💀 அவசரம்"},
    advice: {
      GOOD:     "✅ பயிர் ஆரோக்கியமாக உள்ளது. தொடர்ந்து கண்காணியுங்கள்.",
      MODERATE: "⚠️ பயிருக்கு கவனிப்பு தேவை. ஈரப்பதம் & வெப்பம் சரிபாருங்கள்.",
      POOR:     "🔴 பயிர் கஷ்டப்படுகிறது. நீர் பாய்ச்சி வயலை சோதியுங்கள்.",
      CRITICAL: "💀 அவசரம் — உடனடி நடவடிக்கை தேவை!"
    },
    langBtn: "🇬🇧 EN",
    waBtn:   "📲 வாட்ஸ்அப் எச்சரிக்கை அனுப்பு",
    trendVals:  {stable:"நிலையான", rising:"உயர்கிறது", falling:"குறைகிறது"},
    tdsOk:      "✅ பாதுகாப்பு",
    tdsHigh:    "⚠️ அதிகம்",
    aqiLabels:  {Excellent:"மிகவும் நல்லது", Good:"நல்லது", Moderate:"நடுத்தரம்", Poor:"மோசம்"},
    weatherMap: {
      "Stable weather":"நிலையான வானிலை","Heavy rain":"கனமழை","skip irrigation":"நீர்ப்பாசனம் தவிர்க்கவும்",
      "Light rain":"இலேசான மழை","Heat":"வெப்பம்","ahead":"வரும்","irrigate early":"காலையில் நீர் பாய்ச்சுங்கள்",
      "rain_coming":"மழை வரும்","No rain":"மழை இல்லை","normal":"சாதாரணம்"
    },
    quickLabels: ["💧 பாசனமா?","🧂 நீர் பாதுகாப்பா?","🌱 ஆரோக்கியம்?","🌿 உரமிடலாமா?","☁️ காற்று தரம்?","⚙️ பம்ப் நிலை?"],
    quickQuestions: ["இப்போது நீர் பாய்ச்சலாமா?","நீர் தரம் பாதுகாப்பானதா?",
                     "பயிரின் ஆரோக்கியம் எப்படி?","இப்போது உரமிடலாமா?",
                     "காற்று தரம் பாதுகாப்பானதா?","பம்ப் நிலை என்ன?"],
  }
};
let uiLang = 'ta'; // default Tamil for readings/advice

function toggleUILang() {
  uiLang = (uiLang === 'ta') ? 'en' : 'ta';
  applyUILang();
}

function applyUILang() {
  const S = UI_STRINGS[uiLang];
  const gid = id => document.getElementById(id);
  const qs  = sel => document.querySelector(sel);
  const qsa = sel => document.querySelectorAll(sel);

  // Panel titles
  const pts = qsa('.panel-title');
  if (pts[0]) pts[0].textContent = S.sensorPanel;
  if (pts[1]) pts[1].textContent = S.gasPanel;

  // Advice title
  const at = qs('.advice-title'); if (at) at.textContent = S.adviceTitle;

  // Gauge subtitle
  const gs = qs('.gauge-sub');    if (gs) gs.textContent = S.gaugeLabel;

  // Chat head
  const ch = qs('.chat-head-title'); if (ch) ch.textContent = S.chatHead;

  // Chat input placeholder
  const ci = gid('chatInput'); if (ci) ci.placeholder = S.chatPlaceholder;

  // Decision labels
  const dls = qsa('.d-label');
  S.decisions.forEach((v,i) => { if(dls[i]) dls[i].textContent = v; });

  // Trend keys
  const tks = qsa('.trend-key');
  S.trendKeys.forEach((v,i) => { if(tks[i]) tks[i].textContent = v; });

  // WhatsApp button
  const wa = gid('waBtn');
  if (wa) wa.innerHTML = S.waBtn;

  // Lang toggle button label
  const lb = gid('langToggleBtn'); if (lb) lb.textContent = S.langBtn;

  // Quick prompt buttons
  const qbtns = document.querySelectorAll('.quick-grid button');
  const qlbls = S.quickLabels;
  qbtns.forEach((b,i)=>{ if(qlbls[i]) b.textContent=qlbls[i]; });

  // Re-render all dynamic values using current language
  if (window._lastResult) {
    const d  = window._lastResult;
    const hs = d.health_status || 'GOOD';
    const hel = document.getElementById('healthStatus');
    if (hel) hel.textContent = S.health[hs] || hs;
    const ael = document.getElementById('adviceText');
    if (ael) ael.textContent = S.advice[hs] || '';
    // Trend / TDS / AQI
    const tv = S.trendVals || {};
    const tel = document.getElementById('t-moisture');
    if (tel) tel.textContent = tv[d.trend_moisture] || d.trend_moisture || 'stable';
    const tdsel = document.getElementById('t-tds');
    if (tdsel) tdsel.textContent = d.tds_safe ? (S.tdsOk||'✅ Safe') : (S.tdsHigh||'⚠️ High');
    const aqiel = document.getElementById('t-aqi');
    if (aqiel) aqiel.textContent = (S.aqiLabels && S.aqiLabels[d.field_aqi_label]) || d.field_aqi_label || '--';
    // Weather
    if (d.weather_note && document.getElementById('weatherNote')) {
      const _wmap = S === UI_STRINGS.ta ? {
        'Stable weather next 24h': '🌤 அடுத்த 24 மணி நேரம் நிலையான வானிலை',
        'Light rain expected': '🌦 இலேசான மழை எதிர்பார்க்கப்படுகிறது',
        'Heavy rain': '🌧 கனமழை வரும் — நீர்ப்பாசனம் தவிர்க்கவும்',
        'Stable weather': '🌤 நிலையான வானிலை',
        'Weather normal': '🌤 வானிலை சாதாரணம்',
        'Forecast unavailable': 'வானிலை கணிப்பு இல்லை'
      } : {};
      let _wt = d.weather_note;
      for (const [en, ta] of Object.entries(_wmap)) {
        if (_wt.includes(en)) { _wt = ta; break; }
      }
      document.getElementById('weatherNote').textContent = _wt;
    }
  }
}
