import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
TAGS_FILE = BASE_DIR / "FightControl" / "static" / "js" / "tags.js"
COACHING_FILE = BASE_DIR / "FightControl" / "static" / "js" / "coaching_main.js"


def test_configure_tags_button_populates_and_opens_modal():
    code_path = TAGS_FILE.resolve().as_posix()
    node_script = f"""
    const path = 'file://{code_path}';
    const localStorage = {{
      getItem: () => JSON.stringify({{ red: ['R1','R2','R3'], blue: ['B1','B2','B3'] }}),
      setItem: () => {{}}
    }};
    const nodes = {{
      configModal: {{ style: {{ display: 'none' }} }},
      redBtn1: {{ textContent: '' }},
      redBtn2: {{ textContent: '' }},
      redBtn3: {{ textContent: '' }},
      blueBtn1: {{ textContent: '' }},
      blueBtn2: {{ textContent: '' }},
      blueBtn3: {{ textContent: '' }},
      red1: {{ value: '', placeholder: '' }},
      red2: {{ value: '', placeholder: '' }},
      red3: {{ value: '', placeholder: '' }},
      blue1: {{ value: '', placeholder: '' }},
      blue2: {{ value: '', placeholder: '' }},
      blue3: {{ value: '', placeholder: '' }},
      configTags: {{ addEventListener: function(e, cb) {{ this.click = cb; }} }}
    }};
    global.document = {{
      getElementById: (id) => nodes[id],
      querySelectorAll: () => []
    }};
    global.window = {{}};
    global.localStorage = localStorage;
    (async () => {{
      const mod = await import(path);
      document.getElementById('configTags').addEventListener('click', mod.openConfig);
      document.getElementById('configTags').click();
      const result = [
        nodes.configModal.style.display,
        nodes.redBtn1.textContent,
        nodes.blueBtn1.textContent,
        nodes.red1.value
      ].join(',');
      console.log(result);
    }})();
    """
    completed = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        check=True,
    )
    display, red_btn, blue_btn, red_input = completed.stdout.strip().split(",")
    assert display == "flex"
    assert red_btn == "R1"
    assert blue_btn == "B1"
    assert red_input == "R1"


def test_tag_buttons_submit_correct_fighter():
    code_path = COACHING_FILE.resolve().as_posix()
    node_script = f"""
    const path = 'file://{code_path}';
    const payloads = [];
    global.fetch = (url, opts = {{}}) => {{
      if (opts.body) payloads.push(JSON.parse(opts.body));
      return Promise.resolve({{ json: () => Promise.resolve({{}}) }});
    }};
    global.localStorage = {{ getItem: () => null, setItem: () => {{}} }};
    const redContainer = {{ id: 'redTags' }};
    const blueContainer = {{ id: 'blueTags' }};
    function makeBtn(container, text) {{
      return {{
        textContent: text,
        dataset: {{}},
        classList: {{ add() {{}}, remove() {{}}, toggle() {{}} }},
        addEventListener(event, cb) {{ this.click = cb; }},
        closest(sel) {{ return sel === '#redTags' && container === redContainer ? redContainer : null; }}
      }};
    }}
    const redBtn = makeBtn(redContainer, 'R1');
    const blueBtn = makeBtn(blueContainer, 'B1');
    const nodes = {{
      redName: {{}}, blueName: {{}},
      redBPM: {{}}, blueBPM: {{}},
      redEffort: {{}}, blueEffort: {{}},
      redZone: {{}}, blueZone: {{}},
      redStatus: {{ classList: {{ toggle() {{}} }} }},
      blueStatus: {{ classList: {{ toggle() {{}} }} }}
    }};
    global.document = {{
      getElementById: id => nodes[id] || null,
      querySelectorAll: sel => sel === '#redTags button, #blueTags button' ? [redBtn, blueBtn] : sel === '#redTags button' ? [redBtn] : sel === '#blueTags button' ? [blueBtn] : [],
      addEventListener: () => {{}}
    }};
    global.window = {{}};
    (async () => {{
      const mod = await import(path);
      mod.initCoaching();
      redBtn.click();
      blueBtn.click();
      console.log(payloads.map(p => p.fighter).join(','));
      process.exit(0);
    }})();
    """
    completed = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        check=True,
    )
    fighters = completed.stdout.strip()
    assert fighters == "red,red,blue,blue"


