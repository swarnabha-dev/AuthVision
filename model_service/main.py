# Consolidated DeepFace helpers: use the shared implementations in services.deepface_service
import os
from . import config

if not os.path.isdir(config.DEEPFACE_HOME):
    os.makedirs(config.DEEPFACE_HOME, exist_ok=True)


os.environ["DEEPFACE_HOME"] = str(config.DEEPFACE_HOME)


from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.responses import JSONResponse
from typing import List, Optional
import io
import base64
import traceback
import tempfile
from pathlib import Path
import logging
import time
from logging.handlers import TimedRotatingFileHandler

# Import the shared DeepFace helper implementations from services
from .services import deepface_service


# ---------------------------------------------------
# FastAPI App
# ---------------------------------------------------

app = FastAPI(title="ArcFace Recognition Service")

# ---------------------------------------------------
# Logging middleware and configuration
# ---------------------------------------------------
logger = logging.getLogger("model_service")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    # console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # file handler (rotates daily)
    try:
        log_dir = Path(config.DEEPFACE_HOME)
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = TimedRotatingFileHandler(log_dir / "model_service.log", when="midnight", backupCount=7, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        # fall back to console-only logging
        logger.exception("Could not create file handler for logging; continuing with console logging")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log each incoming request and its response status, time, and basic meta.

    Sensitive headers are not logged; presence of auth headers is indicated instead.
    """
    start_time = time.time()
    client_host = None
    try:
        client = request.client
        if client:
            client_host = client.host
    except Exception:
        client_host = None

    # extract basic info
    method = request.method
    path = request.url.path
    qs = str(request.url.query) if request.url.query else ""
    ua = request.headers.get("user-agent", "")
    has_auth = "authorization" in request.headers
    has_api_key = "x-api-key" in request.headers

    logger.info(f"-> {method} {path}?{qs} from={client_host} ua='{ua}' auth={has_auth} api_key={has_api_key}")

    try:
        response = await call_next(request)
    except Exception as exc:
        # log the exception and re-raise
        elapsed = (time.time() - start_time) * 1000
        logger.exception(f"!! {method} {path} from={client_host} raised error after={elapsed:.2f}ms: {exc}")
        raise

    elapsed = (time.time() - start_time) * 1000
    # response may not have content-length set, so we show status and time
    logger.info(f"<- {method} {path} status={response.status_code} time={elapsed:.2f}ms")
    return response


@app.get("/")
async def root():
    # Ensure DeepFace is imported and (optionally) preload the model
    deepface_service.ensure_deepface()

    deepface_info = {
        "available": deepface_service.DeepFace is not None,
        "preloaded": bool(deepface_service.DEEPFACE_MODELS),
        "model_name": config.MODEL_NAME,
        "detector": config.DETECTOR_BACKEND,
        "normalization": config.NORMALIZATION,
    }

    return {"status": "ok", "pkl": config.ARC_PKL_PATH, "deepface": deepface_info}


# Include modular routers
from .routes import refresh_db as refresh_db_route
from .routes import detect as detect_route
from .routes import recognise as recognise_route
from .routes import auth as auth_route

app.include_router(refresh_db_route.router)
app.include_router(detect_route.router)
app.include_router(recognise_route.router)
app.include_router(auth_route.router)
