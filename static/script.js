let currentLang="en",cropStages={},lastFarmerState=null;
const SCENARIOS={
  normal:  {moisture:72,tds:350,airtemp:27,soiltemp:23,humidity:65,mq135:50, mq4:200, mq7:10,mq2:50},
  dry:     {moisture:32,tds:350,airtemp:36,soiltemp:31,humidity:40,mq135:70, mq4:200, mq7:10,mq2:50},
  saline:  {moisture:72,tds:1400,airtemp:28,soiltemp:24,humidity:60,mq135:50,mq4:200, mq7:10,mq2:50},
  gas:     {moisture:68,tds:350,airtemp:28,soiltemp:24,humidity:62,mq135:290,mq4:1300,mq7:90,mq2:550},
  heat:    {moisture:60,tds:300,airtemp:43,soiltemp:39,humidity:28,mq135:50, mq4:200, mq7:10,mq2:50},
  critical:{moisture:28,tds:1600,airtemp:44,soiltemp:40,humidity:20,mq135:310,mq4:1400,mq7:110,mq2:600},
};
const FARMER={
  CELEBRATING:{emoji:"🧑‍🌾",action:"🎉",mood:"😊 Celebrating",cls:"good",en:"Perfect! All systems green!",ta:"வயல் அருமை!"},
  HAPPY:      {emoji:"🧑‍🌾",action:"✅",mood:"😊 Happy",       cls:"good",en:"Crop is healthy. All clear!",ta:"பயிர் ஆரோக்கியமாக உள்ளது!"},
  WATERING:   {emoji:"🧑‍🌾",action:"💧",mood:"💧 Irrigating",  cls:"good",en:"Irrigation running! Pump ON.",ta:"நீர்ப்பாசனம் நடக்கிறது!"},
  MONITORING: {emoji:"🧑‍🌾",action:"🔍",mood:"🤔 Monitoring",  cls:"warn",en:"Watching closely. Some issues.",ta:"கவனமாக கண்காணிக்கிறேன்."},
  WORRIED:    {emoji:"🧑‍🌾",action:"😟",mood:"😟 Worried",     cls:"warn",en:"Crop is stressed. Take action!",ta:"பயிர் அழுத்தத்தில் உள்ளது!"},
  PUMP_LOCKED:{emoji:"🧑‍🌾",action:"🔒",mood:"⚠️ Pump Locked", cls:"warn",en:"Pump locked! Water too salty!",ta:"பம்ப் பூட்டப்பட்டுள்ளது!"},
  GAS_DANGER: {emoji:"🧑‍🌾",action:"🚨",mood:"🚨 GAS DANGER",  cls:"danger",en:"DANGER! Toxic gas detected!",ta:"ஆபத்து! நச்சு வாயு கண்டறியப்பட்டது!"},
  HEAT_STRESS:{emoji:"🧑‍🌾",action:"🌡️",mood:"🥵 Heat Stress", cls:"warn",en:"Too hot! Crop is wilting!",ta:"மிகவும் சூடாக உள்ளது!"},
  CRITICAL:   {emoji:"🧑‍🌾",action:"💀",mood:"😱 CRITICAL",    cls:"danger",en:"CRITICAL! Act immediately!",ta:"மிகவும் ஆபத்தான நிலை!"},
};

function updateChatbotBadge(isOnline){
  const cb=document.getElementById("chat-source-badge");
  if(!cb)return;
  if(isOnline){cb.textContent="⚡ Gemini AI";cb.className="source-badge gemini";}
  else{cb.textContent="📴 Offline";cb.className="source-badge offline";}
}

window.onload=()=>{
  fetch("/crops").then(r=>r.json()).then(d=>{cropStages=d;onCropChange();});
  setInterval(()=>{document.getElementById("clock").textContent=new Date().toLocaleTimeString("en-IN",{hour12:false});},1000);
  applyScenario();setTimeout(runPredict,600);
  fetch("/status").then(r=>r.json()).then(s=>{
    const b=document.getElementById("gemini-badge");
    if(s.gemini_ready){b.textContent="⚡ Gemini AI";b.style.background="#1565c0";updateChatbotBadge(true);}
    else{b.textContent="📴 Offline Mode";b.style.background="#546e7a";updateChatbotBadge(false);}
  }).catch(()=>{updateChatbotBadge(false);});
};

