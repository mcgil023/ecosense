
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

// Current sensor values held in memory (source of truth)
let currentSensors = Object.assign({}, SCENARIOS.normal);

function gid(x)  { return document.getElementById(x); }
function setBar(id, p) { const el=gid(id); if(el) el.style.width = Math.max(4,Math.min(100,p))+'%'; }
function setText(id, t) { const el=gid(id); if(el) el.textContent = t; }

// ── Clock ───────────────────────────────────────────────────────
function clock() { gid('clock').textContent = new Date().toLocaleTimeString(); }
setInterval(clock, 1000); clock();

// ── Mode Switch ─────────────────────────────────────────────────
function setMode(mode) {
  MODE = mode;
  const liveBtn = gid('btn-live');
  const simBtn  = gid('btn-sim');
  const simBar  = gid('simbar');
  const modeTag = gid('modeTag');

  if (MODE === 'live') {
    liveBtn.classList.add('active-mode');
    simBtn.classList.remove('active-mode');
    if (simBar) simBar.style.opacity = '0.4';
    if (modeTag) { modeTag.textContent = '📡 LIVE'; modeTag.style.background='#1a4d1a'; }
    startLivePoll();
  } else {
    simBtn.classList.add('active-mode');
    liveBtn.classList.remove('active-mode');
    if (simBar) simBar.style.opacity = '1';
    if (modeTag) { modeTag.textContent = '🎛️ SIM'; modeTag.style.background='#3a2a00'; }
    stopLivePoll();
    setScenario('normal');
  }
}

// ── Live Poll ───────────────────────────────────────────────────
function startLivePoll() {
  stopLivePoll();
  fetchLive();
  liveInterval = setInterval(fetchLive, 5000);
}
function stopLivePoll() {
  if (liveInterval) { clearInterval(liveInterval); liveInterval = null; }
}
async function fetchLive() {
  try {
    const r = await fetch('/live');
    const d = await r.json();
    if (d.status === 'no_data') {
      setText('modeTag', '📡 LIVE — No ESP32 data yet');
      gid('modeTag').style.background = '#4d2a00';
      return;
    }
    // Update currentSensors with live data
    Object.keys(d).forEach(k => { if (k !== 'status') currentSensors[k] = d[k]; });
    renderSensors(currentSensors);
    await runPredict();
    gid('modeTag').textContent = '📡 LIVE ✅';
    gid('modeTag').style.background = '#1a4d1a';
  } catch(e) {
    console.error('Live fetch error:', e);
    gid('modeTag').textContent = '📡 LIVE — Error';
    gid('modeTag').style.background = '#4d0000';
  }
}

// ── Render sensor bars ──────────────────────────────────────────
function renderSensors(d) {
  setText('v-moist',    d.soil_moisture + '%');
  setText('v-tds',      d.tds_ppm + ' ppm');
  setText('v-air',      d.air_temp_c + '°C');
  setText('v-hum',      d.humidity_pct + '%');
  setText('v-soiltemp', d.soil_temp_c + '°C');
  setText('v-mq135',    d.mq135_ammonia + ' ppm');
  setText('v-mq4',      d.mq4_methane + ' ppm');
  setText('v-mq7',      d.mq7_co + ' ppm');

  setBar('b-moist',    d.soil_moisture);
  setBar('b-tds',      Math.min(100, d.tds_ppm / 20));
  setBar('b-air',      Math.min(100, d.air_temp_c * 2));
  setBar('b-hum',      d.humidity_pct);
  setBar('b-soiltemp', Math.min(100, d.soil_temp_c * 2));
}

// ── Scenario setter (sim mode) — KEY FIX ───────────────────────
function setScenario(name) {
  const v = SCENARIOS[name];
  // Update currentSensors in memory — this is what runPredict reads
  currentSensors = Object.assign({}, v);
  renderSensors(currentSensors);
  runPredict();   // called AFTER currentSensors is updated
}

