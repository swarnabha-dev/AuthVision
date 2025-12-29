import { useAuthStore } from '../store/authStore'

class WebSocketClient {
  constructor() {
    // Allow multiple sockets (attendance + per-stream)
    this.sockets = new Map(); // key -> WebSocket
    this.reconnectAttempts = {};
    this.maxReconnectAttempts = 5;
    this.listeners = new Map();
    this.isConnected = false; // overall state
  }

  async connect() {
    // Default: connect to recognition/events websocket
    // Read websocket base from config.json if available, fallback to hardcoded
    const cfg = window.__APP_CONFIG__ || await (await fetch('/config.json').then(r => r.json()).catch(() => ({})));
    let WS_URL = cfg.websocket && cfg.websocket.url ? cfg.websocket.url.replace(/\/$/, '') : 'ws://localhost:8000';
    // If config contains a base that already ends with '/ws', strip it to avoid duplication
    WS_URL = WS_URL.replace(/\/ws$/, '');
    const token = useAuthStore.getState().accessToken || null;
    const defaultPath = '/attendance/live';

    try {
      const url = `${WS_URL}${defaultPath}${token ? `?token=${token}` : ''}`;
      this._openSocket(url, (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📨 WebSocket message:', data);
          if (data.type === 'recognition_event') this.emit('recognition', data);
          else if (data.type === 'attendance_marked') this.emit('attendance', data);
          else if (data.type === 'system_status') this.emit('status', data);
          else this.emit('message', data);
        } catch (error) {
          console.error('❌ WebSocket message parsing error:', error);
        }
      });
    } catch (error) {
      console.error('❌ WebSocket connection failed:', error);
    }
  }

  // Generic internal opener to reduce duplication
  _openSocket(url, onMessage, key = 'default') {
    // Close existing socket with same key
    if (this.sockets.has(key)) {
      try { this.sockets.get(key).close(1000, 'Reopening'); } catch (e) {}
      this.sockets.delete(key);
    }

    const ws = new WebSocket(url);
    this.sockets.set(key, ws);
    this.reconnectAttempts[key] = 0;

    ws.onopen = () => {
      console.log('🔌 WebSocket connected', url, key);
      this.isConnected = true;
      this.reconnectAttempts[key] = 0;
      this.emit('connected', { key, connected: true });
    };

    ws.onmessage = onMessage;

    ws.onclose = () => {
      console.log('🔌 WebSocket disconnected', key);
      this.sockets.delete(key);
      this.emit('connected', { key, connected: false });
      this.attemptReconnect(key, url, onMessage);
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error, key);
      this.emit('error', { key, error });
    };
  }

  // Subscribe to events
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  clearListeners(event) {
    if (this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
  }

  // Emit events to listeners
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => callback(data));
    }
  }

  connectStream(streamName) {
    const cfg = window.__APP_CONFIG__ || null;
    let WS_URL = cfg && cfg.websocket && cfg.websocket.url ? cfg.websocket.url.replace(/\/$/, '') : 'ws://localhost:8000';
    WS_URL = WS_URL.replace(/\/ws$/, '');
    const token = useAuthStore.getState().accessToken || null;
    const path = `/stream/ws/${encodeURIComponent(streamName)}`;
    if (!token) {
      console.error('❌ connectStream requires an access token in localStorage under "access_token"');
      return;
    }
    try {
      const url = `${WS_URL}${path}?token=${token}`;
      const key = `stream:${streamName}`;
      this._openSocket(url, (event) => {
        try {
          if (typeof event.data === 'string') {
            const data = JSON.parse(event.data);
            this.emit('message', { key: key, data });
          } else {
            this.emit('binary', { key: key, data: event.data });
          }
        } catch (e) {
          this.emit('binary', { key: key, data: event.data });
        }
      }, key);
    } catch (error) {
      console.error('❌ WebSocket connection failed:', error, 'url:', `${WS_URL}${path}`);
    }
  }

  connectAttendanceLive() {
    // Connect to /attendance/live (no token query expected; uses ws manager to accept connection)
    const cfg = window.__APP_CONFIG__ || null;
    let WS_URL = cfg && cfg.websocket && cfg.websocket.url ? cfg.websocket.url.replace(/\/$/, '') : 'ws://localhost:8000';
    WS_URL = WS_URL.replace(/\/ws$/, '');
    const token = useAuthStore.getState().accessToken || null;
    const path = '/attendance/live';
    try {
      const url = token ? `${WS_URL}${path}?token=${token}` : `${WS_URL}${path}`;
      const key = 'attendance';
      this._openSocket(url, (event) => {
        try {
          const data = JSON.parse(event.data);
          this.emit('attendance', { key, data });
        } catch (e) {
          console.error('❌ WebSocket message parsing error:', e);
        }
      }, key);
    } catch (error) {
      console.error('❌ WebSocket connection failed:', error);
    }
  }

  // Send data to a specific socket (by key)
  send(data, socketKey = 'attendance') {
    console.log('websocketClient.send', socketKey, data);
    const ws = this.sockets.get(socketKey);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    } else {
      console.warn('⚠️ WebSocket not connected on', socketKey, 'cannot send:', data);
    }
  }

  // Start recognition on a stream (sends command over attendance socket)
  startRecognition(streamUrl, modality = 'face') {
    this.send({
      action: 'start_recognition',
      stream_url: streamUrl,
      modality: modality,
      timestamp: new Date().toISOString()
    }, 'attendance');
  }

  // Stop recognition
  stopRecognition(streamUrl) {
    this.send({
      action: 'stop_recognition',
      stream_url: streamUrl,
      timestamp: new Date().toISOString()
    }, 'attendance');
  }

  // Attempt reconnect for a specific key (used by _openSocket onclose)
  attemptReconnect(key, url, onMessage) {
    if (!this.reconnectAttempts[key]) this.reconnectAttempts[key] = 0;
    if (this.reconnectAttempts[key] < this.maxReconnectAttempts) {
      this.reconnectAttempts[key]++;
      const delay = Math.min(3000 * this.reconnectAttempts[key], 30000);
      console.log(`🔄 Reconnecting ${key} in ${delay}ms... Attempt ${this.reconnectAttempts[key]}`);
      setTimeout(() => {
        try {
          this._openSocket(url, onMessage, key);
        } catch (e) {
          console.error('❌ Reconnect failed', e);
        }
      }, delay);
    } else {
      console.error('❌ Max reconnection attempts reached for', key);
      this.emit('reconnection_failed', { key, failed: true });
    }
  }

  // Disconnect a specific socket or all
  disconnect(key = null) {
    if (key) {
      const ws = this.sockets.get(key);
      if (ws) {
        try { ws.close(1000, 'Manual disconnect'); } catch (e) {}
        this.sockets.delete(key);
      }
    } else {
      for (const [k, ws] of this.sockets.entries()) {
        try { ws.close(1000, 'Manual disconnect'); } catch (e) {}
      }
      this.sockets.clear();
    }
    this.isConnected = false;
  }

  getConnectionStatus(key = null) {
    if (key) return this.sockets.has(key);
    return this.isConnected;
  }
}

// Singleton instance
export const websocketClient = new WebSocketClient();