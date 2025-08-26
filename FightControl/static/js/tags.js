const tags = [];

// Current tag mode ("red", "blue" or "split")
export let currentFighter = 'split';

function setBtnClass(btn, cls, color) {
  if (!btn) return;
  if (btn.classList) {
    btn.classList.remove('red-left', 'red-right', 'blue-left', 'blue-right');
    btn.classList.add(cls);
  }
  if (btn.dataset) btn.dataset.color = color;
}

export function loadTagMode() {
  try {
    const stored = localStorage.getItem('tagMode');
    if (stored) currentFighter = stored;
  } catch {}
  updateButtonColors();
}

function updateButtonColors() {
  const leftBtns = document.querySelectorAll('#redTags button');
  const rightBtns = document.querySelectorAll('#blueTags button');

  if (currentFighter === 'red') {
    leftBtns.forEach(btn => setBtnClass(btn, 'red-left', 'red'));
    rightBtns.forEach(btn => setBtnClass(btn, 'red-right', 'red'));
  } else if (currentFighter === 'blue') {
    leftBtns.forEach(btn => setBtnClass(btn, 'blue-left', 'blue'));
    rightBtns.forEach(btn => setBtnClass(btn, 'blue-right', 'blue'));
  } else {
    leftBtns.forEach(btn => setBtnClass(btn, 'red-left', 'red'));
    rightBtns.forEach(btn => setBtnClass(btn, 'blue-right', 'blue'));
  }
}

/**
 * Apply given tag labels to the button elements and associated inputs.
 * @param {{red: string[], blue: string[]}} labels
 */
export function applyTags(labels = {}) {
  ['red', 'blue'].forEach(color => {
    (labels[color] || []).forEach((label, idx) => {
      const btn = document.getElementById(`${color}Btn${idx + 1}`);
      if (btn && label) btn.textContent = label;

      const input = document.getElementById(`${color}${idx + 1}`);
      if (input) input.value = label;
    });
  });
}

export function logTag(entry) {
  if (!entry || !entry.tag) return;
  tags.push({ ...entry, timestamp: Date.now() });
  try {
    fetch('/api/log-tag', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(entry),
    });
  } catch (err) {
    console.error('Tag log failed:', err);
  }
}

export function triggerTag(fighter, tag) {
  if (!fighter || !tag) return;
  const payload = { fighter, tag };
  fetch('/api/trigger-tag', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).catch((err) => console.error('Tag trigger failed:', err));
}

export function openConfig() {
  const config = loadStoredTags();
  applyTags(config);
  const modal = document.getElementById('configModal');
  if (!modal) return;
  const stored = loadStoredTags();
  ['red', 'blue'].forEach(col => {
    stored[col]?.forEach((text, idx) => {
      const input = document.getElementById(`${col}${idx + 1}`);
      if (input) input.value = text || '';
    });
  });
  modal.style.display = 'flex';
}

export function closeConfig() {
  const modal = document.getElementById('configModal');
  if (modal) modal.style.display = 'none';
}

export function loadStoredTags() {
  try {
    const parsed = JSON.parse(localStorage.getItem('tagLabels') || '{}');
    if (parsed && typeof parsed === 'object') {
      applyTags(parsed);  // Unified with exportable applyTags
      return parsed;
    }
  } catch {}
  return { red: [], blue: [] };
}

export function saveTags() {
  const data = {
    red: [1, 2, 3].map(i =>
      document.getElementById(`red${i}`)?.value.trim() ||
      document.getElementById(`red${i}`)?.placeholder || ''
    ),
    blue: [1, 2, 3].map(i =>
      document.getElementById(`blue${i}`)?.value.trim() ||
      document.getElementById(`blue${i}`)?.placeholder || ''
    ),
  };

  applyTags(data);
  try {
    localStorage.setItem('tagLabels', JSON.stringify(data));
  } catch (err) {
    console.error('Failed to save tags', err);
  }

  closeConfig();
}

/**
 * Update tag button classes to reflect the active preset.
 * @param {'red'|'blue'|'half'} mode
 */
export function setButtonMode(mode) {
  const redBtns = [1, 2, 3].map(i => document.getElementById(`redBtn${i}`));
  const blueBtns = [1, 2, 3].map(i => document.getElementById(`blueBtn${i}`));
  const allBtns = [...redBtns, ...blueBtns];

  allBtns.forEach(btn => {
    if (btn?.classList) btn.classList.remove('red-left', 'blue-right');
  });

  if (mode === 'red') {
    allBtns.forEach(btn => {
      if (btn?.classList) btn.classList.add('red-left');
    });
  } else if (mode === 'blue') {
    allBtns.forEach(btn => {
      if (btn?.classList) btn.classList.add('blue-right');
    });
  } else if (mode === 'half') {
    redBtns.forEach((btn, idx) =>
      btn?.classList && btn.classList.add(idx === 0 ? 'red-left' : 'blue-right')
    );
    blueBtns.forEach((btn, idx) =>
      btn?.classList && btn.classList.add(idx === 0 ? 'red-left' : 'blue-right')
    );
  }
}

export function applyPreset(preset) {
  const redInputs = [1, 2, 3].map(i => document.getElementById(`red${i}`));
  const blueInputs = [1, 2, 3].map(i => document.getElementById(`blue${i}`));
  const redBtns = [1, 2, 3].map(i => document.getElementById(`redBtn${i}`));
  const blueBtns = [1, 2, 3].map(i => document.getElementById(`blueBtn${i}`));

  switch (preset) {
    case 'red': {
      const vals = redInputs.map(inp => inp?.value || '');
      blueInputs.forEach((inp, idx) => { if (inp) inp.value = vals[idx]; });
      [...redBtns, ...blueBtns].forEach((btn, idx) => {
        if (!btn) return;
        btn.textContent = vals[idx % 3];
        if (btn.dataset) btn.dataset.color = 'red';
      });
      currentFighter = 'red';
      break;
    }
    case 'blue': {
      const vals = blueInputs.map(inp => inp?.value || '');
      redInputs.forEach((inp, idx) => { if (inp) inp.value = vals[idx]; });
      [...redBtns, ...blueBtns].forEach((btn, idx) => {
        if (!btn) return;
        btn.textContent = vals[idx % 3];
        if (btn.dataset) btn.dataset.color = 'blue';
      });
      currentFighter = 'blue';
      break;
    }
    case 'half': {
      const redVals = redInputs.map(inp => inp?.value || '');
      const blueVals = blueInputs.map(inp => inp?.value || '');
      redInputs.forEach((inp, idx) => {
        if (inp) inp.value = idx === 0 ? redVals[idx] : blueVals[idx];
      });
      blueInputs.forEach((inp, idx) => {
        if (inp) inp.value = idx === 0 ? redVals[idx] : blueVals[idx];
      });
      redBtns.forEach((btn, idx) => {
        if (!btn) return;
        btn.textContent = idx === 0 ? redVals[idx] : blueVals[idx];
        if (btn.dataset) btn.dataset.color = idx === 0 ? 'red' : 'blue';
      });
      blueBtns.forEach((btn, idx) => {
        if (!btn) return;
        btn.textContent = idx === 0 ? redVals[idx] : blueVals[idx];
        if (btn.dataset) btn.dataset.color = idx === 0 ? 'red' : 'blue';
      });
      currentFighter = 'split';
      break;
    }
    default:
      return;
  }

  setButtonMode(preset);
  updateButtonColors();
  try {
    localStorage.setItem('tagMode', currentFighter);
  } catch {}
}

export function getTags() {
  return tags;
}