function selectCrop(btn, cropValue){
  document.querySelectorAll(".crop-btn").forEach(b=>b.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById("crop-select").value=cropValue;
  onCropChange();
}

function onCropChange(){
  const c=document.getElementById("crop-select").value;
  const sel=document.getElementById("stage-select");
  sel.innerHTML="";
  (cropStages[c]?.stages||[]).forEach(s=>{
    const o=document.createElement("option");
    o.value=s;o.textContent=s.replace(/_/g," ").replace(/\b\w/g,x=>x.toUpperCase());
    sel.appendChild(o);
  });
  document.getElementById("tds-max-label").textContent=`Safe: ${cropStages[c]?.tds_max||"—"} ppm`;
  runPredict();
}

function syncVal(k){
  const M={moisture:{i:"s-moisture",o:"val-moisture",f:v=>`${v}%`},tds:{i:"s-tds",o:"val-tds",f:v=>`${v} ppm`},
    airtemp:{i:"s-airtemp",o:"val-airtemp",f:v=>`${v}°C`},soiltemp:{i:"s-soiltemp",o:"val-soiltemp",f:v=>`${v}°C`},
    humidity:{i:"s-humidity",o:"val-humidity",f:v=>`${v}%`},mq135:{i:"s-mq135",o:"val-mq135",f:v=>v},
    mq4:{i:"s-mq4",o:"val-mq4",f:v=>v},mq7:{i:"s-mq7",o:"val-mq7",f:v=>v},mq2:{i:"s-mq2",o:"val-mq2",f:v=>v}};
  const m=M[k];if(!m)return;
  document.getElementById(m.o).textContent=m.f(document.getElementById(m.i).value);
}

function applyScenario(){
  const s=SCENARIOS[document.getElementById("scenario-select").value];if(!s)return;
  const set=(id,v)=>{document.getElementById(id).value=v;};
  set("s-moisture",s.moisture);syncVal("moisture");
  set("s-tds",s.tds);syncVal("tds");set("s-airtemp",s.airtemp);syncVal("airtemp");
  set("s-soiltemp",s.soiltemp);syncVal("soiltemp");set("s-humidity",s.humidity);syncVal("humidity");
  set("s-mq135",s.mq135);syncVal("mq135");set("s-mq4",s.mq4);syncVal("mq4");
  set("s-mq7",s.mq7);syncVal("mq7");set("s-mq2",s.mq2);syncVal("mq2");
  runPredict();
}

function getS(){return{soil_moisture:+document.getElementById("s-moisture").value,tds_ppm:+document.getElementById("s-tds").value,air_temp_c:+document.getElementById("s-airtemp").value,soil_temp_c:+document.getElementById("s-soiltemp").value,humidity_pct:+document.getElementById("s-humidity").value,mq135_ammonia:+document.getElementById("s-mq135").value,mq4_methane:+document.getElementById("s-mq4").value,mq7_co:+document.getElementById("s-mq7").value,mq2_smoke:+document.getElementById("s-mq2").value};}

function runPredict(){
  const crop=document.getElementById("crop-select").value;
  const stage=document.getElementById("stage-select").value;
  if(!stage)return;
  fetch("/predict",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({crop,stage,sensors:getS()})})
  .then(r=>r.json()).then(res=>updateUI(res,crop,stage,getS()));
}

