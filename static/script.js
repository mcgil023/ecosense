
let currentCrop='rice', cropStages={};
const SIM_H=46, SIM_EXP=260;

const SCENARIOS={
  normal:  {moisture:72,tds:350, airtemp:27,soiltemp:23,humidity:65,mq135:50, mq4:200, mq7:10, mq2:50},
  dry:     {moisture:32,tds:350, airtemp:36,soiltemp:31,humidity:40,mq135:70, mq4:200, mq7:10, mq2:50},
  saline:  {moisture:72,tds:1400,airtemp:28,soiltemp:24,humidity:60,mq135:50, mq4:200, mq7:10, mq2:50},
  gas:     {moisture:68,tds:350, airtemp:28,soiltemp:24,humidity:62,mq135:290,mq4:1300,mq7:90, mq2:550},
  heat:    {moisture:60,tds:300, airtemp:43,soiltemp:39,humidity:28,mq135:50, mq4:200, mq7:10, mq2:50},
  critical:{moisture:28,tds:1600,airtemp:44,soiltemp:40,humidity:20,mq135:310,mq4:1400,mq7:110,mq2:600}
};

window.onload=()=>{
  updateGridHeight();
  fetch('/crops').then(r=>r.json()).then(d=>{cropStages=d;buildStages(currentCrop);});
  fetch('/weather').then(r=>r.json()).then(w=>{
    if(w.enabled){
      document.getElementById('weather-pill').textContent=`🌦 ${w.temp}°C`;
      document.getElementById('weather-strip').textContent=`🌦 ${w.city}: ${w.temp}°C · Humidity ${w.humidity}% · Rain ${w.rain||0}mm · Wind ${w.wind}m/s`;
    } else { document.getElementById('weather-strip').textContent='🌦 Weather API not configured'; }
  }).catch(()=>{});
  fetch('/status').then(r=>r.json()).then(s=>{
    const gb=document.getElementById('gemini-badge'),bb=document.getElementById('bot-badge');
    if(s.gemini_ready){gb.textContent='🤖 Gemini ON';gb.className='gbadge on';bb.textContent='ONLINE';bb.className='bbadge on';}
    else{gb.textContent='🤖 AI Offline';gb.className='gbadge off';}
  }).catch(()=>{});
  setInterval(()=>{document.getElementById('clock').textContent=new Date().toLocaleTimeString('en-IN',{hour12:false});},1000);
  setScenario('normal');
};

/* ── sim panel ── */
function toggleSimPanel(){
  const p=document.getElementById('sim-panel');
  p.classList.toggle('expanded');
  updateGridHeight();
}
function updateGridHeight(){
  const p=document.getElementById('sim-panel');
  const topH=document.querySelector('.topbar').offsetHeight||62;
  const simH=p.classList.contains('expanded')?SIM_EXP:SIM_H;
  const grid=document.getElementById('main-grid');
  grid.style.height=`calc(100vh - ${topH}px - ${simH}px)`;
}

/* ── crop / stage ── */
function selectCrop(btn,crop){
  document.querySelectorAll('.ctab').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active'); currentCrop=crop; buildStages(crop);
}
function buildStages(crop){
  const sel=document.getElementById('stage-select'); sel.innerHTML='';
  const stages=cropStages[crop]?.stages||[];
  stages.forEach(s=>{const o=document.createElement('option');o.value=s;o.textContent=s.replace(/_/g,' ').replace(/\b\w/g,x=>x.toUpperCase());sel.appendChild(o);});
  runPredict();
}

/* ── scenarios ── */
function setScenario(s){
  const v=SCENARIOS[s];
  setHid('s-moisture',v.moisture); setHid('s-tds',v.tds); setHid('s-airtemp',v.airtemp);
  setHid('s-soiltemp',v.soiltemp); setHid('s-humidity',v.humidity);
  setHid('s-mq135-v',v.mq135); setHid('s-mq4-v',v.mq4); setHid('s-mq7-v',v.mq7); setHid('s-mq2-v',v.mq2);
  // sync sliders
  setSl('sl-moisture',v.moisture,'disp-moisture','%');
  setSl('sl-tds',v.tds,'disp-tds',' ppm');
  setSl('sl-airtemp',v.airtemp,'disp-airtemp','°C');
  setSl('sl-humidity',v.humidity,'disp-humidity','%');
  setSl('sl-soiltemp',v.soiltemp,'disp-soiltemp','°C');
  setSl('sl-mq135',v.mq135,'disp-mq135',' ppm');
  setSl('sl-mq4',v.mq4,'disp-mq4',' ppm');
  setSl('sl-mq7',v.mq7,'disp-mq7',' ppm');
  setSl('sl-mq2',v.mq2,'disp-mq2',' ppm');
  runPredict();
}
function setSl(slId,val,dispId,unit){
  const sl=document.getElementById(slId); if(sl)sl.value=val;
  const dp=document.getElementById(dispId); if(dp)dp.textContent=val+unit;
}
function setHid(id,val){const el=document.getElementById(id);if(el)el.value=val;}

