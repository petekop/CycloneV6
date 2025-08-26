const redChartCtx = document.getElementById("redChart").getContext("2d");
const blueChartCtx = document.getElementById("blueChart").getContext("2d");
const redData = [];
const blueData = [];
const lastBpm = { red: 0, blue: 0 };

function getZoneColor(pct) {
  if (pct >= 0.9) return "red";
  if (pct >= 0.8) return "orange";
  if (pct >= 0.7) return "yellow";
  if (pct >= 0.6) return "limegreen";
  return "blue";
}

function showFallbackOverlay() {
  console.warn("Showing fallback overlay due to data fetch error");
  const roundDisplay = document.getElementById("roundDisplay");
  if (roundDisplay) roundDisplay.innerText = "Round --";
  const timerEl = document.getElementById("round-timer");
  if (timerEl) timerEl.innerText = "--:--";
  const timerContainer = document.getElementById("timerContainer");
  if (timerContainer) timerContainer.classList.remove("pulse");
  ["redBPM", "blueBPM"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.innerText = "-- bpm";
  });
}

function showRoundRings(current, total) {
  const container = document.getElementById("roundRings");
  if (!container) return;
  const rings = Array.from(
    { length: total },
    (_, i) =>
      `<span style="color:${i < current ? "limegreen" : "#444"}">●</span>`,
  ).join(" ");
  container.innerHTML = rings;
}

function mapToOverlay(state) {
  const mapping = {
    IDLE: "WAITING",
    ARMED: "WAITING",
    LIVE: "ACTIVE",
    ACTIVE: "ACTIVE",
    RESTING: "RESTING",
    PAUSED: "PAUSED",
    ENDED: "ENDED",
  };
  return mapping[state] || state;
}

function drawHRChart(ctx, data, maxHR, isMirrored) {
  ctx.clearRect(0, 0, 400, 120);
  if (isMirrored) {
    ctx.save();
    ctx.translate(400, 0);
    ctx.scale(-1, 1);
  }
  for (let i = 0; i < data.length; i++) {
    const bpm = data[i];
    const pct = maxHR > 0 ? bpm / maxHR : 0;
    const height = Math.min(100, pct * 100);
    const colour = getZoneColor(pct);
    ctx.fillStyle = colour;
    ctx.fillRect(i * 4, 120 - height, 3, height);
  }
  if (isMirrored) ctx.restore();
}

const restingHR = 60;
let regenMode = false;

async function getLiveHRData(color) {
  try {
    const res = await fetch(`/live-json/${color}_bpm`);
    const data = await res.json();
    if (!data.max_hr) data.max_hr = 180;
    return data;
  } catch (err) {
    console.error(`Failed to fetch ${color} BPM`, err);
    showFallbackOverlay();
    return { bpm: 0, max_hr: 180, status: "UNKNOWN" };
  }
}

function getHRZone(bpm) {
  if (bpm < 100) return "Green";
  if (bpm < 130) return "Yellow";
  if (bpm < 160) return "Orange";
  return "Red";
}

function updateGraph(color, bpm = 0, maxHR = 180, status = "UNKNOWN") {
  const isResting = status === "RESTING";
  let displayBpm = bpm;
  if (isResting) {
    if (!bpm) displayBpm = lastBpm[color] || 0;
  } else {
    lastBpm[color] = bpm;
  }
  const range = maxHR - restingHR;
  const effort = Math.max(
    0,
    Math.min(1, (displayBpm - restingHR) / (range || 1)),
  );
  let stamina = Math.max(0, Math.min(100, 100 - effort * 100));

  if (regenMode) stamina = Math.min(100, stamina + 0.25);

  const bar = document.getElementById(`${color}-bar`);
  if (bar) {
    bar.style.width = `${stamina}%`;
    bar.style.backgroundColor = stamina < 25 ? "orange" : "limegreen";
    bar.style.boxShadow = stamina < 25 ? "0 0 8px red" : "none";
  }

  const bpmLabel = document.getElementById(`${color}BPM`);
  if (bpmLabel)
    bpmLabel.innerText = `${displayBpm} bpm | ${Math.round(stamina)}%`;

  const statusEl = document.getElementById(`${color}Status`);
  if (statusEl) {
    statusEl.innerText = isResting ? "Resting" : "Active";
    statusEl.classList.toggle("resting", isResting);
  }

  const effortText = document.getElementById(`${color}-effort`);
  if (effortText) effortText.innerText = `${Math.round(effort * 100)}%`;

  const zoneText = document.getElementById(`${color}-zone`);
  if (zoneText) zoneText.innerText = `${getHRZone(bpm)} Zone`;

  const nameBar = document.getElementById(`${color}Name`);
  if (nameBar) {
    const zoneColor = getZoneColor(bpm / maxHR);
    nameBar.style.boxShadow = `0 0 10px ${zoneColor}`;
    nameBar.style.animation = stamina < 20 ? "flashRed 0.8s infinite" : "none";
  }

  if (color === "red") {
    redData.push(displayBpm);
    if (redData.length > 100) redData.shift();
    drawHRChart(redChartCtx, redData, maxHR, false);
  } else {
    blueData.push(displayBpm);
    if (blueData.length > 100) blueData.shift();
    drawHRChart(blueChartCtx, blueData, maxHR, true);
  }
}

