/* =========================
   CREATE CYCLONE — FULL JS
   ========================= */

/* ---------- tab switch ---------- */
const panes = {
  info: document.getElementById('tab-info'),
  metrics: document.getElementById('tab-metrics'),
  docs: document.getElementById('tab-docs'),
  performance: document.getElementById('tab-performance'),
  charts: document.getElementById('tab-charts'),
};
function showTab(name){
  document.querySelectorAll('.tab').forEach(b=>{
    const on = b.dataset.tab === name;
    b.classList.toggle('on', on);
    b.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  Object.entries(panes).forEach(([k,el])=> el.classList.toggle('on', k===name));
  onTabChange();
}
document.querySelectorAll('.tab').forEach(b=>{
  b.addEventListener('click', ()=> showTab(b.dataset.tab));
});
document.querySelectorAll('.btn.next').forEach(b=>{
  b.addEventListener('click', ()=> showTab(b.dataset.next));
});

/* ---------- card / overlay refs ---------- */
const cardFrame = document.querySelector('.card-frame');
const cardBg    = document.getElementById('cardBg');     // card background image
const olPhoto   = document.getElementById('olPhoto');    // circular photo
const olName    = document.getElementById('olName');
const olFlag    = document.getElementById('olFlag');
const briefAge  = document.getElementById('briefAge');
const briefHt   = document.getElementById('briefHt');
const briefClass= document.getElementById('briefClass');

/* Keep card background on the front/logo */
function onTabChange(){
  if (!cardBg) return;
  cardBg.dataset.front = cardBg.dataset.front || '/static/images/cyclone_card_front_logo.png';
  cardBg.dataset.back  = cardBg.dataset.back  || '/static/images/cyclone_card_back.png';
  cardBg.src = cardBg.dataset.front;
}
onTabChange();

/* ---------- form refs ---------- */
const iName        = document.getElementById('name');
const iCountry     = document.getElementById('country');
const iDob         = document.getElementById('dob');
const iWeight      = document.getElementById('weight');
const iHrMax       = document.getElementById('hrmax');
const iWeightClass = document.getElementById('weightClass');
const iSexM        = document.getElementById('sexM');
const iSexF        = document.getElementById('sexF');

const iHeight      = document.getElementById('height');
const iArmSpan     = document.getElementById('armspan');
const iReach       = document.getElementById('reach');
const iHaveBF      = document.getElementById('haveBodyFat');
const iBF          = document.getElementById('bodyFat');
const iBFAuto      = document.getElementById('bodyFatAuto');
const iBFFinal     = document.getElementById('bodyFatFinal');
const iNeck        = document.getElementById('neck');
const iWaist       = document.getElementById('waist');
const iHip         = document.getElementById('hip');
const hipRow       = document.getElementById('hipRow');

const iPhoto       = document.getElementById('photo');
const iRemoveBg    = document.getElementById('removeBg');

const iPower       = document.getElementById('power');
const iEndurance   = document.getElementById('endurance');
const iStance      = document.getElementById('stance');

const iPerfUpload  = document.getElementById('perfUpload');

const btnCreate    = document.getElementById('createBtn');
const btnView      = document.getElementById('viewBtn');

/* ---------- helpers ---------- */
function parseDMY(s){
  if(!s) return null;
  const m = s.trim().match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})$/);
  if(!m) return null;
  const d = new Date(+m[3], +m[2]-1, +m[1]);
  return isNaN(d) ? null : d;
}
function ageFromDOB(dob){
  if(!dob) return null;
  const now = new Date();
  let a = now.getFullYear() - dob.getFullYear();
  const md = (now.getMonth() - dob.getMonth()) || (now.getDate() - dob.getDate());
  if (md < 0) a -= 1;
  return a;
}
function hrMaxFromAge(age){
  if(age==null) return '';
  // Tanaka formula: HRmax = 208 − 0.7 × age
  return Math.round(208 - 0.7*age);
}

