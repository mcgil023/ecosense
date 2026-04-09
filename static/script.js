
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
  liveInterval = setInterval(fetchLive, 5000);
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

    const healthLabels = {
      'GOOD':     '🌱 HEALTHY',
      'MODERATE': '⚠️ MODERATE',
      'POOR':     '🔴 POOR',
      'CRITICAL': '💀 CRITICAL'
    };
    const adviceMap = {
      'GOOD':     '✅ Crop looks healthy. Keep monitoring.',
      'MODERATE': '⚠️ Crop needs attention. Check moisture & temperature.',
      'POOR':     '🔴 Crop is struggling. Irrigate and inspect field.',
      'CRITICAL': '💀 CRITICAL — Immediate action required!'
    };

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
    setText('d-gas',      d.gas_alert    ? '🚨 ALERT'  : '✅ CLEAR');
    setText('d-stage',    stageEl.value);
    setText('t-moist',    d.trend_moisture || 'stable');
    setText('t-tds',      d.tds_safe ? '✅ Safe' : '⚠️ High');
    setText('t-aqi',      d.field_aqi_label || '--');
    if(gid('confText')) setText('confText', 'Confidence ' + d.confidence_pct + '%');
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
  setInterval(loadWeather, 60000);
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
        sensors: currentSensors
      })
    });
    const d = await r.json();
    addMsg('bot', d.reply || 'No reply');
  } catch { addMsg('bot', 'Connection error — server may be restarting.'); }
}

const stageEl = gid('stageSel');
if (stageEl) stageEl.addEventListener('change', runPredict);
window.addEventListener('load', boot);
