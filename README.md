A compact and clear setup guide for running this project in development.

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

Run this command once before starting the services:

```bash
python deploy_recognition_patch.py
```



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