function kgClassBands(){
  return [
    [45, 'Mini Fly'], [48,'Light Fly'], [51,'Fly'], [54,'Bantam'],
    [57,'Feather'], [60,'Light'], [63.5,'Light Welter'],
    [67,'Welter'], [71,'Light Middle'], [75,'Middle'],
    [81,'Light Heavy'], [86,'Cruiser'], [91,'Heavy'], [999,'Super Heavy']
  ];
}
function classFromKg(kg){
  if (!isFinite(kg)||kg<=0) return {name:'—', low:null, high:null};
  const bands = kgClassBands();
  let prev = 0;
  for (const [cap,name] of bands){
    if (kg <= cap) return { name, low:prev, high:cap };
    prev = cap;
  }
  return {name:'—', low:null, high:null};
}
function formatRange(lo, hi){ if (lo==null||hi==null) return '—'; return `${lo}–${hi} kg`; }
function canon(s){ return (s||'').trim().toLowerCase().replace(/\s+/g,'-'); }

/* Country flag: accept ISO code or name; prefer option value if it looks like a code */
function updateFlag(){
  let val = (iCountry?.value || '').trim();
  if (!val){ olFlag.style.display='none'; return; }
  let codeGuess = val;
  // If not short code, try data-flag on the option, else slug of text
  if (val.length > 3){
    const opt = iCountry.selectedOptions?.[0];
    codeGuess = (opt?.dataset.flag) || canon(opt?.value || opt?.text || val);
  }
  olFlag.src = `/static/flags/${codeGuess}.svg`;
  olFlag.onerror = ()=> { olFlag.style.display='none'; };
  olFlag.style.display='block';
}

/* ---------- overlay updaters ---------- */
function updateName(){ olName.textContent = iName.value.trim() || '—'; }
function updateBrief(){
  // age
  const age = ageFromDOB(parseDMY(iDob.value));
  briefAge.textContent = (age!=null ? age : '--');
  // height
  const h = +iHeight.value || null;
  briefHt.textContent = h ? `${h.toFixed(0)} cm` : '--';
  // class
  const kg = +iWeight.value || 0;
  const k = classFromKg(kg);
  briefClass.textContent = k.name !== '—' ? `${k.name} (${formatRange(k.low,k.high)})` : '--';
}
function updateHrMax(){
  const a = ageFromDOB(parseDMY(iDob.value));
  iHrMax.value = hrMaxFromAge(a);
}
function updateWeightClass(){
  const kg = +iWeight.value || 0;
  const k = classFromKg(kg);
  iWeightClass.value = (k.name==='—') ? '' : `${k.name} (${formatRange(k.low,k.high)})`;
  updateBrief();
}
/* Reach: prefer explicit, else armspan, else 1.02×height */
function updateReach(){
  let r = +iReach.value || 0;
  const a = +iArmSpan.value || 0;
  const h = +iHeight.value || 0;
  if(!r){
    if(a) r = a;
    else if(h) r = Math.round(h * 1.02);
    if (r) iReach.value = r;
  }
}

/* ---------- body fat calculation ---------- */
function computeBF(){
  const h = +iHeight.value;
  const neck = +iNeck.value;
  const waist = +iWaist.value;
  const hip = +iHip.value;
  let bf = null;

  const toIn = cm => cm / 2.54;
  if (iSexM?.checked && h && neck && waist){
    const H = toIn(h);
    const N = toIn(neck);
    const W = toIn(waist);
    bf = 86.010 * Math.log10(W - N) - 70.041 * Math.log10(H) + 36.76;
  }else if(iSexF?.checked && h && neck && waist && hip){
    const H = toIn(h);
    const N = toIn(neck);
    const W = toIn(waist);
    const Hp = toIn(hip);
    bf = 163.205 * Math.log10(W + Hp - N) - 97.684 * Math.log10(H) - 78.387;
  }

  if (bf!=null && isFinite(bf)){
    bf = Math.min(75, Math.max(2, bf));
    bf = Math.round(bf * 10) / 10;
  } else {
    bf = null;
  }

  if (!iHaveBF?.checked){
    if(iBFAuto) iBFAuto.value = bf!=null ? bf : '';
    if(iBFFinal) iBFFinal.value = bf!=null ? bf : '';
  }else{
    if(iBFFinal) iBFFinal.value = iBF?.value ? +iBF.value : '';
  }
}

