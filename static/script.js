// ── EcoSense Interactive Dashboard Script ──────────────────────
let MODE = 'sim';
let currentCrop = 'rice';
let currentSensors = {};
let uiLang = 'en';
let _esp32LastSeen = 0;
let lastResult = null;
let chatHistory = [];

const gid = id => document.getElementById(id);

const PRESETS = {
  optimal: { soil_moisture: 72, tds_ppm: 350, air_temp_c: 28, soil_temp_c: 24, humidity_pct: 65, mq135_ammonia: 50, mq4_methane: 200, mq7_co: 10, mq2_smoke: 20 },
  drought: { soil_moisture: 25, tds_ppm: 380, air_temp_c: 38, soil_temp_c: 34, humidity_pct: 28, mq135_ammonia: 60, mq4_methane: 150, mq7_co: 12, mq2_smoke: 20 },
  saline:  { soil_moisture: 68, tds_ppm: 1450, air_temp_c: 29, soil_temp_c: 25, humidity_pct: 60, mq135_ammonia: 55, mq4_methane: 180, mq7_co: 10, mq2_smoke: 20 },
  gas:     { soil_moisture: 70, tds_ppm: 400, air_temp_c: 30, soil_temp_c: 26, humidity_pct: 70, mq135_ammonia: 450, mq4_methane: 2200, mq7_co: 180, mq2_smoke: 250 },
  heat:    { soil_moisture: 48, tds_ppm: 360, air_temp_c: 42, soil_temp_c: 38, humidity_pct: 35, mq135_ammonia: 70, mq4_methane: 210, mq7_co: 15, mq2_smoke: 25 },
};

function toggleTheme() {
  const root = document.documentElement;
  const current = root.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  const btn = gid('themeToggleBtn');
  if (btn) btn.innerHTML = next === 'dark' ? '&#9728;&#65039;' : '&#127769;';
  localStorage.setItem('ecosense_theme', next);
}

function setMode(m) {
  MODE = m;
  const bl = gid('btn-live'), bs = gid('btn-sim'), mt = gid('modeTag');
  if (bl) bl.className = 'mode-btn' + (m === 'live' ? ' active-mode' : '');
  if (bs) bs.className = 'mode-btn' + (m === 'sim' ? ' active-mode' : '');
  if (mt) mt.textContent = m === 'live' ? '▶ LIVE' : '▶ SIM';
  if (m === 'sim') applyPreset('optimal');
}

function applyPreset(p) {
  if (PRESETS[p]) {
    currentSensors = { ...PRESETS[p] };
    renderSensors(currentSensors);
    runPredict();
  }
}

async function loadCrops() {
  try {
    const crops = await fetch('/crops').then(r => r.json());
    const sel = gid('cropSel');
    if (!sel) return;
    sel.innerHTML = '';
    for (let c in crops) {
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c.toUpperCase();
      sel.appendChild(opt);
    }
    sel.value = currentCrop;
    onCropChange(crops);
  } catch(e) { console.error('loadCrops:', e); }
}

async function onCropChange(cropsData) {
  const cSel = gid('cropSel'), sSel = gid('stageSel');
  if (!cSel || !sSel) return;
  currentCrop = cSel.value;
  try {
    const crops = cropsData || await fetch('/crops').then(r => r.json());
    const cData = crops[currentCrop] || { stages: [] };
    sSel.innerHTML = '';
    (cData.stages || []).forEach(st => {
      const opt = document.createElement('option');
      opt.value = st;
      opt.textContent = st.replace('_', ' ').toUpperCase();
      sSel.appendChild(opt);
    });
    runPredict();
  } catch(e) { console.error('onCropChange:', e); }
}

