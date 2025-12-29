
# Force rewrite connectLiveFeed in app.js - Retry with re import
import re

file_path = 'main_backend/static/dashboard/app.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove any existing connectLiveFeed definition
content = re.sub(r'function\s+connectLiveFeed\s*\([^)]*\)\s*\{(?:[^{}]*|\{(?:[^{}]*|\{[^{}]*\})*\})*\}', '', content)
content = re.sub(r'let\s+LIVE_FEED_WS\s*=\s*null;', '', content)

# Append clean implementation
new_logic = """
let LIVE_FEED_WS = null;
function connectLiveFeed() {
    const streamName = document.getElementById('stream-name')?.value;
    if (!streamName || !ACCESS) return;
    
    // Cleanup old
    if (LIVE_FEED_WS) {
        LIVE_FEED_WS.close();
        LIVE_FEED_WS = null;
    }

    const video = document.getElementById('video');
    const placeholder = document.getElementById('video-placeholder');
    const indicator = document.getElementById('live-indicator');
    
    // Reset UI state
    if (video) {
        video.style.display = 'block';
        video.src = ''; 
    }
    if (placeholder) placeholder.style.display = 'none';
    if (indicator) indicator.classList.remove('hidden');

    const wsUrl = (API_BASE.replace(/^http/, 'ws')) + `/stream/ws/${encodeURIComponent(streamName)}?token=${encodeURIComponent(ACCESS)}`;
    console.debug('Connecting to Live Feed:', wsUrl);
    
    LIVE_FEED_WS = new WebSocket(wsUrl);
    LIVE_FEED_WS.binaryType = 'arraybuffer';
    
    LIVE_FEED_WS.onopen = () => {
        console.debug('Live feed connected');
        if (indicator) indicator.classList.remove('hidden');
    };
    
    LIVE_FEED_WS.onmessage = (ev) => {
        const blob = new Blob([ev.data], { type: 'image/jpeg' });
        const url = URL.createObjectURL(blob);
        if (video) {
            const oldUrl = video.src;
            video.src = url;
            if (oldUrl && oldUrl.startsWith('blob:')) URL.revokeObjectURL(oldUrl);
        }
    };
    
    LIVE_FEED_WS.onerror = (e) => {
        console.debug('Live feed WS error', e);
        if (indicator) indicator.classList.add('hidden');
    };
    
    LIVE_FEED_WS.onclose = () => {
        console.debug('Live feed disconnected');
        if (indicator) indicator.classList.add('hidden');
    };
}
"""

content += "\n" + new_logic

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Forced rewrite of connectLiveFeed (Success)")
