from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Form, Query, Response
from ..services.stream import get_capturer, stop_capturer
from ..services.stream import Capturer
from ..services.db import engine, Base, SessionLocal
from ..services import stream as stream_srv
from ..services.auth import require_role, decode_token, User
from ..services.db import get_db
from sqlalchemy.orm import Session
import asyncio

Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/stream")

@router.get('/{name}/snapshot')
async def get_snapshot(name: str, token: str = Query(None)):
    # Simple auth check if token provided, or maybe reliance on cookie? 
    # Frontend usually uses headers but this is a GET potentially for <img> tag (though we will use fetch in JS).
    # If fetch, we can use Authorization header, but here I'll stick to a simple check or looser auth for convenience 
    # OR better: use Depends(require_role) if I change it to use Header?
    # User asked for "capture photo", likely via JS fetch.
    # Let's use Query token for consistency with WS or just open it for now if we assume Admin context.
    # But `require_role` uses HTTPBearer which checks Header.
    # Let's try to trust the caller or add token param.
    # We'll rely on the frontend sending the token in the header if we use fetch.
    
    # Actually, simplest is to use `Depends(require_role(...))` and call via fetch with Auth header.
    pass

@router.get('/{name}/snapshot_image')
async def snapshot(name: str, user=Depends(require_role('admin', 'faculty'))):
    try:
        c = stream_srv.get_capturer(name)
    except Exception:
        raise HTTPException(status_code=404, detail="Stream not found")
        
    q = c.subscribe()
    try:
        # Wait for a frame (timeout 2s)
        jpg = await asyncio.wait_for(q.get(), timeout=2.0)
        return Response(content=jpg, media_type="image/jpeg")
    except asyncio.TimeoutError:
         raise HTTPException(status_code=504, detail="Timeout waiting for frame")
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
    finally:
        c.unsubscribe(q)



@router.post('/start')
def start_stream(name: str = Form(...), url: str = Form(...), keyframe_interval: int = Form(None), user=Depends(require_role('faculty','admin'))):
    c = get_capturer(name, url=url)
    c.keyframe_interval = keyframe_interval or c.keyframe_interval
    c.start()
    return {"started": True, "name": name}


@router.post('/stop')
def stop_stream(name: str = Form(...), user=Depends(require_role('faculty','admin'))):
    stop_capturer(name)
    return {"stopped": True, "name": name}


@router.get('/list')
def list_streams(user=Depends(require_role('faculty', 'admin'))):
    caps = stream_srv.get_all_capturers()
    return [
        {"name": c.name, "url": c.url, "running": c._running}
        for c in caps.values()
    ]


@router.websocket('/ws/{name}')
async def ws_stream(websocket: WebSocket, name: str, token: str | None = Query(None)):
    """Websocket stream endpoint. Clients must provide ?token=<access_token> in the URL.

    We validate the JWT and ensure the user exists before streaming.
    """
    # validate token from query param
    if not token:
        await websocket.close(code=4401)
        return


    try:
        payload = decode_token(token)
        username = payload.get('sub')
        if not username:
             raise ValueError("no sub")
    except Exception:
        await websocket.close(code=4401)
        return

    # verify user exists
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            await websocket.close(code=4401)
            return
    finally:
        db.close()

    await websocket.accept()
    try:
        c = stream_srv.get_capturer(name)
    except Exception:
        await websocket.close(code=1000)
        return

    q = c.subscribe()
    try:
        while True:
            jpg = await q.get()
            try:
                await websocket.send_bytes(jpg)
            except WebSocketDisconnect:
                break
    finally:
        c.unsubscribe(q)
