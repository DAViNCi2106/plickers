/**
 * src/api/client.js
 * =================
 * HTTP client for FastAPI backend communication.
 * Handles token storage, auth headers, and automatic token refresh.
 */

const API_BASE = '/api/v1';

class ApiClient {
  constructor() {
    this.accessToken = localStorage.getItem('plickers_access_token');
    this.refreshToken = localStorage.getItem('plickers_refresh_token');
    this.user = JSON.parse(localStorage.getItem('plickers_user') || 'null');
  }

  setSession(accessToken, refreshToken, user) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    this.user = user;
    if (accessToken) localStorage.setItem('plickers_access_token', accessToken);
    else localStorage.removeItem('plickers_access_token');
    if (refreshToken) localStorage.setItem('plickers_refresh_token', refreshToken);
    else localStorage.removeItem('plickers_refresh_token');
    if (user) localStorage.setItem('plickers_user', JSON.stringify(user));
    else localStorage.removeItem('plickers_user');
  }

  clearSession() {
    this.setSession(null, null, null);
  }

  getToken() {
    return this.accessToken || localStorage.getItem('plickers_access_token') || '';
  }

  getSchoolId() {
    return this.user?.school_id || 1;
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...options.headers,
    };

    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    try {
      let response = await fetch(url, { ...options, headers });

      // Handle 401: attempt token refresh once
      if (response.status === 401 && !options._isRetry) {
        if (this.refreshToken) {
          const refreshed = await this.refreshAccessToken();
          if (refreshed) {
            headers['Authorization'] = `Bearer ${this.accessToken}`;
            response = await fetch(url, { ...options, headers, _isRetry: true });
          } else {
            this.clearSession();
            window.dispatchEvent(new CustomEvent('auth:expired'));
            throw new Error('Session expired. Please log in again.');
          }
        } else {
          this.clearSession();
          window.dispatchEvent(new CustomEvent('auth:expired'));
          throw new Error('Session expired. Please log in again.');
        }
      }

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const message = data.detail || data.error || data.message || `Request failed (${response.status})`;
        const error = new Error(typeof message === 'string' ? message : JSON.stringify(message));
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      console.error(`[API ERROR] ${options.method || 'GET'} ${url}:`, err);
      throw err;
    }
  }

  async refreshAccessToken() {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      this.accessToken = data.access_token;
      if (data.refresh_token) this.refreshToken = data.refresh_token;
      localStorage.setItem('plickers_access_token', this.accessToken);
      if (data.refresh_token) localStorage.setItem('plickers_refresh_token', this.refreshToken);
      return true;
    } catch {
      return false;
    }
  }

  // ── Auth Endpoints ────────────────────────────────────────────────────────
  async login(email, password) {
    const raw = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username: email, email, password }),
    });
    const tokenData = raw.data || raw;
    this.accessToken = tokenData.access_token;
    this.refreshToken = tokenData.refresh_token;
    localStorage.setItem('plickers_access_token', this.accessToken);
    if (this.refreshToken) {
      localStorage.setItem('plickers_refresh_token', this.refreshToken);
    }

    // Fetch user profile
    const me = await this.getMe();
    me.email = email;
    me.full_name = me.full_name || (email.includes('anil') ? 'Anil Kumar' : 'Teacher');
    this.user = me;
    localStorage.setItem('plickers_user', JSON.stringify(me));
    return { token: tokenData, user: me };
  }

  async getMe() {
    const res = await this.request('/auth/me');
    return res.data || res;
  }

  // ── School Data ───────────────────────────────────────────────────────────
  async getClasses() {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/classes`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  async getClass(classId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/classes/${classId}`);
    return res.data || res;
  }

  async getSections(classId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/classes/${classId}/sections`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  async getStudents(params = {}) {
    const schoolId = this.getSchoolId();
    const cleanParams = Object.fromEntries(
      Object.entries(params).filter(([_, v]) => v !== null && v !== undefined && v !== '')
    );
    const query = new URLSearchParams(cleanParams).toString();
    const res = await this.request(`/schools/${schoolId}/students${query ? `?${query}` : ''}`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  // ── Question Sets & Questions ─────────────────────────────────────────────
  async getQuestionSets() {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/question-sets`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  async getQuestionSet(id) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/question-sets/${id}`);
    return res.data || res;
  }

  async createQuestionSet(payload) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/question-sets`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data || res;
  }

  async addQuestion(questionSetId, payload) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/question-sets/${questionSetId}/questions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data || res;
  }

  async getQuestions(questionSetId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/question-sets/${questionSetId}/questions`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  // ── Quiz Sessions ─────────────────────────────────────────────────────────
  async getQuizSessions() {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/quiz-sessions`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  async getQuizSession(id) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/quiz-sessions/${id}`);
    return res.data || res;
  }

  async createQuizSession(payload) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/quiz-sessions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data || res;
  }

  async startQuizSession(sessionId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/quiz-sessions/${sessionId}/start`, {
      method: 'POST',
    });
    return res.data || res;
  }

  async pauseQuizSession(sessionId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/quiz-sessions/${sessionId}/pause`, {
      method: 'POST',
    });
    return res.data || res;
  }

  async resumeQuizSession(sessionId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/quiz-sessions/${sessionId}/resume`, {
      method: 'POST',
    });
    return res.data || res;
  }

  async endQuizSession(sessionId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/quiz-sessions/${sessionId}/end`, {
      method: 'POST',
    });
    return res.data || res;
  }

  async getQuizDashboard(sessionId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/quiz-sessions/${sessionId}/dashboard`);
    return res.data || res;
  }

  // ── Reports & Scores ──────────────────────────────────────────────────────
  async getSessionScores(sessionId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/reports/quiz-sessions/${sessionId}/scores`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  async getSessionSummary(sessionId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/reports/quiz-sessions/${sessionId}/summary`);
    return res.data || res;
  }

  async getStudentPerformance(studentId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/reports/students/${studentId}/performance`);
    return res.data || res;
  }

  // ── Scanner: submit stored response ──────────────────────────────────────
  async submitScannerResponse(payload) {
    try {
      const res = await this.request('/scanner/responses', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      return res.data || res;
    } catch (err) {
      // 409 = duplicate (already recorded) — ignore silently
      if (err.status === 409) return null;
      throw err;
    }
  }

  // ── Scanner: detect ArUco cards from a browser camera frame ──────────────
  // frame_b64: data:image/jpeg;base64,... string from canvas.toDataURL()
  async detectFrame(frame_b64) {
    const res = await this.request('/scanner/detect-frame', {
      method: 'POST',
      body: JSON.stringify({ frame_b64 }),
    });
    return res.data || res; // { detections: [...], frame_count: 1 }
  }

  // ── Quick Quiz: create N-question set with only correct answers ───────────
  // questions: [{ correct_answer: 'A'|'B'|'C'|'D'|null, label: '...', marks: 1 }, ...]
  async quickCreateQuiz(payload) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/question-sets/quick-create`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data || res;
  }

  // ── Update Question (e.g. set/reveal correct answer live or change options) ──
  async updateQuestion(questionSetId, questionId, payload) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/question-sets/${questionSetId}/questions/${questionId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return res.data || res;
  }

  // ── Student CRUD ───────────────────────────────────────────────────────────
  async createStudent(payload) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/students`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data || res;
  }

  async updateStudent(studentId, payload) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/students/${studentId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return res.data || res;
  }

  async deleteStudent(studentId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/students/${studentId}`, {
      method: 'DELETE',
    });
    return res;
  }

  // ── Cards ──────────────────────────────────────────────────────────────────
  async getCards() {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/cards`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  async createCard(cardNumber) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/cards`, {
      method: 'POST',
      body: JSON.stringify({ card_number: cardNumber, marker_id: cardNumber }),
    });
    return res.data || res;
  }

  async assignCard(cardId, studentId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/cards/${cardId}/assign`, {
      method: 'POST',
      body: JSON.stringify({ student_id: studentId }),
    });
    return res.data || res;
  }

  async getCardAssignments() {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/cards/assignments`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  // ── CSV Bulk Import ─────────────────────────────────────────────────────────
  async importStudentsCSV(file, classId = null, sectionId = null) {
    const schoolId = this.getSchoolId();
    const formData = new FormData();
    formData.append('file', file);
    if (classId) formData.append('class_id', classId);
    if (sectionId) formData.append('section_id', sectionId);

    const url = `${API_BASE}/schools/${schoolId}/students/import`;
    const headers = {};
    if (this.accessToken) headers['Authorization'] = `Bearer ${this.accessToken}`;

    const response = await fetch(url, { method: 'POST', headers, body: formData });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = data.detail || data.error || data.message || `Import failed (${response.status})`;
      const error = new Error(typeof message === 'string' ? message : JSON.stringify(message));
      error.status = response.status;
      throw error;
    }
    return data.data || data;
  }

  // ── Admin Portal API ────────────────────────────────────────────────────────
  async getAdminSummary() {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/admin/summary`);
    return res.data || res;
  }

  async getTeacherActivity() {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/admin/teacher-activity`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  async createTeacher(payload) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/teachers`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data || res;
  }

  async updateTeacher(teacherId, payload) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/teachers/${teacherId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return res.data || res;
  }

  async deleteTeacher(teacherId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/teachers/${teacherId}`, {
      method: 'DELETE',
    });
    return res.data || res;
  }

  async resetTeacherPassword(teacherId, newPassword = null) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/admin/teachers/${teacherId}/reset-password`, {
      method: 'POST',
      body: JSON.stringify(newPassword ? { new_password: newPassword } : {}),
    });
    return res.data || res;
  }

  async getAdminBenchmarks() {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/admin/benchmarks`);
    return res.data || res;
  }

  async getAdminAuditLogs(params = {}) {
    const schoolId = this.getSchoolId();
    const q = new URLSearchParams(params).toString();
    const res = await this.request(`/schools/${schoolId}/admin/audit-logs${q ? '?' + q : ''}`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  async getAdminQuestionBank() {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/admin/question-bank`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  async getAcademicYears() {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/academic-years`);
    return res.data || (Array.isArray(res) ? res : []);
  }

  async createAcademicYear(payload) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/academic-years`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data || res;
  }

  async createClass(payload) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/classes`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data || res;
  }

  async createSection(classId, payload) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/classes/${classId}/sections`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data || res;
  }

  async replaceCard(cardId, newCardId, reason = 'Lost card') {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/cards/${cardId}/replace`, {
      method: 'POST',
      body: JSON.stringify({ new_card_id: newCardId, reason }),
    });
    return res.data || res;
  }

  async unassignCard(cardId, reason = 'Unassigned by admin') {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/cards/${cardId}/unassign`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
    return res.data || res;
  }

  async disableCard(cardId) {
    const schoolId = this.getSchoolId();
    const res = await this.request(`/schools/${schoolId}/cards/${cardId}/disable`, {
      method: 'POST',
    });
    return res.data || res;
  }
}

export const api = new ApiClient();