/* ── slider change ── */
function sliderChange(field,val,unit){
  const map={moisture:'s-moisture',tds:'s-tds',airtemp:'s-airtemp',soiltemp:'s-soiltemp',humidity:'s-humidity',mq135:'s-mq135-v',mq4:'s-mq4-v',mq7:'s-mq7-v',mq2:'s-mq2-v'};
  setHid(map[field],val);
  const dp=document.getElementById('disp-'+field); if(dp)dp.textContent=parseFloat(val).toFixed(field==='airtemp'||field==='soiltemp'?1:0)+unit;
  runPredict();
}

/* ── get sensors ── */
function getSensors(){
  return{soil_moisture:+hv('s-moisture'),tds_ppm:+hv('s-tds'),air_temp_c:+hv('s-airtemp'),soil_temp_c:+hv('s-soiltemp'),humidity_pct:+hv('s-humidity'),mq135_ammonia:+hv('s-mq135-v'),mq4_methane:+hv('s-mq4-v'),mq7_co:+hv('s-mq7-v'),mq2_smoke:+hv('s-mq2-v')};
}
function hv(id){const e=document.getElementById(id);return e?e.value:0;}

/* ── predict ── */
function runPredict(){
  const stage=document.getElementById('stage-select').value; if(!stage)return;
  fetch('/predict',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({crop:currentCrop,stage,sensors:getSensors()})
  }).then(r=>r.json()).then(res=>updateUI(res));
}

/* ── update UI ── */
function updateUI(r){
  const sd=getSensors();
  setBar('moisture',sd.soil_moisture,100,`${Math.round(sd.soil_moisture)}%`,sd.soil_moisture<50?'⚠️ Low — irrigate soon':sd.soil_moisture>85?'💦 Oversaturated':'✅ Optimal range');
  setBar('tds',Math.min(sd.tds_ppm,2000)/20,100,`${Math.round(sd.tds_ppm)} ppm`,r.tds_safe?'✅ Water quality safe':'⚠️ High salinity — risky');
  setBar('airtemp',sd.air_temp_c,50,`${sd.air_temp_c.toFixed(1)}°C`,sd.air_temp_c>38?'🔥 Heat stress risk':sd.air_temp_c<15?'❄️ Too cold':'✅ Normal');
  setBar('hum',sd.humidity_pct,100,`${Math.round(sd.humidity_pct)}%`,sd.humidity_pct>85?'💦 Fungal risk':sd.humidity_pct<35?'🏜 Too dry':'✅ Good');
  setBar('soiltemp',sd.soil_temp_c,50,`${sd.soil_temp_c.toFixed(1)}°C`,sd.soil_temp_c>38?'🔥 Overheating':'✅ Normal');
  setGas('mq135',sd.mq135_ammonia,sd.mq135_ammonia>200?'danger':sd.mq135_ammonia>100?'warning':'ok',sd.mq135_ammonia>200?'🚨 DANGER':sd.mq135_ammonia>100?'⚠️ Warning':'✅ Clear');
  setGas('mq4',sd.mq4_methane,sd.mq4_methane>1000?'danger':sd.mq4_methane>500?'warning':'ok',sd.mq4_methane>1000?'🚨 DANGER':'✅ Clear');
  setGas('mq7',sd.mq7_co,sd.mq7_co>100?'danger':sd.mq7_co>35?'warning':'ok',sd.mq7_co>100?'🚨 DANGER':sd.mq7_co>35?'⚠️ Warning':'✅ Clear');
  setGas('mq2',sd.mq2_smoke,sd.mq2_smoke>400?'danger':sd.mq2_smoke>200?'warning':'ok',sd.mq2_smoke>400?'🚨 DANGER':'✅ Clear');
  // ring
  const circ=327,fill=document.getElementById('r-fill');
  fill.style.strokeDashoffset=circ-(circ*r.health_score/100);
  fill.style.stroke=r.health_score>=75?'#66bb6a':r.health_score>=50?'#ffa726':r.health_score>=25?'#ef5350':'#b71c1c';
  document.getElementById('hs-num').textContent=r.health_score;
  document.getElementById('hs-label').textContent=r.health_status;
  document.getElementById('hs-label').style.color=fill.style.stroke;
  document.getElementById('hs-conf').textContent=`Confidence ${r.confidence_pct}%`;
  updateFarmerState(r);
  const adv={GOOD:`✅ Good health. Moisture ${Math.round(sd.soil_moisture)}%, TDS ${r.tds_safe?'safe':'high'}. ${r.irrigate_now?'Irrigation recommended.':'No irrigation needed.'}`,MODERATE:`⚠️ Moderate. Monitor closely. ${r.irrigate_now?'Irrigate soon.':'Hold irrigation.'} Check nutrients.`,POOR:`🔴 Poor health — action needed. ${r.gas_alert?'Gas detected — ventilate. ':''}${!r.tds_safe?'Switch to fresh water. ':''}`,CRITICAL:`🚨 CRITICAL! ${r.pump_locked?'Pump locked. ':''}${r.gas_alert?'Toxic gas! ':''}Call agricultural expert.`};
  document.getElementById('ai-advice').textContent=adv[r.health_status]||'Analyzing...';
  setChip('dc-irrigate','dv-irrigate',r.irrigate_now,r.irrigate_now?'NOW ✅':'NO',r.irrigate_now?'yes':'');
  setChip('dc-pump','dv-pump',r.pump_locked,r.pump_locked?'LOCKED 🔒':'OK ✅',r.pump_locked?'no':'yes');
  setChip('dc-gas','dv-gas',r.gas_alert,r.gas_alert?'DANGER 🚨':'CLEAR ✅',r.gas_alert?'no':'');
  setChip('dc-stage','dv-stage',r.is_critical_stage,r.is_critical_stage?'CRITICAL ⭐':'Normal',r.is_critical_stage?'warn':'');
  document.getElementById('wa-text').textContent=`${currentCrop} ${document.getElementById('stage-select').value} — Health: ${r.health_status} (${r.health_score}/100) | Pump: ${r.pump_locked?'LOCKED':'OK'} | Gas: ${r.gas_alert?'DANGER':'CLEAR'}`;
  const tm={rising:'📈 Rising ↑',falling:'📉 Falling ↓',stable:'→ Stable'};
  document.getElementById('trend-val').textContent=tm[r.trend_moisture]||'→';
  document.getElementById('tds-safe-val').textContent=r.tds_safe?'✅ Safe':'⚠️ High';
  document.getElementById('tds-safe-val').style.color=r.tds_safe?'#66bb6a':'#ffa726';
  document.getElementById('aqi-val').textContent=`${r.field_aqi} — ${r.field_aqi_label}`;
  document.getElementById('aqi-val').style.color=r.field_aqi>=80?'#66bb6a':r.field_aqi>=50?'#ffa726':'#ef5350';
}
function setBar(id,pct,max,valTxt,subTxt){
  const b=document.getElementById('b-'+id); if(b)b.style.width=Math.min(100,(pct/max)*100)+'%';
  const v=document.getElementById('v-'+id); if(v)v.textContent=valTxt;
  const s=document.getElementById('s-'+id+'-txt'); if(s)s.textContent=subTxt;
}
function setGas(id,val,level,statusTxt){
  const c=document.getElementById('gc-'+id); if(c){c.className='gas-card';if(level!=='ok')c.classList.add(level);}
  const v=document.getElementById('v-'+id); if(v)v.textContent=val.toFixed(0)+' ppm';
  const s=document.getElementById('s-'+id); if(s){s.textContent=statusTxt;s.className='gc-status'+(level==='danger'?' danger':'');}
}
function setChip(chipId,valId,active,txt,cls){
  const c=document.getElementById(chipId); if(c)c.className='dchip'+(cls?' '+cls:'');
  const v=document.getElementById(valId); if(v)v.textContent=txt;
}