function syncUI(){
  if(hipRow) hipRow.style.display = iSexF?.checked ? 'grid' : 'none';
  if(iHaveBF?.checked){
    if(iBF) iBF.style.display = 'block';
    if(iBFAuto) iBFAuto.style.display = 'none';
  }else{
    if(iBF) iBF.style.display = 'none';
    if(iBFAuto) iBFAuto.style.display = 'block';
  }
}

/* ---------- photo: reveal immediately on upload ---------- */
let preparedPhotoURL = '';  // track last uploaded/preview URL
iPhoto?.addEventListener('change', async () => {
  const f = iPhoto.files && iPhoto.files[0];
  preparedPhotoURL = '';
  if(!f){ return; }

  if (iRemoveBg?.checked){
    try{
      const fd = new FormData();
      fd.append('file', f);
      fd.append('remove_bg', '1');
      const res = await fetch('/api/fighter/photo', { method:'POST', body:fd });
      if(res.ok){
        const {url} = await res.json();
        preparedPhotoURL = url || '';
      }
    }catch(_e){/* fall through to local preview */}
  }
  if(!preparedPhotoURL){
    preparedPhotoURL = URL.createObjectURL(f);
  }
  if(preparedPhotoURL){
    olPhoto.src = preparedPhotoURL;
    olPhoto.classList.add('revealed');
  }
});

/* ---------- wire live updates ---------- */
[
  [iName,       updateName],
  [iDob,        () => { updateHrMax(); updateBrief(); }],
  [iWeight,     updateWeightClass],
  [iHeight,     updateBrief],
  [iCountry,    updateFlag],
  [iArmSpan,    updateReach],
  [iReach,      updateReach],
].forEach(([el, fn])=>{
  if (!el) return;
  el.addEventListener('input', fn);
  el.addEventListener('change', fn);
});

[
  iHeight, iNeck, iWaist, iHip, iSexM, iSexF, iHaveBF, iBF
].forEach(el => {
  if(!el) return;
  el.addEventListener('input', ()=> { computeBF(); syncUI(); });
  el.addEventListener('change', ()=> { computeBF(); syncUI(); });
});

/* initial paint */
updateName(); updateFlag(); updateHrMax(); updateWeightClass(); updateReach(); updateBrief(); computeBF(); syncUI();

/* ---------- Performance file parsing & metrics ---------- */
function parseHeatrickCsv(text){
  if(!text) return [];
  const lines = text.trim().split(/\r?\n/).filter(l=>l.trim());
  if(!lines.length) return [];
  const headers = lines[0].split(',').map(h=>h.trim());
  return lines.slice(1).map(line=>{
    const cols = line.split(',');
    const obj = {};
    headers.forEach((h,i)=>{ obj[h] = (cols[i]||'').trim(); });
    return obj;
  });
}
function computeMetricsFromHeatrick(rows){
  if(!Array.isArray(rows)) return {};
  const canonName = canon(iName?.value || '');
  let row = rows.find(r=> canon(r['Athlete']||r['Name']||'')===canonName);
  if(!row && rows.length) row = rows[0];
  const num = v=>{ const n = parseFloat(v); return isFinite(n)? n : null; };
  const apr = {
    aerobic_wkg: num(row?.['MAP W/kg'] || row?.['MAP w/kg'] || row?.['Max Aerobic Power'] || row?.['MAP']),
    anaerobic_wkg: num(row?.['MAnP W/kg'] || row?.['MAnP w/kg'] || row?.['Max Anaerobic Power'] || row?.['MAnP'])
  };
  apr.reserve_wkg = (apr.anaerobic_wkg!=null && apr.aerobic_wkg!=null) ? apr.anaerobic_wkg - apr.aerobic_wkg : null;
  const radar = {
    Strength: num(row?.['Strength Score'] || row?.['Strength']),
    Power: num(row?.['Power Score'] || row?.['Power']),
    Endurance: num(row?.['Endurance Score'] || row?.['Endurance']),
    Mobility: num(row?.['Mobility Score'] || row?.['Mobility']),
    BodyComp: num(row?.['Body Comp Score'] || row?.['BodyComp Score'] || row?.['BodyComp'] || row?.['Body Comp'])
  };
  return {apr, radar, raw: row||{}};
}
function updatePerfStatsGrid(metrics){
  const grid = document.getElementById('perfStatsGrid');
  if(!grid) return;
  const set = (key,val)=>{
    const el = grid.querySelector(`[data-metric="${key}"]`) || document.getElementById(key);
    if(el) el.textContent = (val!=null && val!=='' ? val : '--');
  };
  if(metrics?.apr){
    set('aerobic_wkg', metrics.apr.aerobic_wkg?.toFixed?.(2));
    set('anaerobic_wkg', metrics.apr.anaerobic_wkg?.toFixed?.(2));
    set('reserve_wkg', metrics.apr.reserve_wkg?.toFixed?.(2));
  }
  if(metrics?.radar){
    Object.entries(metrics.radar).forEach(([k,v])=> set(canon(k), v));
  }
}
function updateCardStats(metrics){
  if(!metrics) return;
  const set = (id,val)=>{
    const el = document.getElementById(id);
    if(el) el.textContent = (val!=null && val!=='' ? val : '--');
  };
  if(metrics.apr){
    set('cardAprAer', metrics.apr.aerobic_wkg?.toFixed?.(2));
    set('cardAprAna', metrics.apr.anaerobic_wkg?.toFixed?.(2));
    set('cardAprRes', metrics.apr.reserve_wkg?.toFixed?.(2));
  }
}

