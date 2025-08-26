// Boot initialization script
// Posts to /api/boot/start once and polls /api/boot/status

(() => {
  const hrEl = document.getElementById('hr');
  const hrRedEl = document.getElementById('hr-red');
  const hrBlueEl = document.getElementById('hr-blue');
  const mtxEl = document.getElementById('mtx');
  const obsEl = document.getElementById('obs');
  const statusEl = document.getElementById('status');
  const progressEl = document.getElementById('progress');
  const retryButton = document.getElementById('retryButton');
  const startButton = document.getElementById('startButton');
  const manualStart = /(?:\?|&)manual=1(?:&|$)/.test(window.location.search);

  if (startButton) {
    startButton.style.display = manualStart ? '' : 'none';
  }

  const errorMessages = {
    hr_daemon: 'HR Daemon failed to start.',
    mediamtx: 'MediaMTX failed to start.',
    obs: 'OBS failed to start.'
  };

  let interval = 1000;

  // Fire boot start once
  function startBoot() {
    fetch('/api/boot/start', { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        if (statusEl && data && data.message) {
          statusEl.textContent = data.message;
        }
      })
      .catch(() => {});
  }

  startBoot();

  if (retryButton) {
    retryButton.addEventListener('click', () => {
      retryButton.style.display = 'none';
      startBoot();
    });
  }

  if (startButton) {
    startButton.addEventListener('click', startBoot);
  }

  function update(data) {
    let anyStarting = false;
    let anyError = false;

    if (data && data.services) {
      if (hrEl && typeof data.services.hr_daemon !== 'undefined') {
        hrEl.textContent = data.services.hr_daemon;
      }
      if (mtxEl && typeof data.services.mediamtx !== 'undefined') {
        mtxEl.textContent = data.services.mediamtx;
      }
      if (obsEl && typeof data.services.obs !== 'undefined') {
        obsEl.textContent = data.services.obs;
      }

      const services = data.services;
      const allReady = ['hr_daemon', 'mediamtx', 'obs'].every(
        k => services[k] === 'READY'
      );
      if (allReady) {
        window.location.href = '/index';
      }

      const states = Object.values(services);
      anyStarting = states.some(s => s === 'STARTING');
      anyError = states.some(s => s === 'ERROR');

      if (statusEl) {
        if (anyError) {
          const messages = Object.entries(services)
            .filter(([, state]) => state === 'ERROR')
            .map(([name]) => errorMessages[name] || `${name} failed to start.`);
          statusEl.textContent = messages.join(' ');
        } else if (data.message) {
          statusEl.textContent = data.message;
        }
      }
    } else if (statusEl && data && data.message) {
      statusEl.textContent = data.message;
    }

    if (progressEl && typeof data.progress === 'number') {
      const clamped = Math.max(0, Math.min(100, data.progress));
      progressEl.style.width = clamped + '%';
    }

    if (retryButton) {
      retryButton.style.display = anyError ? 'inline-block' : 'none';
    }

    return anyStarting;
  }

  function updateHr(data) {
    if (!data) return;
    if (hrRedEl) {
      const status = data.red || 'DISCONNECTED';
      hrRedEl.textContent = `Red: ${status}`;
      if (status === 'ERROR' || status === 'DISCONNECTED') {
        hrRedEl.style.color = '#f00';
        hrRedEl.textContent += ' – check strap';
      } else {
        hrRedEl.style.color = '#0f0';
      }
    }
    if (hrBlueEl) {
      const status = data.blue || 'DISCONNECTED';
      hrBlueEl.textContent = `Blue: ${status}`;
      if (status === 'ERROR' || status === 'DISCONNECTED') {
        hrBlueEl.style.color = '#f00';
        hrBlueEl.textContent += ' – check strap';
      } else {
        hrBlueEl.style.color = '#0f0';
      }
    }
  }

  async function poll() {
    try {
      const res = await fetch('/api/boot/status', { cache: 'no-store' });
      const data = await res.json();
      const anyStarting = update(data);
      interval = anyStarting ? 500 : 2000;
    } catch (e) {
      // swallow errors
    } finally {
      setTimeout(poll, interval);
    }
  }

  poll();

  async function pollHr() {
    try {
      const res = await fetch('/api/hr/status', { cache: 'no-store' });
      const data = await res.json();
      updateHr(data);
    } catch (e) {
      // swallow errors
    } finally {
      setTimeout(pollHr, 1000);
    }
  }

  pollHr();
})();