function renderSensors(s) {
  const setV = (id, val, unit) => { const el = gid(id); if (el) el.textContent = val !== undefined ? val + unit : '--'; };
  const setBar = (id, pct) => { const el = gid(id); if (el) el.style.width = Math.min(100, Math.max(0, pct)) + '%'; };

  setV('v-moist', Math.round(s.soil_moisture || 0), '%');
  setBar('b-moist', s.soil_moisture || 0);

  setV('v-tds', Math.round(s.tds_ppm || 0), ' ppm');
  setBar('b-tds', (s.tds_ppm || 0) / 15);

  setV('v-air', Math.round(s.air_temp_c || 0), '°C');
  setBar('b-air', ((s.air_temp_c || 0) + 10) * 1.8);

  setV('v-hum', Math.round(s.humidity_pct || 0), '%');
  setBar('b-hum', s.humidity_pct || 0);

  setV('v-soiltemp', Math.round(s.soil_temp_c || 0), '°C');
  setBar('b-soiltemp', ((s.soil_temp_c || 0) + 10) * 1.8);

  setV('v-mq135', Math.round(s.mq135_ammonia || 0), ' ppm');
  setV('v-mq4', Math.round(s.mq4_methane || 0), ' ppm');
  setV('v-mq7', Math.round(s.mq7_co || 0), ' ppm');
}

async function runPredict() {
  const sSel = gid('stageSel');
  const stage = sSel ? sSel.value : 'germination';
  try {
    const res = await fetch('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ crop: currentCrop, stage: stage, sensors: currentSensors, mode: MODE })
    }).then(r => r.json());
    lastResult = res;
    renderPredictions(res);
  } catch(e) { console.error('runPredict:', e); }
}

function renderPredictions(p) {
  if (!p) return;
  const sc = p.health_score || 0;
  const hs = p.health_status || 'GOOD';

  const sText = gid('scoreText'), hTag = gid('healthTag'), gPath = gid('gaugePath');
  if (sText) sText.textContent = sc;
  if (hTag) {
    hTag.textContent = `${hs} (${sc}/100)`;
    hTag.style.color = hs === 'GOOD' ? 'var(--accent-green)' : hs === 'MODERATE' ? 'var(--accent-yellow)' : 'var(--accent-red)';
    hTag.style.borderColor = hTag.style.color;
  }
  if (gPath) {
    const total = 126;
    const offset = total - (total * (sc / 100));
    gPath.style.strokeDashoffset = offset;
    gPath.style.stroke = hs === 'GOOD' ? 'var(--accent-green)' : hs === 'MODERATE' ? 'var(--accent-yellow)' : 'var(--accent-red)';
  }

  const dIrr = gid('d-irrigate'), dPump = gid('d-pump'), dGas = gid('d-gas'), dStage = gid('d-stage');
  if (dIrr) { dIrr.textContent = p.irrigate_now ? 'YES' : 'NO'; dIrr.style.color = p.irrigate_now ? 'var(--accent-green)' : 'var(--text-muted)'; }
  if (dPump) { dPump.textContent = p.pump_locked ? 'LOCKED' : p.pump_on ? 'ON' : 'OFF'; dPump.style.color = p.pump_locked ? 'var(--accent-red)' : p.pump_on ? 'var(--accent-green)' : 'var(--text-muted)'; }
  if (dGas) { dGas.textContent = p.gas_alert ? 'ALERT' : 'SAFE'; dGas.style.color = p.gas_alert ? 'var(--accent-red)' : 'var(--accent-green)'; }
  if (dStage) { dStage.textContent = p.is_critical_stage ? 'CRITICAL' : 'NORMAL'; dStage.style.color = p.is_critical_stage ? 'var(--accent-yellow)' : 'var(--text-muted)'; }

  const adv = gid('adviceText'), conf = gid('confText'), src = gid('inferSource');
  if (adv) {
    const irrMsg = p.irrigate_now ? 'Irrigation recommended. ' : 'Moisture adequate. ';
    const lockMsg = p.pump_locked ? '⚠️ Pump locked due to safety interlock. ' : '';
    adv.textContent = lockMsg + irrMsg + (p.weather_note || '');
  }
  if (conf) conf.textContent = (p.confidence_pct || 90) + '%';
  if (src) src.textContent = (p.inference_source || 'hybrid').toUpperCase();

  const tm = gid('t-moist'), tw = gid('t-tds'), ta = gid('t-aqi');
  if (tm) tm.textContent = p.trend_moisture || 'stable';
  if (tw) tw.textContent = p.tds_safe ? 'Safe' : 'Saline';
  if (ta) ta.textContent = `${p.field_aqi || 95} (${p.field_aqi_label || 'Good'})`;
}

