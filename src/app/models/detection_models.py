"""
Detection-related Pydantic v2 models with strict typing.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelMeta(BaseModel):
    """Model metadata information."""

    model_config = ConfigDict(strict=True)

    name: str = Field(..., description="Model name", min_length=1)
    version: str = Field(..., description="Model version", min_length=1)
    stage: str = Field(..., description="Model stage (dev/staging/production)", min_length=1)
    checksum: str = Field(..., description="SHA256 checksum", min_length=64, max_length=64)


class ModelListResponse(BaseModel):
    """Response with list of available models."""

    model_config = ConfigDict(strict=True)

    models: list[ModelMeta] = Field(..., description="List of available models")


class ModelActivateRequest(BaseModel):
    """Request to activate a specific model version."""

    model_config = ConfigDict(strict=True)

    name: str = Field(..., description="Model name", min_length=1)
    version: str = Field(..., description="Model version to activate", min_length=1)


class ModelActivateResponse(BaseModel):
    """Response after model activation."""

    model_config = ConfigDict(strict=True)

    success: bool = Field(..., description="Whether activation was successful")
    message: str = Field(..., description="Status message")
