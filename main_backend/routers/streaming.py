from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Form, Query
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
