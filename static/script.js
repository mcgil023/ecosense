'use strict';
// ═══════════════════════════════════════════════════════
//  EcoSense script.js — FINAL CLEAN BUILD
//  Tamil/English: readings + advice + chat only
//  Sim menu stays English always
// ═══════════════════════════════════════════════════════

// ── Helpers ──────────────────────────────────────────────────
const gid = id => document.getElementById(id);
const setText = (id, t) => { const el = gid(id); if (el) el.textContent = t; };
const setHTML = (id, h) => { const el = gid(id); if (el) el.innerHTML  = h; };

// ── State ─────────────────────────────────────────────────────
let MODE         = 'sim';
let currentCrop  = 'rice';
let currentLang  = 'ta';          // 'ta' = Tamil (default), 'en' = English
let liveInterval = null;
let currentSensors = {};
let lastResult   = null;

const cropStages = {};   // filled by /crops

// ── Language Strings ─────────────────────────────────────────
const L = {
  en: {
    ptSensor:   'LIVE SENSOR READINGS',
    ptGas:      'GAS SENSORS',
    advTitle:   '🤖 AI Field Advice',
    chatHead:   '🌿 AI Farming Companion',
    chatWelcome:'👋 Hi! I\'m your AI Farming Companion. Ask any farming question! 🌱',
    chatPH:     'Ask me anything about your farm...',
    conf:       'Confidence ',
    dlIrr:      'Irrigate', dlPump: 'Pump', dlGas: 'Gas', dlStage: 'Stage',
    tkMoist:    'Moisture Trend:', tkWater: 'Water:', tkAir: 'Air Quality:',
    health:     { GOOD:'🌱 GOOD', MODERATE:'⚠️ MODERATE', POOR:'😢 POOR', CRITICAL:'💀 CRITICAL' },
    advice:     {
      GOOD:     '✅ Crop looks healthy. Keep monitoring.',
      MODERATE: '⚠️ Crop needs attention. Check moisture & temperature.',
      POOR:     '🔴 Crop is struggling. Irrigate and inspect field.',
      CRITICAL: '💀 CRITICAL — Immediate action required!'
    },
    trend:      { stable:'Stable', rising:'Rising', falling:'Falling' },
    tdsOk:      '✅ Safe',  tdsHigh:   '⚠️ High',
    aqi:        { Excellent:'Excellent', Good:'Good', Moderate:'Moderate', Poor:'Poor' },
    lblMoist:   '💧 Soil Moisture', lblTds: '🧂 Water TDS',
    lblAir:     '🌡️ Air Temp',       lblHum: '💦 Humidity', lblSoil: '🌱 Soil Temp',
    waBtn:      '📲 Send WhatsApp Alert',
    langBtn:    '🇮🇳 TA',
    ql: ['💧 Irrigate?','🧂 Water safe?','🌱 Health?','🌿 Fertilize?','☁️ Air quality?','⚙️ Pump status?'],
    qq: ['Should I irrigate now?','Is water quality safe?','How is crop health?',
         'Can I fertilize now?','Is air quality safe?','What is pump status?'],
    weather: {}
  },
  ta: {
    ptSensor:   'நேரடி உணரி அளவீடுகள்',
    ptGas:      'வாயு உணரிகள்',
    advTitle:   '🤖 AI வயல் ஆலோசனை',
    chatHead:   '🌿 AI வேளாண் உதவியாளர்',
    chatWelcome:'👋 வணக்கம்! நான் உங்கள் AI வேளாண் உதவியாளர். கேளுங்கள்! 🌱',
    chatPH:     'உங்கள் வயலைப் பற்றி கேளுங்கள்...',
    conf:       'நம்பகத்தன்மை ',
    dlIrr:      'நீர்ப்பாசனம்', dlPump: 'பம்ப்', dlGas: 'வாயு', dlStage: 'நிலை',
    tkMoist:    'ஈரப்பதம்:', tkWater: 'நீர்:', tkAir: 'காற்று தரம்:',
    health:     { GOOD:'🌱 நல்லது', MODERATE:'⚠️ நடுத்தரம்', POOR:'😢 மோசம்', CRITICAL:'💀 அவசரம்' },
    advice:     {
      GOOD:     '✅ பயிர் ஆரோக்கியமாக உள்ளது. தொடர்ந்து கண்காணியுங்கள்.',
      MODERATE: '⚠️ பயிருக்கு கவனிப்பு தேவை. ஈரப்பதம் & வெப்பம் சரிபாருங்கள்.',
      POOR:     '🔴 பயிர் கஷ்டப்படுகிறது. நீர் பாய்ச்சி வயலை சோதியுங்கள்.',
      CRITICAL: '💀 அவசரம் — உடனடி நடவடிக்கை தேவை!'
    },
    trend:      { stable:'நிலையான', rising:'உயர்கிறது', falling:'குறைகிறது' },
    tdsOk:      '✅ பாதுகாப்பு',  tdsHigh:   '⚠️ அதிகம்',
    aqi:        { Excellent:'மிகவும் நல்லது', Good:'நல்லது', Moderate:'நடுத்தரம்', Poor:'மோசம்' },
    lblMoist:   '💧 மண் ஈரப்பதம்', lblTds: '🧂 நீர் TDS',
    lblAir:     '🌡️ காற்று வெப்பம்', lblHum: '💦 ஈரப்பதம்', lblSoil: '🌱 மண் வெப்பம்',
    waBtn:      '📲 வாட்ஸ்அப் எச்சரிக்கை அனுப்பு',
    langBtn:    '🇬🇧 EN',
    ql: ['💧 பாசனமா?','🧂 நீர் பாதுகாப்பா?','🌱 ஆரோக்கியம்?','🌿 உரமிடலாமா?','☁️ காற்று தரம்?','⚙️ பம்ப் நிலை?'],
    qq: ['இப்போது நீர் பாய்ச்சலாமா?','நீர் தரம் பாதுகாப்பானதா?',
         'பயிரின் ஆரோக்கியம் எப்படி?','இப்போது உரமிடலாமா?',
         'காற்று தரம் பாதுகாப்பானதா?','பம்ப் நிலை என்ன?'],
    weather: {
      'Stable weather next 24h': '🌤 அடுத்த 24 மணி நேரம் நிலையான வானிலை',
      'Light rain expected':     '🌦 இலேசான மழை எதிர்பார்க்கப்படுகிறது',
      'Heavy rain':              '🌧 கனமழை வரும் — நீர்ப்பாசனம் தவிர்க்கவும்',
      'Stable weather':          '🌤 நிலையான வானிலை',
      'Weather normal':          '🌤 வானிலை சாதாரணம்',
      'Forecast unavailable':    'வானிலை கணிப்பு இல்லை',
      'Heat':                    '🌡️ வெப்பம்'
    }
  }
};

