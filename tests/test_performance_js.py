import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SELECT_FILE = BASE_DIR / "FightControl" / "static" / "js" / "select_fighter.js"


def _run_node(script: str) -> str:
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_radar_chart_and_card_stats_use_canonical_keys():
    code_path = SELECT_FILE.as_posix()
    script = f"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync('{code_path}', 'utf8');
const elements = {{}};
function el() {{
  return {{
    textContent: '',
    style: {{}},
    classList: {{ toggle(){{}}, add(){{}}, remove(){{}} }},
    remove() {{}},
    getContext: () => null,
    querySelectorAll: () => [],
    querySelector: () => null,
    insertBefore: () => {{}},
    appendChild: () => {{}},
    addEventListener: () => {{}}
  }};
}}
['cardWrapper','fighterName','fighterDivision','fighterRating','fighterStats','fighterNameFront','fighterWeight','fighterHeight','fighterStance','fighterCard','nextBtn','prevBtn','radarChart','barChart','performanceMessage','division-filter','editBtn','backBtn'].forEach(id => elements[id]=el());
const calls = [];
const sandbox = {{
  document: {{
    getElementById: id => elements[id],
    querySelectorAll: () => [],
    querySelector: () => null,
    createElement: () => el(),
    addEventListener: () => {{}}
  }},
  fetch: () => Promise.resolve({{ json: () => Promise.resolve([]) }}),
  Chart: function(ctx, cfg) {{
    calls.push(cfg);
    return {{ destroy(){{}} }};
  }},
  console: console,
  setTimeout: () => {{}},
  window: {{}},
  elements,
  calls,
}};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
vm.runInContext("fighters = [{{name:'Test', power:10, endurance:20, speed:30, technique:40, wins:1, losses:2, draws:3}}]; filteredFighters = fighters; currentIndex = 0; setFighterAssets = () => {{}}; loadPerformance = () => {{}}; renderFighter(); drawPerformanceCharts(elements['radarChart'], elements['barChart'], fighters[0]);", sandbox);
console.log(elements['fighterStats'].textContent);
console.log(JSON.stringify(calls[0].data.datasets[0].data));
console.log(JSON.stringify(calls[1].data.datasets[0].data));
"""
    output = _run_node(script).splitlines()
    assert output[0] == "Power: 10 | Endurance: 20"
    assert output[1] == "[10,20,30,40]"
    assert output[2] == "[1,2,3]"
