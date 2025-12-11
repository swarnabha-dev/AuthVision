"""
DEPRECATION NOTICE

The module `model_service.arcface_refresh` was a compatibility shim.
It has been removed. Please import the service directly:

	from model_service.services import arcface_refresh

This file now raises ImportError to make the change explicit.
"""

raise ImportError(
	"model_service.arcface_refresh has been removed. Import from model_service.services.arcface_refresh instead."
)

