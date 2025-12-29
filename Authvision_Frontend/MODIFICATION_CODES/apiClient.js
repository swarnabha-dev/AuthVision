// Lightweight API client with built-in auth (register/login/refresh) for local dev
class ApiClient {
  constructor() {
    // baseURL should include the API root (e.g. http://localhost:8000/api/v1/backend)
    this.baseURL = '';
    this.accessToken = null;
  }

  async init(config) {
    // IMPORTANT: only set baseURL when provided in config (do not fallback to hardcoded defaults here)
    if (config && config.api && config.api.baseURL) {
      this.baseURL = config.api.baseURL
      console.info('[apiClient] baseURL set to', this.baseURL)
    } else {
      console.info('[apiClient] init called without baseURL in config; apiClient.baseURL remains unset')
    }

    // Load persisted tokens if present
    try { this.accessToken = localStorage.getItem('access_token') || this.accessToken } catch (e) {}
    try { this.refreshToken = localStorage.getItem('refresh_token') || this.refreshToken } catch (e) {}

    // If we have no access token but the app provided default-login config, attempt to register/login
    // Config may include defaultAdmin: { username, password }
    if (!this.accessToken && config && config.api && config.api.defaultAdmin) {
      const creds = config.api.defaultAdmin
      // try register (ignore errors), then login
      try {
        await this._post('/auth/register', { username: creds.username, password: creds.password, role: creds.role || 'admin' })
      } catch (e) {
        // ignore register errors (user may already exist)
      }
      try {
        await this.login(creds.username, creds.password)
      } catch (e) {
        console.warn('[apiClient] default admin login failed:', e && e.message ? e.message : e)
      }
    }
  }

  // ---------- Internal low-level helpers used by init/login/register/refresh ----------
  async _fetchRaw(url, opts = {}) {
    return fetch(url, opts)
  }

  async _post(path, body) {
    // convenience JSON POST used during init/auth flows (bypass auth header behavior)
    if (!this.baseURL) throw new Error('apiClient.baseURL is not set')
    const url = new URL(path.startsWith('/') ? path : '/' + path, this.baseURL).toString()
    const res = await this._fetchRaw(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    const text = await res.text()
    try { return JSON.parse(text) } catch (e) { return text }
  }

  async request(endpoint, options = {}) {
    // Normalize endpoint: ensure calls target /api/v1/backend when a relative endpoint is passed
    let ep = endpoint
    if (typeof ep === 'string' && !ep.startsWith('http') && !ep.startsWith('/api/v1/backend')) {
      // prefix backend base path
      ep = '/api/v1/backend' + (ep.startsWith('/') ? ep : '/' + ep)
    }

    // Build full URL safely
    let url = ep
    try {
      // If endpoint is relative, combine with baseURL
      const u = new URL(ep, this.baseURL)
      url = u.toString()
    } catch (e) {
      // fallback to simple concat
      url = `${this.baseURL.replace(/\/$/, '')}/${ep.replace(/^\//, '')}`
    }
    
    // Prepare headers
    const headers = {
      ...options.headers,
    };

    // Refresh local token cache from localStorage if missing
    if (!this.accessToken) {
      try { this.accessToken = localStorage.getItem('access_token') || null } catch (e) { this.accessToken = null }
    }
    // Attach Authorization header for all non-auth endpoints
    const isAuthEndpoint = typeof endpoint === 'string' && (/\/auth\//.test(endpoint) || endpoint.includes('/auth/login') || endpoint.includes('/auth/register') || endpoint.includes('/auth/refresh'))
    if (this.accessToken && !isAuthEndpoint) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    // Only add Content-Type for non-form-data requests
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    try {
      const config = {
        headers,
        ...options,
      };

      // Stringify body if it's not FormData
      if (options.body && !(options.body instanceof FormData)) {
        config.body = JSON.stringify(options.body);
      }

      // Debug: show final request URL and headers (helps diagnose connection/CORS/auth)
      try {
        console.debug('[apiClient] Request ->', { method: config.method || 'GET', url, headers })
      } catch (e) {}

      const response = await fetch(url, config);

      // Handle token expiration (401) by attempting refresh once
      if (response.status === 401 && !isAuthEndpoint) {
        const refreshed = await this.refreshTokens();
        if (refreshed) {
          // Update header and retry once
          headers['Authorization'] = `Bearer ${this.accessToken}`;
          const retryConfig = { ...config, headers };
          if (options.body && !(options.body instanceof FormData)) retryConfig.body = JSON.stringify(options.body);
          const retryResponse = await fetch(url, retryConfig);
          if (!retryResponse.ok) {
            const errTxt = await retryResponse.text();
            throw new Error(`HTTP error after refresh! status: ${retryResponse.status}, message: ${errTxt}`);
          }
          return await retryResponse.json();
        }
        // refresh failed: clear tokens
        this.clearTokens();
        throw new Error('Authentication required (refresh failed)');
      }

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      // Try to parse JSON, otherwise return text
      const txt = await response.text();
      try { return JSON.parse(txt) } catch (e) { return txt }
    } catch (error) {
      // Improve error message for common network/CORS issues
      const msg = error && error.message ? error.message : String(error)
      console.error('[apiClient] API request failed:', msg, { endpoint, url: (typeof url !== 'undefined' ? url : endpoint) })
      // Provide a friendlier hint for developers
      if (msg === 'Failed to fetch' || /NetworkError|TypeError/.test(msg)) {
        throw new Error(`Network or CORS error when fetching ${endpoint}. Is the backend running at ${this.baseURL || '[unset]' } and reachable from the browser? Original: ${msg}`)
      }
      throw error;
    }
  }

  // ==================== AUTHENTICATION ====================
  async apiGet(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  }

  async apiPost(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: data,
    });
  }

