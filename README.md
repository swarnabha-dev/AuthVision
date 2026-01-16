This repository contains three main areas:
- `deepface/` - the core face-recognition library and model code.
- `model_service/` - a FastAPI service that wraps DeepFace model endpoints (recognise, refresh-db, detect) and exposes auth (JWT + API keys).
- `main_backend/` - an orchestrator and simple frontend that captures streams, forwards keyframes to `model_service`, manages users/students/subjects/attendance, and serves a small static test UI.

**Recommended**: run each service in its own terminal using a virtual environment.

**See**: `requirements.txt`, `model_service/requirements.txt`, `main_backend/requirements.txt` for per-module dependencies.

**Python version**: 3.11 (recommended)

**Quick index**
- Running the services
- First-time setup notes
- Authentication flow (model <-> backend)
- Frontend quick guide
- Troubleshooting and tips

**Running the services (development)**

1) Create and activate a virtual environment (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2) Install top-level dependencies (or per-module):

```powershell
# top-level (pulls module files)
pip install -r requirements.txt

# or per-service
pip install -r model_service/requirements.txt
pip install -r main_backend/requirements.txt
```

## First-Time Setup (IMPORTANT)

### Run deployment patch

```bash
python deploy_recognition_patch.py
```

3) Start `model_service` and `main_backend` in separate terminals.

You can start `model_service` either as a package or as a script:

```powershell
# recommended (package entrypoint)
python -m model_service

# or direct script (convenience)
python model_service
```

Start the orchestrator (`main_backend`):

```powershell
python -m main_backend
```

The `main_backend` serves a small static test UI at `/static/` (e.g. http://localhost:8002/static/ or whatever host/port you configured).

Configuration
- `main_backend/config.py` and `model_service/config.py` contain runtime settings (ports, JWT secret, MODEL_SERVICE_URL, auto-auth credentials). Set via environment variables where needed.
- Important env vars:
	- `MAIN_BACKEND_JWT_SECRET` – set a secure secret in multi-node setups.
	- `MODEL_SERVICE_URL` – URL used by `main_backend` to reach `model_service` (default http://localhost:8080).
	- `MODEL_SERVICE_USER` / `MODEL_SERVICE_PASS` – credentials used by `main_backend` to auto-register/login with `model_service` and create an API key.

Auth summary (how services authenticate)
- `model_service` supports both API keys and JWT tokens.
	- Model endpoints used by `main_backend` (recognise, refresh-db, detect) accept API key authentication so `main_backend` can call them without logging in each time.
	- `model_service` still exposes `/login`, `/register`, `/refresh`, and `/apikey/create` for manual admin workflows.
- `main_backend` acts as an orchestrator and will auto-register/login to `model_service` if needed and create an API key (see `main_backend/services/model_client.py`).

Frontend (test UI)
- Open the frontend at `{MAIN_BACKEND_HOST}/static/` after `main_backend` is running.
- Key UI actions:
	- Login / Admin bootstrap: you can create an initial admin via the UI (bootstrap) then login.
	- Create subjects: choose department (dropdown), code, name, semester. Departments are auto-created when you enter a new department name.
	- Create students: admin-only; select department from dropdown.
	- Start/Stop streams and connect via WebSocket to view live frames.
	- Upload enrollment photos for a student (faculty/admin) — forwarded to `model_service` `/refresh-db`.
	- Trigger attendance (uses the currently displayed frame) and Stop Attendance (placeholder endpoint included).

Notes on departments and subjects
- The DB is normalized: departments are stored in a `departments` table with an integer id and name.
- You may provide department names when creating subjects or students; the backend will create the `Department` row and associate the subject/student with its id.
- API responses (e.g., `/subjects/list`) now include the department name under the `department` field (human-friendly) rather than exposing only the numeric id.

Attendance workflow
- Trigger attendance via the frontend or `POST /attendance/trigger` with `subject` (id or code/name), `department` (id or name), `semester`, `section` and `stream_image_b64` (base64 image). The endpoint resolves names to ids and records attendance for eligible students.
- A basic `POST /attendance/stop` endpoint exists as a placeholder; if you want stateful start/stop sessions I can implement session tracking and cancellation.

Troubleshooting & tips
- If you see frequent H.264 decode warnings like `reader is too slow` or `error while decoding MB`, try:
	- Use a smaller frame resolution on the RTSP source or lower capture keyframe frequency.
	- The capturer downsamples frames to a max dimension (≈800px) and sets a small capture buffer, which helps but may still depend on OpenCV/FFmpeg build and system performance.
- If model calls fail with 401, ensure `MODEL_SERVICE_USER`/`MODEL_SERVICE_PASS` match a registered user in `model_service` or allow `main_backend` to auto-register (it will attempt to register and then login).
- To avoid accidental 422/400 validation errors, use the frontend dropdowns for departments and provide required fields (subject, department, semester).

Development notes
- `.gitignore` is present at repository root to ignore venvs, logs, DB files and model artifacts.
- Requirements files:
	- Top-level `requirements.txt` includes module `-r` includes.
	- `model_service/requirements.txt` and `main_backend/requirements.txt` include their specific packages.

Recommended next improvements (optional)
- Add a small `/departments` admin UI to manage department names explicitly.
- Add stateful attendance sessions (start/stop with server-side state and cancellation).
- Add integration tests that run a headless model_service and main_backend and exercise the UI endpoints.

