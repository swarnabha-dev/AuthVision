from fastapi import FastAPI
from . import config
import logging

# set up basic logging for the main_backend app
LOG = logging.getLogger("main_backend")
LOG.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename=str(__file__) + '.log', mode='a', encoding='utf-8')
fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
handler.setFormatter(fmt)
LOG.addHandler(handler)
LOG.addHandler(logging.StreamHandler())

app = FastAPI(title="Main Backend - Attendance & Stream Gateway")


# Request logging middleware - logs method, path, status and duration
@app.middleware("http")
async def log_requests(request, call_next):
    import time
    try:
        LOG.info("HTTP request start: %s %s", request.method, request.url.path)
    except Exception:
        pass
        
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        try:
            LOG.exception("Unhandled exception for %s %s", request.method, request.url.path)
        except Exception:
            pass
        raise
    duration = (time.time() - start) * 1000.0
    
    try:
        LOG.info("HTTP request finished: %s %s -> %s (%.2f ms)", request.method, request.url.path, response.status_code, duration)
    except Exception:
        pass
    return response

# include routers
from .routers import auth as auth_router
from .routers import students as students_router
from .routers import attendance as attendance_router
from .routers import streaming as streaming_router
from .routers import subjects as subjects_router
from .routers import departments as departments_router
from .routers import faculty as faculty_router
from .routers import reports as reports_router
from .services.auth import get_current_user

from fastapi import Depends
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app.include_router(auth_router.router)
# secure other routers - require authentication (roles enforced per-endpoint)
app.include_router(students_router.router, tags=["students"], dependencies=[Depends(get_current_user)])
app.include_router(subjects_router.router, tags=["subjects"], dependencies=[Depends(get_current_user)])
# attendance router contains a WebSocket endpoint (/attendance/live)
# Do NOT apply HTTP dependency globally. Endpoints are protected individually.
app.include_router(attendance_router.router, tags=["attendance"])
app.include_router(departments_router.router, tags=["departments"], dependencies=[Depends(get_current_user)])
app.include_router(faculty_router.router, tags=["faculty"], dependencies=[Depends(get_current_user)])
app.include_router(reports_router.router, tags=["reports"], dependencies=[Depends(get_current_user)])
from .routers import conferences as conferences_router
app.include_router(conferences_router.router, tags=["conferences"], dependencies=[Depends(get_current_user)])
# streaming router contains a WebSocket endpoint which performs its own token check
# Do NOT apply the HTTP request-based `get_current_user` dependency at router-level
# because it uses HTTPBearer (expects a Request) and will fail for WebSocket scopes.
app.include_router(streaming_router.router)

# mount static frontend if present
static_dir = Path(__file__).parent / 'static'
if static_dir.exists():
    app.mount('/static', StaticFiles(directory=str(static_dir)), name='static')

@app.get("/health")
def health():
    return {"status": "ok"}