setInterval(async () => {
  const red = await getLiveHRData("red");
  const blue = await getLiveHRData("blue");
  updateGraph("red", red.bpm, red.max_hr, red.status);
  updateGraph("blue", blue.bpm, blue.max_hr, blue.status);
}, 1000);

document.body.addEventListener("keydown", (e) => {
  if (e.key === "r") regenMode = !regenMode;
});

let currentStatus = null;

function updateRoundUI() {
  const roundDisplay = document.getElementById("roundDisplay");
  const timerEl = document.getElementById("round-timer");
  const timerContainer = document.getElementById("timerContainer");
  const liveBadge = document.getElementById("liveBadge");
  if (
    !currentStatus ||
    !roundDisplay ||
    !timerEl ||
    !liveBadge ||
    !timerContainer
  )
    return;

  const round = currentStatus.round || "--";
  const totalRounds = currentStatus.rounds || 5;
  roundDisplay.innerText = `Round ${round}`;

  const start = currentStatus.start_time
    ? new Date(currentStatus.start_time).getTime()
    : null;
  const now = Date.now();
  let remaining = 0;
  timerContainer.classList.remove("pulse");

  if (currentStatus.status === "ACTIVE" && start) {
    const elapsed = Math.floor((now - start) / 1000);
    remaining = Math.max(0, currentStatus.duration - elapsed);
    const mins = Math.floor(remaining / 60);
    const secs = String(remaining % 60).padStart(2, "0");
    timerEl.innerText = `${mins}:${secs}`;
    timerContainer.classList.add("pulse");
  } else if (currentStatus.status === "RESTING" && start) {
    // start_time for RESTING is already set when the rest period begins
    // so elapsed rest time is simply the difference between now and start
    const elapsed = Math.floor((now - start) / 1000);
    remaining = Math.max(0, currentStatus.rest - elapsed);
    const mins = Math.floor(remaining / 60);
    const secs = String(remaining % 60).padStart(2, "0");
    timerEl.innerText = `Rest: ${mins}:${secs}`;
  } else if (currentStatus.status === "WAITING") {
    const mins = Math.floor(currentStatus.duration / 60);
    const secs = String(currentStatus.duration % 60).padStart(2, "0");
    timerEl.innerText = `${mins}:${secs}`;
  } else {
    timerEl.innerText = "--:--";
  }

  if (currentStatus.status === "ACTIVE") {
    liveBadge.innerText = "LIVE";
    liveBadge.className = "live-badge";
  } else if (currentStatus.status === "RESTING") {
    liveBadge.innerText = "REST";
    liveBadge.className = "live-badge resting";
  } else if (currentStatus.status === "PAUSED") {
    liveBadge.innerText = "PAUSED";
    liveBadge.className = "live-badge paused";
  }

  showRoundRings(currentStatus.round || 1, totalRounds);
}

setInterval(async () => {
  try {
    const res = await fetch("/overlay/data/round_status.json");
    const json = await res.json();
    const overlayState = json.overlay_state || mapToOverlay(json.state);
    currentStatus = { ...json, status: overlayState };
    updateRoundUI();
  } catch (err) {
    console.error("Failed to fetch round status", err);
    showFallbackOverlay();
  }
}, 1000);

(async function updateFighterNames() {
  try {
    const res = await fetch("/overlay/data/current_fight.json");
    const data = await res.json();
    const red = data.red_fighter || "RORY";
    const blue = data.blue_fighter || "PETE";
    document.getElementById("redName").innerText = red.toUpperCase();
    document.getElementById("blueName").innerText = blue.toUpperCase();
  } catch {
    document.getElementById("redName").innerText = "RORY";
    document.getElementById("blueName").innerText = "PETE";
  }
})();