  async apiPut(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: data,
    });
  }

  async apiDelete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }

  async apiPostForm(endpoint, formData) {
    return this.request(endpoint, {
      method: 'POST',
      body: formData,
    });
  }

  // ==================== AUTH HELPERS (register/login/refresh) ====================
  async login(username, password) {
    if (!this.baseURL) throw new Error('apiClient.baseURL is not set')
    const url = new URL('/auth/login', this.baseURL).toString()
    const res = await this._fetchRaw(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) })
    const txt = await res.text()
    if (!res.ok) throw new Error(`Login failed: ${res.status} ${txt}`)
    let json
    try { json = JSON.parse(txt) } catch (e) { throw new Error('Invalid login response') }
    // Expect { access_token, refresh_token }
    if (json.access_token) {
      this.setAccessToken(json.access_token)
    }
    if (json.refresh_token) {
      this.setRefreshToken(json.refresh_token)
    }
    return json
  }

  async refreshTokens() {
    if (!this.refreshToken) {
      try { this.refreshToken = localStorage.getItem('refresh_token') || null } catch (e) { this.refreshToken = null }
    }
    if (!this.refreshToken) return false
    try {
      const url = new URL('/auth/refresh', this.baseURL).toString()
      const res = await this._fetchRaw(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: this.refreshToken }) })
      const txt = await res.text()
      if (!res.ok) {
        console.warn('[apiClient] refreshTokens failed', res.status, txt)
        return false
      }
      const json = JSON.parse(txt)
      if (json.access_token) this.setAccessToken(json.access_token)
      if (json.refresh_token) this.setRefreshToken(json.refresh_token)
      return true
    } catch (e) {
      console.warn('[apiClient] refreshTokens error', e)
      return false
    }
  }

  clearTokens() {
    this.accessToken = null
    this.refreshToken = null
    try { localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token') } catch (e) {}
  }

  // 🆕 ==================== SEMESTER-BASED ATTENDANCE ====================
  async getStudentsBySemester(semester) {
    return this.apiGet(`/students/semester/${semester}`);
  }

  async validateStudentSemester(studentId, semester) {
    return this.apiGet(`/students/${studentId}/validate-semester?semester=${semester}`);
  }

  async markSubjectAttendance(attendanceData) {
    return this.apiPost('/attendance/mark-subject', attendanceData);
  }

  async getSubjectAttendance(subjectId, date = null) {
    const query = date ? `?date=${date}` : '';
    return this.apiGet(`/attendance/subject/${subjectId}${query}`);
  }

  // 🆕 ==================== ATTENDANCE SESSIONS ====================
  async createAttendanceSession(sessionData) {
    return this.apiPost('/attendance/sessions', sessionData);
  }

  async endAttendanceSession(sessionToken) {
    return this.apiPut(`/attendance/sessions/${sessionToken}/end`);
  }

  async getActiveSessions() {
    return this.apiGet('/attendance/sessions/active');
  }

  // 🆕 ==================== SUBJECT MANAGEMENT ====================
  async getSubjects() {
    return this.apiGet('/subjects');
  }

  async createSubject(subjectData) {
    return this.apiPost('/subjects', subjectData);
  }

  async updateSubject(subjectId, subjectData) {
    return this.apiPut(`/subjects/${subjectId}`, subjectData);
  }

  async deleteSubject(subjectId) {
    return this.apiDelete(`/subjects/${subjectId}`);
  }

  async getSubjectsBySemester(semester) {
    return this.apiGet(`/subjects/semester/${semester}`);
  }

  // ==================== STUDENT MANAGEMENT ====================
  async createStudent(studentData) {
    return this.apiPost('/students', studentData);
  }

  async enrollStudent(studentId, formData) {
    return this.apiPostForm(`/students/${studentId}/enroll`, formData);
  }

  async getStudent(studentId) {
    return this.apiGet(`/students/${studentId}`);
  }

  async getAllStudents(filters = {}) {
    const queryParams = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) queryParams.append(key, value);
    });
    const queryString = queryParams.toString();
    return this.apiGet(`/students${queryString ? `?${queryString}` : ''}`);
  }

  async getStudentAttendance(studentId) {
    return this.apiGet(`/students/${studentId}/attendance`);
  }

  async getLowAttendanceStudents(threshold = 75) {
    return this.apiGet(`/students/low-attendance?threshold=${threshold}`);
  }

  // ==================== ATTENDANCE & REPORTS ====================
  async getAttendanceStats(timeframe = 'month') {
    return this.apiGet(`/attendance/stats?timeframe=${timeframe}`);
  }

  async exportAttendanceReport(format = 'csv', filters = {}) {
    const queryParams = new URLSearchParams({ format });
    Object.entries(filters).forEach(([key, value]) => {
      if (value) queryParams.append(key, value);
    });
    return this.apiGet(`/reports/export?${queryParams.toString()}`);
  }

  // 🆕 ==================== FACE RECOGNITION ATTENDANCE ====================
  async recognizeFaceForAttendance(imageData, sessionToken) {
    return this.apiPost('/recognition/attend', {
      image_data: imageData,
      session_token: sessionToken
    });
  }

  // ==================== SYSTEM & ADMIN ====================
  async getSystemStatus() {
    return this.apiGet('/system/status');
  }

  async getUsers() {
    return this.apiGet('/users');
  }

  async createUser(userData) {
    return this.apiPost('/users', userData);
  }

  async getDashboardStats() {
    return this.apiGet('/dashboard/stats');
  }

  setAccessToken(token) {
    this.accessToken = token;
    try { localStorage.setItem('access_token', token) } catch (e) {}
  }

  setRefreshToken(token) {
    this.refreshToken = token
    try { localStorage.setItem('refresh_token', token) } catch (e) {}
  }

  // ==================== UTILITY METHODS ====================
  async healthCheck() {
    try {
      await this.apiGet('/health');
      return true;
    } catch (error) {
      return false;
    }
  }

  async uploadFile(file, onProgress = null) {
    const formData = new FormData();
    formData.append('file', file);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      if (onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            onProgress(percentComplete);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status === 200) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch (e) {
            resolve(xhr.responseText);
          }
        } else {
          reject(new Error(`Upload failed: ${xhr.statusText}`));
        }
      };

      xhr.onerror = () => reject(new Error('Upload failed'));
      
      xhr.open('POST', `${this.baseURL}/upload`);
      if (this.accessToken) {
        xhr.setRequestHeader('Authorization', `Bearer ${this.accessToken}`);
      }
      xhr.send(formData);
    });
  }
}

export const apiClient = new ApiClient();