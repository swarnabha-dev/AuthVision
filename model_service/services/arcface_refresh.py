from typing import List
import tempfile
import os
import pickle
from pathlib import Path

from deepface.modules import recognition
from deepface.commons import image_utils

from .. import config


# Access private DeepFace helper (name-mangled)
find_bulk = getattr(recognition, "_recognition__find_bulk_embeddings", None)
if find_bulk is None:
    find_bulk = getattr(recognition, "__find_bulk_embeddings", None)


PKL_PATH = config.ARC_PKL_PATH


def load_db() -> list:
    """Load entire ArcFace PKL database."""
    if not os.path.exists(PKL_PATH):
        return []
    return pickle.load(open(PKL_PATH, "rb"))


def save_db(data: list):
    """Write updated ArcFace PKL database."""
    os.makedirs(os.path.dirname(PKL_PATH), exist_ok=True)
    pickle.dump(data, open(PKL_PATH, "wb"), pickle.HIGHEST_PROTOCOL)


def add_face_arcface(image_bytes: bytes, identity: str, index: int = 0) -> dict:
    """
    Add a single face embedding to the ArcFace PKL DB.
    Supports multiple images per SAME identity.
    
    identity → the student ID or person ID (constant)
    index → gives each temporary file a unique name to avoid detector confusion
    """

    if find_bulk is None:
        raise RuntimeError("DeepFace internal find_bulk helper not available in this DeepFace version")

    # ---- UNIQUE TEMP FILENAME FOR MULTIPLE IMAGES ----
    safe_id = identity.replace("/", "_").replace("\\", "_")
    temp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(temp_dir, f"{safe_id}_{index}.jpg")

    with open(tmp_path, "wb") as f:
        f.write(image_bytes)

    try:
        employees = {tmp_path}

        reps = find_bulk(
            employees=employees,
            model_name=config.MODEL_NAME,
            detector_backend=config.DETECTOR_BACKEND,
            enforce_detection=True,
            align=config.ALIGN,
            expand_percentage=0,
            normalization=config.NORMALIZATION,
            silent=False,
        )

        # ---- OVERRIDE IDENTITY (CRITICAL) ----
        # DeepFace normally stores the filename and other metadata; we will
        # sanitize the stored record so the PKL contains only the identity
        # and the embedding vector. This avoids keeping references to
        # temporary image files which later cause logs to show temp paths.

        # def _extract_embedding(record):
        #     # Try common keys first
        #     for k in ("embedding", "rep", "representations", "representation", "emb"):
        #         if k in record and record[k]:
        #             return record[k]
        #     # Fallback: find first list/tuple/ndarray value
        #     for v in record.values():
        #         if isinstance(v, (list, tuple)):
        #             return v
        #         try:
        #             import numpy as _np
        #             if _np and isinstance(v, _np.ndarray):
        #                 return v.tolist()
        #         except Exception:
        #             pass
        #     return None


        def _extract_embedding(record):
            # Primary: canonical key 'embedding'
            if "embedding" in record and record["embedding"]:
                # ensure it's a python list (some older PKL might still contain numpy arrays)
                val = record["embedding"]
                try:
                    import numpy as _np
                    if isinstance(val, _np.ndarray):
                        return val.tolist()
                except Exception:
                    pass
                # if it's a list/tuple, return as list
                if isinstance(val, (list, tuple)):
                    return list(val)
                # otherwise try to coerce single-value containers
                try:
                    return list(val)
                except Exception:
                    return None

            # fallback to 'rep' or 'representations' which some versions used
            for k in ("rep", "representations", "representation", "emb"):
                if k in record and record[k]:
                    val = record[k]
                    try:
                        import numpy as _np
                        if isinstance(val, _np.ndarray):
                            return val.tolist()
                    except Exception:
                        pass
                    if isinstance(val, (list, tuple)):
                        return list(val)
            return None


        cleaned = []
        for idx_r, r in enumerate(reps):
            emb = _extract_embedding(r)
            if emb is None:
                # If we couldn't find an embedding, skip this record
                continue
            # normalize embedding to plain python list
            try:
                # if it's a numpy array, convert
                import numpy as _np
                if isinstance(emb, _np.ndarray):
                    emb = emb.tolist()
            except Exception:
                pass

            # DeepFace expects certain keys in DB records (target_x/y/w/h and hash)
            # We provide neutral defaults (0) for bounding box and a stable hash.
            record_hash = f"{identity}_{index}_{idx_r}"

                        # CHANGED: extract bounding-box info from the representation returned by find_bulk (if present)
            # This prevents always writing zeros into PKL when actual detection produced bbox coords.
            def _to_int_safe(v, default=0):
                try:
                    import numpy as _np
                    if isinstance(v, _np.generic):
                        return int(v.item())
                    if isinstance(v, _np.ndarray):
                        if v.shape == ():
                            return int(v.item())
                        return int(v.flat[0])
                    if v is None:
                        return default
                    return int(v)
                except Exception:
                    return default

            # try to find bbox fields on the `r` record which find_bulk returned
            tx = _to_int_safe(r.get("target_x") if isinstance(r, dict) else None, 0)
            ty = _to_int_safe(r.get("target_y") if isinstance(r, dict) else None, 0)
            tw = _to_int_safe(r.get("target_w") if isinstance(r, dict) else None, 0)
            th = _to_int_safe(r.get("target_h") if isinstance(r, dict) else None, 0)

            cleaned.append({
                "identity": identity,
                # keep both common embedding keys for compatibility
                "embedding": list(emb),
                "rep": list(emb),
                "representations": list(emb),
                "model": config.MODEL_NAME,
                # bounding box: prefer values returned by find_bulk, fallback to 0
                "target_x": tx,
                "target_y": ty,
                "target_w": tw,
                "target_h": th,
                # some deepface versions expect a hash key
                "hash": record_hash,
            })
# END CHANGED: now storing bbox values from rep when available


        # ---- APPEND CLEANED RECORDS TO DB ----
        db = load_db()
        db.extend(cleaned)
        save_db(db)

        return {"status": "success", "identity": identity, "added": len(cleaned)}

    finally:
        # Delete temp file
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def add_faces_from_uploads(files: List[bytes], identity: str) -> List[dict]:
    """
    Add multiple faces for the SAME identity.
    identity → student ID (e.g., "202200248")
    """
    results = []
    for idx, file_bytes in enumerate(files):
        try:
            res = add_face_arcface(file_bytes, identity, index=idx)
            results.append(res)
        except Exception as e:
            results.append({"status": "error", "error": str(e), "identity": identity})
    return results
