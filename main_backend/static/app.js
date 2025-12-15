const API_BASE = window.location.origin;
let ACCESS = null;
let LIVE_WS = null;

async function refreshDepartments() {
  if (!ACCESS) return;
  try {
    const r = await fetch(API_BASE + '/departments/list', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (!r.ok) return;
    const deps = await r.json();
    const sub = document.getElementById('sub-dept');
    const reg = document.getElementById('reg-dept');
    const att = document.getElementById('att-dept');
    // clear
    sub.innerHTML = '';
    reg.innerHTML = '';
    if (att) att.innerHTML = '';
    deps.forEach(d => {
      const opt = document.createElement('option'); opt.value = d.name; opt.textContent = d.name; sub.appendChild(opt);
      const opt2 = document.createElement('option'); opt2.value = d.name; opt2.textContent = d.name; reg.appendChild(opt2);
      if (att) { const opt3 = document.createElement('option'); opt3.value = d.name; opt3.textContent = d.name; att.appendChild(opt3); }
    });
  } catch (e) { console.debug('failed to refresh departments', e) }
}

function connectLiveFeed() {
  if (LIVE_WS) return; // already connected
  if (!ACCESS) return;

  const wsUrl = (API_BASE.replace(/^http/, 'ws')) + `/attendance/live`; // No auth on handshake for now, relying on later messages or simple connection
  // Actually, authentication on WebSocket upgrade is tricky without cookies. 
  // Ideally pass token in query param.

  const finalUrl = wsUrl; // skipping auth for demo, or add ?token=...

  LIVE_WS = new WebSocket(finalUrl);
  LIVE_WS.onopen = () => console.log('Live feed connected');
  LIVE_WS.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'recognition') {
        addToFeed(msg.student);
      }
    } catch (e) {
      console.error('feed parse error', e);
    }
  };
  LIVE_WS.onclose = () => { LIVE_WS = null; setTimeout(connectLiveFeed, 3000); };
}

function addToFeed(student) {
  const feed = document.getElementById('live-feed');
  // Create item
  const div = document.createElement('div');
  div.className = 'feed-item';
  const info = `${student.department || ''} ${student.semester || ''}${student.section || ''}`;
  div.innerHTML = `<span class="feed-time">[${student.timestamp}]</span> <strong>${student.name}</strong> (${student.reg_no}) <small>${info}</small>`;

  // Prepend
  feed.insertBefore(div, feed.firstChild);
}

document.getElementById('btn-login').addEventListener('click', async () => {
  const u = document.getElementById('username').value;
  const p = document.getElementById('password').value;
  const form = new URLSearchParams(); form.append('username', u); form.append('password', p);
  const r = await fetch(API_BASE + '/auth/login', { method: 'POST', body: form });
  if (!r.ok) { alert('login failed'); return }
  const j = await r.json();
  ACCESS = j.access_token;
  document.getElementById('tokens').textContent = 'access token set';
  // refresh department lists after login
  await refreshDepartments();
  connectLiveFeed(); // START LISTENING FOR RECOGNITION
});

// connect (view only) - open websocket without starting the stream
document.getElementById('btn-connect').addEventListener('click', async () => {
  const name = document.getElementById('stream-name').value;
  if (!ACCESS) { alert('login first'); return }
  const wsUrl = (API_BASE.replace(/^http/, 'ws')) + `/stream/ws/${encodeURIComponent(name)}?token=${encodeURIComponent(ACCESS)}`;
  const ws = new WebSocket(wsUrl);
  ws.binaryType = 'arraybuffer';
  ws.onmessage = (ev) => {
    const blob = new Blob([ev.data], { type: 'image/jpeg' });
    const url = URL.createObjectURL(blob);
    const img = document.getElementById('video');
    // Revoke previous object URL after new image is loaded to avoid flicker / stale revokes
    img.onload = () => {
      if (window._lastImageUrl && window._lastImageUrl !== url) {
        try { URL.revokeObjectURL(window._lastImageUrl); } catch (e) { }
      }
      window._lastImageUrl = url;
    };
    img.src = url;
  }
  window._stream_ws = ws;
});

