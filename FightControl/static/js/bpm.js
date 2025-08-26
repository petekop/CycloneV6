// bpm.js

/**
 * Start polling for BPM data from the given base URL.
 *
 * @param {string} baseUrl - Base URL for the live JSON endpoints
 * @param {number} interval - Polling interval in milliseconds
 * @param {Function|null} callback - Optional callback invoked with the
 *                                   parsed JSON for red and blue corners
 * @returns {number} interval ID that can be cleared via stopBpmPolling
 */
export function startBpmPolling(baseUrl = '/live-json', interval = 1000, callback = null) {
  async function fetchAndUpdate() {
    try {
      const [redRes, blueRes] = await Promise.all([
        fetch(`${baseUrl}/red_bpm`).then(r => r.json()),
        fetch(`${baseUrl}/blue_bpm`).then(r => r.json()),
      ]);

      if (callback) callback({ red: redRes, blue: blueRes });
    } catch (err) {
      console.error("💥 BPM fetch error:", err);
    }
  }

  fetchAndUpdate();
  return setInterval(fetchAndUpdate, interval);
}

/**
 * Stop an active BPM polling interval created by startBpmPolling.
 *
 * @param {number} id - ID returned from startBpmPolling
 */
export function stopBpmPolling(id) {
  clearInterval(id);
}
