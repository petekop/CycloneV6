(function () {
  const bar = document.getElementById("progress-bar");
  const txt = document.getElementById("status-text");

  async function poll() {
    try {
      const r = await fetch("/status?ts=" + Date.now());
      const j = await r.json();
      const pct = Math.floor((j.step / Math.max(j.total || 1, 1)) * 100);
      if (bar) bar.style.width = pct + "%";
      if (txt) txt.textContent = (j.message ? (pct + "% — " + j.message) : (pct + "%"));
      if (j.done) { location.href="/index"; return; }
    } catch (e) { /* ignore, keep polling */ }
    setTimeout(poll, 500);
  }
  poll();

  // boot.html calls this on the Start button
  window.startBoot = async function startBoot() {
    try { await fetch("/api/start", { method: "POST" }); } catch (e) {}
  };
})();