function updateUI(r,crop,stage,sensors){
  const circ=314,off=circ-(circ*r.health_score/100);
  const ring=document.getElementById("ring-fill");
  ring.style.strokeDashoffset=off;
  ring.style.stroke=r.health_score>=75?"#66bb6a":r.health_score>=50?"#ffa726":r.health_score>=25?"#ef5350":"#b71c1c";
  document.getElementById("health-score-num").textContent=r.health_score;
  const hl=document.getElementById("health-label");
  hl.textContent=r.health_status;hl.className="ring-label status-"+r.health_status.toLowerCase();
  setDec("dc-irrigate-val",r.irrigate_now,"YES","NO");
  setDec("dc-lock-val",r.pump_locked,"LOCKED","NO",true);
  setDec("dc-gas-val",r.gas_alert,"ALERT","CLEAR",true);
  setDec("dc-critical-val",r.is_critical_stage,"YES","NO");
  const ps=document.getElementById("pump-status");
  if(r.pump_locked){ps.textContent="LOCKED";ps.className="card-value status-lock";}
  else if(r.pump_on){ps.textContent="ON";ps.className="card-value status-on";}
  else{ps.textContent="OFF";ps.className="card-value status-off";}
  const ts=document.getElementById("tds-status");
  ts.textContent=r.tds_safe?"SAFE":"HIGH ⚠️";ts.className="card-value "+(r.tds_safe?"status-ok":"status-lock");
  const gs=document.getElementById("gas-status");
  gs.textContent=r.gas_alert?"DANGER 🚨":"CLEAR";gs.className="card-value "+(r.gas_alert?"status-danger":"status-ok");
  document.getElementById("stage-status").textContent=r.is_critical_stage?"⭐ CRITICAL":"Normal";
  document.getElementById("aqi-score-label").textContent=`${r.field_aqi} — ${r.field_aqi_label}`;
  document.getElementById("aqi-bar-fill").style.width=r.field_aqi+"%";
  document.getElementById("moisture-min-label").textContent=`Min:${r.moist_min}%`;
  document.getElementById("moisture-opt-label").textContent=`Opt:${r.moist_opt}%`;
  document.getElementById("tds-max-label").textContent=`Safe:${r.tds_max}ppm`;
  const cn=crop.charAt(0).toUpperCase()+crop.slice(1);
  const sn=stage.replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase());
  let adv="";
  if(r.health_status==="GOOD") adv=`${cn} at ${sn} is in excellent health. All sensors within safe range. Continue current schedule.`;
  else if(r.health_status==="MODERATE") adv=`${cn} shows moderate stress at ${sn}. ${!r.tds_safe?"TDS elevated — avoid current water source.":"Check soil moisture and irrigation schedule."}`;
  else if(r.health_status==="POOR") adv=`${cn} is under stress at ${sn}. ${r.pump_locked?"Pump locked — unsafe water.":"Immediate irrigation needed."} ${r.gas_alert?"Gas levels dangerous.":""}`;
  else adv=`CRITICAL: ${cn.toUpperCase()} at ${sn} is in danger. Multiple parameters out of range. Take immediate action now.`;
  document.getElementById("ai-advice").textContent=adv;
  const ti=document.getElementById("trend-indicator");
  ti.textContent=r.trend_moisture==="falling"?"↘ Falling":r.trend_moisture==="rising"?"↗ Rising":"⟶ Stable";
  ti.className="trend-"+(r.trend_moisture||"stable");
  let wa;
  if(r.pump_locked) wa=`⚠️ PUMP LOCKED. TDS: ${Math.round(sensors.tds_ppm)}ppm — unsafe for ${crop}. Use alternate water source!`;
  else if(r.gas_alert) wa="🚨 GAS DANGER near field. Check CO/Methane immediately. Evacuate if needed.";
  else if(r.pump_on) wa=`✅ Irrigation started. Moisture was ${Math.round(sensors.soil_moisture)}% — below threshold. Pump ON.`;
  else if(r.health_status==="CRITICAL") wa=`🔴 CRITICAL alert for ${crop} crop. Multiple sensors out of range. Inspect now.`;
  else wa=`🌅 Farm update: ${crop} health is ${r.health_status} (${r.health_score}/100). All clear.`;
  document.getElementById("wa-message").textContent=wa;
  const ban=document.getElementById("alert-banner");
  if(r.gas_alert||r.pump_locked||r.health_status==="CRITICAL"){
    ban.classList.remove("hidden");
    ban.textContent=r.gas_alert?"🚨 GAS ALERT":r.pump_locked?"⚠️ PUMP LOCKED":"🔴 CRITICAL";
  }else ban.classList.add("hidden");
  updateFarmer(r,sensors);applyLang();
}

