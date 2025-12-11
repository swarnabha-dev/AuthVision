from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
import os

from ..services import deepface_service
from .. import config
from ..services.auth import require_auth

router = APIRouter()


@router.post("/detect", dependencies=[Depends(require_auth(require_api_key=True))])
async def detect(img1: UploadFile = File(...), img2: UploadFile = File(...)):
    deepface_service.ensure_deepface()
    if deepface_service.DeepFace is None:
        raise HTTPException(500, "DeepFace not installed")

    p1 = await deepface_service.write_upload_to_tempfile(img1)
    p2 = await deepface_service.write_upload_to_tempfile(img2)

    try:
        res = deepface_service.DeepFace.verify(
            img1_path=p1,
            img2_path=p2,
            model_name=config.MODEL_NAME,
            detector_backend=config.DETECTOR_BACKEND,
            distance_metric=config.DISTANCE_METRIC,
        )
        return JSONResponse(deepface_service._serialize_deepface_result(res))
    finally:
        for p in (p1, p2):
            try:
                os.remove(p)
            except:
                pass
