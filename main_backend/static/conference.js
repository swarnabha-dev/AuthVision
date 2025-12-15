const API_BASE = window.location.origin;
let ACCESS = null;
let LIVE_WS = null;

// Auth
document.getElementById('btn-login').addEventListener('click', async () => {
    const u = document.getElementById('username').value;
    const p = document.getElementById('password').value;
    const form = new URLSearchParams(); form.append('username', u); form.append('password', p);
    try {
        const r = await fetch(API_BASE + '/auth/login', { method: 'POST', body: form });
        if (!r.ok) { alert('login failed'); return }
        const j = await r.json();
        ACCESS = j.access_token;
        document.getElementById('auth-status').textContent = 'Logged In';
        document.getElementById('app').style.display = 'block';
        loadConferences();
    } catch (e) { alert('error ' + e) }
});

// Create Conf
document.getElementById('btn-create-conf').addEventListener('click', async () => {
    const code = document.getElementById('conf-code').value;
    const name = document.getElementById('conf-name').value;
    const desc = document.getElementById('conf-desc').value;
    const start = document.getElementById('conf-start').value;
    const end = document.getElementById('conf-end').value;

    if (!code || !name) return alert('code/name required');

    const form = new URLSearchParams();
    form.append('code', code); form.append('name', name); form.append('description', desc);
    form.append('start_date', start || new Date().toISOString().split('T')[0]);
    form.append('end_date', end || new Date().toISOString().split('T')[0]);

    const r = await fetch(API_BASE + '/conferences/create', { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (r.ok) {
        alert('Created');
        loadConferences();
    } else {
        alert('Failed: ' + await r.text());
    }
});

async function loadConferences() {
    const r = await fetch(API_BASE + '/conferences/list', { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    const list = await r.json();
    const container = document.getElementById('conf-list');
    container.innerHTML = '';
    list.forEach(c => {
        const div = document.createElement('div');
        div.className = 'conf-card';
        div.innerHTML = `<strong>${c.name}</strong> (${c.code}) - ${c.start_date} <button onclick="manageConf('${c.code}', '${c.name.__proto__.toString.call(c.name) === '[object String]' ? c.name.replace(/'/g, "\\'") : c.name}')">Manage</button>`;
        container.appendChild(div);
    });
}

window.manageConf = async (code, name) => {
    document.getElementById('manage-conf').style.display = 'block';
    document.getElementById('current-conf-title').textContent = 'Manage: ' + name;
    document.getElementById('current-conf-code').value = code;
    loadGuests(code);
};

document.getElementById('btn-refresh-conf').addEventListener('click', loadConferences);

// Guests
document.getElementById('btn-add-guest').addEventListener('click', async () => {
    const code = document.getElementById('current-conf-code').value;
    const name = document.getElementById('guest-name').value;
    const email = document.getElementById('guest-email').value;
    const org = document.getElementById('guest-org').value;
    const file = document.getElementById('guest-photo').files[0];

    if (!name || !file) return alert('Name and Photo required');

    const fd = new FormData();
    fd.append('name', name);
    fd.append('email', email);
    fd.append('organization', org);
    fd.append('file', file);

    const r = await fetch(API_BASE + `/conferences/${code}/guests/add`, { method: 'POST', body: fd, headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (r.ok) {
        document.getElementById('add-guest-res').textContent = 'Guest Added. Remember to RESTART Model Service manually if hot-reload is off.';
        loadGuests(code);
    } else {
        alert('Failed ' + await r.text());
    }
});

async function loadGuests(code) {
    const r = await fetch(API_BASE + `/conferences/${code}/guests`, { headers: { 'Authorization': 'Bearer ' + ACCESS } });
    const list = await r.json();
    const div = document.getElementById('guest-list-container');
    div.innerHTML = list.map(g => `<div>${g.name} (${g.organization})</div>`).join('');
}

// Session & Live Feed
function connectLiveFeed() {
    if (LIVE_WS) return;
    const wsUrl = (API_BASE.replace(/^http/, 'ws')) + `/attendance/live`;
    LIVE_WS = new WebSocket(wsUrl);
    LIVE_WS.onmessage = (ev) => {
        try {
            const msg = JSON.parse(ev.data);
            if (msg.type === 'recognition') {
                addToFeed(msg.student);
            }
        } catch (e) { }
    };
    LIVE_WS.onclose = () => { LIVE_WS = null; setTimeout(connectLiveFeed, 3000); };
}

function addToFeed(p) {
    const feed = document.getElementById('live-feed');
    const div = document.createElement('div');
    div.className = 'feed-item';

    // Check if guest
    const typeLabel = p.is_guest ? '<span style="background:orange;color:white;padding:2px;border-radius:3px;">GUEST</span>' : '';
    const details = p.is_guest ? `${p.department || ''}` : `${p.department} ${p.semester}${p.section}`; // department field reused for org

    div.innerHTML = `<span class="feed-time">[${p.timestamp}]</span> ${typeLabel} <strong>${p.name}</strong> <small>(${p.reg_no})</small> - ${details} <b>Conf: ${p.confidence}%</b>`;
    feed.insertBefore(div, feed.firstChild);
}

document.getElementById('btn-start-session').addEventListener('click', async () => {
    const code = document.getElementById('current-conf-code').value;
    const stream = document.getElementById('stream-name').value;

    const form = new URLSearchParams(); form.append('stream_name', stream);

    // Ensure stream is started first? 
    // Just try starting session, it validates stream

    const r = await fetch(API_BASE + `/conferences/${code}/start-session`, { method: 'POST', body: form, headers: { 'Authorization': 'Bearer ' + ACCESS } });
    if (r.ok) {
        document.getElementById('live-feed').innerHTML = '';
        connectLiveFeed();
        alert('Session Started');
    } else {
        alert('Failed: ' + await r.text());
    }
});

document.getElementById('btn-stop-session').addEventListener('click', async () => {
    await fetch(API_BASE + '/attendance/stop', { method: 'POST', headers: { 'Authorization': 'Bearer ' + ACCESS } });
    alert('Stopped');
});