// ── applyLang — updates every labelled element ────────────────
function applyLang() {
  const S = L[currentLang];
  setText('pt-sensor',    S.ptSensor);
  setText('pt-gas',       S.ptGas);
  setText('adviceTitle',  S.advTitle);
  setText('chatHeadTitle',S.chatHead);
  setText('chatWelcome',  S.chatWelcome);
  const ci = gid('chatInput'); if (ci) ci.placeholder = S.chatPH;
  setText('dlbl-irrigate',S.dlIrr);
  setText('dlbl-pump',    S.dlPump);
  setText('dlbl-gas',     S.dlGas);
  setText('dlbl-stage',   S.dlStage);
  setText('tk-moist',     S.tkMoist);
  setText('tk-water',     S.tkWater);
  setText('tk-air',       S.tkAir);
  setText('lbl-moist',    S.lblMoist);
  setText('lbl-tds',      S.lblTds);
  setText('lbl-airtemp',  S.lblAir);
  setText('lbl-hum',      S.lblHum);
  setText('lbl-soiltemp', S.lblSoil);
  const wa = gid('waBtn'); if (wa) wa.textContent = S.waBtn;
  const lb = gid('langToggleBtn'); if (lb) lb.textContent = S.langBtn;
  // Quick prompts
  const qbtns = document.querySelectorAll('.quick-grid button');
  S.ql.forEach((lbl, i) => { if (qbtns[i]) qbtns[i].textContent = lbl; });
  // Re-render dynamic values if result available
  if (lastResult) renderLangValues(lastResult);
}

