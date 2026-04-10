'use strict';
// EcoSense — Final Perfect Build
// Tamil (default) / English toggle for readings, advice, chat
// Sim menu always English

const gid     = id => document.getElementById(id);
const setText = (id, t) => { const e = gid(id); if (e) e.textContent = t; };

// ── State ─────────────────────────────────────────────────────
let MODE         = 'sim';
let currentCrop  = 'rice';
let uiLang       = 'ta';
let liveInterval = null;
let lastResult   = null;
let currentSensors = {};
const cropStages   = {};

// ── Language table (only readings/advice/chat — sim stays EN) ─
const L = {
  en: {
    ptSensor:'LIVE SENSOR READINGS', ptGas:'GAS SENSORS',
    advTitle:'🤖 AI Field Advice', chatHead:'🌿 AI Farming Companion',
    chatWelcome:"👋 Hi! I'm your AI Farming Companion. Ask me anything! 🌱",
    chatPH:'Ask me anything about your farm...',
    conf:'Confidence ',
    dlIrr:'Irrigate', dlPump:'Pump', dlGas:'Gas', dlStage:'Stage',
    tkMoist:'Moisture Trend:', tkWater:'Water:', tkAir:'Air Quality:',
    lblMoist:'💧 Soil Moisture', lblTds:'🧂 Water TDS',
    lblAir:'🌡️ Air Temp', lblHum:'💦 Humidity', lblSoil:'🌱 Soil Temp',
    health:{ GOOD:'🌱 GOOD', MODERATE:'⚠️ MODERATE', POOR:'😢 POOR', CRITICAL:'💀 CRITICAL' },
    advice:{
      GOOD:'✅ Crop looks healthy. Keep monitoring.',
      MODERATE:'⚠️ Crop needs attention. Check moisture & temperature.',
      POOR:'🔴 Crop is struggling. Irrigate and inspect field.',
      CRITICAL:'💀 CRITICAL — Immediate action required!'
    },
    trend:{ stable:'Stable', rising:'Rising', falling:'Falling' },
    tdsOk:'✅ Safe', tdsHigh:'⚠️ High',
    aqi:{ Excellent:'Excellent', Good:'Good', Moderate:'Moderate', Poor:'Poor' },
    waBtn:'📲 Send WhatsApp Alert', langBtn:'🇮🇳 TA',
    ql:['💧 Irrigate?','🧂 Water safe?','🌱 Health?','🌿 Fertilize?','☁️ Air quality?','⚙️ Pump status?'],
    qq:['Should I irrigate now?','Is water quality safe?','How is crop health?',
        'Can I fertilize now?','Is air quality safe?','What is pump status?'],
    wmap:{}
  },
  ta: {
    ptSensor:'நேரடி உணரி அளவீடுகள்', ptGas:'வாயு உணரிகள்',
    advTitle:'🤖 AI வயல் ஆலோசனை', chatHead:'🌿 AI வேளாண் உதவியாளர்',
    chatWelcome:'👋 வணக்கம்! நான் உங்கள் AI வேளாண் உதவியாளர். கேளுங்கள்! 🌱',
    chatPH:'உங்கள் வயலைப் பற்றி கேளுங்கள்...',
    conf:'நம்பகத்தன்மை ',
    dlIrr:'நீர்ப்பாசனம்', dlPump:'பம்ப்', dlGas:'வாயு', dlStage:'நிலை',
    tkMoist:'ஈரப்பதம்:', tkWater:'நீர்:', tkAir:'காற்று தரம்:',
    lblMoist:'💧 மண் ஈரப்பதம்', lblTds:'🧂 நீர் TDS',
    lblAir:'🌡️ காற்று வெப்பம்', lblHum:'💦 ஈரப்பதம்', lblSoil:'🌱 மண் வெப்பம்',
    health:{ GOOD:'🌱 நல்லது', MODERATE:'⚠️ நடுத்தரம்', POOR:'😢 மோசம்', CRITICAL:'💀 அவசரம்' },
    advice:{
      GOOD:'✅ பயிர் ஆரோக்கியமாக உள்ளது. தொடர்ந்து கண்காணியுங்கள்.',
      MODERATE:'⚠️ பயிருக்கு கவனிப்பு தேவை. ஈரப்பதம் & வெப்பம் சரிபாருங்கள்.',
      POOR:'🔴 பயிர் கஷ்டப்படுகிறது. நீர் பாய்ச்சி வயலை சோதியுங்கள்.',
      CRITICAL:'💀 அவசரம் — உடனடி நடவடிக்கை தேவை!'
    },
    trend:{ stable:'நிலையான', rising:'உயர்கிறது', falling:'குறைகிறது' },
    tdsOk:'✅ பாதுகாப்பு', tdsHigh:'⚠️ அதிகம்',
    aqi:{ Excellent:'மிகவும் நல்லது', Good:'நல்லது', Moderate:'நடுத்தரம்', Poor:'மோசம்' },
    waBtn:'📲 வாட்ஸ்அப் எச்சரிக்கை அனுப்பு', langBtn:'🇬🇧 EN',
    ql:['💧 பாசனமா?','🧂 நீர் பாதுகாப்பா?','🌱 ஆரோக்கியம்?','🌿 உரமிடலாமா?','☁️ காற்று தரம்?','⚙️ பம்ப் நிலை?'],
    qq:['இப்போது நீர் பாய்ச்சலாமா?','நீர் தரம் பாதுகாப்பானதா?',
        'பயிரின் ஆரோக்கியம் எப்படி?','இப்போது உரமிடலாமா?',
        'காற்று தரம் பாதுகாப்பானதா?','பம்ப் நிலை என்ன?'],
    wmap:{
      'Stable weather next 24h':'🌤 அடுத்த 24 மணி நேரம் நிலையான வானிலை',
      'Light rain expected':'🌦 இலேசான மழை எதிர்பார்க்கப்படுகிறது',
      'Heavy rain':'🌧 கனமழை வரும் — நீர்ப்பாசனம் தவிர்க்கவும்',
      'Stable weather':'🌤 நிலையான வானிலை',
      'Weather normal':'🌤 வானிலை சாதாரணம்',
      'Forecast unavailable':'வானிலை கணிப்பு இல்லை'
    }
  }
};

