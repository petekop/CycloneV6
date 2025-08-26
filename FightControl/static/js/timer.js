export async function startRound() {
  await fetch('/api/timer/start', {
    method: 'POST',
    headers: { 'Cache-Control': 'no-store' },
  });
}

export async function pauseRound() {
  await fetch('/api/timer/pause', {
    method: 'POST',
    headers: { 'Cache-Control': 'no-store' },
  });
}

export async function resumeRound() {
  await fetch('/api/timer/resume', {
    method: 'POST',
    headers: { 'Cache-Control': 'no-store' },
  });
}

export function pollTimer(onTick, interval = null) {
  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/timer', { cache: 'no-store' });
      const data = await res.json();
      if (onTick) onTick(data);
      if (typeof document !== 'undefined') {
        const status = document.getElementById('timer-status');
        if (status && status.style) status.style.color = '';
      }
    } catch (err) {
      console.error('💥 Timer fetch error:', err);
      if (typeof document !== 'undefined') {
        const status = document.getElementById('timer-status');
        if (status) {
          status.textContent = '⚠️ TIMER OFFLINE';
          if (status.style) status.style.color = 'red';
        }
      }
    }
  };

  fetchStatus();
  if (interval) return setInterval(fetchStatus, interval);
  return null;
}
