import json
import subprocess
from pathlib import Path

BOOT_JS = Path(__file__).resolve().parents[1] / "FightControl" / "static" / "js" / "boot.js"


def test_boot_manual_retry() -> None:
    """Boot page supports manual start and retry after errors."""
    script = r"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync(process.argv[1], 'utf8');
function createEl(display) {
  return {
    textContent: '',
    style: { display: display },
    listeners: {},
    addEventListener(event, fn) { this.listeners[event] = fn; },
    click() { if (this.listeners.click) this.listeners.click(); }
  };
}
const elements = {};
['status','progress','hr','hr-red','hr-blue','mtx','obs','retryButton','startButton'].forEach(id => { elements[id] = createEl(id === 'retryButton' ? 'none' : '') });
const fetchCalls = [];
const sandbox = {
  document: { getElementById: id => elements[id] || null },
  window: { location: { search: '?manual=1', href: '' } },
  fetch: (url, opts={}) => {
    if (url === '/api/boot/start' && opts.method !== 'POST') {
      throw new Error('Expected POST for /api/boot/start');
    }
    fetchCalls.push({ url, opts });
    if (url === '/api/boot/status') {
      return Promise.resolve({ json: () => Promise.resolve({ services: { obs: 'ERROR' } }) });
    }
    return Promise.resolve({ json: () => Promise.resolve({}) });
  },
  console: console,
  setTimeout: () => {}
};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);

setTimeout(() => {
  const startCall = c => c.url === '/api/boot/start' && c.opts.method === 'POST';
  const initialStartCalls = fetchCalls.filter(startCall).length;
  elements.startButton.click();
  const afterStartButtonCalls = fetchCalls.filter(startCall).length;
  const statusText = elements.status.textContent;
  const retryDisplay = elements.retryButton.style.display;
  elements.retryButton.click();
  const afterRetryCalls = fetchCalls.filter(startCall).length;
  console.log(JSON.stringify({
    startVisible: elements.startButton.style.display !== 'none',
    initialStartCalls,
    afterStartButtonCalls,
    statusText,
    retryDisplay,
    afterRetryCalls
  }));
}, 0);
"""
    result = subprocess.run(
        ["node", "-e", script, BOOT_JS.as_posix()],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout.strip())
    assert data["startVisible"]
    assert data["initialStartCalls"] == 1
    assert data["afterStartButtonCalls"] == 2
    assert data["statusText"] == "OBS failed to start."
    assert data["retryDisplay"] == "inline-block"
    assert data["afterRetryCalls"] == 3
