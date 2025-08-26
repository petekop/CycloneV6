let fighters = [];
let filteredFighters = [];
let currentIndex = 0;
let performanceChart = null;
let radarChartInstance;
let barChartInstance;

function createPreviewCard(fighter) {
  const card = document.createElement('div');
  card.className = 'preview-card';
  card.style.width = '200px';
  card.style.height = '260px';
  card.style.display = 'flex';
  card.style.alignItems = 'center';
  card.style.justifyContent = 'center';
  card.style.background = 'rgba(0,0,0,0.6)';
  card.style.borderRadius = '12px';
  card.style.transform = 'scale(0.8)';
  card.style.pointerEvents = 'none';
  if (fighter.card_url) {
    const img = document.createElement('img');
    img.src = `${fighter.card_url}?t=${Date.now()}`;
    img.alt = fighter.name || '';
    img.style.maxWidth = '100%';
    img.style.maxHeight = '100%';
    card.appendChild(img);
  } else {
    card.textContent = fighter.name || '';
  }
  return card;
}

async function loadPerformance(name) {
  const radarEl = document.getElementById('radarChart');
  const barEl = document.getElementById('barChart');
  const msgEl = document.getElementById('performanceMessage');
  if (!radarEl || !barEl) return;

  try {
    const res = await fetch(`/fighter_data/${encodeURIComponent(name)}/performance.json`);
    if (!res.ok) throw new Error('missing');
    const perf = await res.json();
    drawPerformanceCharts(radarEl, barEl, perf);
    radarEl.style.display = 'block';
    barEl.style.display = 'block';
    if (msgEl) msgEl.textContent = '';
  } catch (err) {
    if (radarChartInstance) radarChartInstance.destroy();
    if (barChartInstance) barChartInstance.destroy();
    radarChartInstance = null;
    barChartInstance = null;
    radarEl.style.display = 'none';
    barEl.style.display = 'none';
    if (msgEl) msgEl.textContent = 'No performance data available.';
  }
}

function drawPerformanceCharts(radarEl, barEl, perf) {
  const radarCtx = radarEl.getContext('2d');
  const barCtx = barEl.getContext('2d');

  const radarData = {
    labels: ['Power', 'Endurance', 'Speed', 'Technique'],
    datasets: [{
      label: 'Attributes',
      data: [
        perf.power || 0,
        perf.endurance || 0,
        perf.speed || 0,
        perf.technique || 0
      ],
      backgroundColor: 'rgba(0,255,255,0.2)',
      borderColor: '#0ff'
    }]
  };

  const barData = {
    labels: ['Wins', 'Losses', 'Draws'],
    datasets: [{
      label: 'Record',
      data: [
        perf.wins || 0,
        perf.losses || 0,
        perf.draws || 0
      ],
      backgroundColor: ['#0ff', '#f00', '#ff0']
    }]
  };

  if (radarChartInstance) radarChartInstance.destroy();
  if (barChartInstance) barChartInstance.destroy();

  radarChartInstance = new Chart(radarCtx, {
    type: 'radar',
    data: radarData,
    options: {
      scales: { r: { beginAtZero: true, max: 100 } },
      plugins: { legend: { display: false } }
    }
  });

  barChartInstance = new Chart(barCtx, {
    type: 'bar',
    data: barData,
    options: {
      scales: { y: { beginAtZero: true } },
      plugins: { legend: { display: false } }
    }
  });
}

function renderFighter() {
  const wrapper = document.getElementById('cardWrapper');
  wrapper.querySelectorAll('.preview-card').forEach(el => el.remove());

  if (!filteredFighters.length) {
    document.getElementById('fighterName').textContent = '';
    document.getElementById('fighterDivision').textContent = '';
    document.getElementById('fighterRating').textContent = '';
    document.getElementById('fighterStats').textContent = '';
    document.getElementById('fighterNameFront').textContent = '';
    document.getElementById('fighterWeight').textContent = '';
    document.getElementById('fighterHeight').textContent = '';
    document.getElementById('fighterStance').textContent = '';
    loadPerformance('');
    return;
  }

  const fighter = filteredFighters[currentIndex];
  document.getElementById('fighterName').textContent = fighter.name || '';
  document.getElementById('fighterDivision').textContent = fighter.division || fighter.weight || '';
  document.getElementById('fighterRating').textContent = fighter.rating ? `Rating: ${fighter.rating}` : '';

  const statsEl = document.getElementById('fighterStats');
  if (statsEl) {
    const parts = [];
    if (fighter.power !== undefined) parts.push(`Power: ${fighter.power}`);
    if (fighter.endurance !== undefined) parts.push(`Endurance: ${fighter.endurance}`);
    if (fighter.hr_zones !== undefined) parts.push(`HR Zones: ${fighter.hr_zones}`);
    statsEl.textContent = parts.join(' | ') || fighter.stats || '';
  }

  document.getElementById('fighterNameFront').textContent = fighter.name || '';
  document.getElementById('fighterWeight').textContent = fighter.weight || '';
  document.getElementById('fighterHeight').textContent = fighter.height || '';
  document.getElementById('fighterStance').textContent = fighter.stance || '';

  const cardEl = document.getElementById('fighterCard');
  cardEl.classList.toggle('flipped', !!fighter.flipped);
  cardEl.style.transform = 'scale(1)';
  cardEl.style.position = 'relative';

  // Display fighter card image if available
  let img = cardEl.querySelector('img.fighter-card-img');
  if (fighter.card_url) {
    if (!img) {
      img = document.createElement('img');
      img.className = 'fighter-card-img';
      img.style.position = 'absolute';
      img.style.top = '0';
      img.style.left = '0';
      img.style.width = '100%';
      img.style.height = '100%';
      cardEl.appendChild(img);
    }
    img.src = `${fighter.card_url}?t=${Date.now()}`;
    img.alt = fighter.name || '';
    img.style.display = 'block';
  } else if (img) {
    img.remove();
  }

  if (filteredFighters.length > 1) {
    const prevIndex = (currentIndex - 1 + filteredFighters.length) % filteredFighters.length;
    const nextIndex = (currentIndex + 1) % filteredFighters.length;
    const prevCard = createPreviewCard(filteredFighters[prevIndex]);
    const nextCard = createPreviewCard(filteredFighters[nextIndex]);
    const nextBtn = document.getElementById('nextBtn');
    wrapper.insertBefore(prevCard, cardEl);
    wrapper.insertBefore(nextCard, nextBtn);
  }

  setFighterAssets(fighter);
  loadPerformance(fighter.name);
}

