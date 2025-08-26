const WebSocket = require('ws');

// Allow the WebSocket URL to be provided via the `WS_URL` environment variable
// or a command-line argument. Fall back to localhost if neither is set.
const url = process.env.WS_URL || process.argv[2] || 'ws://localhost:4455';
const ws = new WebSocket(url);

ws.on('open', () => { console.log(`✅ CONNECTED to ${url}`); ws.close(); });
ws.on('error', err => { console.error('❌ ERROR:', err); process.exit(0); });
ws.on('close', () => { console.warn('⚠️ DISCONNECTED'); process.exit(0); });
setTimeout(() => process.exit(0), 5000);  // safety timeout
