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
_access_exp: Optional[int] = None

_refresh_token: Optional[str] = None
_refresh_exp: Optional[int] = None

_api_key: Optional[str] = None

def _is_valid(exp: Optional[int], margin: int = 30) -> bool:
    if not exp: return False
    return (exp - margin) > int(time.time())

def ensure_auth_sync() -> None:
    """Ensure we have access token / api key (synchronous)."""
    global _access_token, _refresh_token, _api_key, _access_exp, _refresh_exp
    with _lock:
        now = int(time.time())
        # 1. Check Access Token
        if _access_token and _is_valid(_access_exp):
            return # Valid

        # 2. Try Refresh
        refreshed = False
        if _refresh_token and _is_valid(_refresh_exp):
            LOG.info("refreshing access token (expires in %ds)", (_access_exp - now) if _access_exp else -1)
            try:
                url = f"{config.MODEL_SERVICE_URL}/refresh"
                with httpx.Client() as client:
                    resp = client.post(url, data={"refresh_token": _refresh_token}, timeout=20.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        _access_token = data.get("access_token")
                        _refresh_token = data.get("refresh_token")
                        _access_exp = data.get("access_exp")
                        _refresh_exp = data.get("refresh_exp")
                        LOG.info("token refresh successful. access_exp=%s refresh_exp=%s", _access_exp, _refresh_exp)
                        refreshed = True
                    else:
                        LOG.warning("token refresh failed: %s %s", resp.status_code, resp.text)
            except Exception as e:
                LOG.error("token refresh exception: %s", e)
        
        if refreshed:
            # check api key
            if not _api_key: _ensure_api_key_sync()
            return

        # 3. Fallback to Full Login
        LOG.info("performing full login to model service")
        if not config.MODEL_SERVICE_USER or not config.MODEL_SERVICE_PASS:
            LOG.error("MODEL_SERVICE_USER/PASS not configured")
            return

        url = f"{config.MODEL_SERVICE_URL}/login"
        with httpx.Client() as client:
            resp = client.post(url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
            
            # Auto-register if 401
            if resp.status_code == 401:
                LOG.info("login 401, attempting registration")
                try:
                    reg_url = f"{config.MODEL_SERVICE_URL}/register"
                    rreg = client.post(reg_url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
                    if rreg.status_code not in (200, 201):
                         LOG.error("register failed: %s", rreg.text)
                    resp = client.post(url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
                except Exception as e:
                    LOG.error("register/login exception: %s", e)

            if resp.status_code != 200:
                LOG.error("login failed: %s %s", resp.status_code, resp.text)
                return
            
            data = resp.json()
            _access_token = data.get("access_token")
            _refresh_token = data.get("refresh_token")
            _access_exp = data.get("access_exp")
            _refresh_exp = data.get("refresh_exp")
            LOG.info("login successful. access_exp=%s refresh_exp=%s", _access_exp, _refresh_exp)
            
            _ensure_api_key_sync()


def _ensure_api_key_sync():
    global _api_key
    if _api_key: return
    try:
        url = f"{config.MODEL_SERVICE_URL}/apikey/create"
        with httpx.Client() as client:
            r = client.post(url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=10.0)
            if r.status_code == 200:
                _api_key = r.json().get("api_key")
                LOG.info("obtained api key")
    except Exception as e:
        LOG.warning("failed to obtain api key: %s", e)


async def ensure_auth_async() -> None:
    global _access_token, _refresh_token, _api_key, _access_exp, _refresh_exp
    async with _async_lock:
        now = int(time.time())
        # 1. Check Access
        if _access_token and _is_valid(_access_exp):
            return

        # 2. Try Refresh
        refreshed = False
        if _refresh_token and _is_valid(_refresh_exp):
             LOG.info("async refreshing access token")
             try:
                 url = f"{config.MODEL_SERVICE_URL}/refresh"
                 async with httpx.AsyncClient() as client:
                     resp = await client.post(url, data={"refresh_token": _refresh_token}, timeout=20.0)
                     if resp.status_code == 200:
                         data = resp.json()
                         _access_token = data.get("access_token")
                         _refresh_token = data.get("refresh_token")
                         _access_exp = data.get("access_exp")
                         _refresh_exp = data.get("refresh_exp")
                         LOG.info("async refresh successful")
                         refreshed = True
                     else:
                         LOG.warning("async refresh failed: %s", resp.status_code)
             except Exception as e:
                 LOG.error("async refresh exception: %s", e)
        
        if refreshed:
            if not _api_key: await _ensure_api_key_async()
            return

        # 3. Full Login
        LOG.info("performing async full login")
        if not config.MODEL_SERVICE_USER or not config.MODEL_SERVICE_PASS: return

        url = f"{config.MODEL_SERVICE_URL}/login"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
            if resp.status_code == 401:
                # register
                reg_url = f"{config.MODEL_SERVICE_URL}/register"
                try:
                    await client.post(reg_url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
                    resp = await client.post(url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=30.0)
                except Exception as e:
                     LOG.error("async reg/login failed: %s", e)

            if resp.status_code == 200:
                data = resp.json()
                _access_token = data.get("access_token")
                _refresh_token = data.get("refresh_token")
                _access_exp = data.get("access_exp")
                _refresh_exp = data.get("refresh_exp")
                LOG.info("async login successful. exp=%s", _access_exp)
                await _ensure_api_key_async()
            else:
                LOG.error("async login failed: %s", resp.text)


async def _ensure_api_key_async():
    global _api_key
    if _api_key: return
    try:
        url = f"{config.MODEL_SERVICE_URL}/apikey/create"
        async with httpx.AsyncClient() as client:
            r = await client.post(url, data={"username": config.MODEL_SERVICE_USER, "password": config.MODEL_SERVICE_PASS}, timeout=10.0)
            if r.status_code == 200:
                _api_key = r.json().get("api_key")
    except Exception as e:
        LOG.warning("async api key fetch failed: %s", e)


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
