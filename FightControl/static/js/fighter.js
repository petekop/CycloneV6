let fighters = [];
let currentIndex = 0;
const DROPDOWN_SELECTOR = 'select.fighter-select, select#fighterSelect';

function fetchFighters() {
  fetch('/api/fighters')
    .then((res) => res.json())
    .then((data) => {
      fighters = data.map(mapFighterAssets);
      populateDropdowns();
      if (fighters.length) {
        renderCard(fighters[currentIndex]);
      }
    });
}

// Convert a fighter object so that flag/style asset paths are always present.
function mapFighterAssets(fighter) {
  const toSlug = (s) => (s || '').toLowerCase().replace(/\s+/g, '_');
  const imgPath = (folder, value, ext = 'svg') =>
    `/static/images/${folder}/${toSlug(value || 'default')}.${ext}`;

  const nation = fighter.nation || fighter.country;

return {
  ...fighter,
  nation,
  flagSrc: imgPath('flags', nation),
  styleSrc: imgPath('styles', fighter.style, 'png'),
};

}

// Populate any dropdowns for fighter selection.  Dropdowns should have the
// class "fighter-select" or an id of "fighterSelect".
function populateDropdowns() {
  const selects = document.querySelectorAll(DROPDOWN_SELECTOR);
  selects.forEach((sel) => {
    sel.innerHTML = '<option value="">-- Select Fighter --</option>';
    fighters.forEach((f, idx) => {
      const opt = document.createElement('option');
      opt.value = idx;
      opt.textContent = f.name;
      sel.appendChild(opt);
    });
    sel.value = String(currentIndex);
  });
}

// Render the currently selected fighter's metadata into an element with the id
// "cardContainer".  All available fields are displayed so that templates have a
// simple way to show fighter information.
function renderCard(fighter) {
  const container = document.getElementById('cardContainer');
  if (!container) return;

  const stats =
    fighter.stats && typeof fighter.stats === 'object'
      ? Object.entries(fighter.stats)
          .map(([k, v]) => `${k}: ${v}`)
          .join(', ')
      : '';

  const flagImg = `<img id="flagImg" src="${fighter.flagSrc}" alt="${fighter.nation || 'flag'}" onerror="this.onerror=null;this.src='/static/images/flags/default.svg'">`;
  const styleImg = `<img id="styleImg" src="${fighter.styleSrc}" alt="${fighter.style || 'style'}" onerror="this.onerror=null;this.src='/static/images/styles/default.png'">`;

  container.innerHTML = `
    <h3>${fighter.name || ''}</h3>
    <p>Division: ${fighter.division || ''}</p>
    <p>Style: ${fighter.style || ''}</p>
    <p>Rating: ${fighter.rating ?? ''}</p>
    <p>Nation: ${fighter.nation || ''}</p>
    <p>Stats: ${stats}</p>
    ${flagImg}
    ${styleImg}
  `;
}

// When a dropdown changes, render the associated fighter card.
document.addEventListener('change', (e) => {
  if (e.target.matches(DROPDOWN_SELECTOR)) {
    const idx = parseInt(e.target.value, 10);
    if (!isNaN(idx)) {
      currentIndex = idx;
      renderCard(fighters[idx]);
      document.querySelectorAll(DROPDOWN_SELECTOR).forEach((sel) => {
        sel.value = String(idx);
      });
    }
  }
});

fetchFighters();
