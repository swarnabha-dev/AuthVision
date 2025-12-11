import threading
import cv2
import asyncio
import base64
import time
import logging
from typing import Dict, Set, Callable, Any
import httpx
from .. import config

LOG = logging.getLogger("main_backend.stream")
LOG.setLevel(logging.DEBUG)

# Simple RTSP capturer that captures frames in a background thread and
# allows async subscribers to receive JPEG bytes. It also can send keyframes
# to the model service for recognition.


class Capturer:
    def __init__(self, url: str, name: str = None, keyframe_interval: int = None):
        self.url = url
        self.name = name or url
        self.keyframe_interval = keyframe_interval or config.DEFAULT_KEYFRAME_INTERVAL
        self._running = False
        self._thread = None
        self._subscribers = set()  # set of asyncio.Queue
        self._lock = threading.Lock()

    def start(self):
        if self._running:
            return
        self._running = True
        LOG.info("Starting capturer '%s' -> %s", self.name, self.url)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            LOG.info("Stopping capturer '%s'", self.name)
            self._thread.join(timeout=1.0)

    def subscribe(self):
        # larger buffer for subscribers to tolerate bursts
        q = asyncio.Queue(maxsize=32)
        with self._lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            try:
                self._subscribers.remove(q)
            except KeyError:
                pass

    def _broadcast(self, jpg_bytes: bytes):
        # notify subscribers (async queues)
        for q in list(self._subscribers):
            try:
                q.put_nowait(jpg_bytes)
            except asyncio.QueueFull:
                # drop frame silently (or debug log) to avoid spam/crashes
                # self.unsubscribe(q) # Do not unsubscribe, just drop frame. Client might be slow.
                pass

    def _run(self):
        # try opening with FFMPEG backend first (Windows builds may need CAP_FFMPEG)
        cap = None
        try_backends = []
        try:
            # prefer FFMPEG if available
            try_backends.append(cv2.CAP_FFMPEG)
        except Exception:
            pass
        try:
            try_backends.append(0)
        except Exception:
            try_backends = [0]

        for backend in try_backends:
            try:
                LOG.debug("Attempting to open capture '%s' with backend %s", self.url, backend)
                cap = cv2.VideoCapture(self.url, backend)
                # small delay to allow open
                time.sleep(0.2)
                if cap is not None and cap.isOpened():
                    LOG.info("Opened capture '%s' using backend %s", self.url, backend)
                    break
                else:
                    LOG.warning("Failed to open capture '%s' with backend %s", self.url, backend)
                    try:
                        cap.release()
                    except Exception:
                        pass
                    cap = None
            except Exception as e:
                LOG.exception("Error opening capture with backend %s: %s", backend, e)
                cap = None

        if cap is None:
            LOG.error("Unable to open video capture for %s", self.url)
            return
        frame_idx = 0
        client = httpx.AsyncClient()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Try to minimize decoder latency and buffer size where supported
        try:
            # CAP_PROP_BUFFERSIZE may not be supported on all builds; ignore errors
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        async def send_to_model(b64img: str):
            try:
                # call model layer recognise endpoint (JSON image_b64)
                from .model_client import get_headers_async
                url = f"{config.MODEL_SERVICE_URL}/recognise"
                headers = await get_headers_async()
                resp = await client.post(url, json={"image_b64": b64img}, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                return None

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.02)
                    continue
                frame_idx += 1
                # downscale frame a bit to reduce decode/encode load (keep aspect ratio)
                try:
                    h, w = frame.shape[:2]
                    max_dim = max(w, h)
                    if max_dim > 800:
                        scale = 800 / float(max_dim)
                        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
                except Exception:
                    # ignore resize errors and proceed with original frame
                    pass

                # encode to JPEG
                try:
                    ret2, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                except Exception:
                    LOG.exception("imencode failed for frame in '%s'", self.name)
                    continue
                if not ret2:
                    continue
                jpg_bytes = jpg.tobytes()
                # broadcast to subscribers
                self._broadcast(jpg_bytes)

                # keyframe send logic removed - attendance service handles recognition now
                # if frame_idx % self.keyframe_interval == 0:
                #     ...

                # small sleep to avoid hogging CPU
                time.sleep(0.01)
        finally:
            try:
                loop.run_until_complete(client.aclose())
            except Exception:
                LOG.exception("Error closing httpx client")
            cap.release()


# manager for multiple streams
_CAPTURERS: Dict[str, Capturer] = {}


def get_capturer(name: str, url: str = None) -> Capturer:
    if name in _CAPTURERS:
        return _CAPTURERS[name]
    if not url:
        raise RuntimeError("capturer not found and url not provided")
    c = Capturer(url=url, name=name)
    _CAPTURERS[name] = c
    return c


def stop_capturer(name: str):
    c = _CAPTURERS.pop(name, None)
    if c:
        c.stop()