def test_preset_buttons_submit_correct_fighter():
    code_path = COACHING_FILE.resolve().as_posix()
    node_script = f"""
    const path = 'file://{code_path}';
    const payloads = [];
    global.fetch = (url, opts = {{}}) => {{
      if (opts.body) payloads.push(JSON.parse(opts.body));
      return Promise.resolve({{ json: () => Promise.resolve({{}}) }});
    }};
    global.localStorage = {{ getItem: () => null, setItem: () => {{}} }};
    const redContainer = {{ id: 'redTags' }};
    const blueContainer = {{ id: 'blueTags' }};
    function makeBtn(container, text, id) {{
      let _text = text;
      return {{
        id,
        get textContent() {{ return _text; }},
        set textContent(v) {{ if (v !== undefined && v !== null) _text = v; }},
        dataset: {{}},
        classList: {{ add() {{}}, remove() {{}}, toggle() {{}} }},
        addEventListener(event, cb) {{ this.click = cb; }},
        closest(sel) {{ return sel === '#redTags' && container === redContainer ? redContainer : null; }}
      }};
    }}
    const redBtn = makeBtn(redContainer, 'R1', 'redBtn1');
    const blueBtn = makeBtn(blueContainer, 'B1', 'blueBtn1');
    const nodes = {{
      redName: {{}}, blueName: {{}},
      redBPM: {{}}, blueBPM: {{}},
      redEffort: {{}}, blueEffort: {{}},
      redZone: {{}}, blueZone: {{}},
      redStatus: {{ classList: {{ toggle() {{}} }} }},
      blueStatus: {{ classList: {{ toggle() {{}} }} }},
      redBtn1: redBtn,
      blueBtn1: blueBtn,
      red1: {{ value: 'R1' }}, red2: {{ value: 'R2' }}, red3: {{ value: 'R3' }},
      blue1: {{ value: 'B1' }}, blue2: {{ value: 'B2' }}, blue3: {{ value: 'B3' }},
    }};
    global.document = {{
      getElementById: id => nodes[id] || null,
      querySelectorAll: sel => sel === '#redTags button, #blueTags button'
        ? [redBtn, blueBtn]
        : sel === '#redTags button'
          ? [redBtn]
          : sel === '#blueTags button'
            ? [blueBtn]
            : [],
      addEventListener: () => {{}}
    }};
    global.window = {{}};
    (async () => {{
      const mod = await import(path);
      mod.initCoaching();
      mod.applyPreset('red');
      redBtn.click();
      blueBtn.click();
      const allRed = payloads.map(p => p.fighter).join(',');
      payloads.length = 0;
      mod.applyPreset('blue');
      redBtn.click();
      blueBtn.click();
      const allBlue = payloads.map(p => p.fighter).join(',');
      console.log(allRed + '|' + allBlue);
      process.exit(0);
    }})();
    """
    completed = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        check=True,
    )
    red_mode, blue_mode = completed.stdout.strip().split("|")
    assert red_mode == "red,red,red,red"
    assert blue_mode == "blue,blue,blue,blue"


def test_presets_keep_button_labels_and_colors():
    code_path = TAGS_FILE.resolve().as_posix()
    node_script = f"""
    const path = 'file://{code_path}';
    function makeBtn(id, text) {{
      return {{
        id,
        textContent: text,
        dataset: {{}},
        classList: {{ add() {{}}, remove() {{}}, toggle() {{}} }},
      }};
    }}
    const nodes = {{
      redBtn1: makeBtn('redBtn1', 'R1'),
      redBtn2: makeBtn('redBtn2', 'R2'),
      redBtn3: makeBtn('redBtn3', 'R3'),
      blueBtn1: makeBtn('blueBtn1', 'B1'),
      blueBtn2: makeBtn('blueBtn2', 'B2'),
      blueBtn3: makeBtn('blueBtn3', 'B3'),
      red1: {{ value: 'R1' }}, red2: {{ value: 'R2' }}, red3: {{ value: 'R3' }},
      blue1: {{ value: 'B1' }}, blue2: {{ value: 'B2' }}, blue3: {{ value: 'B3' }},
    }};
    global.document = {{
      getElementById: id => nodes[id] || null,
      querySelectorAll: sel => sel === '#redTags button'
        ? [nodes.redBtn1, nodes.redBtn2, nodes.redBtn3]
        : sel === '#blueTags button'
          ? [nodes.blueBtn1, nodes.blueBtn2, nodes.blueBtn3]
          : sel === '#redTags button, #blueTags button'
            ? [nodes.redBtn1, nodes.redBtn2, nodes.redBtn3, nodes.blueBtn1, nodes.blueBtn2, nodes.blueBtn3]
            : [],
    }};
    global.window = {{}};
    global.localStorage = {{ getItem: () => null, setItem: () => {{}} }};
    (async () => {{
      const mod = await import(path);
      mod.applyPreset('red');
      const redLabels = [
        nodes.redBtn1.textContent,
        nodes.redBtn2.textContent,
        nodes.redBtn3.textContent,
        nodes.blueBtn1.textContent,
        nodes.blueBtn2.textContent,
        nodes.blueBtn3.textContent,
      ].join(',');
      const redColors = [
        nodes.redBtn1.dataset.color,
        nodes.redBtn2.dataset.color,
        nodes.redBtn3.dataset.color,
        nodes.blueBtn1.dataset.color,
        nodes.blueBtn2.dataset.color,
        nodes.blueBtn3.dataset.color,
      ].join(',');
      nodes.red1.value = 'R1'; nodes.red2.value = 'R2'; nodes.red3.value = 'R3';
      nodes.blue1.value = 'B1'; nodes.blue2.value = 'B2'; nodes.blue3.value = 'B3';
      mod.applyPreset('blue');
      const blueLabels = [
        nodes.redBtn1.textContent,
        nodes.redBtn2.textContent,
        nodes.redBtn3.textContent,
        nodes.blueBtn1.textContent,
        nodes.blueBtn2.textContent,
        nodes.blueBtn3.textContent,
      ].join(',');
      const blueColors = [
        nodes.redBtn1.dataset.color,
        nodes.redBtn2.dataset.color,
        nodes.redBtn3.dataset.color,
        nodes.blueBtn1.dataset.color,
        nodes.blueBtn2.dataset.color,
        nodes.blueBtn3.dataset.color,
      ].join(',');
      console.log(redLabels + '|' + redColors + '|' + blueLabels + '|' + blueColors);
      process.exit(0);
    }})();
    """
    completed = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        check=True,
    )
    red_labels, red_colors, blue_labels, blue_colors = completed.stdout.strip().split("|")
    assert red_labels == "R1,R2,R3,R1,R2,R3"
    assert red_colors == "red,red,red,red,red,red"
    assert blue_labels == "B1,B2,B3,B1,B2,B3"
    assert blue_colors == "blue,blue,blue,blue,blue,blue"
