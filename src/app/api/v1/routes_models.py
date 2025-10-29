"""
Model management routes.
"""

from fastapi import APIRouter

from app.models.detection_models import (
    ModelActivateRequest,
    ModelActivateResponse,
    ModelListResponse,
    ModelMeta,
)

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=ModelListResponse)
def list_models() -> ModelListResponse:
    """List all available models.

    Returns:
        ModelListResponse with list of models
    """
    # TODO: Query MLflow model registry in Module 14
    # Return stub data
    dummy_models = [
        ModelMeta(
            name="yolov10-tiny",
            version="1.0.0",
            stage="production",
            checksum="a" * 64,
        ),
        ModelMeta(
            name="adaface",
            version="1.0.0",
            stage="production",
            checksum="b" * 64,
        ),
    ]
    return ModelListResponse(models=dummy_models)


@router.post("/activate", response_model=ModelActivateResponse)
def activate_model(request: ModelActivateRequest) -> ModelActivateResponse:
    """Activate a specific model version.

    Args:
        request: Model activation request

    Returns:
        ModelActivateResponse with activation status
    """
    # TODO: Implement model activation logic in Module 14
    return ModelActivateResponse(
        success=True,
        message=f"Model {request.name} v{request.version} activated (STUB)",
    )