async function loadWeather() {
  try {
    const w = await fetch('/weather').then(r => r.json());
    const pill = gid('weatherPill');
    if (pill && w.enabled) {
      pill.textContent = `🌤️ ${w.city}: ${w.temp}°C, Hum ${w.humidity}%, Rain ${w.rain || 0}mm`;
    }
  } catch(e) {}
}

async function loadForecast() {
  try {
    const f = await fetch('/forecast').then(r => r.json());
    const str = gid('forecastStrip'), note = gid('weatherNote');
    if (note) note.textContent = f.summary || '';
    if (str && f.enabled) {
      str.innerHTML = (f.next24h || []).map(s => `
        <div class="fc-slot">
          <div>${s.time}</div>
          <div style="font-weight:700;color:var(--accent-green)">${s.temp}°C</div>
          <div style="color:var(--accent-blue)">${s.rain}mm</div>
        </div>
      `).join('');
    }
  } catch(e) {}
}

async function loadStatus() {
  try {
    const d = await fetch('/status').then(r => r.json());
    const sb = gid('chatSourceBadge');
    if (sb) {
      sb.textContent = d.gemini_ready ? '✨ Live AI' : '🌿 Local Engine';
      sb.style.background = d.gemini_ready ? '#8e44ad' : '#27ae60';
    }
  } catch(e) {}
}

// ── Complete AI Chat System ──────────────────────────────────
function clearChat() {
  chatHistory = [];
  const box = gid('chatBox');
  if (!box) return;
  const welcomeText = uiLang === 'ta'
    ? '👋 வணக்கம்! நான் உங்கள் முழுமையான AI விவசாய வழிகாட்டி. எக்கோசென்ஸ் திட்டம், சென்சார்கள், பயிர் நோய்கள், உரங்கள், அல்லது எந்த பொதுவான கேள்வியும் கேளுங்கள்! 🌾'
    : '👋 Hi! I am your complete AI Farming Companion. Ask me anything about EcoSense, sensors, crop diseases, fertilizers, irrigation, weather, or general questions! 🌾';
  box.innerHTML = `
    <div class="chat-msg bot">
      <div class="chat-msg-header"><span class="bot-badge">EcoSense Complete AI</span></div>
      <div class="chat-msg-content">${welcomeText}</div>
    </div>
  `;
}

