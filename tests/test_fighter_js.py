import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
JS_FILE = BASE_DIR / "FightControl" / "static" / "js" / "fighter.js"


def _run_node(script: str) -> str:
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_map_fighter_assets_uses_svg_and_default():
    code_path = JS_FILE.as_posix()
    script = f"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync('{code_path}', 'utf8');
const container = {{ innerHTML: '' }};
const sandbox = {{
  document: {{
    getElementById: () => container,
    querySelectorAll: () => [],
    addEventListener: () => {{}}
  }},
  fetch: () => Promise.resolve({{ json: () => Promise.resolve([]) }}),
  console: console
}};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const withNation = sandbox.mapFighterAssets({{ nation: 'GB' }}).flagSrc;
const withoutNation = sandbox.mapFighterAssets({{}}).flagSrc;
console.log(withNation);
console.log(withoutNation);
"""
    output = _run_node(script).splitlines()
    assert output[0].endswith("/static/images/flags/gb.svg")
    assert output[1].endswith("/static/images/flags/default.svg")