function updateFarmer(r,sensors){
  let state;
  if(r.gas_alert) state="GAS_DANGER";
  else if(r.health_status==="CRITICAL") state="CRITICAL";
  else if(r.pump_locked) state="PUMP_LOCKED";
  else if(sensors.air_temp_c>38) state="HEAT_STRESS";
  else if(r.health_status==="POOR") state="WORRIED";
  else if(r.pump_on) state="WATERING";
  else if(r.health_status==="MODERATE") state="MONITORING";
  else if(r.health_score>=85) state="CELEBRATING";
  else state="HAPPY";
  const fs=FARMER[state];
  const ce=document.getElementById("farmer-char");
  document.getElementById("farmer-action").textContent=fs.action;
  document.getElementById("farmer-bubble").textContent=currentLang==="ta"?fs.ta:fs.en;
  document.getElementById("farmer-bubble").className="farmer-bubble "+fs.cls;
  document.getElementById("farmer-mood-label").textContent=fs.mood;
  if(state!==lastFarmerState){
    ce.className="farmer-char";void ce.offsetWidth;
    if(state==="GAS_DANGER"||state==="CRITICAL") ce.className="farmer-char pulse-anim";
    else if(state==="PUMP_LOCKED"||state==="WORRIED") ce.className="farmer-char shake";
    else if(state==="CELEBRATING"||state==="WATERING") ce.className="farmer-char bounce";
    else ce.className="farmer-char";
    lastFarmerState=state;
  }
  ce.textContent=fs.emoji;
}

function setDec(id,val,yes,no,isDanger=false){
  const el=document.getElementById(id);
  el.textContent=val?yes:no;
  el.className=val?(isDanger?"dc-val dc-warn":"dc-val dc-yes"):"dc-val dc-no";
}

function sendChat(){
  const inp=document.getElementById("chat-input");
  const msg=inp.value.trim();if(!msg)return;
  appendChat(msg,"user");inp.value="";
  const tip=document.getElementById("typing-indicator");
  tip.classList.remove("hidden");
  const crop=document.getElementById("crop-select").value;
  const stage=document.getElementById("stage-select").value;
  fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({message:msg,crop,stage,sensors:getS(),lang:currentLang})})
  .then(r=>r.json()).then(res=>{
    tip.classList.add("hidden");
    appendChat(res.reply,"bot");
    updateChatbotBadge(res.source==="gemini");
  }).catch(()=>{tip.classList.add("hidden");appendChat("Connection error. Make sure the app is running.","bot");});
}

function quickAsk(q){document.getElementById("chat-input").value=q;sendChat();}

function appendChat(msg,sender){
  const win=document.getElementById("chat-window");
  const div=document.createElement("div");
  div.className="chat-msg "+(sender==="bot"?"bot-msg":"user-msg");
  div.innerHTML=sender==="bot"?`<span class="bot-icon">🌿</span><span class="msg-text">${msg}</span>`:`<span class="msg-text">${msg}</span>`;
  win.appendChild(div);win.scrollTop=win.scrollHeight;
}

function toggleLang(){
  currentLang=currentLang==="en"?"ta":"en";
  document.getElementById("lang-toggle").textContent=currentLang==="en"?"🌐 தமிழ்":"🌐 English";
  applyLang();runPredict();
}

function applyLang(){
  document.querySelectorAll("[data-en]").forEach(el=>{
    el.textContent=currentLang==="ta"?(el.getAttribute("data-ta")||el.getAttribute("data-en")):el.getAttribute("data-en");
  });
  document.getElementById("chat-input").placeholder=currentLang==="ta"?"உங்கள் கேள்வியை தமிழில் கேளுங்கள்...":"Ask anything about your crop...";
  if(lastFarmerState){
    const fs=FARMER[lastFarmerState];
    document.getElementById("farmer-bubble").textContent=currentLang==="ta"?fs.ta:fs.en;
  }
}