// ── Apply language to all static labels ───────────────────────
function applyLang() {
  const S = L[uiLang];
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
  const wa = gid('waBtn');        if (wa) wa.textContent = S.waBtn;
  const lb = gid('langToggleBtn');if (lb) lb.textContent = S.langBtn;
  document.querySelectorAll('.quick-grid button')
    .forEach((b,i) => { if (S.ql[i]) b.textContent = S.ql[i]; });
  if (lastResult) applyResultLang(lastResult);
}

// ── Apply language to dynamic result values ────────────────────
function applyResultLang(d) {
  const S  = L[uiLang];
  const hs = d.health_status || 'GOOD';
  setText('healthTag',  S.health[hs]);
  setText('adviceText', S.advice[hs]);
  setText('confText',   S.conf + (d.confidence_pct||'--') + '%');
  setText('t-moist',    S.trend[d.trend_moisture] || d.trend_moisture || '--');
  setText('t-tds',      d.tds_safe ? S.tdsOk : S.tdsHigh);
  setText('t-aqi',      S.aqi[d.field_aqi_label]  || d.field_aqi_label || '--');
  if (d.weather_note) {
    let wt = d.weather_note;
    if (uiLang === 'ta') {
      for (const [en,ta] of Object.entries(S.wmap)) {
        if (wt.includes(en)) { wt = ta; break; }
      }
    }
    setText('weatherNote', wt);
  }
}

// ── Toggle button handler (called from HTML onclick) ──────────
function toggleUILang() {
  uiLang = uiLang === 'ta' ? 'en' : 'ta';
  applyLang();
}

// ── Clock ─────────────────────────────────────────────────────
setInterval(() => setText('clock', new Date().toLocaleTimeString('en-IN')), 1000);