/* ---------- Heavy Hitters: safe hooks (Chart via CDN in HTML) ---------- */
let aprChart, radarChart;
function ensureCharts(){ return !!window.Chart; }
function renderAprChart(aerobic_wkg, anaerobic_wkg){
  if(!ensureCharts()) return;
  const ctx = document.getElementById('aprChart')?.getContext('2d');
  if(!ctx) return;
  if (aprChart) aprChart.destroy();
  aprChart = new Chart(ctx, {
    type:'bar',
    data:{
      labels:['Max Aerobic Power','Max Anaerobic Power'],
      datasets:[{
        label:'Watts/kg',
        data:[aerobic_wkg||0, anaerobic_wkg||0],
        backgroundColor:['rgba(0,255,255,.25)','rgba(255,122,0,.25)'],
        borderColor:['#00ffff','#ff7a00'],
        borderWidth:2
      }]
    },
    options:{
      plugins:{ legend:{ labels:{ color:'#ffd900', font:{family:'Orbitron'} } } },
      scales:{
        x:{ ticks:{ color:'#00ffff', font:{family:'Orbitron'} }, grid:{ color:'rgba(0,255,255,.2)' } },
        y:{ ticks:{ color:'#ffd900', font:{family:'Orbitron'} }, grid:{ color:'rgba(0,255,255,.2)' } }
      }
    }
  });
}
function renderRadarChart(scores){
  if(!ensureCharts()) return;
  const ctx = document.getElementById('radarChart')?.getContext('2d');
  if(!ctx) return;
  if (radarChart) radarChart.destroy();
  const labels = Object.keys(scores||{Strength:0, Power:0, Endurance:0, Mobility:0, BodyComp:0});
  const data = labels.map(k=> scores[k]||0);
  radarChart = new Chart(ctx, {
    type:'radar',
    data:{ labels, datasets:[{ label:'Score (1–10)', data, borderColor:'#ff7a00', backgroundColor:'rgba(255,122,0,.18)' }] },
    options:{
      plugins:{ legend:{ labels:{ color:'#ffd900', font:{family:'Orbitron'} } } },
      scales:{ r:{ grid:{ color:'rgba(0,255,255,.2)' }, angleLines:{ color:'rgba(0,255,255,.25)' },
        pointLabels:{ color:'#00ffff', font:{family:'Orbitron'} }, ticks:{ color:'#ffd900', display:true, stepSize:2, showLabelBackdrop:false } } }
    }
  });
}