function renderLangValues(d) {
  const S  = L[currentLang];
  const hs = d.health_status || 'GOOD';
  setText('healthTag',  S.health[hs] || hs);
  setText('adviceText', S.advice[hs] || '');
  setText('confText',   S.conf + (d.confidence_pct || '--') + '%');
  setText('t-moist',    S.trend[d.trend_moisture] || d.trend_moisture || '--');
  setText('t-tds',      d.tds_safe ? S.tdsOk : S.tdsHigh);
  const aqiKey = d.field_aqi_label || 'Good';
  setText('t-aqi', S.aqi[aqiKey] || aqiKey);
  // Weather note
  if (d.weather_note) {
    let wt = d.weather_note;
    if (currentLang === 'ta') {
      for (const [en, ta] of Object.entries(S.weather)) {
        if (wt.includes(en)) { wt = ta; break; }
      }
    }
    setText('weatherNote', wt);
  }
}

function toggleLang() {
  currentLang = (currentLang === 'ta') ? 'en' : 'ta';
  applyLang();
}

// ── Clock ──────────────────────────────────────────────────────
setInterval(() => { setText('clock', new Date().toLocaleTimeString('en-IN')); }, 1000);

// ── Crop tabs ─────────────────────────────────────────────────
async function loadCrops() {
  try {
    const data = await fetch('/crops').then(r => r.json());
    Object.assign(cropStages, data);
    const tabs = gid('crop-tabs');
    if (!tabs) return;
    tabs.innerHTML = '';
    const crops = Object.keys(data);
    crops.forEach(c => {
      const btn = document.createElement('button');
      btn.textContent = c.charAt(0).toUpperCase() + c.slice(1);
      btn.className = 'crop-tab' + (c === currentCrop ? ' active' : '');
      btn.onclick = () => { currentCrop = c; fillStages(); runPredict();
        tabs.querySelectorAll('.crop-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active'); };
      tabs.appendChild(btn);
    });
    fillStages();
  } catch(e) { console.warn('loadCrops:', e); }
}

function fillStages() {
  const s = gid('stageSel'); if (!s) return;
  s.innerHTML = '';
  const crop = cropStages[currentCrop];
  if (!crop) return;
  const stages = Array.isArray(crop) ? crop : (crop.stages || []);
  stages.forEach(st => {
    const o = document.createElement('option');
    o.value = st; o.textContent = st.charAt(0).toUpperCase() + st.slice(1);
    s.appendChild(o);
  });
}

// ── Simulate scenarios ────────────────────────────────────────
const SCENARIOS = {
  normal:   { soil_moisture:72, tds_ppm:350, air_temp_c:28, soil_temp_c:24, humidity_pct:65, mq135_ammonia:50,  mq4_methane:200, mq7_co:10 },
  dry:      { soil_moisture:30, tds_ppm:380, air_temp_c:34, soil_temp_c:30, humidity_pct:40, mq135_ammonia:60,  mq4_methane:210, mq7_co:12 },
  saline:   { soil_moisture:55, tds_ppm:1400,air_temp_c:30, soil_temp_c:26, humidity_pct:60, mq135_ammonia:55,  mq4_methane:200, mq7_co:10 },
  gas:      { soil_moisture:68, tds_ppm:360, air_temp_c:29, soil_temp_c:25, humidity_pct:70, mq135_ammonia:320, mq4_methane:1200,mq7_co:150},
  heat:     { soil_moisture:50, tds_ppm:400, air_temp_c:42, soil_temp_c:38, humidity_pct:30, mq135_ammonia:70,  mq4_methane:220, mq7_co:15 },
  critical: { soil_moisture:20, tds_ppm:1600,air_temp_c:44, soil_temp_c:40, humidity_pct:20, mq135_ammonia:350, mq4_methane:1300,mq7_co:180}
};
let activeScenario = 'normal';