// ── Run Predict — always uses currentSensors ────────────────────
async function runPredict() {
  try {
    const r = await fetch('/predict', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        crop:    currentCrop,
        stage:   gid('stageSel').value,
        sensors: currentSensors        // ← always fresh object
      })
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || 'Predict failed');

    setText('scoreText', d.health_score);
    setText('healthTag', d.health_status === 'GOOD'     ? '🌱 HEALTHY' :
                         d.health_status === 'MODERATE' ? '⚠️ MODERATE' :
                         d.health_status === 'POOR'     ? '🔴 POOR' : '💀 CRITICAL');
    setText('adviceText',
      d.health_status === 'GOOD'     ? '✅ Crop looks healthy. Keep monitoring.' :
      d.health_status === 'MODERATE' ? '⚠️ Crop needs attention. Check moisture & temperature.' :
      d.health_status === 'POOR'     ? '🔴 Crop is struggling. Irrigate and inspect field.' :
                                       '💀 CRITICAL — Immediate action required!');

    setText('d-irrigate', d.irrigate_now ? '✅ YES' : 'NO');
    setText('d-pump',     d.pump_locked  ? '🔒 LOCKED' : (d.pump_on ? '🟢 ON' : 'OFF'));
    setText('d-gas',      d.gas_alert    ? '🚨 ALERT'  : '✅ CLEAR');
    setText('d-stage',    gid('stageSel').value);
    setText('t-moist',    d.trend_moisture);
    setText('t-tds',      d.tds_safe ? '✅ Safe' : '⚠️ High');
    setText('t-aqi',      d.field_aqi_label);
    if (gid('confText')) setText('confText', 'Confidence ' + d.confidence_pct + '%');
  } catch(e) {
    console.error('Predict error:', e);
    setText('adviceText', 'Prediction error — check server.');
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
  } catch {}
}

// ── Crop tabs ───────────────────────────────────────────────────
async function boot() {
  const c = await fetch('/crops').then(r => r.json());
  cropStages = c;
  const tabs = gid('crop-tabs');
  Object.keys(c).forEach((k, i) => {
    const b = document.createElement('button');
    b.textContent = '🌾 ' + k[0].toUpperCase() + k.slice(1);
    b.className   = 'crop-btn' + (i === 0 ? ' active' : '');
    b.onclick = () => {
      document.querySelectorAll('.crop-btn').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      currentCrop = k;
      fillStages();
      runPredict();
    };
    tabs.appendChild(b);
  });
  fillStages();
  await loadStatus();
  await loadWeather();
  setInterval(loadWeather, 60000);
  setMode('sim');
}

function fillStages() {
  const s = gid('stageSel');
  s.innerHTML = '';
  const crop = cropStages[currentCrop];
  const stages = crop?.stages ? Object.keys(crop.stages) : (crop || ['germination']);
  stages.forEach(v => {
    const o = document.createElement('option');
    o.value = v; o.textContent = v[0].toUpperCase() + v.slice(1).replace('_',' ');
    s.appendChild(o);
  });
  runPredict();
}

// ── Chat ─────────────────────────────────────────────────────────
function addMsg(cls, txt) {
  const box = gid('chatBox');
  const div = document.createElement('div');
  div.className = cls; div.textContent = txt;
  box.appendChild(div); box.scrollTop = box.scrollHeight;
}
function quickAsk(q) { gid('chatInput').value = q; sendChat(); }
async function sendChat() {
  const msg = gid('chatInput').value.trim();
  if (!msg) return;
  addMsg('user', msg); gid('chatInput').value = '';
  try {
    const r = await fetch('/chat', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        message: msg,
        crop:    currentCrop,
        stage:   gid('stageSel').value,
        sensors: currentSensors          // ← uses currentSensors too
      })
    });
    const d = await r.json();
    addMsg('bot', d.reply || 'No reply');
  } catch { addMsg('bot', 'Connection error.'); }
}

gid('stageSel')?.addEventListener('change', runPredict);
window.addEventListener('load', boot);
