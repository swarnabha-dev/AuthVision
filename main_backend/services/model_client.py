import threading
import asyncio
import time
from typing import Optional, Dict
import httpx
import jwt

from .. import config

import logging
# Module-level state
LOG = logging.getLogger("main_backend.model_client")
_lock = threading.Lock()
_async_lock = asyncio.Lock()
_access_token: Optional[str] = None
_refresh_token: Optional[str] = None
_api_key: Optional[str] = None
_access_exp: Optional[int] = None


def _decode_exp(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
        return int(payload.get("exp")) if payload.get("exp") else None
    except Exception:
        return None


def ensure_auth_sync() -> None:
    """Ensure we have access token / api key (synchronous)."""
    global _access_token, _refresh_token, _api_key, _access_exp
    with _lock:
        now = int(time.time())
        if _access_token and _access_exp:
            remaining = _access_exp - now
            if remaining > config.MODEL_SERVICE_REFRESH_MARGIN:
                return
            else:
                 LOG.debug("token expired or close to expiry: exp=%s now=%s margin=%s", _access_exp, now, config.MODEL_SERVICE_REFRESH_MARGIN)
        else:
             LOG.debug("no token available")

        # perform login
        LOG.info("performing login to model service")
        if not config.MODEL_SERVICE_USER or not config.MODEL_SERVICE_PASS:
            return
        url = f"{config.MODEL_SERVICE_URL}/login"
        with httpx.Client() as client:
            resp = client.post(url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
            # If login failed because user does not exist, try to register then login again
            if resp.status_code == 401:
                # attempt register
                try:
                    reg_url = f"{config.MODEL_SERVICE_URL}/register"
                    rreg = client.post(reg_url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
                    if rreg.status_code not in (200, 201):
                        raise RuntimeError(f"model service register failed: {rreg.status_code} {rreg.text}")
                    # retry login
                    resp = client.post(url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
                except Exception as e:
                    raise RuntimeError(f"model service login/register failed: {e}")

            if resp.status_code != 200:
                raise RuntimeError(f"model service login failed: {resp.status_code} {resp.text}")
            data = resp.json()
            _access_token = data.get("access_token")
            _refresh_token = data.get("refresh_token")
            # If exp claim is missing, default to 5 minutes (300s) from now
            exp = _decode_exp(_access_token) if _access_token else None
            _access_exp = exp if exp else (int(time.time()) + 300)
            LOG.info("login successful. token set. exp=%s (calculated fallback=%s)", _access_exp, not exp)

            # create api key if not present
            if not _api_key:
                ak_url = f"{config.MODEL_SERVICE_URL}/apikey/create"
                r2 = client.post(ak_url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
                if r2.status_code == 200:
                    try:
                        _api_key = r2.json().get("api_key")
                    except Exception:
                        _api_key = None


async def ensure_auth_async() -> None:
    global _access_token, _refresh_token, _api_key, _access_exp
    async with _async_lock:
        now = int(time.time())
        if _access_token and _access_exp and (_access_exp - config.MODEL_SERVICE_REFRESH_MARGIN) > now:
            return

        if not config.MODEL_SERVICE_USER or not config.MODEL_SERVICE_PASS:
            return
        url = f"{config.MODEL_SERVICE_URL}/login"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
            if resp.status_code == 401:
                # try register then login
                try:
                    reg_url = f"{config.MODEL_SERVICE_URL}/register"
                    rreg = await client.post(reg_url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
                    if rreg.status_code not in (200, 201):
                        raise RuntimeError(f"model service register failed: {rreg.status_code} {rreg.text}")
                    resp = await client.post(url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
                except Exception as e:
                    raise RuntimeError(f"model service login/register failed: {e}")

            if resp.status_code != 200:
                raise RuntimeError(f"model service login failed: {resp.status_code} {resp.text}")
            data = resp.json()
            _access_token = data.get("access_token")
            _refresh_token = data.get("refresh_token")
            # If exp claim is missing, default to 5 minutes (300s) from now
            exp = _decode_exp(_access_token) if _access_token else None
            _access_exp = exp if exp else (int(time.time()) + 300)

            if not _api_key:
                ak_url = f"{config.MODEL_SERVICE_URL}/apikey/create"
                r2 = await client.post(ak_url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
                if r2.status_code == 200:
                    try:
                        _api_key = r2.json().get("api_key")
                    except Exception:
                        _api_key = None


def get_headers_sync() -> Dict[str, str]:
    ensure_auth_sync()
    headers = {}
    if _api_key:
        headers["x-api-key"] = _api_key
    if _access_token:
        headers["Authorization"] = f"Bearer {_access_token}"
    return headers


async def get_headers_async() -> Dict[str, str]:
    await ensure_auth_async()
    headers = {}
    if _api_key:
        headers["x-api-key"] = _api_key
    if _access_token:
        headers["Authorization"] = f"Bearer {_access_token}"
    return headers
