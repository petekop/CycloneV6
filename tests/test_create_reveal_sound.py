import json
import subprocess


def test_reveal_sound_play_failure_logs_error_and_flips_card():
    code = """
const removed = [];
const added = [];
const revealSound = { currentTime: 0, play: () => Promise.reject(new Error('boom')) };
const card = { classList: { remove: cls => removed.push(cls), add: cls => added.push(cls) } };

global.requestAnimationFrame = cb => cb();
global.setTimeout = (fn, t) => fn();

console.error = (msg, err) => console.log('ERR', msg, err && err.message);

(async () => {
  if (revealSound) {
    revealSound.currentTime = 0;
    await revealSound
      .play()
      .catch(err => console.error('Audio playback failed', err));
  }

  setTimeout(() => card.classList.remove('spin-once'), 1000);
  requestAnimationFrame(() => card.classList.add('flipped'));

  console.log(JSON.stringify({ removed, added }));
})();
"""
    result = subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True)
    lines = result.stdout.strip().splitlines()
    assert lines[0].startswith("ERR Audio playback failed")
    data = json.loads(lines[1])
    assert data["removed"] == ["spin-once"]
    assert data["added"] == ["flipped"]
