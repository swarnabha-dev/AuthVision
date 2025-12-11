from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import base64
import os

from ..services import deepface_service
from .. import config
from ..services.auth import require_auth

router = APIRouter()


@router.post("/recognise", dependencies=[Depends(require_auth(require_api_key=True))])
async def recognise(request: Request, file: UploadFile = File(None), image_b64: Optional[str] = Form(None)):
    """
    Unified endpoint that accepts:
    - multipart/form-data with file field `file`, OR
    - multipart/form-data with form field `image_b64`, OR
    - application/json body: {"image_b64": "..."}
    """

    deepface_service.ensure_deepface()
    if deepface_service.DeepFace is None:
        raise HTTPException(500, "DeepFace not installed")

    temp_path = None

    try:
        # Priority: explicit uploaded file
        if file is not None:
            temp_path = await deepface_service.write_upload_to_tempfile(file)
        else:
            # If request is JSON, parse it
            content_type = request.headers.get("content-type", "")
            image_b64_local = None

            if content_type.startswith("application/json"):
                try:
                    body = await request.json()
                except Exception:
                    body = {}
                image_b64_local = body.get("image_b64")
            else:
                # Could be multipart/form with image_b64 as Form field
                image_b64_local = image_b64

            if not image_b64_local:
                raise HTTPException(400, "No image provided. Send multipart file, form field 'image_b64', or JSON {'image_b64': ...}.")

            if image_b64_local.startswith("data:"):
                image_b64_local = image_b64_local.split(",", 1)[1]

            try:
                raw = base64.b64decode(image_b64_local)
            except Exception as e:
                raise HTTPException(400, f"Invalid base64 payload: {e}")

            temp_path = deepface_service.write_bytes_to_tempfile(raw)

        # Run DeepFace.find with the temp file
        try:
            res = deepface_service.DeepFace.find(
                img_path=temp_path,
                db_path=config.ARC_DB_DIR,
                model_name=config.MODEL_NAME,
                detector_backend=config.DETECTOR_BACKEND,
                distance_metric=config.DISTANCE_METRIC,
                normalization=config.NORMALIZATION,
                anti_spoofing=config.ANTI_SPOOFING,
                refresh_database=config.REFRESH_DATABASE,
                threshold=config.THRESHOLD,
                batched = True,
            )

        except ValueError as ve:
            # This usually indicates anti-spoofing detected a fake, or other validation errors.
            # Return 422 Unprocessable Entity with the message so the client can handle it.
            return JSONResponse(
                status_code=422,
                content={"status": "error", "reason": "spoof_detected", "message": str(ve)},
            )

        except Exception as e:
            # Generic catch: return 500 with diagnostic message (can be made less verbose in prod).
            # CHANGED: we convert unexpected errors into HTTP responses rather than letting them bubble.
            return JSONResponse(
                status_code=500,
                content={"status": "error", "reason": "internal_error", "message": str(e)},
            )

        # Normal successful response
        clean = deepface_service._serialize_deepface_result(res)

        # DeepFace returns: [ [ {...}, {...}, ... ] ]
        if isinstance(clean, list) and len(clean) > 0 and isinstance(clean[0], list):
            # keep ONLY the best match (first one)
            for i in range(len(clean)):
                if len(clean[i]) > 0:
                    clean[i] = [clean[i][0]]

        return JSONResponse(clean)


        
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except:
                pass