function setScenario(name) {
  activeScenario = name;
  currentSensors = { ...SCENARIOS[name] };
  document.querySelectorAll('.scenario-chips button').forEach(b => {
    b.classList.toggle('active-chip', b.id === 'sc-' + name);
  });
  renderSensors(currentSensors);
  runPredict();
}

// ── Sensor display ────────────────────────────────────────────
function renderSensors(s) {
  const set = (id, v, unit) => setText(id, v !== undefined ? (Number(v).toFixed(1) + unit) : '--');
  set('v-moist',    s.soil_moisture,  '%');
  set('v-tds',      s.tds_ppm,        ' ppm');
  set('v-air',      s.air_temp_c,     '°C');
  set('v-hum',      s.humidity_pct,   '%');
  set('v-soiltemp', s.soil_temp_c,    '°C');
  set('v-mq135',    s.mq135_ammonia,  ' ppm');
  set('v-mq4',      s.mq4_methane,    ' ppm');
  set('v-mq7',      s.mq7_co,         ' ppm');
  // Sensor bar widths
  const bars = { 'b-moist':s.soil_moisture, 'b-tds':Math.min(100,s.tds_ppm/20),
    'b-air':Math.min(100,(s.air_temp_c/50)*100), 'b-hum':s.humidity_pct,
    'b-soiltemp':Math.min(100,(s.soil_temp_c/50)*100) };
  for (const [id, pct] of Object.entries(bars)) {
    const el = gid(id); if (el) el.style.width = Math.max(2, pct) + '%';
  }
}

// ── Predict ───────────────────────────────────────────────────
async function runPredict() {
  const stageEl = gid('stageSel');
  try {
    const d = await fetch('/predict', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ crop: currentCrop,
        stage: stageEl ? stageEl.value : 'germination',
        sensors: currentSensors })
    }).then(r => r.json());

    lastResult = d;

    // Score + gauge
    setText('scoreText', d.health_score);
    const S = L[currentLang];
    const hs = d.health_status || 'GOOD';
    setText('healthTag',  S.health[hs] || hs);
    setText('adviceText', S.advice[hs] || '');
    setText('confText',   S.conf + (d.confidence_pct || '--') + '%');

    // Gauge animation
    const fill   = gid('gaugeFill');
    const needle = gid('gaugeNeedle');
    if (fill)   fill.style.width   = d.health_score + '%';
    if (needle) needle.style.left  = d.health_score + '%';

    // Crop face
    animateFace(hs);

    // Decisions
    setText('d-irrigate', d.irrigate_now  ? '✅ YES' : 'NO');
    setText('d-pump',     d.pump_locked   ? '🔒 LOCKED' : (d.pump_on ? '🟢 ON' : '⚪ OFF'));
    setText('d-gas',      d.gas_alert     ? '🚨 ALERT'  : '✅ CLEAR');
    setText('d-stage',    stageEl ? stageEl.value : '--');

    // Trend / TDS / AQI
    setText('t-moist',    S.trend[d.trend_moisture] || d.trend_moisture || '--');
    setText('t-tds',      d.tds_safe ? S.tdsOk : S.tdsHigh);
    setText('t-aqi',      S.aqi[d.field_aqi_label] || d.field_aqi_label || '--');

    // Weather note
    if (d.weather_note) {
      let wt = d.weather_note;
      if (currentLang === 'ta') {
        for (const [en, ta] of Object.entries(S.weather)) {
          if (wt.includes(en)) { wt = ta; break; }
        }
      }
      setText('weatherNote', wt);
    }

    // WhatsApp alert button pulse
    const waBtn = gid('waBtn');
    if (waBtn) {
      if (d.gas_alert || hs === 'CRITICAL' || hs === 'POOR') {
        waBtn.classList.add('alert-active');
      } else {
        waBtn.classList.remove('alert-active');
      }
    }

  } catch(e) {
    console.error('Predict error:', e);
    setText('adviceText', 'Server starting up — retrying...');
    setTimeout(runPredict, 3000);
  }
}

