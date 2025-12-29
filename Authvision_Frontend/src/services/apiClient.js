import { useAuthStore } from '../store/authStore';

class ApiClient {
  constructor() {
    this.baseURL = '';
    this.accessToken = null;
    this._configPromise = null;
  }

  async init(config) {
    this.baseURL = config.api.baseURL;
  }

  async _loadConfig() {
    if (this._configPromise) return this._configPromise;
    this._configPromise = (async () => {
      if (typeof window !== 'undefined' && window.__APP_CONFIG__) return window.__APP_CONFIG__;
      try {
        const resp = await fetch('/config.json');
        if (!resp.ok) throw new Error('failed to load config');
        return await resp.json();
      } catch (e) {
        return { api: { baseURL: '' } };
      }
    })();
    return this._configPromise;
  }

  async _ensureConfig() {
    if (this.baseURL) return;
    const cfg = await this._loadConfig();
    if (cfg && cfg.api && cfg.api.baseURL) this.baseURL = cfg.api.baseURL;
  }

  async request(endpoint, options = {}) {
    await this._ensureConfig();
    const url = `${this.baseURL}${endpoint}`;
    console.log('API request:', (options.method || 'GET'), url, { bodyIsFormData: options.body instanceof FormData });
    
    // Prepare headers
    const headers = {
      ...options.headers,
    };

    // Add Authorization header if token exists (except for login)
    if (this.accessToken && !endpoint.includes('/auth/login')) {
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

      const response = await fetch(url, config);
      console.log('API response:', response.status, url);

      // Handle token expiration
      if (response.status === 401) {
        const refreshed = await useAuthStore.getState().refreshTokens();
        if (refreshed) {
          // Update token and retry
          this.accessToken = useAuthStore.getState().accessToken;
          headers['Authorization'] = `Bearer ${this.accessToken}`;
          
          // Retry the request
          const retryConfig = { ...config, headers };
          if (options.body && !(options.body instanceof FormData)) {
            retryConfig.body = JSON.stringify(options.body);
          }
          
          const retryResponse = await fetch(url, retryConfig);
          if (!retryResponse.ok) {
            throw new Error(`HTTP error! status: ${retryResponse.status}`);
          }
          return await retryResponse.json();
        } else {
          // Refresh failed, logout user
          useAuthStore.getState().logout();
          throw new Error('Authentication failed');
        }
      }

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      // Try parsing JSON, but fall back to text if response isn't JSON
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        return await response.json();
      }
      try {
        return await response.json();
      } catch (_e) {
        return await response.text();
      }
    } catch (error) {
      console.error('API request failed:', error);
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

  // ==================== LOGOUT ====================
  async logout(refreshToken) {
    const form = new FormData();
    form.append('refresh_token', refreshToken);
    return this.apiPostForm('/auth/logout', form);
  }

  // 🆕 ==================== SEMESTER-BASED ATTENDANCE ====================
  async getStudentsBySemester(semester) {
    // OpenAPI exposes students listing with semester as query param
    return this.apiGet(`/students/list?semester=${encodeURIComponent(semester)}`);
  }

  async validateStudentSemester(studentId, semester) {
    return this.apiGet(`/students/${studentId}/validate-semester?semester=${semester}`);
  }

  async markSubjectAttendance(attendanceData) {
    // Backend OpenAPI does not specify a dedicated mark endpoint; keep existing call if backend supports it.
    return this.apiPost('/attendance/mark-subject', attendanceData);
  }

  async getSubjectAttendance(subjectId, date = null) {
    const query = date ? `?date=${date}` : '';
    return this.apiGet(`/attendance/subject/${subjectId}${query}`);
  }

  // 🆕 ==================== ATTENDANCE SESSIONS ====================
  async createAttendanceSession(sessionData) {
    // Backend expects form fields on POST /attendance/start
    // sessionData should contain: subject, department, semester, section, stream_name
    const fd = new FormData();
    if (sessionData.subject !== undefined) fd.append('subject', String(sessionData.subject));
    if (sessionData.department !== undefined) fd.append('department', String(sessionData.department));
    if (sessionData.semester !== undefined) fd.append('semester', String(sessionData.semester));
    if (sessionData.section !== undefined) fd.append('section', String(sessionData.section));
    if (sessionData.stream_name !== undefined) fd.append('stream_name', String(sessionData.stream_name));
    if (sessionData.stream !== undefined) fd.append('stream_name', String(sessionData.stream));
    return this.apiPostForm('/attendance/start', fd);
  }

  async endAttendanceSession() {
    // Backend uses POST /attendance/stop without body
    return this.apiPost('/attendance/stop', {});
  }

  async getActiveSessions() {
    // Backend exposes /attendance/status
    return this.apiGet('/attendance/status');
  }

  // 🆕 ==================== SUBJECT MANAGEMENT ====================
  async getSubjects() {
    // OpenAPI path: /subjects/list
    return this.apiGet('/subjects/list');
  }

  async getDepartments() {
    // Try departments endpoint, otherwise derive from subjects
    try {
      const resp = await this.apiGet('/departments/list');
      if (Array.isArray(resp)) return resp;
      if (resp && resp.departments) return resp.departments;
    } catch (e) {
      // ignore and fallback
    }

    // Fallback: fetch subjects and extract unique departments
    try {
      const subs = await this.getSubjects();
      const list = Array.isArray(subs) ? subs : (subs.subjects || []);
      const set = new Set(list.map(s => (s.department || s.dept || '').toString()).filter(Boolean));
      return Array.from(set).sort();
    } catch (e) {
      return ['CSE', 'ECE', 'ME', 'EEE'];
    }
  }

  async createSubject(subjectData) {
    // OpenAPI path: POST /subjects/create
    // Backend accepts form fields for subject creation; send as FormData
    const fd = new FormData();
    if (subjectData.code !== undefined) fd.append('code', String(subjectData.code));
    if (subjectData.name !== undefined) fd.append('name', String(subjectData.name));
    if (subjectData.department !== undefined) fd.append('department', String(subjectData.department));
    if (subjectData.semester !== undefined) fd.append('semester', String(subjectData.semester));
    return this.apiPostForm('/subjects/create', fd);
  }

  async updateSubject(subjectId, subjectData) {
    // OpenAPI exposes POST /subjects/modify with target_code
    // Use FormData to match backend expectation
    const fd = new FormData();
    fd.append('target_code', String(subjectId));
    if (subjectData.code !== undefined) fd.append('code', String(subjectData.code));
    if (subjectData.name !== undefined) fd.append('name', String(subjectData.name));
    if (subjectData.department !== undefined) fd.append('department', String(subjectData.department));
    if (subjectData.semester !== undefined) fd.append('semester', String(subjectData.semester));
    return this.apiPostForm('/subjects/modify', fd);
  }

  async deleteSubject(subjectId) {
    // OpenAPI exposes POST /subjects/delete with target_code
    const fd = new FormData();
    fd.append('target_code', String(subjectId));
    return this.apiPostForm('/subjects/delete', fd);
  }

  async getSubjectsBySemester(semester) {
    return this.apiGet(`/subjects/list?semester=${encodeURIComponent(semester)}`);
  }

  // Fetch per-subject summary (attendance per student) used by frontend filters
  async getSubjectSummary(subjectIdentifier, opts = {}) {
    // Backend path: /reports/subject/{subject_identifier}/summary
    // opts can include department, semester, section to scope the summary
    const qs = new URLSearchParams()
    if (opts.department) qs.append('department', opts.department)
    if (opts.semester) qs.append('semester', opts.semester)
    if (opts.section) qs.append('section', opts.section)
    const qstr = qs.toString()
    return this.apiGet(`/reports/subject/${encodeURIComponent(subjectIdentifier)}/summary${qstr ? `?${qstr}` : ''}`);
  }

  // ==================== STUDENT MANAGEMENT ====================
  async createStudent(studentData) {
    // OpenAPI: POST /students/create
    return this.apiPost('/students/create', studentData);
  }

  async enrollStudent(studentId, formData) {
    // Backend endpoint: POST /students/{reg_no}/enroll-photos
    return this.apiPostForm(`/students/${studentId}/enroll-photos`, formData);
  }

  async getStudent(studentId) {
    return this.apiGet(`/students/${studentId}`);
  }

  async getAllStudents(filters = {}) {
    const queryParams = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') queryParams.append(key, value);
    });
    const qs = queryParams.toString();
    // OpenAPI: GET /students/list
    return this.apiGet(`/students/list${qs ? `?${qs}` : ''}`);
  }

  async getStudentAttendance(studentId) {
    // OpenAPI: GET /reports/student/{reg_no}/attendance
    return this.apiGet(`/reports/student/${encodeURIComponent(studentId)}/attendance`);
  }

  async getLowAttendanceStudents(threshold = 75) {
    return this.apiGet(`/students/low-attendance?threshold=${threshold}`);
  }

  // ==================== NOTIFICATIONS / EMAILS ====================
  async sendBulkLowAttendanceEmails(threshold = 75) {
    // Attempts to trigger backend bulk low-attendance emails
    return this.apiPost('/notifications/low-attendance', { threshold });
  }

  async sendCustomEmail(target = 'all', subject = '', body = '', attachments = []) {
    // Generic email sending endpoint
    return this.apiPost('/notifications/send', { target, subject, body, attachments });
  }

  async sendLowAttendanceEmail(studentId, message = '') {
    return this.apiPost(`/notifications/low-attendance/${studentId}`, { message });
  }

  // ==================== ATTENDANCE & REPORTS ====================
  async getAttendanceStats(timeframe = 'month') {
    // Dashboard stats are provided by /reports/stats in the backend
    return this.apiGet(`/reports/stats?timeframe=${timeframe}`);
  }

  async exportAttendanceReport(format = 'csv', filters = {}) {
    const queryParams = new URLSearchParams({ format });
    Object.entries(filters).forEach(([key, value]) => {
      if (value) queryParams.append(key, value);
    });
    // Backend provides several download endpoints; keep a generic export endpoint if available
    return this.apiGet(`/reports/export?${queryParams.toString()}`);
  }

  // 🆕 ==================== FACE RECOGNITION ATTENDANCE ====================
  async recognizeFaceForAttendance(imageData, sessionToken) {
    // Function not available on backend (no /recognition/attend route). Commented out.
    throw new Error('Function not available: /recognition/attend endpoint not implemented on backend');
  }

  // ==================== SYSTEM & ADMIN ====================
  async getSystemStatus() {
    return this.apiGet('/system/status');
  }

  async getUsers() {
    return this.apiGet('/users');
  }

  async getMe() {
    return this.apiGet('/auth/me');
  }

  async getFacultyList() {
    return this.apiGet('/faculty/list');
  }

  async createFaculty(facultyData) {
    // facultyData: { username, name, department, password }
    const fd = new FormData()
    if (facultyData.username !== undefined) fd.append('username', String(facultyData.username))
    if (facultyData.name !== undefined) fd.append('name', String(facultyData.name))
    if (facultyData.department !== undefined) fd.append('department', String(facultyData.department))
    if (facultyData.password !== undefined) fd.append('password', String(facultyData.password))
    return this.apiPostForm('/faculty/create', fd)
  }

  async createUser(userData) {
    return this.apiPost('/users', userData);
  }

  async getDashboardStats() {
    return this.apiGet('/reports/stats');
  }

  setAccessToken(token) {
    this.accessToken = token;
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

  // ==================== STREAMING ====================
  async startStream({ name, url, keyframe_interval = null }) {
    // Backend expects form fields (Form(...)) for start endpoint
    const fd = new FormData();
    if (name !== undefined && name !== null) fd.append('name', String(name));
    if (url !== undefined && url !== null) fd.append('url', String(url));
    if (keyframe_interval !== null && keyframe_interval !== undefined) fd.append('keyframe_interval', String(keyframe_interval));
    return this.apiPostForm('/stream/start', fd);
  }

  async stopStream(name) {
    const fd = new FormData();
    fd.append('name', String(name));
    return this.apiPostForm('/stream/stop', fd);
  }

  async listStreams() {
    return this.apiGet('/stream/list');
  }

  async getStreamSnapshotImage(name) {
    // Returns image bytes as JSON currently; caller may need to request blob directly
    return this.apiGet(`/stream/${encodeURIComponent(name)}/snapshot_image`);
  }

  async getRecentAttendance() {
    return this.apiGet('/attendance/recent');
  }
}

export const apiClient = new ApiClient();