
// ── State ──────────────────────────────────────────────────────
let currentCrop = 'rice', cropStages = {};
let MODE = 'sim';          // 'sim' or 'live'
let liveInterval = null;

const SCENARIOS = {
  normal:   {soil_moisture:72,  tds_ppm:350,  air_temp_c:28, humidity_pct:65, soil_temp_c:24, mq135_ammonia:50,  mq4_methane:200,  mq7_co:10},
  dry:      {soil_moisture:28,  tds_ppm:420,  air_temp_c:34, humidity_pct:42, soil_temp_c:31, mq135_ammonia:60,  mq4_methane:220,  mq7_co:15},
  saline:   {soil_moisture:55,  tds_ppm:1200, air_temp_c:30, humidity_pct:58, soil_temp_c:27, mq135_ammonia:70,  mq4_methane:250,  mq7_co:20},
  gas:      {soil_moisture:68,  tds_ppm:360,  air_temp_c:29, humidity_pct:64, soil_temp_c:25, mq135_ammonia:260, mq4_methane:1400, mq7_co:140},
  heat:     {soil_moisture:48,  tds_ppm:500,  air_temp_c:41, humidity_pct:30, soil_temp_c:36, mq135_ammonia:80,  mq4_methane:300,  mq7_co:22},
  critical: {soil_moisture:18,  tds_ppm:1600, air_temp_c:43, humidity_pct:22, soil_temp_c:39, mq135_ammonia:320, mq4_methane:1800, mq7_co:170}
};

function gid(x)  { return document.getElementById(x); }
function hv(id)  { return +gid(id).value; }
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

// ── Live Poll — fetches /live every 5s ──────────────────────────
function startLivePoll() {
  stopLivePoll();
  fetchLive();  // immediate first fetch
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

    // Update hidden sim inputs with live values so predict uses them
    if (d.soil_moisture !== undefined) gid('s-moist-v').value    = d.soil_moisture;
    if (d.tds_ppm       !== undefined) gid('s-tds-v').value      = d.tds_ppm;
    if (d.air_temp_c    !== undefined) gid('s-air-v').value      = d.air_temp_c;
    if (d.humidity_pct  !== undefined) gid('s-hum-v').value      = d.humidity_pct;
    if (d.soil_temp_c   !== undefined) gid('s-soiltemp-v').value = d.soil_temp_c;
    if (d.mq135_ammonia !== undefined) gid('s-mq135-v').value    = d.mq135_ammonia;
    if (d.mq4_methane   !== undefined) gid('s-mq4-v').value      = d.mq4_methane;
    if (d.mq7_co        !== undefined) gid('s-mq7-v').value      = d.mq7_co;

    renderSensors(d);
    runPredict();
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
  const moist = d.soil_moisture !== undefined ? d.soil_moisture : hv('s-moist-v');
  const tds   = d.tds_ppm       !== undefined ? d.tds_ppm       : hv('s-tds-v');
  const air   = d.air_temp_c    !== undefined ? d.air_temp_c    : hv('s-air-v');
  const hum   = d.humidity_pct  !== undefined ? d.humidity_pct  : hv('s-hum-v');
  const st    = d.soil_temp_c   !== undefined ? d.soil_temp_c   : hv('s-soiltemp-v');
  const nh3   = d.mq135_ammonia !== undefined ? d.mq135_ammonia : hv('s-mq135-v');
  const ch4   = d.mq4_methane   !== undefined ? d.mq4_methane   : hv('s-mq4-v');
  const co    = d.mq7_co        !== undefined ? d.mq7_co        : hv('s-mq7-v');

  setText('v-moist',   moist + '%');     setBar('b-moist',   moist);
  setText('v-tds',     tds   + ' ppm');  setBar('b-tds',     Math.min(100, tds/20));
  setText('v-air',     air   + '°C');    setBar('b-air',     Math.min(100, air*2));
  setText('v-hum',     hum   + '%');     setBar('b-hum',     hum);
  setText('v-soiltemp',st    + '°C');    setBar('b-soiltemp',Math.min(100, st*2));
  setText('v-mq135',   nh3   + ' ppm');
  setText('v-mq4',     ch4   + ' ppm');
  setText('v-mq7',     co    + ' ppm');
}

