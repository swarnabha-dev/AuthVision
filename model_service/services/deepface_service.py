import os
import base64
import tempfile
from typing import Optional
import base64

try:
    from PIL import Image
    import numpy as np
except Exception:
    Image = None
    np = None


DEEPFACE_MODELS = None
DeepFace = None

from .. import config


def ensure_deepface():
    """Lazy import DeepFace and optionally preload the ArcFace model.
    Keeps the same behavior as the original single-file implementation.
    """
    global DeepFace, DEEPFACE_MODELS
    if DeepFace is not None:
        return

    try:
        from importlib import import_module

        # First try the common pattern: package exposes DeepFace at the top level
        pkg = import_module("deepface")
        DeepFace = getattr(pkg, "DeepFace", None)

        # If not present, try importing the DeepFace module directly
        if DeepFace is None:
            try:
                mod = import_module("deepface.DeepFace")
                DeepFace = getattr(mod, "DeepFace", None) or mod
            except Exception:
                DeepFace = None

        # As a last resort, try the installed package entry point module name
        if DeepFace is None:
            # some installations may expose the implementation under different paths
            for alt in ("deepface.DeepFace", "DeepFace"):
                try:
                    mod = import_module(alt)
                    DeepFace = getattr(mod, "DeepFace", None) or mod
                    if DeepFace is not None:
                        break
                except Exception:
                    continue

        if DeepFace is None:
            raise ImportError("could not locate DeepFace symbol in installed package")
    except Exception as exc:
        DeepFace = None
        print(f"[ensure_deepface] Error: {exc}")
        return

    if DEEPFACE_MODELS is None:
        try:
            print("[DeepFace] Preloading ArcFace...")
            model = DeepFace.build_model(config.MODEL_NAME)
            DEEPFACE_MODELS = {"model": model, "detector": config.DETECTOR_BACKEND}
            print("[DeepFace] Loaded.")
        except Exception as e:
            print(f"[DeepFace] Preload failed: {e}")
            DEEPFACE_MODELS = None


def ensure_image_libs():
    if Image is None or np is None:
        raise RuntimeError("Pillow & numpy required")


async def write_upload_to_tempfile(upload, suffix: str = ".jpg"):
    data = await upload.read()
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tf.write(data)
    tf.flush()
    tf.close()
    return tf.name


def write_bytes_to_tempfile(data: bytes, suffix: str = ".jpg"):
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tf.write(data)
    tf.flush()
    tf.close()
    return tf.name


def _serialize_deepface_result(obj):
    try:
        import pandas as pd
        import numpy as _np
    except Exception:
        pd = None
        _np = None

    def convert(o):
        if pd and isinstance(o, pd.DataFrame):
            return o.fillna("").to_dict(orient="records")
        if pd and isinstance(o, pd.Series):
            return convert(o.to_dict())
        if _np and isinstance(o, _np.ndarray):
            return convert(o.tolist())
        if _np and isinstance(o, _np.generic):
            return o.item()
        if isinstance(o, dict):
            return {k: convert(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [convert(v) for v in o]
        return o

    return convert(obj)
