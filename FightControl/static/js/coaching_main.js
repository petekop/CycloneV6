// coaching_main.js

import { startRound, pauseRound, resumeRound, pollTimer } from './timer.js';
import { startBpmPolling, stopBpmPolling } from './bpm.js';
import {
  openConfig, closeConfig, loadStoredTags,
  saveTags, applyPreset, logTag, triggerTag,
  loadTagMode, currentFighter
} from './tags.js';

// Store the last non-null BPM so the text display can keep showing a value
// even when the fighter is marked as RESTING and no BPM is provided.
const lastBpm = { red: null, blue: null };

// Recent BPM samples for charting
const bpmCharts = { red: null, blue: null };
const MAX_SAMPLES = 30;

function initCharts() {
  const redCtx = document.getElementById('redChart')?.getContext('2d');
  const blueCtx = document.getElementById('blueChart')?.getContext('2d');

  if (redCtx) {
    bpmCharts.red = new Chart(redCtx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          data: [],
          borderColor: '#b70000',
          backgroundColor: 'rgba(0,0,0,0)',
          pointRadius: 0,
          tension: 0.3,
        }],
      },
      options: {
        animation: false,
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { display: false },
          y: { display: true },
        },
      },
    });
  }

  if (blueCtx) {
    bpmCharts.blue = new Chart(blueCtx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          data: [],
          borderColor: '#0073e6',
          backgroundColor: 'rgba(0,0,0,0)',
          pointRadius: 0,
          tension: 0.3,
        }],
      },
      options: {
        animation: false,
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { display: false },
          y: { display: true },
        },
      },
    });
  }
}

function pushChartSample(color, bpm) {
  const chart = bpmCharts[color];
  if (!chart) return;
  chart.data.labels.push('');
  chart.data.datasets[0].data.push(bpm);
  if (chart.data.labels.length > MAX_SAMPLES) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }
  chart.update('none');
}

export function initCoaching(roundDuration = 180, baseUrl = '/live-json') {
  initCharts();

  // Keep a reference so polling can be stopped if needed
  startBpmPolling(baseUrl, 1000, (data = {}) => {
    const red = data.red || {};
    const blue = data.blue || {};

    const status = red.status || blue.status;

    const rName = document.getElementById('redName');
    if (rName && red.name) rName.textContent = red.name;

    let redBpm = red.bpm;
    let redChartVal = redBpm;
    if (status === 'RESTING' && redBpm == null) {
      redBpm = lastBpm.red;
      redChartVal = null;
    } else if (redBpm != null) {
      lastBpm.red = redBpm;
    } else {
      redChartVal = null;
    }
    document.getElementById('redBPM').textContent = `${redBpm ?? '--'} bpm`;
    document.getElementById('redEffort').textContent = `${red.effort_percent ?? '--'}%`;
    document.getElementById('redZone').textContent = red.zone || '--Zone';
    const redStatus = document.getElementById('redStatus');
    if (redStatus) {
      redStatus.textContent = status === 'RESTING' ? 'Resting' : 'Active';
      redStatus.classList.toggle('resting', status === 'RESTING');
    }
    pushChartSample('red', redChartVal);

    const bName = document.getElementById('blueName');
    if (bName && blue.name) bName.textContent = blue.name;

    let blueBpm = blue.bpm;
    let blueChartVal = blueBpm;
    if (status === 'RESTING' && blueBpm == null) {
      blueBpm = lastBpm.blue;
      blueChartVal = null;
    } else if (blueBpm != null) {
      lastBpm.blue = blueBpm;
    } else {
      blueChartVal = null;
    }
    document.getElementById('blueBPM').textContent = `${blueBpm ?? '--'} bpm`;
    document.getElementById('blueEffort').textContent = `${blue.effort_percent ?? '--'}%`;
    document.getElementById('blueZone').textContent = blue.zone || '--Zone';
    const blueStatus = document.getElementById('blueStatus');
    if (blueStatus) {
      blueStatus.textContent = status === 'RESTING' ? 'Resting' : 'Active';
      blueStatus.classList.toggle('resting', status === 'RESTING');
    }
    pushChartSample('blue', blueChartVal);
  });

  // Apply any stored tag labels and mode
  loadStoredTags();
  loadTagMode();

  document.querySelectorAll('#redTags button, #blueTags button').forEach(btn => {
    btn.addEventListener('click', () => {
      const fighter = btn.dataset?.color || currentFighter;
      const tag = btn.textContent.trim();
      logTag({ fighter, tag });
      triggerTag(fighter, tag);
    });
  });
}