function renderMarkdown(txt) {
  if (!txt) return '';
  let esc = txt.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  esc = esc.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  esc = esc.replace(/(^|[^\*])\*(?!\*)(.*?)\*/g, '$1<em>$2</em>');
  const lines = esc.split('\n');
  let inList = false;
  let html = '';
  for (let line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${trimmed.substring(2)}</li>`;
    } else {
      if (inList) { html += '</ul>'; inList = false; }
      if (trimmed.length > 0) html += `<p>${line}</p>`;
    }
  }
  if (inList) html += '</ul>';
  return html;
}

function quickAsk(i) {
  const enQuestions = [
    'Should I irrigate the farm now?',
    'Is the water salinity and TDS safe for irrigation?',
    'What is the overall crop health score and status?',
    'What fertilizer and NPK should I apply at this stage?',
    'How do I detect and treat common pests and diseases?',
    'What is the pump lock and field gas sensor status?'
  ];
  const taQuestions = [
    'தற்போது வயலுக்கு பாசனம் செய்ய வேண்டுமா?',
    'நீரின் உப்புத்தன்மை (TDS) பாசனத்திற்கு பாதுகாப்பானதா?',
    'பயிரின் தற்போதைய ஆரோக்கிய நிலை மற்றும் மதிப்பெண் என்ன?',
    'இந்த வளர்ச்சிப் பருவத்தில் என்ன உரம் (NPK) இட வேண்டும்?',
    'பயிரைத் தாக்கும் பூச்சி மற்றும் நோய்களை எவ்வாறு கட்டுப்படுத்துவது?',
    'பாசன பம்ப் மற்றும் வாயு கசிவு எச்சரிக்கை நிலை என்ன?'
  ];
  const qList = (uiLang === 'ta') ? taQuestions : enQuestions;
  const q = qList[i] || enQuestions[0];
  const inp = gid('chatInput');
  if (inp) {
    inp.value = q;
    sendChat();
  }
}

async function sendChat() {
  const inp = gid('chatInput'), box = gid('chatBox');
  if (!inp || !box) return;
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = '';

  const uDiv = document.createElement('div');
  uDiv.className = 'chat-msg user';
  uDiv.textContent = msg;
  box.appendChild(uDiv);

  const dot = document.createElement('div');
  dot.className = 'chat-msg bot typing';
  dot.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  box.appendChild(dot);
  box.scrollTop = box.scrollHeight;

  try {
    const sSel = gid('stageSel');
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: msg,
        history: chatHistory,
        crop: currentCrop,
        stage: sSel ? sSel.value : 'germination',
        sensors: currentSensors,
        lang: uiLang
      })
    });
    const data = await res.json();
    dot.remove();

    const replyText = data.reply || (uiLang === 'ta' ? 'பதில் பெற முடியவில்லை.' : 'No response.');
    const sourceLabel = data.source === 'gemini' ? '✨ Live AI' : '🌿 EcoSense Local AI';

    chatHistory.push({ role: 'user', text: msg });
    chatHistory.push({ role: 'model', text: replyText });
    if (chatHistory.length > 12) chatHistory = chatHistory.slice(-12);

    const bDiv = document.createElement('div');
    bDiv.className = 'chat-msg bot';
    bDiv.innerHTML = `
      <div class="chat-msg-header">
        <span class="bot-badge">EcoSense AI</span>
        <span class="chat-msg-source">${sourceLabel}</span>
      </div>
      <div class="chat-msg-content">${renderMarkdown(replyText)}</div>
    `;
    box.appendChild(bDiv);
    box.scrollTop = box.scrollHeight;
  } catch(err) {
    dot.remove();
    const eDiv = document.createElement('div');
    eDiv.className = 'chat-msg bot';
    eDiv.textContent = uiLang === 'ta' ? 'பிழை - மீண்டும் முயற்சிக்கவும்.' : 'Error — please try again.';
    box.appendChild(eDiv);
    box.scrollTop = box.scrollHeight;
  }
}

function toggleUILang() {
  uiLang = uiLang === 'en' ? 'ta' : 'en';
  const btn = gid('langToggleBtn');
  if (btn) btn.textContent = uiLang === 'en' ? '🇮🇳 TA' : '🇬🇧 EN';
  clearChat();
}

function updateClock() {
  const el = gid('clock');
  if (el) el.textContent = new Date().toLocaleTimeString();
}

async function boot() {
  const savedTheme = localStorage.getItem('ecosense_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  const btn = gid('themeToggleBtn');
  if (btn) btn.innerHTML = savedTheme === 'dark' ? '&#9728;&#65039;' : '&#127769;';

  await loadCrops();
  await loadStatus();
  loadWeather();
  loadForecast();
  applyPreset('optimal');
  updateClock();
  setInterval(updateClock, 1000);
  setInterval(loadWeather, 60000);
  setInterval(loadForecast, 300000);
  setInterval(loadStatus, 30000);
}

window.addEventListener('load', boot);
