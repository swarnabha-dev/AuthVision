import { apiClient } from './apiClient'

class WebSocketClient {
  constructor(options = {}) {
    this.socket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.listeners = new Map();
    this.isConnected = false;
  // optional config (guard process.env for browser)
  const envBase = (typeof process !== 'undefined' && process.env && process.env.REACT_APP_API_BASE) ? process.env.REACT_APP_API_BASE : null
  const envWsPath = (typeof process !== 'undefined' && process.env && process.env.REACT_APP_WS_PATH) ? process.env.REACT_APP_WS_PATH : null
  this.baseUrl = options.baseUrl || envBase || ''
  this.wsPath = options.wsPath || envWsPath || '/api/v1/backend/ws/events'
    // HTTP endpoint to fetch recognition history/results (GET)
    this.historyEndpoint = options.historyEndpoint || '/api/v1/backend/recognitions'
  }

  connect() {
    const token = apiClient.accessToken || localStorage.getItem('access_token') || '';
    // Build WebSocket URL: prefer explicit env var, else combine baseUrl + wsPath
  const envWsUrl = (typeof process !== 'undefined' && process.env && process.env.REACT_APP_WS_URL) ? process.env.REACT_APP_WS_URL : null
  let WS_URL = envWsUrl || null
    if (!WS_URL) {
      const protocol = (this.baseUrl && this.baseUrl.startsWith('https')) ? 'wss' : 'ws'
      const base = this.baseUrl || 'http://localhost:8000'
      // transform http(s)://host[:port] to ws(s)://host[:port]
      try {
        const u = new URL(base)
        WS_URL = `${protocol}://${u.host}${this.wsPath}`
      } catch (e) {
        WS_URL = `ws://localhost:8000${this.wsPath}`
      }
    }

    try {
      // Attach token as query param for backend auth (backend expects ?token=...)
      const sep = WS_URL.includes('?') ? '&' : '?'
      this.socket = new WebSocket(`${WS_URL}${sep}token=${encodeURIComponent(token || '')}`);
      
      this.socket.onopen = () => {
        console.log('🔌 WebSocket connected for real-time recognition');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.emit('connected', true);
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Only forward recognition events by default to reduce noise
          if (data && data.type === 'recognition_event') {
            this.emit('recognition', data);
          } else {
            // still emit raw messages for advanced listeners
            this.emit('raw', data);
          }
        } catch (error) {
          console.error('❌ WebSocket message parsing error:', error);
        }
      };

      this.socket.onclose = () => {
        console.log('🔌 WebSocket disconnected');
        this.isConnected = false;
        this.emit('connected', false);
        this.attemptReconnect();
      };

      this.socket.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        this.emit('error', error);
      };
    } catch (error) {
      console.error('❌ WebSocket connection failed:', error);
    }
  }

  // Subscribe to events
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  // Shorthand for subscribing to recognition events specifically
  onRecognition(callback) {
    this.on('recognition', callback)
  }

  // Emit events to listeners
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => callback(data));
    }
  }

  // Send data to backend
  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    } else {
      console.warn('⚠️ WebSocket not connected, cannot send:', data);
    }
  }

  // Fetch recognition results (HTTP) from backend history endpoint.
  // params: object -> converted to query string (e.g., { stream_url, since, limit })
  async fetchRecognitionResults(params = {}) {
    const qs = Object.keys(params).map(k => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`).join('&')
    const endpoint = this.historyEndpoint + (qs ? `?${qs}` : '')
    try {
      return await apiClient.apiGet(endpoint)
    } catch (err) {
      console.error('❌ fetchRecognitionResults error:', err)
      return { error: true, message: err.message }
    }
  }

  // Start recognition on a stream
  startRecognition(streamUrl, modality = 'face') {
    this.send({
      action: 'start_recognition',
      stream_url: streamUrl,
      modality: modality,
      timestamp: new Date().toISOString()
    });
  }

  // Stop recognition
  stopRecognition(streamUrl) {
    this.send({
      action: 'stop_recognition',
      stream_url: streamUrl,
      timestamp: new Date().toISOString()
    });
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(3000 * this.reconnectAttempts, 30000);
      
      console.log(`🔄 Reconnecting in ${delay}ms... Attempt ${this.reconnectAttempts}`);
      
      setTimeout(() => {
        this.connect();
      }, delay);
    } else {
      console.error('❌ Max reconnection attempts reached');
      this.emit('reconnection_failed', true);
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close(1000, 'Manual disconnect');
      this.socket = null;
    }
    this.isConnected = false;
    this.reconnectAttempts = 0;
  }

  getConnectionStatus() {
    return this.isConnected;
  }
}

// Singleton instance
export const websocketClient = new WebSocketClient();