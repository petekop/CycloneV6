"""Tests for create.js verifying chart updates and overlay rendering.

Ensures the script uses ``safe_name`` instead of ``fighter_id`` and includes
card asset information.
"""

import json
import subprocess
from pathlib import Path

CREATE_JS = Path(__file__).resolve().parents[1] / "FightControl" / "static" / "js" / "create.js"


def test_create_js_charts_and_overlay():
    """create.js parses CSV response and updates charts and card overlay."""
    script = r"""
const fs=require('fs');
const vm=require('vm');
const code=fs.readFileSync(process.argv[1],'utf8');
function makeEl(){return {value:'',checked:false,files:[],textContent:'',src:'',href:'',dataset:{},style:{},listeners:{},classList:{classes:new Set(),add(c){this.classes.add(c);},remove(c){this.classes.delete(c);},toggle(c,on){if(on===undefined){if(this.classes.has(c))this.classes.delete(c);else this.classes.add(c);}else{if(on)this.classes.add(c);else this.classes.delete(c);}},contains(c){return this.classes.has(c);}},addEventListener(evt,fn){this.listeners[evt]=fn;},click(){return this.listeners.click&&this.listeners.click();},setAttribute(){},getContext(){return {};}};}
const elements={};
const ids=['tab-info','tab-metrics','tab-docs','tab-performance','tab-charts','cardFrame','cardBg','olPhoto','olName','olFlag','briefAge','briefHt','briefClass','name','country','dob','weight','hrmax','weightClass','sexM','sexF','height','armspan','reach','haveBodyFat','bodyFat','bodyFatAuto','bodyFatFinal','neck','waist','hip','hipRow','photo','removeBg','power','endurance','stance','perfUpload','createBtn','viewBtn','aprChart','radarChart'];
ids.forEach(id=>elements[id]=makeEl());
elements['country'].selectedOptions=[{dataset:{flag:'gb'},value:'GB',text:'United Kingdom'}];
elements['name'].value='Alice';
elements['dob'].value='01/01/2000';
elements['weight'].value='60';
elements['height'].value='170';
elements['armspan'].value='171';
const sampleCSV='fighter_id,name,date,max_anaerobic_power_wkg,max_aerobic_power_wkg,rating_strength,rating_power,rating_endurance,rating_mobility,rating_bodycomp\nf001,Alice,2024-04-30,14.5,9.2,7,6,8,5,4';
function FakeFile(name,content){this.name=name;this.content=content;}
FakeFile.prototype.text=function(){return Promise.resolve(this.content);};
elements['perfUpload'].files=[new FakeFile('perf.csv',sampleCSV)];
const doc={
  getElementById:id=>elements[id]||null,
  querySelectorAll:sel=>{
    if(sel==='.tab'){
      return ['info','metrics','docs','performance','charts'].map(t=>{const e=makeEl();e.dataset.tab=t;return e;});
    }
    if(sel==='.btn.next') return [];
    return [];
  },
  querySelector:sel=> sel==='.card-frame' ? elements['cardFrame'] : null,
};
function FormData(){this.map={};}
FormData.prototype.append=function(k,v){this.map[k]=v;};
const chartCalls=[];
function Chart(ctx,cfg){chartCalls.push(cfg);return {destroy(){}};}
async function fakeFetch(url,{method='GET',body}={}){
  const csvText=body.map.perf_csv.content;
  const lines=csvText.trim().split(/\r?\n/);
  const headers=lines[0].split(',');
  const values=lines[1].split(',');
  const row={}; headers.forEach((h,i)=> row[h]=values[i]);
  const data={
    apr:{anaerobic_wkg:parseFloat(row.max_anaerobic_power_wkg),aerobic_wkg:parseFloat(row.max_aerobic_power_wkg)},
    radar:{Strength:+row.rating_strength,Power:+row.rating_power,Endurance:+row.rating_endurance,Mobility:+row.rating_mobility,BodyComp:+row.rating_bodycomp},
    safe_name:'alice',
    photo_url:'http://example.com/photo.jpg',
    assets:{card_url:'http://example.com/card.png'}
  };
  return {ok:true,headers:{get:()=> 'application/json'},json:async()=>data};
}
const sandbox={document:doc,window:{},fetch:fakeFetch,console:console,setTimeout:(fn)=>fn(),FormData:FormData,URL:{createObjectURL:()=> 'blob:photo'},alert:()=>{},Chart:Chart};
sandbox.window.Chart=Chart;
vm.createContext(sandbox);
vm.runInContext(code,sandbox);
(async()=>{
  await elements['createBtn'].click();
  const out={
    aprDataset:chartCalls[0].data.datasets[0].data,
    radarDataset:chartCalls[1].data.datasets[0].data,
    olName:elements['olName'].textContent,
    briefHt:elements['briefHt'].textContent,
    briefClass:elements['briefClass'].textContent,
    photoRevealed:elements['olPhoto'].classList.contains('revealed'),
    olPhoto:elements['olPhoto'].src,
    cardBg:elements['cardBg'].src,
    viewHref:elements['viewBtn'].href
  };
  console.log(JSON.stringify(out));
})();
"""
    result = subprocess.run(
        ["node", "-e", script, CREATE_JS.as_posix()],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout.strip())
    assert data["olName"] == "Alice"
    assert data["briefHt"] == "170 cm"
    assert data["briefClass"] == "Light (57–60 kg)"
    assert data["aprDataset"] == [9.2, 14.5]
    assert data["radarDataset"] == [7,6,8,5,4]
    assert data["photoRevealed"] is True
    assert data["olPhoto"] == "http://example.com/photo.jpg"
    assert data["cardBg"] == "http://example.com/card.png"
    assert data["viewHref"] == "/fighters/alice"
