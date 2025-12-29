const API_BASE = window.location.origin;
let ACCESS = localStorage.getItem('access_token');
let LIVE_WS = null;

let CURRENT_SUBJECTS = [];
let EDIT_MODE_SUBJECT = null;
let CURRENT_STUDENTS = [];
let EDIT_MODE_STUDENT = null;
let ENROLL_SAMPLES = [];

// Helper to check if we are on a specific page
const isPage = (name) => window.location.pathname.includes(name);

/**
 * Modern notification system
 * @param {string} message 
 * @param {'success'|'error'|'info'} type 
 */
function showNotification(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `fixed bottom-6 right-6 z-[9999] flex items-center gap-3 px-6 py-4 rounded-xl shadow-2xl transition-all duration-500 translate-y-4 opacity-0 font-semibold border backdrop-blur-md`;

  if (type === 'error') {
    toast.classList.add('bg-red-50/90', 'text-red-800', 'border-red-200', 'dark:bg-red-900/40', 'dark:text-red-300', 'dark:border-red-800');
  } else if (type === 'success') {
    toast.classList.add('bg-green-50/90', 'text-green-800', 'border-green-200', 'dark:bg-green-900/40', 'dark:text-green-300', 'dark:border-green-800');
  } else {
    toast.classList.add('bg-blue-50/90', 'text-blue-800', 'border-blue-200', 'dark:bg-blue-900/40', 'dark:text-blue-300', 'dark:border-blue-800');
  }

  const icon = type === 'error' ? 'error' : (type === 'success' ? 'check_circle' : 'info');
  toast.innerHTML = `
    <span class="material-symbols-outlined text-2xl">${icon}</span>
    <span class="max-w-[300px]">${message}</span>
  `;

  document.body.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-4', 'opacity-0');
  });

  // Auto-remove
  setTimeout(() => {
    toast.classList.add('translate-y-4', 'opacity-0');
    setTimeout(() => toast.remove(), 500);
  }, 5000);
}

/**
 * Standard error handler for API responses
 */
async function handleApiError(response, defaultMsg = 'An unexpected error occurred') {
  let msg = defaultMsg;
  try {
    const data = await response.json();
    if (data && data.detail) {
      msg = data.detail;
      // Friendly mappings
      const mappings = {
        'student exists': 'A student with this registration number already exists.',
        'user exists': 'A user with this username/ID already exists.',
        'invalid department': 'The selected department is invalid.',
        'not found': 'The requested resource was not found.',
        'Insufficient role': 'You do not have permission to perform this action.'
      };
      msg = mappings[msg] || msg;
    }
  } catch (e) {
    try {
      const text = await response.text();
      if (text && text.length < 200) msg = text;
    } catch (e2) { }
  }
  showNotification(msg, 'error');
}

async function refreshDepartments() {
  if (!ACCESS) return;
  try {
    const r = await fetch(API_BASE + '/departments/list', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (!r.ok) return;
    const deps = await r.json();

    // Support multiple possible IDs for department selects
    const deptSelectors = ['sub-dept', 'reg-dept', 'att-dept'];
    deptSelectors.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        // Keep "Select Department" if it exists as first option
        const firstOpt = el.options[0] && el.options[0].value === "" ? el.options[0] : null;
        el.innerHTML = '';
        if (firstOpt) el.appendChild(firstOpt);

        deps.forEach(d => {
          const opt = document.createElement('option');
          opt.value = d.name;
          opt.textContent = d.name;
          el.appendChild(opt);
        });
      }
    });

  } catch (e) { console.debug('failed to refresh departments', e) }
}

async function refreshSubjects() {
  if (!ACCESS) return;
  const attSub = document.getElementById('att-subject');
  if (!attSub) return;

  try {
    const r = await fetch(API_BASE + '/subjects/list', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (!r.ok) return;
    const subs = await r.json();

    attSub.innerHTML = '<option value="">Select Subject</option>';
    subs.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.code;
      opt.textContent = `${s.code} - ${s.name}`;
      attSub.appendChild(opt);
    });
  } catch (e) { console.debug('failed to fetch subjects', e) }
}