// start/stop stream
document.getElementById('btn-start').addEventListener('click', async () => {
  const name = document.getElementById('stream-name').value;
  const url = document.getElementById('stream-url').value;
  if (!ACCESS) { alert('login first'); return }
  // call start
  const form = new URLSearchParams(); form.append('name', name); form.append('url', url);
  const r = await fetch(API_BASE + '/stream/start', { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
  if (!r.ok) { alert('start failed'); return }
  // connect websocket
  const wsUrl = (API_BASE.replace(/^http/, 'ws')) + `/stream/ws/${encodeURIComponent(name)}?token=${encodeURIComponent(ACCESS)}`;
  const ws = new WebSocket(wsUrl);
  ws.binaryType = 'arraybuffer';
  ws.onmessage = (ev) => {
    const blob = new Blob([ev.data], { type: 'image/jpeg' });
    const url = URL.createObjectURL(blob);
    const img = document.getElementById('video');
    img.onload = () => {
      if (window._lastImageUrl && window._lastImageUrl !== url) {
        try { URL.revokeObjectURL(window._lastImageUrl); } catch (e) { }
      }
      window._lastImageUrl = url;
    };
    img.src = url;
  }
  window._stream_ws = ws;
});

document.getElementById('btn-stop').addEventListener('click', async () => {
  const name = document.getElementById('stream-name').value;
  if (!ACCESS) { alert('login first'); return }
  const form = new URLSearchParams(); form.append('name', name);
  await fetch(API_BASE + '/stream/stop', { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
  if (window._stream_ws) { window._stream_ws.close(); window._stream_ws = null }
});

// subjects
document.getElementById('btn-create-sub').addEventListener('click', async () => {
  if (!ACCESS) { alert('login first'); return }
  const code = document.getElementById('sub-code').value;
  const name = document.getElementById('sub-name').value;
  const dept = document.getElementById('sub-dept').value;
  const sem = document.getElementById('sub-sem').value;
  const form = new URLSearchParams(); form.append('code', code); form.append('name', name); form.append('department', dept); form.append('semester', sem);
  const r = await fetch(API_BASE + '/subjects/create', { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
  const txt = await r.text();
  alert('create: ' + r.status + ' ' + txt);
  // refresh departments in case a new dept was created
  await refreshDepartments();
});

document.getElementById('btn-list-sub').addEventListener('click', async () => {
  if (!ACCESS) { alert('login first'); return }
  const r = await fetch(API_BASE + '/subjects/list', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
  const j = await r.json();
  document.getElementById('sub-list').textContent = JSON.stringify(j, null, 2);
});

// attendance trigger (uses currently displayed frame)
// attendance: start session
document.getElementById('btn-trigger').textContent = 'Start Session';
document.getElementById('btn-trigger').addEventListener('click', async () => {
  if (!ACCESS) { alert('login first'); return }

  const streamName = document.getElementById('stream-name').value;
  if (!streamName) { alert('Stream name required (check Stream section)'); return }

  const subjVal = document.getElementById('att-subject').value;
  const deptVal = document.getElementById('att-dept').value;
  const semVal = document.getElementById('att-sem').value;
  if (!subjVal) { alert('please enter subject code'); return }
  if (!deptVal) { alert('please select department'); return }
  if (!semVal) { alert('please enter semester'); return }

  // Clear live feed
  document.getElementById('live-feed').innerHTML = '';

  const form = new URLSearchParams();
  form.append('stream_name', streamName);
  form.append('subject', subjVal);
  form.append('department', deptVal);
  form.append('semester', semVal);
  form.append('section', document.getElementById('att-section').value || 'A');

  const r = await fetch(API_BASE + '/attendance/start', { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
  const j = await r.json();
  document.getElementById('att-result').textContent = 'Start: ' + JSON.stringify(j, null, 2);
});

document.getElementById('btn-stop-att').addEventListener('click', async () => {
  if (!ACCESS) { alert('login first'); return }
  // stop endpoint: remove any running attendance session (no stateful sessions currently maintained, but provide endpoint for future)
  const r = await fetch(API_BASE + '/attendance/stop', { method: 'POST', headers: { 'Authorization': 'Bearer ' + ACCESS } });
  const txt = await r.text();
  document.getElementById('att-result').textContent = `stop: ${r.status} ${txt}`;
});

// Register (student/faculty/admin)
document.getElementById('reg-role').addEventListener('change', () => {
  const role = document.getElementById('reg-role').value;
  const studentFields = document.getElementById('student-fields');
  const profileFields = document.getElementById('profile-fields');
  if (role === 'student') {
    profileFields.style.display = '';
    studentFields.style.display = '';
  } else if (role === 'faculty') {
    profileFields.style.display = '';
    studentFields.style.display = 'none';
  } else {
    // admin
    profileFields.style.display = 'none';
    studentFields.style.display = 'none';
  }
});

// initialize visibility on load
try { document.getElementById('reg-role').dispatchEvent(new Event('change')) } catch (e) { }

document.getElementById('btn-register').addEventListener('click', async () => {
  const regno = document.getElementById('reg-regno').value;
  const pass = document.getElementById('reg-pass').value;
  const role = document.getElementById('reg-role').value || 'student';

  if (!regno || !pass) { alert('please provide username and password'); return }

  // Admin self-register (bootstrap) -- allow unauthenticated admin creation
  if (role === 'admin' && !ACCESS) {
    const form = new URLSearchParams();
    form.append('username', regno);
    form.append('password', pass);
    form.append('role', 'admin');
    const r = await fetch(API_BASE + '/auth/register', { method: 'POST', body: form });
    const txt = await r.text();
    if (!r.ok) { document.getElementById('reg-result').textContent = `admin create failed: ${r.status} ${txt}`; return }
    // auto-login the new admin
    const loginForm = new URLSearchParams(); loginForm.append('username', regno); loginForm.append('password', pass);
    const lr = await fetch(API_BASE + '/auth/login', { method: 'POST', body: loginForm });
    if (lr.ok) { const lj = await lr.json(); ACCESS = lj.access_token; document.getElementById('tokens').textContent = 'admin token set'; }
    document.getElementById('reg-result').textContent = `admin created: ${txt}`;
    return
  }

  // For non-admin creations, admin must be logged in
  if (!ACCESS) { alert('admin login required to create users'); return }

  // if role is student, create via /students/create
  if (role === 'student') {
    const name = document.getElementById('reg-name').value;
    const dept = document.getElementById('reg-dept').value;
    const sem = document.getElementById('reg-sem').value;
    const section = document.getElementById('reg-section').value || 'A';
    if (!name || !dept || !sem) { alert('please fill all student fields'); return }
    const sform = new URLSearchParams();
    sform.append('reg_no', regno);
    sform.append('name', name);
    sform.append('department', dept);
    sform.append('semester', sem);
    sform.append('section', section);
    sform.append('password', pass);
    const r2 = await fetch(API_BASE + '/students/create', { method: 'POST', body: sform, headers: { 'Authorization': 'Bearer ' + ACCESS } });
    const txt2 = await r2.text();
    if (!r2.ok) { document.getElementById('reg-result').textContent = `student create failed: ${r2.status} ${txt2}`; return }
    document.getElementById('reg-result').textContent = `student created successfully`;
    return
  }

  // if role is faculty, create via /faculty/create
  if (role === 'faculty') {
    const name = document.getElementById('reg-name').value;
    const dept = document.getElementById('reg-dept').value;
    if (!name || !dept) { alert('please fill all faculty fields'); return }
    const fform = new URLSearchParams();
    fform.append('username', regno);
    fform.append('name', name);
    fform.append('department', dept);
    fform.append('password', pass);
    const r3 = await fetch(API_BASE + '/faculty/create', { method: 'POST', body: fform, headers: { 'Authorization': 'Bearer ' + ACCESS } });
    const txt3 = await r3.text();
    if (!r3.ok) { document.getElementById('reg-result').textContent = `faculty create failed: ${r3.status} ${txt3}`; return }
    document.getElementById('reg-result').textContent = `faculty created successfully`;
    return
  }

  // Admin creations via /auth/register (requires admin token if bootstrap phase passed)
  alert('For creating additional admins, use /auth/register manually or bootstrap logic');
});

// Enrollment photos upload
document.getElementById('btn-enroll-photos').addEventListener('click', async () => {
  const regno = document.getElementById('enroll-regno').value;
  const input = document.getElementById('file-input');
  if (!regno) { alert('enter registration no'); return }
  if (!ACCESS) { alert('login first'); return }
  if (!input.files || input.files.length === 0) { alert('select files'); return }
  const fd = new FormData();
  for (let i = 0; i < input.files.length; i++) fd.append('files', input.files[i], input.files[i].name);
  const r = await fetch(API_BASE + `/students/${encodeURIComponent(regno)}/enroll-photos`, { method: 'POST', body: fd, headers: { 'Authorization': 'Bearer ' + ACCESS } });
  const txt = await r.text();
  document.getElementById('enroll-result').textContent = `status: ${r.status} detail: ${txt}`;
});

// Reports
document.getElementById('btn-rep-sub').addEventListener('click', async () => {
  const subId = document.getElementById('rep-sub-id').value;
  if (!subId) { alert('enter subject code'); return }
  if (!ACCESS) { alert('login first'); return }

  const r = await fetch(API_BASE + `/reports/subject/${subId}/summary`, { headers: { 'Authorization': 'Bearer ' + ACCESS } });
  if (!r.ok) {
    document.getElementById('rep-sub-result').textContent = `error: ${r.status} ${await r.text()}`;
    return;
  }
  const j = await r.json();
  document.getElementById('rep-sub-result').textContent = JSON.stringify(j, null, 2);
});

document.getElementById('btn-rep-student').addEventListener('click', async () => {
  const reg = document.getElementById('rep-student-reg').value;
  if (!reg) { alert('enter student reg no'); return }
  if (!ACCESS) { alert('login first'); return }

  const r = await fetch(API_BASE + `/reports/student/${encodeURIComponent(reg)}/attendance`, { headers: { 'Authorization': 'Bearer ' + ACCESS } });
  if (!r.ok) {
    document.getElementById('rep-student-result').textContent = `error: ${r.status} ${await r.text()}`;
    return;
  }
  const j = await r.json();
  document.getElementById('rep-student-result').textContent = JSON.stringify(j, null, 2);
});
