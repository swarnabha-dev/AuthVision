from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List

from .. import config
from ..services import deepface_service
from ..services.auth import require_auth

router = APIRouter()


@router.post("/refresh-db", dependencies=[Depends(require_auth(require_api_key=True))])
async def refresh_db(identity: str = Form(...), files: List[UploadFile] = File(...)):
    """
    Register multiple images for ONE identity (student ID).
    """

    deepface_service.ensure_deepface()
    if deepface_service.DeepFace is None:
        raise HTTPException(500, "DeepFace not installed")

    # Read all files -> bytes
    files_bytes = [await f.read() for f in files]

    # Import arcface_refresh lazily to avoid heavy deepface imports at module import time
    from ..services import arcface_refresh

    # Add all to PKL
    results = arcface_refresh.add_faces_from_uploads(files_bytes, identity)

    return JSONResponse({"status": "done", "identity": identity, "results": results})