// ── Crop face animation ───────────────────────────────────────
function animateFace(s) {
  const face   = gid('cropFace');
  const eyeL   = gid('eye-l');
  const eyeR   = gid('eye-r');
  const mouth  = gid('mouth');
  const sparks = gid('sparkles');
  const colors = { GOOD:'#2ecc71', MODERATE:'#f39c12', POOR:'#e67e22', CRITICAL:'#e74c3c' };
  const c = colors[s] || '#2ecc71';
  if (face) face.className = 'crop-face ' + s.toLowerCase();
  if (eyeL) eyeL.setAttribute('fill', c);
  if (eyeR) eyeR.setAttribute('fill', c);
  if (mouth) {
    const paths = { GOOD:'M33 43 Q40 50 47 43', MODERATE:'M33 44 Q40 46 47 44',
                    POOR:'M33 47 Q40 44 47 47',  CRITICAL:'M32 48 Q40 42 48 48' };
    mouth.setAttribute('d', paths[s] || paths.GOOD);
    mouth.setAttribute('stroke', c);
  }
  if (sparks) sparks.style.display = s === 'GOOD' ? '' : 'none';
}

// ── Mode switching ────────────────────────────────────────────
function setMode(mode) {
  MODE = mode;
  const liveBtn = gid('btn-live'), simBtn = gid('btn-sim');
  const simBar  = gid('simbar'),   modeTag = gid('modeTag');
  stopLive();
  if (MODE === 'live') {
    if (liveBtn) liveBtn.classList.add('active-mode');
    if (simBtn)  simBtn.classList.remove('active-mode');
    if (simBar)  simBar.style.opacity = '0.4';
    if (modeTag) { modeTag.textContent = '📡 LIVE'; modeTag.style.background = '#c0392b'; }
    fetchLive();
    liveInterval = setInterval(fetchLive, 2000);
  } else {
    if (simBtn)  simBtn.classList.add('active-mode');
    if (liveBtn) liveBtn.classList.remove('active-mode');
    if (simBar)  simBar.style.opacity = '1';
    if (modeTag) { modeTag.textContent = '🎛️ SIM'; modeTag.style.background = '#27ae60'; }
    setScenario(activeScenario || 'normal');
  }
}

function stopLive() {
  if (liveInterval) { clearInterval(liveInterval); liveInterval = null; }
}

async function fetchLive() {
  try {
    const d = await fetch('/live').then(r => r.json());
    if (d.status === 'no_data') return;
    currentSensors = { ...currentSensors, ...d };
    renderSensors(currentSensors);
    runPredict();
  } catch(e) { console.warn('fetchLive:', e); }
}

// ── Weather ───────────────────────────────────────────────────
async function loadWeather() {
  try {
    const d = await fetch('/weather').then(r => r.json());
    const pill = gid('weatherPill');
    if (pill && d.enabled) {
      pill.textContent = `${d.city} ${d.temp}°C 💧${d.humidity}%`;
    }
  } catch {}
}

// ── Forecast strip ────────────────────────────────────────────
async function loadForecast() {
  try {
    const d = await fetch('/forecast').then(r => r.json());
    const strip = gid('forecastStrip'); if (!strip) return;
    if (!d.enabled || !d.next24h || !d.next24h.length) {
      strip.innerHTML = '<span style="opacity:.5;font-size:11px">Forecast unavailable</span>';
      return;
    }
    strip.innerHTML = d.next24h.map(s =>
      `<div class="fc-slot"><div class="fc-time">${s.time}</div>
       <div class="fc-icon">${s.rain>1?'🌧':s.temp>36?'🌡️':'☀️'}</div>
       <div class="fc-temp">${s.temp}°</div>
       <div class="fc-rain">${s.rain>0?s.rain+'mm':''}</div></div>`
    ).join('');
  } catch {}
}

