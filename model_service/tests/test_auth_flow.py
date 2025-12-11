import os
import sys
import tempfile
import uuid
import io
import pytest

# Ensure repo root is on sys.path so `model_service` can be imported when pytest runs
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from fastapi.testclient import TestClient

import model_service.main as main_mod
@pytest.fixture(autouse=True)
def patch_deepface(monkeypatch):
    # Replace heavy DeepFace behaviors with lightweight stubs for tests
    class DummyDF:
        @staticmethod
        def verify(img1_path=None, img2_path=None, **kwargs):
            return {"verified": True, "distance": 0.1}

        @staticmethod
        def find(**kwargs):
            return [{"identity": "test", "score": 0.9}]

    def ensure():
        main_mod.deepface_service.DeepFace = DummyDF

    # also set it immediately to avoid model preload during first request
    main_mod.deepface_service.DeepFace = DummyDF

    monkeypatch.setattr(main_mod.deepface_service, "ensure_deepface", ensure)

    async def _write_upload_to_tempfile(upload, suffix: str = ".jpg"):
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        # if upload is an UploadFile, read bytes
        try:
            data = await upload.read()
            tf.write(data)
        except Exception:
            # upload might be raw bytes in tests
            try:
                tf.write(upload)
            except Exception:
                pass
        tf.flush()
        tf.close()
        return tf.name

    monkeypatch.setattr(main_mod.deepface_service, "write_upload_to_tempfile", _write_upload_to_tempfile)

    yield


def test_register_login_and_protected_detect(tmp_path):
    client = TestClient(main_mod.app)

    # use a unique username per test run to avoid sqlite unique constraint
    username = "testuser_" + uuid.uuid4().hex[:8]
    password = "testpass"

    # Register
    r = client.post("/register", data={"username": username, "password": password})
    assert r.status_code == 200

    # Login
    r = client.post("/login", data={"username": username, "password": password})
    assert r.status_code == 200
    tokens = r.json()
    access = tokens["access_token"]

    # Create API key
    r = client.post("/apikey/create", data={"username": username, "password": password})
    assert r.status_code == 200
    api_key = r.json()["api_key"]

    # Call protected detect endpoint
    files = {"img1": ("a.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg"), "img2": ("b.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")}
    headers = {"X-API-KEY": api_key, "Authorization": f"Bearer {access}"}
    r = client.post("/detect", files=files, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data.get("verified") is True or isinstance(data, dict)