async function refreshDashboardStats() {
  if (!ACCESS || !isPage('classroom.html')) return;
  try {
    const r = await fetch(API_BASE + '/reports/stats', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (!r.ok) return;
    const stats = await r.json();

    const els = {
      'stat-students': stats.students,
      'stat-faculty': stats.faculty,
      'stat-attendance': stats.avg_attendance + '%',
      'stat-classes': stats.active_classes
    };

    for (const [id, val] of Object.entries(els)) {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    }
  } catch (e) { console.error('failed to refresh stats', e); }
}

async function refreshFacultyList() {
  if (!ACCESS || !isPage('faculty.html')) return;
  const tbody = document.getElementById('faculty-list-body');
  if (!tbody) return;

  try {
    const r = await fetch(API_BASE + '/faculty/list', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (!r.ok) return;
    const list = await r.json();

    tbody.innerHTML = '';
    list.forEach(f => {
      const tr = document.createElement('tr');
      tr.className = "hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors group";
      tr.innerHTML = `
        <td class="px-5 py-4">
          <div class="flex items-center gap-3">
            <div class="size-10 rounded-full bg-blue-100 dark:bg-blue-900/40 text-primary flex items-center justify-center font-bold border border-[#e7ebf3] dark:border-slate-600">
              ${f.name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2)}
            </div>
            <div>
              <p class="text-sm font-bold text-[#0d121b] dark:text-white">${f.name}</p>
              <p class="text-xs text-[#4c669a] dark:text-slate-500">${f.username}@univ.edu</p>
            </div>
          </div>
        </td>
        <td class="px-5 py-4 text-sm text-[#0d121b] dark:text-slate-300 font-medium">${f.username}</td>
        <td class="px-5 py-4 text-sm text-[#4c669a] dark:text-slate-400 hidden sm:table-cell">${f.department}</td>
        <td class="px-5 py-4">
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
            <span class="size-1.5 rounded-full bg-green-500"></span>
            Active
          </span>
        </td>
        <td class="px-5 py-4 text-right">
          <div class="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-[#4c669a] dark:text-slate-400 hover:text-primary transition-colors">
              <span class="material-symbols-outlined text-[20px]">edit</span>
            </button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error('failed to refresh faculty list', e); }
}

async function refreshSubjectList() {
  if (!ACCESS || !isPage('subject.html')) return;
  const tbody = document.getElementById('subject-list-body');
  if (!tbody) return;

  try {
    const r = await fetch(API_BASE + '/subjects/list', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (!r.ok) return;
    CURRENT_SUBJECTS = await r.json();
    renderSubjects(CURRENT_SUBJECTS);

    // Setup search listener once
    const searchInput = document.getElementById('subject-search-input');
    if (searchInput && !searchInput.dataset.listenerSet) {
      searchInput.addEventListener('input', (e) => {
        const val = e.target.value.toLowerCase();
        const filtered = CURRENT_SUBJECTS.filter(s =>
          s.code.toLowerCase().includes(val) ||
          s.name.toLowerCase().includes(val) ||
          s.department.toLowerCase().includes(val)
        );
        renderSubjects(filtered);
      });
      searchInput.dataset.listenerSet = 'true';
    }
  } catch (e) { console.error('failed to refresh subject list', e); }
}

async function refreshStudentList() {
  if (!ACCESS || !isPage('student.html')) return;
  const tbody = document.getElementById('student-list-body');
  if (!tbody) return;

  try {
    const r = await fetch(API_BASE + '/students/list', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (!r.ok) return;
    CURRENT_STUDENTS = await r.json();
    renderStudents(CURRENT_STUDENTS);

    // Setup search listener once
    const searchInput = document.getElementById('student-search-input');
    if (searchInput && !searchInput.dataset.listenerSet) {
      searchInput.addEventListener('input', (e) => {
        const val = e.target.value.toLowerCase();
        const filtered = CURRENT_STUDENTS.filter(s =>
          s.name.toLowerCase().includes(val) ||
          s.reg_no.toLowerCase().includes(val) ||
          s.department.toLowerCase().includes(val)
        );
        renderStudents(filtered);
      });
      searchInput.dataset.listenerSet = 'true';
    }
  } catch (e) { console.error('failed to refresh student list', e); }
}

function renderStudents(list) {
  const tbody = document.getElementById('student-list-body');
  if (!tbody) return;
  tbody.innerHTML = '';
  const countEl = document.getElementById('student-count-visible');
  if (countEl) countEl.textContent = list.length;

  list.forEach(s => {
    const tr = document.createElement('tr');
    tr.className = "hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors group";
    tr.innerHTML = `
      <td class="px-6 py-4">
        <div class="flex items-center gap-3">
          <div class="size-9 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs border border-primary/20">
            ${s.name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2)}
          </div>
          <div class="min-w-0">
            <p class="text-sm font-semibold text-slate-900 dark:text-white truncate">${s.name}</p>
            <p class="text-[10px] text-slate-500">${s.department} • ${s.semester}th Sem</p>
          </div>
        </div>
      </td>
      <td class="px-6 py-4 text-sm text-slate-600 dark:text-slate-400 font-mono">${s.reg_no}</td>
      <td class="px-6 py-4 text-sm text-slate-600 dark:text-slate-400">Section ${s.section}</td>
      <td class="px-6 py-4">
        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Active</span>
      </td>
      <td class="px-6 py-4 text-right">
        <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onclick="editStudent('${s.reg_no}')" class="p-1 px-2 text-primary hover:bg-primary/10 rounded transition-colors text-xs font-bold">Edit</button>
          <button onclick="deleteStudent('${s.reg_no}')" class="p-1 px-2 text-red-500 hover:bg-red-500/10 rounded transition-colors text-xs font-bold">Delete</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

window.editStudent = (reg_no) => {
  const s = CURRENT_STUDENTS.find(x => x.reg_no === reg_no);
  if (!s) return;

  EDIT_MODE_STUDENT = reg_no;
  document.getElementById('reg-regno').value = s.reg_no;
  document.getElementById('reg-regno').disabled = true;
  document.getElementById('reg-name').value = s.name;
  document.getElementById('reg-dept').value = s.department;
  document.getElementById('reg-sem').value = s.semester;
  document.getElementById('reg-section').value = s.section || 'A';

  const title = document.getElementById('student-form-title');
  if (title) title.innerHTML = '<span class="material-symbols-outlined text-primary">edit</span> Edit Student Profile';
  const btn = document.getElementById('btn-register');
  if (btn) btn.innerHTML = '<span class="material-symbols-outlined text-lg">update</span> Update Profile';
};

window.deleteStudent = async (reg_no) => {
  if (!confirm(`Are you sure you want to delete student ${reg_no}?`)) return;
  const form = new URLSearchParams();
  form.append('target_reg', reg_no);
  try {
    const r = await fetch(API_BASE + '/students/delete', { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (r.ok) {
      showNotification(`Student ${reg_no} deleted`, 'success');
      refreshStudentList();
    } else {
      await handleApiError(r, 'Failed to delete student');
    }
  } catch (e) { showNotification('Network error during delete', 'error'); }
};

function renderSubjects(list) {
  const tbody = document.getElementById('subject-list-body');
  if (!tbody) return;
  tbody.innerHTML = '';
  list.forEach(s => {
    const tr = document.createElement('tr');
    tr.className = "group hover:bg-[#f0f9ff] dark:hover:bg-[#2d3748]/50 transition-colors";
    tr.innerHTML = `
      <td class="py-4 px-6 text-sm font-medium text-[#0d121b] dark:text-white">${s.code}</td>
      <td class="py-4 px-6 text-sm text-[#4c669a] dark:text-[#cbd5e1]">${s.name}</td>
      <td class="py-4 px-6 text-sm text-[#4c669a] dark:text-[#cbd5e1]">Sem ${s.semester} (${s.department})</td>
      <td class="py-4 px-6">
        <span class="inline-flex items-center rounded-full bg-green-50 dark:bg-green-900/30 px-2.5 py-0.5 text-xs font-medium text-green-700 dark:text-green-300 ring-1 ring-inset ring-green-600/20">Active</span>
      </td>
      <td class="py-4 px-6 text-right">
        <div class="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onclick="editSubject('${s.code}')" class="text-[#4c669a] hover:text-primary transition-colors p-1" title="Edit">
            <span class="material-symbols-outlined text-[20px]">edit</span>
          </button>
          <button onclick="deleteSubject('${s.code}')" class="text-red-400 hover:text-red-600 transition-colors p-1" title="Delete">
            <span class="material-symbols-outlined text-[20px]">delete</span>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

window.editSubject = (code) => {
  const s = CURRENT_SUBJECTS.find(x => x.code === code);
  if (!s) return;

  EDIT_MODE_SUBJECT = code;
  const codeInp = document.getElementById('sub-code');
  const nameInp = document.getElementById('sub-name');
  const deptInp = document.getElementById('sub-dept');
  const semInp = document.getElementById('sub-sem');

  if (codeInp) { codeInp.value = s.code; codeInp.disabled = true; }
  if (nameInp) nameInp.value = s.name;
  if (deptInp) deptInp.value = s.department;
  if (semInp) semInp.value = s.semester;

  const btn = document.getElementById('btn-create-sub');
  if (btn) btn.innerHTML = '<span class="material-symbols-outlined text-xl">update</span> Update Subject';
};

window.deleteSubject = async (code) => {
  if (!confirm(`Are you sure you want to delete subject ${code}?`)) return;

  const form = new URLSearchParams();
  form.append('target_code', code);

  try {
    const r = await fetch(API_BASE + '/subjects/delete', { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (r.ok) {
      showNotification(`Subject ${code} deleted`, 'success');
      refreshSubjectList();
    } else {
      await handleApiError(r, 'Failed to delete subject');
    }
  } catch (e) { showNotification('Network error during delete', 'error'); }
};

async function refreshRecentActivity() {
  if (!ACCESS || !isPage('classroom.html')) return;
  const tbody = document.getElementById('recent-activity-body');
  if (!tbody) return;

  try {
    const r = await fetch(API_BASE + '/attendance/recent', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (!r.ok) return;
    const list = await r.json();

    tbody.innerHTML = '';
    list.forEach(item => {
      const tr = document.createElement('tr');
      const statusClass = item.status === 'present' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      const indicatorClass = item.status === 'present' ? 'bg-green-500' : 'bg-red-500';

      tr.innerHTML = `
        <td class="px-6 py-4">
          <div class="flex items-center gap-3">
            <div class="size-8 rounded-full bg-blue-100 dark:bg-blue-900/40 text-primary flex items-center justify-center text-xs font-bold">
              ${item.student_name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2)}
            </div>
            <span class="font-medium text-slate-900 dark:text-white">${item.student_name}</span>
          </div>
        </td>
        <td class="px-6 py-4 text-slate-600 dark:text-slate-300">${item.subject_code}</td>
        <td class="px-6 py-4 text-slate-500 dark:text-slate-400">${item.timestamp}</td>
        <td class="px-6 py-4">
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusClass}">
            <span class="size-1.5 rounded-full ${indicatorClass}"></span>
            ${item.status.charAt(0).toUpperCase() + item.status.slice(1)}
          </span>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error('failed to refresh recent activity', e); }
}


function connectLiveFeed() {
  if (LIVE_WS) return;
  if (!ACCESS) return;
  if (!document.getElementById('live-feed')) return;

  const wsUrl = (API_BASE.replace(/^http/, 'ws')) + `/attendance/live`;
  LIVE_WS = new WebSocket(wsUrl);
  LIVE_WS.onopen = () => console.log('Live feed connected');
  LIVE_WS.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'recognition') {
        addToFeed(msg.student);
      }
    } catch (e) { console.error('feed parse error', e); }
  };
  LIVE_WS.onclose = () => { LIVE_WS = null; setTimeout(connectLiveFeed, 3000); };
}

function addToFeed(student) {
  const list = document.getElementById('att-list');
  if (!feed) return;

  // Custom template for the new UI if it looks like a list
  if (feed.tagName === 'UL') {
    const li = document.createElement('li');
    li.className = "p-3 bg-blue-50/50 dark:bg-blue-900/10 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors flex items-center gap-3 border-l-4 border-primary animate-in fade-in slide-in-from-right-4 duration-500";
    li.innerHTML = `
      <div class="relative">
        <div class="size-10 rounded-full bg-slate-200 bg-cover bg-center border border-gray-200 dark:border-gray-600" style="background-color: #ccc"></div>
        <div class="absolute -bottom-1 -right-1 bg-green-500 border-2 border-white dark:border-[#1a2233] rounded-full p-0.5">
          <span class="material-symbols-outlined text-white text-[10px] font-bold block">check</span>
        </div>
      </div>
      <div class="flex-1 min-w-0">
        <h4 class="text-sm font-bold text-[#0d121b] dark:text-white truncate">${student.name}</h4>
        <p class="text-xs text-[#4c669a] dark:text-gray-400 truncate">ID: ${student.reg_no} • ${student.department || ''}</p>
      </div>
      <div class="flex flex-col items-end gap-0.5">
        <span class="text-xs font-mono font-bold text-primary">Just Now</span>
        <span class="text-[10px] font-bold px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">Match</span>
      </div>
    `;
    feed.insertBefore(li, feed.firstChild);
  } else {
    // Fallback for old UI
    const div = document.createElement('div');
    div.className = 'feed-item';
    const info = `${student.department || ''} ${student.semester || ''}${student.section || ''}`;
    div.innerHTML = `<span class="feed-time">[${student.timestamp}]</span> <strong>${student.name}</strong> (${student.reg_no}) <small>${info}</small>`;
    feed.insertBefore(div, feed.firstChild);
  }
}

// Login logic
const btnLogin = document.getElementById('btn-login');
if (btnLogin) {
  btnLogin.addEventListener('click', async () => {
    const u = document.getElementById('username')?.value;
    const p = document.getElementById('password')?.value;
    if (!u || !p) { showNotification('Please enter username and password', 'error'); return; }

    const form = new URLSearchParams();
    form.append('username', u);
    form.append('password', p);

    try {
      const r = await fetch(API_BASE + '/auth/login', { method: 'POST', body: form });
      if (!r.ok) { showNotification('Login failed. Please check your credentials.', 'error'); return }
      const j = await r.json();
      ACCESS = j.access_token;
      localStorage.setItem('access_token', ACCESS);

      showNotification('Login successful!', 'success');
      // Redirect to classroom/dashboard
      window.location.href = '/dashboard/classroom.html';
    } catch (e) { showNotification('Connection error. Server may be offline.', 'error'); }
  });
}

// Register logic
const btnRegister = document.getElementById('btn-register');
if (btnRegister) {
  btnRegister.addEventListener('click', async () => {
    const regno = document.getElementById('reg-regno')?.value;
    const pass = document.getElementById('reg-pass')?.value;
    const role = document.getElementById('reg-role')?.value || 'student';

    if (!regno || !pass) { showNotification('Please provide Registration No. and Password', 'error'); return }

    // Admin bootstrap
    if (role === 'admin' && !ACCESS) {
      const form = new URLSearchParams();
      form.append('username', regno);
      form.append('password', pass);
      form.append('role', 'admin');
      const r = await fetch(API_BASE + '/auth/register', { method: 'POST', body: form });
      if (!r.ok) { await handleApiError(r, 'Initial admin setup failed'); return; }
      showNotification('Admin created successfully! Please login.', 'success');
      window.location.reload();
      return;
    }

    if (!ACCESS) { showNotification('Admin session required for this action.', 'error'); return }

    if (role === 'student') {
      const name = document.getElementById('reg-name')?.value;
      const dept = document.getElementById('reg-dept')?.value;
      const sem = document.getElementById('reg-sem')?.value;
      const section = document.getElementById('reg-section')?.value || 'A';

      try {
        const path = EDIT_MODE_STUDENT ? '/students/modify' : '/students/create';
        const target_reg = EDIT_MODE_STUDENT;

        const sform = new URLSearchParams();
        if (EDIT_MODE_STUDENT) {
          sform.append('target_reg', target_reg);
          sform.append('name', name);
          sform.append('department', dept);
          sform.append('semester', sem);
          sform.append('section', section);
        } else {
          sform.append('reg_no', regno);
          sform.append('name', name);
          sform.append('department', dept);
          sform.append('semester', sem);
          sform.append('section', section);
          sform.append('password', pass);
        }

        const r = await fetch(API_BASE + path, { method: 'POST', body: sform, headers: { 'Authorization': 'Bearer ' + ACCESS } });
        if (r.ok) {
          showNotification(EDIT_MODE_STUDENT ? 'Student profile updated' : 'Student profile created', 'success');
          // Reset form
          EDIT_MODE_STUDENT = null;
          document.getElementById('reg-regno').disabled = false;
          document.getElementById('reg-regno').value = '';
          document.getElementById('reg-name').value = '';
          document.getElementById('student-form-title').innerHTML = '<span class="material-symbols-outlined text-primary">person_add</span> Student Information';
          document.getElementById('btn-register').innerHTML = '<span class="material-symbols-outlined text-lg">save</span> Create Profile';
          refreshStudentList();
        } else {
          await handleApiError(r);
        }
      } catch (e) { showNotification('Network error occurred.', 'error'); }
    } else if (role === 'faculty') {
      const name = document.getElementById('reg-name')?.value;
      const dept = document.getElementById('reg-dept')?.value;

      const fform = new URLSearchParams();
      fform.append('username', regno);
      fform.append('name', name);
      fform.append('department', dept);
      fform.append('password', pass);

      try {
        const r = await fetch(API_BASE + '/faculty/create', { method: 'POST', body: fform, headers: { 'Authorization': 'Bearer ' + ACCESS } });
        if (r.ok) {
          showNotification('Faculty profile created successfully', 'success');
          window.location.reload();
        } else {
          await handleApiError(r);
        }
      } catch (e) { showNotification('Network error during faculty creation', 'error'); }
    }
  });
}

// Stream Control
const btnStart = document.getElementById('btn-start');
if (btnStart) {
  btnStart.addEventListener('click', async () => {
    const name = document.getElementById('stream-name')?.value || 'camera1';
    const url = document.getElementById('stream-url')?.value;
    if (!ACCESS) return showNotification('Please login as admin first', 'error');

    const form = new URLSearchParams();
    form.append('name', name);
    form.append('url', url);
    try {
      const r = await fetch(API_BASE + '/stream/start', { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
      if (r.ok) {
        showNotification(`Stream ${name} started`, 'success');
        setupStreamWS(name);
      } else {
        await handleApiError(r, 'Failed to start stream');
      }
    } catch (e) { showNotification('Failed to connect to stream service', 'error'); }
  });
}

const btnConnect = document.getElementById('btn-connect');
if (btnConnect) {
  btnConnect.addEventListener('click', () => {
    const name = document.getElementById('stream-name')?.value;
    if (name) setupStreamWS(name);
  });
}

const btnStop = document.getElementById('btn-stop');
if (btnStop) {
  btnStop.addEventListener('click', async () => {
    const name = document.getElementById('stream-name')?.value;
    if (!ACCESS || !name) return;
    const form = new URLSearchParams(); form.append('name', name);
    await fetch(API_BASE + '/stream/stop', { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (window._stream_ws) { window._stream_ws.close(); window._stream_ws = null; }
  });
}

function setupStreamWS(name) {
  if (!ACCESS) return;
  if (window._stream_ws) window._stream_ws.close();

  const wsUrl = (API_BASE.replace(/^http/, 'ws')) + `/stream/ws/${encodeURIComponent(name)}?token=${encodeURIComponent(ACCESS)}`;
  const ws = new WebSocket(wsUrl);
  ws.binaryType = 'arraybuffer';
  ws.onmessage = (ev) => {
    const blob = new Blob([ev.data], { type: 'image/jpeg' });
    const url = URL.createObjectURL(blob);
    const img = document.getElementById('video');
    if (img) {
      img.onload = () => {
        if (window._lastImageUrl && window._lastImageUrl !== url) {
          try { URL.revokeObjectURL(window._lastImageUrl); } catch (e) { }
        }
        window._lastImageUrl = url;
      };
      img.src = url;
      img.style.display = 'block';
      // Hide placeholder if exists
      const placeholder = document.getElementById('video-placeholder');
      if (placeholder) placeholder.style.display = 'none';
      const container = document.getElementById('video-container');
      if (container) container.style.backgroundImage = 'none';
    }
  }
  window._stream_ws = ws;
}

// Attendance trigger
const btnTrigger = document.getElementById('btn-trigger');
if (btnTrigger) {
  btnTrigger.addEventListener('click', async () => {
    if (!ACCESS) return showNotification('Login required', 'error');
    const streamName = document.getElementById('stream-name')?.value || 'camera1';
    const subjVal = document.getElementById('att-subject')?.value;
    const deptVal = document.getElementById('att-dept')?.value;
    const semVal = document.getElementById('att-sem')?.value || '1';
    const secVal = document.getElementById('att-section')?.value || 'A';

    if (!subjVal || !deptVal) return showNotification('Please select Subject and Department', 'error');

    const list = document.getElementById('att-list');
    if (list) list.innerHTML = '';

    const form = new URLSearchParams();
    form.append('stream_name', streamName);
    form.append('subject', subjVal);
    form.append('department', deptVal);
    form.append('semester', semVal);
    form.append('section', secVal);

    try {
      const r = await fetch(API_BASE + '/attendance/start', { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
      if (r.ok) {
        showNotification('Attendance session started', 'success');
        setTimeout(refreshAttendanceSessionStatus, 1000); // Wait for loop to start
      } else {
        await handleApiError(r);
      }
    } catch (e) { showNotification('Failed to connect to attendance service', 'error'); }
  });
}

const btnStopAtt = document.getElementById('btn-stop-att');
if (btnStopAtt) {
  btnStopAtt.addEventListener('click', async () => {
    if (!ACCESS) return;
    try {
      const r = await fetch(API_BASE + '/attendance/stop', { method: 'POST', headers: { 'Authorization': 'Bearer ' + ACCESS } });
      if (r.ok) {
        showNotification('Attendance session stopped', 'success');
        // Clear UI
        const title = document.getElementById('session-subject-title');
        if (title) title.textContent = 'Select Subject to Start';
        const list = document.getElementById('att-list');
        if (list) list.innerHTML = '';
        if (window._stream_ws) { window._stream_ws.close(); window._stream_ws = null; }
        if (ATT_WS) { ATT_WS.close(); ATT_WS = null; }
        ['stat-total', 'stat-present', 'stat-absent'].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.textContent = '0';
        });
      } else {
        await handleApiError(r);
      }
    } catch (e) { showNotification('Error stopping session', 'error'); }
  });
}

// Subject creation
const btnCreateSub = document.getElementById('btn-create-sub');
if (btnCreateSub) {
  btnCreateSub.addEventListener('click', async () => {
    if (!ACCESS) return;
    const code = document.getElementById('sub-code')?.value;
    const name = document.getElementById('sub-name')?.value;
    const dept = document.getElementById('sub-dept')?.value;
    const sem = document.getElementById('sub-sem')?.value;

    const form = new URLSearchParams();
    if (EDIT_MODE_SUBJECT) {
      form.append('target_code', EDIT_MODE_SUBJECT);
      form.append('name', name);
      form.append('department', dept);
      form.append('semester', sem);
    } else {
      form.append('code', code);
      form.append('name', name);
      form.append('department', dept);
      form.append('semester', sem);
    }

    try {
      const path = EDIT_MODE_SUBJECT ? '/subjects/modify' : '/subjects/create';
      const r = await fetch(API_BASE + path, { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
      if (r.ok) {
        showNotification(EDIT_MODE_SUBJECT ? 'Subject details updated' : 'New subject created', 'success');
        // Reset form
        EDIT_MODE_SUBJECT = null;
        const codeInp = document.getElementById('sub-code');
        if (codeInp) { codeInp.value = ''; codeInp.disabled = false; }
        document.getElementById('sub-name').value = '';
        btnCreateSub.innerHTML = '<span class="material-symbols-outlined text-xl">save</span> Create Subject';
        refreshSubjectList();
      } else {
        await handleApiError(r);
      }
    } catch (e) { showNotification('Network error occurred', 'error'); }
  });
}

// Global Initialization
async function init() {
  if (ACCESS) {
    await refreshDepartments();
    await refreshSubjects();
    if (isPage('attaendence.html')) {
      // Auto-connect if stream name is set or default
      const streamName = document.getElementById('stream-name')?.value || 'camera1';
      setupStreamWS(streamName);
      connectLiveFeed();
    }

    // Page specific refreshes
    if (isPage('classroom.html')) {
      await refreshDashboardStats();
      await refreshRecentActivity();
    }
    if (isPage('faculty.html')) {
      await refreshFacultyList();
    }
    if (isPage('subject.html')) {
      await refreshSubjectList();
    }
    if (isPage('student.html')) {
      await refreshStudentList();
      await populateEnrollmentSources();
      setupFaceEnrollmentHandlers();
    }
    if (isPage('settings.html')) {
      await refreshSettingsStreamList();
      setupSettingsHandlers();
    }
    if (isPage('attendance.html')) {
      await refreshDepartments();
      await refreshSubjects();
      await populateAttendanceStreams();
      await refreshAttendanceSessionStatus();
    } else {
      // If no access and not on login page, redirect to login?
      // Only if trying to access dashboard subpages
      if (window.location.pathname.startsWith('/dashboard') && !isPage('index.html')) {
        // window.location.href = '/dashboard/index.html';
      }
    }
  }
}

init();
// Face Enrollment (Independent Flow)
let ENROLL_STREAM = null;
function setupFaceEnrollmentHandlers() {
  if (!isPage('student.html')) return;

  const btnVerify = document.getElementById('btn-verify-enroll');
  const enrollRegInput = document.getElementById('enroll-reg-no');
  const enrollStatus = document.getElementById('enroll-status');
  const cameraContainer = document.getElementById('enrollment-camera-container');

  btnVerify?.addEventListener('click', async () => {
    const reg_no = enrollRegInput.value.trim();
    if (!reg_no) return showNotification('Please enter a registration number', 'error');

    try {
      enrollStatus.textContent = 'Verifying...';
      const r = await fetch(API_BASE + '/students/' + reg_no, { headers: { 'Authorization': 'Bearer ' + ACCESS } });
      if (r.ok) {
        const data = await r.json();
        enrollStatus.textContent = `Student: ${data.name} (Verified)`;
        enrollStatus.className = 'text-[10px] text-green-500 font-bold';
        cameraContainer.classList.remove('opacity-50', 'pointer-events-none');
        startEnrollmentCamera();
        showNotification('Student verified. You can now capture photos.', 'success');
      } else {
        enrollStatus.textContent = 'Student not found. Create profile first.';
        enrollStatus.className = 'text-[10px] text-red-500 font-bold';
        cameraContainer.classList.add('opacity-50', 'pointer-events-none');
        await handleApiError(r, 'Student not registered');
      }
    } catch (e) { showNotification('Verification failed. Check network.', 'error'); }
  });

  document.getElementById('btn-capture-face')?.addEventListener('click', captureEnrollSlot);
  document.getElementById('btn-clear-samples')?.addEventListener('click', () => {
    ENROLL_SAMPLES = [];
    renderEnrollSamples();
  });

  document.getElementById('enroll-source-select')?.addEventListener('change', () => {
    // Restart camera with new source if verified
    const container = document.getElementById('enrollment-camera-container');
    if (!container.classList.contains('opacity-50')) {
      startEnrollmentCamera();
    }
  });

  document.getElementById('btn-save-enrollment')?.addEventListener('click', submitEnrollment);

  document.getElementById('btn-cancel-reg')?.addEventListener('click', () => {
    EDIT_MODE_STUDENT = null;
    document.getElementById('reg-regno').value = '';
    document.getElementById('reg-regno').disabled = false;
    document.getElementById('reg-name').value = '';
    document.getElementById('reg-sem').value = '';
    document.getElementById('reg-dept').value = '';
    const title = document.getElementById('student-form-title');
    if (title) title.innerHTML = '<span class="material-symbols-outlined text-primary">person_add</span> Student Information';
    const btn = document.getElementById('btn-register');
    if (btn) btn.innerHTML = '<span class="material-symbols-outlined text-lg">save</span> Create Profile';
  });
}

let ENROLL_WS = null;

async function populateEnrollmentSources() {
  const select = document.getElementById('enroll-source-select');
  if (!select || !ACCESS) return;

  try {
    const r = await fetch(API_BASE + '/stream/list', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (!r.ok) return;
    const streams = await r.json();

    // Clear existing remote options (keep webcam and separator)
    while (select.options.length > 2) select.remove(2);

    streams.forEach(s => {
      if (s.running) {
        const opt = document.createElement('option');
        opt.value = `remote:${s.name}`;
        opt.textContent = `Remote: ${s.name}`;
        select.appendChild(opt);
      }
    });
  } catch (e) { console.debug('Failed to fetch streams for enrollment', e); }
}

async function startEnrollmentCamera() {
  const video = document.getElementById('enrollment-video');
  const remoteView = document.getElementById('enrollment-remote-view');
  const placeholder = document.getElementById('enrollment-placeholder');
  const source = document.getElementById('enroll-source-select')?.value || 'webcam';

  // Stop current
  if (ENROLL_STREAM) {
    ENROLL_STREAM.getTracks().forEach(t => t.stop());
    ENROLL_STREAM = null;
  }
  if (ENROLL_WS) {
    ENROLL_WS.close();
    ENROLL_WS = null;
  }

  video.classList.add('hidden');
  remoteView.classList.add('hidden');
  placeholder.classList.remove('hidden');

  if (source === 'webcam') {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      video.srcObject = stream;
      video.classList.remove('hidden');
      placeholder.classList.add('hidden');
      video.play();
      ENROLL_STREAM = stream;
    } catch (e) {
      showNotification('Could not access webcam. Check permissions.', 'error');
    }
  } else if (source.startsWith('remote:')) {
    const streamName = source.split(':')[1];
    const wsUrl = (API_BASE.replace(/^http/, 'ws')) + `/stream/ws/${encodeURIComponent(streamName)}?token=${encodeURIComponent(ACCESS)}`;
    ENROLL_WS = new WebSocket(wsUrl);
    ENROLL_WS.binaryType = 'arraybuffer';
    ENROLL_WS.onopen = () => {
      remoteView.classList.remove('hidden');
      placeholder.classList.add('hidden');
    };
    ENROLL_WS.onmessage = (ev) => {
      const blob = new Blob([ev.data], { type: 'image/jpeg' });
      const url = URL.createObjectURL(blob);
      const oldUrl = remoteView.src;
      remoteView.src = url;
      if (oldUrl.startsWith('blob:')) URL.revokeObjectURL(oldUrl);
    };
    ENROLL_WS.onerror = () => showNotification('Remote stream connection failed', 'error');
  }
}

function captureEnrollSlot() {
  const source = document.getElementById('enroll-source-select')?.value || 'webcam';
  const video = document.getElementById('enrollment-video');
  const remoteView = document.getElementById('enrollment-remote-view');

  if (ENROLL_SAMPLES.length >= 4) return showNotification('Maximum 4 samples allowed', 'error');

  const canvas = document.createElement('canvas');
  let ctx = canvas.getContext('2d');

  if (source === 'webcam') {
    if (!ENROLL_STREAM) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);
  } else {
    if (!remoteView.src || remoteView.classList.contains('hidden')) return;
    canvas.width = remoteView.naturalWidth;
    canvas.height = remoteView.naturalHeight;
    ctx.drawImage(remoteView, 0, 0);
  }

  canvas.toBlob((blob) => {
    ENROLL_SAMPLES.push(blob);
    renderEnrollSamples();
    showNotification(`Captured sample ${ENROLL_SAMPLES.length}/4`, 'info');
  }, 'image/jpeg', 0.9);
}

function renderEnrollSamples() {
  const grid = document.getElementById('enroll-samples-grid');
  if (!grid) return;
  grid.innerHTML = '';
  document.getElementById('sample-count').textContent = ENROLL_SAMPLES.length;

  ENROLL_SAMPLES.forEach((blob, idx) => {
    const url = URL.createObjectURL(blob);
    const div = document.createElement('div');
    div.className = "relative aspect-square rounded-lg overflow-hidden group";
    div.innerHTML = `
      <img src="${url}" class="w-full h-full object-cover" />
      <button onclick="removeEnrollSample(${idx})" class="absolute top-1 right-1 p-0.5 bg-red-500 text-white rounded-full">
        <span class="material-symbols-outlined text-xs block">close</span>
      </button>
    `;
    grid.appendChild(div);
  });

  document.getElementById('btn-save-enrollment').disabled = ENROLL_SAMPLES.length < 1;
}

window.removeEnrollSample = (idx) => {
  ENROLL_SAMPLES.splice(idx, 1);
  renderEnrollSamples();
};

async function submitEnrollment() {
  const reg_no = document.getElementById('enroll-reg-no').value.trim();
  if (!reg_no || ENROLL_SAMPLES.length < 1) return;

  const formData = new FormData();
  ENROLL_SAMPLES.forEach((blob, i) => {
    formData.append('files', blob, `sample_${i}.jpg`);
  });

  try {
    document.getElementById('btn-save-enrollment').disabled = true;
    document.getElementById('btn-save-enrollment').textContent = 'Uploading...';

    const r = await fetch(`${API_BASE}/students/${reg_no}/enroll-photos`, {
      method: 'POST',
      body: formData,
      headers: { 'Authorization': 'Bearer ' + ACCESS }
    });

    if (r.ok) {
      showNotification('Face enrollment completed successfully!', 'success');
      ENROLL_SAMPLES = [];
      renderEnrollSamples();
      // Optional: stop camera
      if (ENROLL_STREAM) {
        ENROLL_STREAM.getTracks().forEach(t => t.stop());
        ENROLL_STREAM = null;
      }
      if (ENROLL_WS) {
        ENROLL_WS.close();
        ENROLL_WS = null;
      }
      document.getElementById('enrollment-video').classList.add('hidden');
      document.getElementById('enrollment-remote-view').classList.add('hidden');
      document.getElementById('enrollment-placeholder').classList.remove('hidden');
    } else {
      await handleApiError(r, 'Enrollment failed');
    }
  } catch (e) { showNotification('Network error during upload', 'error'); }
  finally {
    document.getElementById('btn-save-enrollment').disabled = false;
    document.getElementById('btn-save-enrollment').textContent = 'Complete Face Enrollment';
  }
}

// Settings Logic
async function refreshSettingsStreamList() {
  if (!ACCESS || !isPage('settings.html')) return;
  const tbody = document.getElementById('stream-list-body');
  if (!tbody) return;

  try {
    const r = await fetch(API_BASE + '/stream/list', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (!r.ok) return;
    const streams = await r.json();

    tbody.innerHTML = '';
    streams.forEach(s => {
      const tr = document.createElement('tr');
      tr.className = "hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors group";
      tr.innerHTML = `
                <td class="px-6 py-4 font-bold text-sm select-all cursor-pointer" onclick="previewStreamInSettings('${s.name}')">${s.name}</td>
                <td class="px-6 py-4 text-xs font-mono text-slate-500 overflow-hidden text-ellipsis max-w-[200px]" title="${s.url}">${s.url}</td>
                <td class="px-6 py-4">
                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${s.running ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-slate-100 text-slate-500 dark:bg-slate-800/50'}">
                        ${s.running ? 'Connected' : 'Stopped'}
                    </span>
                </td>
                <td class="px-6 py-4 text-right">
                    <button onclick="stopStreamSettings('${s.name}')" class="p-1 px-3 text-red-500 hover:bg-red-500/10 rounded transition-colors text-xs font-bold">Stop</button>
                </td>
            `;
      tbody.appendChild(tr);
    });
  } catch (e) { showNotification('Failed to load stream list', 'error'); }
}

function setupSettingsHandlers() {
  document.getElementById('btn-add-stream')?.addEventListener('click', async () => {
    const name = document.getElementById('stream-name').value.trim();
    const url = document.getElementById('stream-url').value.trim();
    if (!name || !url) return showNotification('Name and URL required', 'error');

    const form = new URLSearchParams();
    form.append('name', name);
    form.append('url', url);

    try {
      const r = await fetch(API_BASE + '/stream/start', { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
      if (r.ok) {
        showNotification(`Stream ${name} started and saved`, 'success');
        refreshSettingsStreamList();
        document.getElementById('stream-name').value = '';
        document.getElementById('stream-url').value = '';
      } else {
        await handleApiError(r);
      }
    } catch (e) { showNotification('Network error', 'error'); }
  });
}

window.stopStreamSettings = async (name) => {
  const form = new URLSearchParams();
  form.append('name', name);
  try {
    const r = await fetch(API_BASE + '/stream/stop', { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (r.ok) {
      showNotification(`Stream ${name} stopped`, 'success');
      refreshSettingsStreamList();
    } else {
      await handleApiError(r);
    }
  } catch (e) { showNotification('Network error', 'error'); }
};

async function populateAttendanceStreams() {
  const select = document.getElementById('stream-name');
  if (!select) return;
  try {
    const r = await fetch(API_BASE + '/stream/list', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (!r.ok) return;
    const streams = await r.json();
    streams.forEach(s => {
      if (s.name !== 'camera1' && s.name !== 'camera2') {
        const opt = document.createElement('option');
        opt.value = s.name;
        opt.textContent = `${s.name} (${s.running ? 'Live' : 'Stopped'})`;
        select.appendChild(opt);
      }
    });
  } catch (e) { console.debug('Failed to load streams', e); }
}

async function refreshAttendanceSessionStatus() {
  if (!isPage('attendance.html')) return;
  try {
    const r = await fetch(API_BASE + '/attendance/status', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (r.ok) {
      const data = await r.json();
      if (data.active) {
        const sess = data.session;
        // Update UI to reflect running session
        const title = document.getElementById('session-subject-title');
        if (title) title.textContent = `${sess.subject_code} Session (Active)`;

        document.getElementById('att-subject').value = sess.subject_code;
        document.getElementById('att-dept').value = sess.department;
        document.getElementById('att-sem').value = sess.semester;
        document.getElementById('att-section').value = sess.section;
        document.getElementById('stream-name').value = sess.stream_name;

        const dateEl = document.getElementById('session-date');
        if (dateEl) dateEl.textContent = new Date(sess.start_time).toLocaleDateString();
        const timeEl = document.getElementById('session-time');
        if (timeEl) timeEl.textContent = new Date(sess.start_time).toLocaleTimeString() + ' - Current';

        const totalEl = document.getElementById('stat-total');
        if (totalEl && sess.total_students) totalEl.textContent = sess.total_students;

        connectLiveFeed(); // Video
        setupAttendanceWebSocket(); // Records
        showNotification('Resumed active attendance session', 'info');
      }
    }
  } catch (e) { console.debug('Failed to get session status', e); }
}

let ATT_WS = null;
function setupAttendanceWebSocket() {
  if (ATT_WS) ATT_WS.close();
  const wsUrl = (API_BASE.replace(/^http/, 'ws')) + `/attendance/live?token=${encodeURIComponent(ACCESS)}`;
  ATT_WS = new WebSocket(wsUrl);
  ATT_WS.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    if (data.type === 'recognition') {
      addRecognizedStudent(data.student);
    }
  };
  ATT_WS.onerror = () => console.debug('Attendance WS error');
}

function addRecognizedStudent(student) {
  const list = document.getElementById('att-list');
  if (!list) return;

  // Check if already in list
  const existing = document.getElementById(`att-rec-${student.reg_no}`);
  if (existing) {
    existing.classList.add('bg-blue-100', 'dark:bg-blue-900/30');
    setTimeout(() => existing.classList.remove('bg-blue-100', 'dark:bg-blue-900/30'), 2000);
    return;
  }

  const li = document.createElement('li');
  li.id = `att-rec-${student.reg_no}`;
  li.className = "p-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors flex items-center gap-3 border-l-4 border-primary animate-in slide-in-from-right";
  li.innerHTML = `
        <div class="relative">
            <div class="size-10 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center border border-gray-200 dark:border-gray-600">
                <span class="material-symbols-outlined text-slate-400">person</span>
            </div>
            <div class="absolute -bottom-1 -right-1 bg-green-500 border-2 border-white dark:border-[#1a2233] rounded-full p-0.5">
                <span class="material-symbols-outlined text-white text-[10px] font-bold block">check</span>
            </div>
        </div>
        <div class="flex-1 min-w-0">
            <h4 class="text-sm font-bold text-[#0d121b] dark:text-white truncate">${student.name}</h4>
            <p class="text-xs text-[#4c669a] dark:text-gray-400 truncate">ID: ${student.reg_no} • ${student.department}</p>
        </div>
        <div class="flex flex-col items-end gap-0.5">
            <span class="text-xs font-mono font-bold text-primary">${student.timestamp}</span>
            <span class="text-[10px] font-bold px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">${Math.round(student.confidence * 100)}% Match</span>
        </div>
    `;
  list.prepend(li);

  // Update stats
  const presentEl = document.getElementById('stat-present');
  const totalEl = document.getElementById('stat-total');
  const absentEl = document.getElementById('stat-absent');

  const count = list.children.length;
  if (presentEl) presentEl.textContent = count;

  if (totalEl && totalEl.textContent != '0') {
    const total = parseInt(totalEl.textContent) || 0;
    if (absentEl) absentEl.textContent = Math.max(0, total - count);
  }
}


  // CSV Download
  document.getElementById('btn-download-csv')?.addEventListener('click', () => {
    const subj = document.getElementById('att-subject')?.value;
    if (!subj) return showNotification('Select a subject first', 'error');
    window.open(`${API_BASE}/reports/subject/${encodeURIComponent(subj)}/download/csv?token=${encodeURIComponent(ACCESS)}`, '_blank');
  });

  // PDF Download
  document.getElementById('btn-download-pdf')?.addEventListener('click', () => {
    const subj = document.getElementById('att-subject')?.value;
    if (!subj) return showNotification('Select a subject first', 'error');
    window.open(`${API_BASE}/reports/subject/${encodeURIComponent(subj)}/download/pdf?token=${encodeURIComponent(ACCESS)}`, '_blank');
  });


let SETTINGS_PREVIEW_WS = null;
window.previewStreamInSettings = (name) => {
  const grid = document.getElementById('settings-preview-grid');
  if (SETTINGS_PREVIEW_WS) SETTINGS_PREVIEW_WS.close();

  grid.innerHTML = `
        <div class="relative aspect-video bg-black rounded-xl overflow-hidden shadow-2xl">
            <img id="settings-preview-img" class="w-full h-full object-cover" />
            <div class="absolute top-2 left-2 bg-black/60 backdrop-blur-md px-2 py-1 rounded text-[10px] font-bold text-white flex items-center gap-2">
                <span class="size-2 bg-red-500 rounded-full animate-pulse"></span>
                LIVE: ${name}
            </div>
            <button onclick="this.parentElement.remove(); if(SETTINGS_PREVIEW_WS) SETTINGS_PREVIEW_WS.close();" class="absolute top-2 right-2 p-1 bg-white/10 hover:bg-white/20 text-white rounded">
                <span class="material-symbols-outlined text-sm">close</span>
            </button>
        </div>
    `;

  const wsUrl = (API_BASE.replace(/^http/, 'ws')) + `/stream/ws/${encodeURIComponent(name)}?token=${encodeURIComponent(ACCESS)}`;
  SETTINGS_PREVIEW_WS = new WebSocket(wsUrl);
  SETTINGS_PREVIEW_WS.binaryType = 'arraybuffer';
  SETTINGS_PREVIEW_WS.onmessage = (ev) => {
    const blob = new Blob([ev.data], { type: 'image/jpeg' });
    const url = URL.createObjectURL(blob);
    const img = document.getElementById('settings-preview-img');
    if (img) {
      const oldUrl = img.src;
      img.src = url;
      if (oldUrl.startsWith('blob:')) URL.revokeObjectURL(oldUrl);
    }
  };
};