// ── Status badge ─────────────────────────────────────────────
async function loadStatus() {
  try {
    const d = await fetch('/status').then(r => r.json());
    const badge = gid('aiBadge');
    if (badge) {
      badge.textContent = d.gemini_ready ? '✨ Gemini' : '🔧 Offline';
      badge.style.background = d.gemini_ready ? '#8e44ad' : '#7f8c8d';
    }
  } catch {}
}

// ── Chat ──────────────────────────────────────────────────────
function quickAsk(i) {
  const q = L[currentLang].qq[i];
  if (!q) return;
  const inp = gid('chatInput');
  if (inp) inp.value = q;
  sendChat();
}

async function sendChat() {
  const inp  = gid('chatInput');
  const box  = gid('chatBox');
  if (!inp || !box) return;
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = '';

  // User bubble
  const userDiv = document.createElement('div');
  userDiv.className = 'chat-msg user-msg';
  userDiv.textContent = msg;
  box.appendChild(userDiv);
  box.scrollTop = box.scrollHeight;

  // Typing indicator
  const dot = document.createElement('div');
  dot.className = 'chat-msg bot-msg typing';
  dot.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  box.appendChild(dot);
  box.scrollTop = box.scrollHeight;

  try {
    const stageEl = gid('stageSel');
    const r = await fetch('/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: msg, crop: currentCrop,
        stage:   stageEl ? stageEl.value : 'germination',
        sensors: currentSensors,
        lang:    currentLang
      })
    });
    const d = await r.json();
    dot.remove();
    const botDiv = document.createElement('div');
    botDiv.className = 'chat-msg bot-msg';
    botDiv.textContent = d.reply || '...';
    box.appendChild(botDiv);
    box.scrollTop = box.scrollHeight;
  } catch(e) {
    dot.remove();
    const errDiv = document.createElement('div');
    errDiv.className = 'chat-msg bot-msg';
    errDiv.textContent = currentLang === 'ta'
      ? 'பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.'
      : 'Error — please try again.';
    box.appendChild(errDiv);
    box.scrollTop = box.scrollHeight;
  }
}

// ── Enter key for chat ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const inp = gid('chatInput');
  if (inp) inp.addEventListener('keydown', e => { if (e.key === 'Enter') sendChat(); });
});

// ── WhatsApp alert ────────────────────────────────────────────
function sendWhatsApp() {
  if (!lastResult) return;
  const hs  = lastResult.health_status;
  const sc  = lastResult.health_score;
  const msg = currentLang === 'ta'
    ? `EcoSense எச்சரிக்கை!\nபயிர் ஆரோக்கியம்: ${sc}/100 (${hs})\nமண் ஈரப்பதம்: ${currentSensors.soil_moisture || '--'}%\n${lastResult.gas_alert ? '🚨 வாயு எச்சரிக்கை!' : ''}`
    : `EcoSense Alert!\nCrop Health: ${sc}/100 (${hs})\nSoil Moisture: ${currentSensors.soil_moisture || '--'}%\n${lastResult.gas_alert ? '🚨 Gas Alert!' : ''}`;
  window.open('https://wa.me/?text=' + encodeURIComponent(msg), '_blank');
}

// ── Boot ──────────────────────────────────────────────────────
async function boot() {
  await loadCrops();
  await loadStatus();
  await loadWeather();
  await loadForecast();
  applyLang();
  setMode('sim');
  setScenario('normal');
  setInterval(loadWeather,  60000);
  setInterval(loadForecast, 300000);
  setInterval(loadStatus,   30000);
}

window.addEventListener('load', boot);