if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    initCoaching();

    const updateTimerUI = data => {
      const timer = document.getElementById('timer');
      const status = document.getElementById('timer-status');
      if (timer) timer.textContent = data.timer;
      if (status) status.textContent = data.status;
    };

    const applyTimer = data => {
      const startBtn = document.getElementById('startBtn');
      const pauseBtn = document.getElementById('pauseBtn');
      const resumeBtn = document.getElementById('resumeBtn');
      switch (data.status) {
        case 'ACTIVE':
          if (startBtn) startBtn.disabled = true;
          if (pauseBtn) pauseBtn.disabled = false;
          if (resumeBtn) resumeBtn.disabled = true;
          break;
        case 'PAUSED':
          if (startBtn) startBtn.disabled = true;
          if (pauseBtn) pauseBtn.disabled = true;
          if (resumeBtn) resumeBtn.disabled = false;
          break;
        case 'RESTING':
          if (startBtn) startBtn.disabled = true;
          if (pauseBtn) pauseBtn.disabled = true;
          if (resumeBtn) resumeBtn.disabled = true;
          break;
        case 'WAITING':
          if (startBtn) startBtn.disabled = false;
          if (pauseBtn) pauseBtn.disabled = true;
          if (resumeBtn) resumeBtn.disabled = true;
          break;
        default:
          if (startBtn) startBtn.disabled = false;
          if (pauseBtn) pauseBtn.disabled = false;
          if (resumeBtn) resumeBtn.disabled = false;
      }
    };

    const refreshTimer = async () => {
      const res = await fetch('/api/timer', { cache: 'no-store' });
      const data = await res.json();
      updateTimerUI(data);
      applyTimer(data);
    };

    // Poll once per second to keep the coaching panel updated without
    // overloading the server or causing overlay flicker.
    pollTimer(data => { updateTimerUI(data); applyTimer(data); }, 1000);

    document.getElementById('startBtn')?.addEventListener('click', async () => {
      await fetch('/api/timer/start', {
        method: 'POST',
        headers: { 'Cache-Control': 'no-store' },
      });
      await new Promise(r => setTimeout(r, 50));
      await refreshTimer();
    });
    document.getElementById('pauseBtn')?.addEventListener('click', async () => {
      await fetch('/api/timer/pause', {
        method: 'POST',
        headers: { 'Cache-Control': 'no-store' },
      });
      await new Promise(r => setTimeout(r, 50));
      await refreshTimer();
    });
    document.getElementById('resumeBtn')?.addEventListener('click', async () => {
      await fetch('/api/timer/resume', {
        method: 'POST',
        headers: { 'Cache-Control': 'no-store' },
      });
      await new Promise(r => setTimeout(r, 50));
      await refreshTimer();
    });
    document.getElementById('configTags')?.addEventListener('click', openConfig);
    document.getElementById('toggleCharts')?.addEventListener('click', () => {
      document.body.classList.toggle('hide-charts');
    });
    // 🔄 Fallback name fetch if live-json hasn't populated yet
    fetch('/api/fight-data')
      .then(res => res.json())
      .then(data => {
        const r = document.getElementById('redName');
        const b = document.getElementById('blueName');

        const redName = (data.red && data.red.name) || data.red_fighter;
        const blueName = (data.blue && data.blue.name) || data.blue_fighter;

        if (redName && r && (r.textContent === 'RED' || r.textContent === 'RED CORNER'))
          r.textContent = redName;

        if (blueName && b && (b.textContent === 'BLUE' || b.textContent === 'BLUE CORNER'))
          b.textContent = blueName;
      })
      .catch(err => console.warn('💥 Fallback name fetch failed:', err));
  });
}

// Exports for testing
export {
  startRound, pauseRound, resumeRound, pollTimer,
  applyPreset, saveTags, openConfig, closeConfig,
  logTag, triggerTag, startBpmPolling, stopBpmPolling,
  loadStoredTags, loadTagMode
};

// Window globals
if (typeof window !== 'undefined') {
  window.startRound = startRound;
  window.pauseRound = pauseRound;
  window.resumeRound = resumeRound;
  window.applyPreset = applyPreset;
  window.saveTags = saveTags;
  window.openConfig = openConfig;
  window.closeConfig = closeConfig;
  window.initCoaching = initCoaching;
}