// ── Get sensor values for predict ──────────────────────────────
function getSensors() {
  return {
    soil_moisture: hv('s-moist-v'),  tds_ppm: hv('s-tds-v'),
    air_temp_c:    hv('s-air-v'),    humidity_pct: hv('s-hum-v'),
    soil_temp_c:   hv('s-soiltemp-v'), mq135_ammonia: hv('s-mq135-v'),
    mq4_methane:   hv('s-mq4-v'),   mq7_co: hv('s-mq7-v')
  };
}

// ── Scenario setter (sim mode) ──────────────────────────────────
function setScenario(name) {
  const v = SCENARIOS[name];
  gid('s-moist-v').value    = v.soil_moisture;
  gid('s-tds-v').value      = v.tds_ppm;
  gid('s-air-v').value      = v.air_temp_c;
  gid('s-hum-v').value      = v.humidity_pct;
  gid('s-soiltemp-v').value = v.soil_temp_c;
  gid('s-mq135-v').value    = v.mq135_ammonia;
  gid('s-mq4-v').value      = v.mq4_methane;
  gid('s-mq7-v').value      = v.mq7_co;
  renderSensors(v);
  runPredict();
}

// ── Predict ─────────────────────────────────────────────────────
async function runPredict() {
  try {
    const sensors = getSensors();
    const r = await fetch('/predict', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({crop: currentCrop, stage: gid('stageSel').value, sensors})
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || 'Predict failed');

    gid('scoreText').textContent = d.health_score;
    gid('healthTag').textContent = d.health_status === 'GOOD' ? '🌱 HEALTHY' : d.health_status;
    gid('adviceText').textContent =
      d.health_status === 'GOOD'     ? 'Crop looks healthy. Keep monitoring.' :
      d.health_status === 'MODERATE' ? 'Crop needs attention. Check moisture.' :
      d.health_status === 'POOR'     ? 'Crop is struggling. Take action soon.' :
                                       'Urgent! Crop is in critical condition.';
    gid('d-irrigate').textContent = d.irrigate_now ? 'YES' : 'NO';
    gid('d-pump').textContent     = d.pump_locked  ? 'LOCKED' : (d.pump_on ? 'ON' : 'OFF');
    gid('d-gas').textContent      = d.gas_alert    ? 'ALERT'  : 'CLEAR';
    gid('d-stage').textContent    = gid('stageSel').value;
    gid('t-moist').textContent    = d.trend_moisture;
    gid('t-tds').textContent      = d.tds_safe ? 'Safe' : 'High';
    gid('t-aqi').textContent      = d.field_aqi_label;
  } catch(e) {
    console.error(e);
    gid('adviceText').textContent = 'Prediction error.';
  }
}

// ── Weather ─────────────────────────────────────────────────────
async function loadWeather() {
  try {
    const d = await fetch('/weather').then(r => r.json());
    gid('weatherPill').textContent  = '☁️ ' + d.temp + '°C';
    gid('weatherStrip').textContent = `🌥 ${d.city}: ${d.temp}°C · Humidity ${d.humidity}% · Rain ${d.rain}mm · Wind ${d.wind}m/s`;
  } catch {}
}

// ── Status ──────────────────────────────────────────────────────
async function loadStatus() {
  try {
    const d = await fetch('/status').then(r => r.json());
    gid('aiBadge').textContent    = d.gemini_ready ? '🤖 Gemini ON' : '🤖 AI';
    gid('chatStatus').textContent = d.gemini_ready ? 'ONLINE' : 'OFFLINE';
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
  setMode('sim');   // default sim mode
}

function fillStages() {
  const s = gid('stageSel');
  s.innerHTML = '';
  (cropStages[currentCrop]?.stages || ['germination']).forEach(v => {
    const o = document.createElement('option');
    o.value = v; o.textContent = v[0].toUpperCase() + v.slice(1);
    s.appendChild(o);
  });
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
    const sensors = getSensors();
    const r = await fetch('/chat', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({message: msg, crop: currentCrop, stage: gid('stageSel').value, sensors})
    });
    const d = await r.json();
    addMsg('bot', d.reply || 'No reply');
  } catch { addMsg('bot', 'Connection error.'); }
}

gid('stageSel')?.addEventListener('change', runPredict);
window.addEventListener('load', boot);