/* ---------- performance upload handler ---------- */
iPerfUpload?.addEventListener('change', async ()=>{
  const file = iPerfUpload.files?.[0];
  if(!file) return;
  try{
    const text = await file.text();
    let data;
    if (/\.json$/i.test(file.name)) data = JSON.parse(text);
    else data = parseHeatrickCsv(text);
    const metrics = computeMetricsFromHeatrick(data);
    window.__cycloneMetrics = metrics;
    renderAprChart(metrics?.apr?.aerobic_wkg, metrics?.apr?.anaerobic_wkg);
    renderRadarChart(metrics?.radar);
    updatePerfStatsGrid(metrics);
    updateCardStats(metrics);
    showTab('charts');
  }catch(e){
    console.error('perf parse error', e);
    alert('Unable to parse performance file');
  }
});

/* ---------- CREATE ACTION ---------- */
btnCreate?.addEventListener('click', async ()=>{
  const sexVal = iSexM?.checked ? 'M' : iSexF?.checked ? 'F' : null;
  const profile = {
    name: iName.value.trim(),
    country: iCountry.value,
    dob: iDob.value.trim(),
    weight: +iWeight.value || null,
    stance: iStance?.value,
    hrmax: +iHrMax.value || null,
    height: +iHeight.value || null,
    armspan: +iArmSpan.value || null,
    reach: +iReach.value || null,
    sex: sexVal,
    bodyFatFinal: +iBFFinal.value || null,
    body_fat: +iBFFinal.value || null,
    power: +iPower?.value || null,
    endurance: +iEndurance?.value || null,
  };

  const fd = new FormData();
  fd.append('profile', JSON.stringify(profile));
  if (sexVal) fd.append('sex', sexVal);
  const csv = iPerfUpload?.files?.[0];
  if (csv) fd.append('perf_csv', csv);
  if (window.__cycloneMetrics) {
    try { fd.append('metrics', JSON.stringify(window.__cycloneMetrics)); } catch(_e){}
  }
  const photo = iPhoto?.files?.[0];
  if (photo) fd.append('photo', photo);

  // Optionally include precomputed charts from global metrics
  const metrics = typeof window !== 'undefined' ? window.__cycloneMetrics : null;
  if (metrics && typeof metrics === 'object') {
    const charts = {};

    const apr = metrics.apr || metrics.APR;
    if (apr && typeof apr === 'object') {
      const { aerobic_wkg, anaerobic_wkg } = apr;
      const aprClean = {};
      if (aerobic_wkg != null) aprClean.aerobic_wkg = aerobic_wkg;
      if (anaerobic_wkg != null) aprClean.anaerobic_wkg = anaerobic_wkg;
      if (Object.keys(aprClean).length) charts.apr = aprClean;
    }

    const radar = metrics.radar || metrics.radar_scores || metrics.spider;
    if (radar && typeof radar === 'object') {
      charts.radar = radar;
    }

    const summary = metrics.summary || metrics.summaryStats || metrics.summary_stats;
    if (summary && typeof summary === 'object') {
      charts.summary = summary;
    }

    if (Object.keys(charts).length) {
      fd.append('charts', JSON.stringify(charts));
    }
  }

  try{
    const res = await fetch('/api/create-cyclone', { method:'POST', body:fd });
    const ct = res.headers.get('content-type') || '';
    if (!ct.includes('application/json')) {
      const t = await res.text();
      console.log('Non-JSON response', t);
      alert('Save failed: ' + t);
      return;
    }
    const data = await res.json();
    if (!res.ok || !data || typeof data !== 'object') {
      alert('Save failed: ' + (data?.message || res.statusText));
      return;
    }
    const slug = data?.safe_name || data?.fighter_id;
    if (data?.photo_url) {
      preparedPhotoURL = data.photo_url;
      olPhoto.src = preparedPhotoURL;
      olPhoto.classList.add('revealed');
    }
    if (data?.assets?.card_url && cardBg) {
      cardBg.dataset.front = data.assets.card_url;
      cardBg.src = data.assets.card_url;
    }
    showTab('charts');
    renderAprChart(data?.apr?.aerobic_wkg, data?.apr?.anaerobic_wkg);
    renderRadarChart(data?.spider || data?.radar || data?.charts?.radar || {});
    if (btnView){
      if (slug){
        btnView.href = `/fighters/${slug}`;
        btnView.style.display = 'inline-block';
      }else{
        btnView.style.display = 'none';
      }
    }
  }catch(e){
    alert('Network error: ' + e.message);
  }
});
