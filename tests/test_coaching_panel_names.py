import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
JS_FILE = BASE_DIR / "FightControl" / "static" / "js" / "coaching_main.js"
HTML_FILE = BASE_DIR / "templates" / "touchportal" / "coaching_panel.html"


def test_coaching_panel_module_exports():
    html = HTML_FILE.read_text(encoding="utf-8")
    assert '<script type="module" src="/static/js/coaching_main.js"></script>' in html

    code_path = JS_FILE.resolve().as_posix()
    node_script = f"""
    global.document = {{ addEventListener: () => {{}} }};
    global.window = {{}};
    (async () => {{
      const mod = await import('file://{code_path}');
      console.log(Object.keys(mod).sort().join(','));
    }})();
    """
    completed = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        check=True,
    )
    exported = set(completed.stdout.strip().split(","))
    expected = {
        "initCoaching",
        "startRound",
        "pauseRound",
        "resumeRound",
        "pollTimer",
        "applyPreset",
        "saveTags",
        "openConfig",
        "closeConfig",
        "logTag",
        "triggerTag",
    }
    assert expected.issubset(exported)


def test_coaching_panel_fetch_updates_names():
    code_path = JS_FILE.resolve().as_posix()
    node_script = f"""
    const results = {{ red_fighter: 'Alice', blue_fighter: 'Bob' }};
    global.fetch = (url) => Promise.resolve({{ json: () => Promise.resolve(url.includes('/api/fight-data') ? results : {{}}) }});

    const nodes = {{
      '#redName': {{ textContent: 'RED' }},
      '#blueName': {{ textContent: 'BLUE' }},
      '#redBPM': {{ textContent: '' }},
      '#redEffort': {{ textContent: '' }},
      '#redZone': {{ textContent: '' }},
      '#blueBPM': {{ textContent: '' }},
      '#blueEffort': {{ textContent: '' }},
      '#blueZone': {{ textContent: '' }},
      '#timer': {{ textContent: '' }},
      '#timer-status': {{ textContent: '' }}
    }};

    global.document = {{
      nodes,
      getElementById(id) {{ return this.nodes['#' + id] || null; }},
      querySelectorAll() {{ return []; }},
      addEventListener(event, cb) {{ if (event === 'DOMContentLoaded') cb(); }}
    }};
    global.window = {{}};

    (async () => {{
      await import('file://{code_path}');
      setTimeout(() => {{
        const r = document.getElementById('redName').textContent;
        const b = document.getElementById('blueName').textContent;
        console.log(r + ',' + b);
        process.exit(0);
      }}, 0);
    }})();
    """
    completed = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        check=True,
    )
    output = completed.stdout.strip()
    assert output == "Alice,Bob"
