A compact and clear setup guide for running this project in development.

> **📦 For production deployment or multi-PC setup, see [DEPLOYMENT.md](DEPLOYMENT.md)**

---

## Requirements

* Python **3.11.0**

---

## Setup

### 1. Create a virtual environment

**Windows (PowerShell)**

```powershell
python -m venv .venv
```


### 2. Activate the virtual environment

**Windows (PowerShell)**

```powershell
.venv\Scripts\Activate.ps1
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## First-Time Setup (IMPORTANT)

### 1. Run deployment patch

```bash
python deploy_recognition_patch.py
```

### 2. Configure JWT Secret (Multi-PC Deployment)

If deploying to multiple PCs, run the setup script to configure a shared JWT secret:

**Windows:**
```powershell
.\setup-deployment.ps1
```

**Linux/Mac:**
```bash
chmod +x setup-deployment.sh
./setup-deployment.sh
```

Or manually set the environment variable:
```powershell
# Windows
$env:MAIN_BACKEND_JWT_SECRET="your-secure-secret-here"

# Linux/Mac
export MAIN_BACKEND_JWT_SECRET="your-secure-secret-here"
```

> ⚠️ **Important:** Use the same JWT_SECRET on all PCs to avoid "Signature verification failed" errors.
> See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

---

## Run the Development Server

Run these **two commands in separate terminals** inside the project folder.

**Terminal 1**

```bash
python model_service
```

**Terminal 2**

```bash
python main_backend
```

Backend will run on:

```
http://0.0.0.0:8002
```


---

## License

Add the project license here (e.g., MIT).