// ── Crop tabs ─────────────────────────────────────────────────
async function loadCrops() {
  try {
    const data = await fetch('/crops').then(r => r.json());
    Object.assign(cropStages, data);
    const tabs = gid('crop-tabs'); if (!tabs) return;
    tabs.innerHTML = '';
    Object.keys(data).forEach(c => {
      const btn = document.createElement('button');
      btn.textContent = c.charAt(0).toUpperCase() + c.slice(1);
      btn.className = 'crop-tab' + (c === currentCrop ? ' active' : '');
      btn.onclick = () => {
        currentCrop = c; fillStages(); runPredict();
        tabs.querySelectorAll('.crop-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      };
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

// ── Scenarios ─────────────────────────────────────────────────
const SCENARIOS = {
  normal:  {soil_moisture:72,tds_ppm:350, air_temp_c:28,soil_temp_c:24,humidity_pct:65,mq135_ammonia:50, mq4_methane:200, mq7_co:10},
  dry:     {soil_moisture:30,tds_ppm:380, air_temp_c:34,soil_temp_c:30,humidity_pct:40,mq135_ammonia:60, mq4_methane:210, mq7_co:12},
  saline:  {soil_moisture:55,tds_ppm:1400,air_temp_c:30,soil_temp_c:26,humidity_pct:60,mq135_ammonia:55, mq4_methane:200, mq7_co:10},
  gas:     {soil_moisture:68,tds_ppm:360, air_temp_c:29,soil_temp_c:25,humidity_pct:70,mq135_ammonia:320,mq4_methane:1200,mq7_co:150},
  heat:    {soil_moisture:50,tds_ppm:400, air_temp_c:42,soil_temp_c:38,humidity_pct:30,mq135_ammonia:70, mq4_methane:220, mq7_co:15},
  critical:{soil_moisture:20,tds_ppm:1600,air_temp_c:44,soil_temp_c:40,humidity_pct:20,mq135_ammonia:350,mq4_methane:1300,mq7_co:180}
};

function setScenario(name) {
  currentSensors = {...SCENARIOS[name]};
  document.querySelectorAll('.scenario-chips button')
    .forEach(b => b.classList.toggle('active-chip', b.id === 'sc-'+name));
  renderSensors(currentSensors);
  runPredict();
}

// ── Render sensors ────────────────────────────────────────────
function renderSensors(s) {
  const num = (v, dec=1) => v !== undefined ? Number(v).toFixed(dec) : '--';
  setText('v-moist',    num(s.soil_moisture)  + '%');
  setText('v-tds',      num(s.tds_ppm, 0)     + ' ppm');
  setText('v-air',      num(s.air_temp_c)     + '°C');
  setText('v-hum',      num(s.humidity_pct)   + '%');
  setText('v-soiltemp', num(s.soil_temp_c)    + '°C');
  setText('v-mq135',    num(s.mq135_ammonia,0)+ ' ppm');
  setText('v-mq4',      num(s.mq4_methane, 0) + ' ppm');
  setText('v-mq7',      num(s.mq7_co, 0)      + ' ppm');
  const pct = (v, max) => Math.max(2, Math.min(100, (v/max)*100));
  const bar = (id, v, max) => { const el=gid(id); if(el) el.style.width=pct(v,max)+'%'; };
  bar('b-moist',   s.soil_moisture,  100);
  bar('b-tds',     s.tds_ppm,        2000);
  bar('b-air',     s.air_temp_c,     50);
  bar('b-hum',     s.humidity_pct,   100);
  bar('b-soiltemp',s.soil_temp_c,    50);
}

// ── Predict ───────────────────────────────────────────────────
async function runPredict() {
  const stEl = gid('stageSel');
  try {
    const d = await fetch('/predict', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({crop:currentCrop,
        stage: stEl ? stEl.value : 'germination',
        sensors: currentSensors})
    }).then(r => r.json());

    lastResult = d;
    const S  = L[uiLang];
    const hs = d.health_status || 'GOOD';

    setText('scoreText',  d.health_score);
    setText('healthTag',  S.health[hs]);
    setText('adviceText', S.advice[hs]);
    setText('confText',   S.conf + (d.confidence_pct||'--') + '%');

    // Gauge
    const fill = gid('gaugeFill'), needle = gid('gaugeNeedle');
    if (fill)   fill.style.width  = d.health_score + '%';
    if (needle) needle.style.left = d.health_score + '%';

    // Face animation
    const colors = {GOOD:'#2ecc71',MODERATE:'#f39c12',POOR:'#e67e22',CRITICAL:'#e74c3c'};
    const c = colors[hs] || '#2ecc71';
    const face = gid('cropFace'); if(face) face.className='crop-face '+hs.toLowerCase();
    const eyeL=gid('eye-l'), eyeR=gid('eye-r'), mouth=gid('mouth'), sparks=gid('sparkles');
    if(eyeL) eyeL.setAttribute('fill',c);
    if(eyeR) eyeR.setAttribute('fill',c);
    if(mouth){
      const mp={GOOD:'M33 43 Q40 50 47 43',MODERATE:'M33 44 Q40 46 47 44',
                POOR:'M33 47 Q40 44 47 47',CRITICAL:'M32 48 Q40 42 48 48'};
      mouth.setAttribute('d', mp[hs]||mp.GOOD);
      mouth.setAttribute('stroke', c);
    }
    if(sparks) sparks.style.display = hs==='GOOD' ? '' : 'none';

    // Decisions
    setText('d-irrigate', d.irrigate_now ? '✅ YES' : 'NO');
    setText('d-pump',     d.pump_locked  ? '🔒 LOCKED' : (d.pump_on ? '🟢 ON' : '⚪ OFF'));
    setText('d-gas',      d.gas_alert    ? '🚨 ALERT'  : '✅ CLEAR');
    setText('d-stage',    stEl ? stEl.value : '--');

    // Trend / TDS / AQI
    setText('t-moist', S.trend[d.trend_moisture] || d.trend_moisture || '--');
    setText('t-tds',   d.tds_safe ? S.tdsOk : S.tdsHigh);
    setText('t-aqi',   S.aqi[d.field_aqi_label] || d.field_aqi_label || '--');

    // Weather note
    if (d.weather_note) {
      let wt = d.weather_note;
      if (uiLang === 'ta') {
        for (const [en,ta] of Object.entries(S.wmap)) {
          if (wt.includes(en)) { wt = ta; break; }
        }
      }
      setText('weatherNote', wt);
    }

    // WhatsApp pulse
    const wa = gid('waBtn');
    if (wa) wa.classList.toggle('alert-active',
      d.gas_alert || hs === 'CRITICAL' || hs === 'POOR');

  } catch(e) {
    console.error('Predict:', e);
    setTimeout(runPredict, 3000);
  }
}

// ── Mode ──────────────────────────────────────────────────────
function setMode(mode) {
  MODE = mode;
  stopLive();
  const lb = gid('btn-live'), sb = gid('btn-sim');
  const bar= gid('simbar'),   mt = gid('modeTag');
  if (MODE === 'live') {
    if(lb) lb.classList.add('active-mode');    if(sb) sb.classList.remove('active-mode');
    if(bar) bar.style.opacity='0.4';
    if(mt){ mt.textContent='📡 LIVE'; mt.style.background='#c0392b'; }
    startLive();
  } else {
    if(sb) sb.classList.add('active-mode');    if(lb) lb.classList.remove('active-mode');
    if(bar) bar.style.opacity='1';
    if(mt){ mt.textContent='🎛️ SIM'; mt.style.background='#27ae60'; }
    setScenario('normal');
  }
}

// ── Live: SSE push (<200ms) with 1s poll fallback ────────────────
let _sse = null;
function startLive() {
  stopLive();
  // Try SSE first — instant push from ESP32
  try {
    _sse = new EventSource('/stream');
    _sse.onmessage = e => {
      try {
        const d = JSON.parse(e.data);
        if (!d || Object.keys(d).length === 0) return;  // heartbeat
        currentSensors = {...currentSensors, ...d};
        renderSensors(currentSensors);
        runPredict();
      } catch {}
    };
    _sse.onerror = () => {
      // SSE failed — fall back to 1s polling
      if (_sse) { _sse.close(); _sse = null; }
      if (!liveInterval) liveInterval = setInterval(fetchLive, 1000);
    };
    console.log('✅ SSE live stream connected');
  } catch {
    // SSE not supported — use polling
    fetchLive();
    liveInterval = setInterval(fetchLive, 1000);
  }
}
function stopLive() {
  if (_sse)        { _sse.close(); _sse = null; }
  if (liveInterval){ clearInterval(liveInterval); liveInterval = null; }
}
async function fetchLive() {
  try {
    const d = await fetch('/live').then(r => r.json());
    if (d.status === 'no_data') return;
    currentSensors = {...currentSensors, ...d};
    renderSensors(currentSensors);
    runPredict();
  } catch(e) { console.warn('fetchLive:', e); }
}

// ── Weather & Forecast ────────────────────────────────────────
async function loadWeather() {
  try {
    const d = await fetch('/weather').then(r => r.json());
    const p = gid('weatherPill');
    if(p && d.enabled) p.textContent = d.city+' '+d.temp+'°C 💧'+d.humidity+'%';
  } catch {}
}

async function loadForecast() {
  try {
    const d = await fetch('/forecast').then(r => r.json());
    const s = gid('forecastStrip'); if (!s) return;
    if (!d.enabled || !d.next24h?.length) {
      s.innerHTML = '<span style="opacity:.5;font-size:11px">Forecast unavailable</span>';
      return;
    }
    s.innerHTML = d.next24h.map(f =>
      `<div class="fc-slot"><div class="fc-time">${f.time}</div>
       <div class="fc-icon">${f.rain>1?'🌧':f.temp>36?'🌡️':'☀️'}</div>
       <div class="fc-temp">${f.temp}°</div>
       <div class="fc-rain">${f.rain>0?f.rain+'mm':''}</div></div>`
    ).join('');
  } catch {}
}

async function loadStatus() {
  try {
    const d = await fetch('/status').then(r => r.json());
    const b = gid('aiBadge');
    if(b){ b.textContent=d.gemini_ready?'✨ Gemini':'🔧 Offline';
           b.style.background=d.gemini_ready?'#8e44ad':'#7f8c8d'; }
  } catch {}
}

// ── Chat ──────────────────────────────────────────────────────
function quickAsk(i) {
  const q = L[uiLang].qq[i]; if (!q) return;
  const inp = gid('chatInput'); if(inp) inp.value = q;
  sendChat();
}

async function sendChat() {
  const inp = gid('chatInput'), box = gid('chatBox');
  if (!inp || !box) return;
  const msg = inp.value.trim(); if (!msg) return;
  inp.value = '';
  const uDiv = document.createElement('div');
  uDiv.className = 'chat-msg user-msg'; uDiv.textContent = msg;
  box.appendChild(uDiv);
  const dot = document.createElement('div');
  dot.className = 'chat-msg bot-msg typing';
  dot.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  box.appendChild(dot); box.scrollTop = box.scrollHeight;
  try {
    const stEl = gid('stageSel');
    const r = await fetch('/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message:msg, crop:currentCrop,
        stage: stEl ? stEl.value : 'germination',
        sensors: currentSensors, lang: uiLang })
    });
    const d = await r.json(); dot.remove();
    const bDiv = document.createElement('div');
    bDiv.className = 'chat-msg bot-msg'; bDiv.textContent = d.reply || '...';
    box.appendChild(bDiv); box.scrollTop = box.scrollHeight;
  } catch {
    dot.remove();
    const eDiv = document.createElement('div');
    eDiv.className = 'chat-msg bot-msg';
    eDiv.textContent = uiLang==='ta'?'பிழை — மீண்டும் முயற்சிக்கவும்.':'Error — please try again.';
    box.appendChild(eDiv);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const inp = gid('chatInput');
  if (inp) inp.addEventListener('keydown', e => { if(e.key==='Enter') sendChat(); });
});

// ── WhatsApp ──────────────────────────────────────────────────
function sendWhatsApp() {
  if (!lastResult) return;
  const hs = lastResult.health_status, sc = lastResult.health_score;
  const msg = uiLang==='ta'
    ? `EcoSense எச்சரிக்கை!\nபயிர் ஆரோக்கியம்: ${sc}/100 (${hs})\nமண் ஈரப்பதம்: ${currentSensors.soil_moisture||'--'}%\n${lastResult.gas_alert?'🚨 வாயு எச்சரிக்கை!':''}`
    : `EcoSense Alert!\nCrop Health: ${sc}/100 (${hs})\nSoil Moisture: ${currentSensors.soil_moisture||'--'}%\n${lastResult.gas_alert?'🚨 Gas Alert!':''}`;
  window.open('https://wa.me/?text='+encodeURIComponent(msg),'_blank');
}

// ── Boot ──────────────────────────────────────────────────────
async function boot() {
  await loadCrops();
  await loadStatus();
  loadWeather();
  loadForecast();
  applyLang();
  setMode('sim');
  setInterval(loadWeather,  60000);
  setInterval(loadForecast, 300000);
  setInterval(loadStatus,   30000);
}

window.addEventListener('load', boot);