function applyFilters() {
  const activeTab = document.querySelector('.filter-tab.active');
  const ageFilter = activeTab ? activeTab.dataset.age : '';
  const divisionFilter = document.getElementById('division-filter').value;

  filteredFighters = fighters.filter(f => {
    let ageMatch = true;
    if (ageFilter) {
      const ageNum = parseInt(f.age, 10);
      if (isNaN(ageNum)) {
        ageMatch = false;
      } else if (ageFilter.includes('-')) {
        const [min, max] = ageFilter.split('-').map(Number);
        ageMatch = ageNum >= min && ageNum <= max;
      } else if (ageFilter.endsWith('+')) {
        const min = parseInt(ageFilter, 10);
        ageMatch = ageNum >= min;
      } else if (ageFilter.startsWith('under')) {
        const max = parseInt(ageFilter.replace('under', ''), 10);
        ageMatch = ageNum < max;
      } else {
        ageMatch = String(f.age) === ageFilter;
      }
    }

    const divisionMatch = !divisionFilter || f.division === divisionFilter;
    return ageMatch && divisionMatch;
  });

  currentIndex = 0;
  renderFighter();
}

fetch('/api/fighters')
  .then(res => res.json())
  .then(data => {
    fighters = data;
    filteredFighters = fighters;
    fighters.forEach(f => {
      f.card_url = f.card_url || '';
      f.power = f.power || 50;
      f.endurance = f.endurance || 50;
      f.speed = f.speed || 50;
      f.technique = f.technique || 50;
      f.wins = f.wins || 0;
      f.losses = f.losses || 0;
      f.draws = f.draws || 0;
      f.flipped = false;
    });
    const divisionSelect = document.getElementById('division-filter');
    const divisions = [...new Set(fighters.map(f => f.division).filter(Boolean))].sort();
    divisions.forEach(div => {
      const opt = document.createElement('option');
      opt.value = div;
      opt.textContent = div;
      divisionSelect.appendChild(opt);
    });
    renderFighter();
  })
  .catch(() => {
    fighters = [];
    filteredFighters = [];
  });

document.querySelectorAll('.filter-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    applyFilters();
  });
});

document.getElementById('division-filter').addEventListener('change', applyFilters);

function navigateFighter(step) {
  if (!filteredFighters.length) return;
  const card = document.getElementById('fighterCard');
  card.classList.remove('flipped');
  currentIndex = (currentIndex + step + filteredFighters.length) % filteredFighters.length;
  renderFighter();
}

document.getElementById('prevBtn').addEventListener('click', () => navigateFighter(-1));

document.getElementById('nextBtn').addEventListener('click', () => navigateFighter(1));

document.addEventListener('keydown', e => {
  if (e.key === 'ArrowLeft') {
    navigateFighter(-1);
  } else if (e.key === 'ArrowRight') {
    navigateFighter(1);
  }
});

document.getElementById('fighterCard').addEventListener('click', () => {
  if (!filteredFighters.length) return;
  const fighter = filteredFighters[currentIndex];
  fighter.flipped = !fighter.flipped;
  document.getElementById('fighterCard').classList.toggle('flipped', fighter.flipped);
});

document.getElementById('editBtn').addEventListener('click', (e) => {
  e.stopPropagation();
  if (!filteredFighters.length) return;
  const fighter = filteredFighters[currentIndex];
  editFighter(fighter.name);
});

document.getElementById('backBtn').addEventListener('click', () => {
  window.location.href = '/index';
});