/* ── Farmer state switcher ── */
function updateFarmerState(r) {
  let state = 'good';
  if (r.gas_alert)                      state = 'gas';
  else if (r.health_status==='CRITICAL') state = 'critical';
  else if (r.health_status==='POOR')     state = 'poor';
  else if (r.health_status==='MODERATE') state = 'moderate';

  // toggle SVG groups
  document.querySelectorAll('.fstate').forEach(g => g.classList.remove('active'));
  const el = document.getElementById('fs-'+state);
  if (el) el.classList.add('active');

  // update SVG class for glow+animation
  const svg = document.getElementById('farmer-main');
  if (svg) svg.className = `farmer-svg fs-${state}`;

  // update badge
  const badge = document.getElementById('farmer-badge');
  const labels = {
    good:     ['🌱 HEALTHY',   'good'],
    moderate: ['🤔 CONCERNED', 'moderate'],
    poor:     ['😰 STRESSED',  'poor'],
    critical: ['🚨 CRITICAL',  'critical'],
    gas:      ['😷 GAS DANGER','gas']
  };
  if (badge && labels[state]) {
    badge.textContent  = labels[state][0];
    badge.className    = `farmer-state-badge ${labels[state][1]}`;
  }
}




/* ── chat ── */
function qa(msg){document.getElementById('chat-in').value=msg;sendChat();}
function sendChat(){
  const inp=document.getElementById('chat-in'),msg=inp.value.trim(); if(!msg)return;
  appendMsg('user',msg,''); inp.value='';
  const stage=document.getElementById('stage-select').value;
  document.getElementById('typing').classList.remove('hidden');
  fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:msg,crop:currentCrop,stage,sensors:getSensors()})
  }).then(r=>r.json()).then(res=>{document.getElementById('typing').classList.add('hidden');appendMsg('bot',res.reply,res.source);})
  .catch(()=>{document.getElementById('typing').classList.add('hidden');appendMsg('bot','Connection error.','system');});
}
function appendMsg(who,text,source){
  const win=document.getElementById('chat-win'),d=document.createElement('div');
  d.className='msg '+who;
  const tag=source==='gemini'?'<div class="src-tag">✨ Gemini AI</div>':source==='offline'?'<div class="src-tag">🔌 Offline</div>':'';
  d.innerHTML=`<div class="bubble">${text}${tag}</div>`;
  win.appendChild(d); win.scrollTop=win.scrollHeight;
}
