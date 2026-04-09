let currentCrop='rice', cropStages={};
const SCENARIOS = {
  normal:{moist:72,tds:350,air:28,hum:65,soiltemp:24,mq135:50,mq4:200,mq7:10},
  dry:{moist:28,tds:420,air:34,hum:42,soiltemp:31,mq135:60,mq4:220,mq7:15},
  saline:{moist:55,tds:1200,air:30,hum:58,soiltemp:27,mq135:70,mq4:250,mq7:20},
  gas:{moist:68,tds:360,air:29,hum:64,soiltemp:25,mq135:260,mq4:1400,mq7:140},
  heat:{moist:48,tds:500,air:41,hum:30,soiltemp:36,mq135:80,mq4:300,mq7:22},
  critical:{moist:18,tds:1600,air:43,hum:22,soiltemp:39,mq135:320,mq4:1800,mq7:170}
};
function gid(x){return document.getElementById(x)}
function hv(id){return +gid(id).value}
function setBar(id,p){ gid(id).style.width=Math.max(4,Math.min(100,p))+'%'; }
function setText(id,t){ gid(id).textContent=t; }
function clock(){ const d=new Date(); gid('clock').textContent=d.toLocaleTimeString(); }
setInterval(clock,1000); clock();

async function boot(){
  const c = await fetch('/crops').then(r=>r.json()); cropStages = c;
  const tabs = gid('crop-tabs');
  Object.keys(c).forEach((k,i)=>{
    const b=document.createElement('button'); b.textContent='🌾 '+k[0].toUpperCase()+k.slice(1); b.className='crop-btn'+(i===0?' active':'');
    b.onclick=()=>{document.querySelectorAll('.crop-btn').forEach(x=>x.classList.remove('active')); b.classList.add('active'); currentCrop=k; fillStages(); runPredict();};
    tabs.appendChild(b);
  });
  fillStages();
  await loadStatus();
  await loadWeather();
  setScenario('normal');
}
function fillStages(){ const s=gid('stageSel'); s.innerHTML=''; (cropStages[currentCrop]?.stages||['germination']).forEach(v=>{const o=document.createElement('option'); o.value=v; o.textContent=v[0].toUpperCase()+v.slice(1); s.appendChild(o);}); }
function getSensors(){ return {soil_moisture:hv('s-moist-v'),tds_ppm:hv('s-tds-v'),air_temp_c:hv('s-air-v'),humidity_pct:hv('s-hum-v'),soil_temp_c:hv('s-soiltemp-v'),mq135_ammonia:hv('s-mq135-v'),mq4_methane:hv('s-mq4-v'),mq7_co:hv('s-mq7-v')}; }
function setScenario(name){ const v=SCENARIOS[name]; gid('s-moist-v').value=v.moist; gid('s-tds-v').value=v.tds; gid('s-air-v').value=v.air; gid('s-hum-v').value=v.hum; gid('s-soiltemp-v').value=v.soiltemp; gid('s-mq135-v').value=v.mq135; gid('s-mq4-v').value=v.mq4; gid('s-mq7-v').value=v.mq7; renderSensors(v); runPredict(); }
function renderSensors(sd){
  setText('v-moist', sd.moist!==undefined?sd.moist+'%':'—'); setBar('b-moist', sd.moist||0);
  setText('v-tds', sd.tds!==undefined?sd.tds+' ppm':'—'); setBar('b-tds', Math.min(100,(sd.tds||0)/20));
  setText('v-air', sd.air!==undefined?sd.air+'°C':'—'); setBar('b-air', Math.min(100,(sd.air||0)*2));
  setText('v-hum', sd.hum!==undefined?sd.hum+'%':'—'); setBar('b-hum', sd.hum||0);
  setText('v-soiltemp', sd.soiltemp!==undefined?sd.soiltemp+'°C':'—'); setBar('b-soiltemp', Math.min(100,(sd.soiltemp||0)*2));
  setText('v-mq135', sd.mq135!==undefined?sd.mq135+' ppm':'—');
  setText('v-mq4', sd.mq4!==undefined?sd.mq4+' ppm':'—');
  setText('v-mq7', sd.mq7!==undefined?sd.mq7+' ppm':'—');
}
async function runPredict(){
  try{
    const sensors=getSensors();
    renderSensors({moist:sensors.soil_moisture,tds:sensors.tds_ppm,air:sensors.air_temp_c,hum:sensors.humidity_pct,soiltemp:sensors.soil_temp_c,mq135:sensors.mq135_ammonia,mq4:sensors.mq4_methane,mq7:sensors.mq7_co});
    const r = await fetch('/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({crop:currentCrop,stage:gid('stageSel').value,sensors})});
    const d = await r.json();
    if(!r.ok) throw new Error(d.error||'Predict failed');
    gid('scoreText').textContent = d.health_score;
    gid('healthTag').textContent = d.health_status==='GOOD'?'🌱 HEALTHY':d.health_status;
    gid('adviceText').textContent = d.health_status==='GOOD'?'Crop looks healthy. Keep monitoring.':d.health_status==='MODERATE'?'Crop needs attention. Check moisture.':d.health_status==='POOR'?'Crop is struggling. Take action soon.':'Urgent! Crop is in critical condition.';
    gid('d-irrigate').textContent = d.irrigate_now?'YES':'NO';
    gid('d-pump').textContent = d.pump_locked?'LOCKED':(d.pump_on?'ON':'OFF');
    gid('d-gas').textContent = d.gas_alert?'ALERT':'CLEAR';
    gid('d-stage').textContent = gid('stageSel').value;
    gid('t-moist').textContent = d.trend_moisture;
    gid('t-tds').textContent = d.tds_safe?'Safe':'High';
    gid('t-aqi').textContent = d.field_aqi_label;
  }catch(e){ console.error(e); gid('adviceText').textContent='Prediction error.'; }
}
async function loadWeather(){ try{ const d=await fetch('/weather').then(r=>r.json()); gid('weatherPill').textContent='☁️ '+d.temp+'°C'; gid('weatherStrip').textContent=`🌥 ${d.city}: ${d.temp}°C · Humidity ${d.humidity}% · Rain ${d.rain}mm · Wind ${d.wind}m/s`; }catch{} }
async function loadStatus(){ try{ const d=await fetch('/status').then(r=>r.json()); gid('aiBadge').textContent=d.gemini_ready?'🤖 Gemini ON':'🤖 AI'; gid('chatStatus').textContent=d.gemini_ready?'ONLINE':'OFFLINE'; }catch{} }
function addMsg(cls,txt){ const box=gid('chatBox'); const div=document.createElement('div'); div.className=cls; div.textContent=txt; box.appendChild(div); box.scrollTop=box.scrollHeight; }
function quickAsk(q){ gid('chatInput').value=q; sendChat(); }
async function sendChat(){ const msg=gid('chatInput').value.trim(); if(!msg) return; addMsg('user',msg); gid('chatInput').value=''; try{ const sensors=getSensors(); const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg,crop:currentCrop,stage:gid('stageSel').value,sensors})}); const d=await r.json(); addMsg('bot',d.reply||'No reply'); }catch(e){ addMsg('bot','Connection error.'); } }
gid('stageSel')?.addEventListener('change', runPredict);
window.addEventListener('load', boot);
