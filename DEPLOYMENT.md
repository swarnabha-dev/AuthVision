# Deployment Guide - AuthVision 5G Lab

## 🚀 Quick Deployment Checklist

### 1. **Configure JWT Secret (CRITICAL)**

The JWT_SECRET must be **the same across all deployments** for token validation to work.

#### Option A: Set Environment Variable (Recommended)
```bash
# Windows PowerShell
$env:MAIN_BACKEND_JWT_SECRET="your-secure-secret-key-here"

# Linux/Mac
export MAIN_BACKEND_JWT_SECRET="your-secure-secret-key-here"
```

#### Option B: Create `.env` file
Create a `.env` file in the project root:
```env
MAIN_BACKEND_JWT_SECRET=your-secure-secret-key-here
```

#### Generate a Secure Secret
```python
# Run this in Python to generate a secure secret
import secrets
print(secrets.token_urlsafe(32))
```

### 2. **Database Location**

By default, the database is created at `main_backend_data/main_backend.db`. To use a custom location:

```bash
$env:MAIN_BACKEND_DATABASE_URL="sqlite:///C:/path/to/your/database.db"
```

### 3. **Backend Configuration**

Edit `main_backend/config.py` or set these environment variables:

```env
# JWT Configuration
MAIN_BACKEND_JWT_SECRET=your-secret-key-here
MAIN_BACKEND_JWT_ALGORITHM=HS256
MAIN_BACKEND_ACCESS_EXPIRES=3600
MAIN_BACKEND_REFRESH_EXPIRES=2592000

# Database
MAIN_BACKEND_DATABASE_URL=sqlite:///path/to/db.db

# Model Service
MODEL_SERVICE_URL=http://localhost:8080
MODEL_SERVICE_USER=main_backend_bot
MODEL_SERVICE_PASS=change-me
```

### 4. **Frontend Configuration**

Edit `Authvision_Frontend/public/config.json`:

```json
{
  "api": {
    "baseURL": "http://your-server-ip:5000/api",
    "timeout": 10000
  },
  "websocket": {
    "url": "ws://your-server-ip:5000/ws",
    "reconnectInterval": 3000
  }
}
```

## 📦 Installation Steps

### Backend Setup

1. **Install Python dependencies:**
```bash
cd "Face Recognition v6"
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate    # Linux/Mac

pip install -r requirements.txt
```

2. **Set JWT Secret (IMPORTANT):**
```bash
$env:MAIN_BACKEND_JWT_SECRET="your-shared-secret-key"
```

3. **Run Backend:**
```bash
python -m main_backend
```

### Model Service Setup

1. **Run Model Service:**
```bash
python -m model_service
```

### Frontend Setup

1. **Install Node dependencies:**
```bash
cd Authvision_Frontend
npm install
```

2. **Update config.json** with your server IP

3. **Build for production:**
```bash
npm run build
```

4. **Run development server:**
```bash
npm run dev
```

## 🔐 Security Considerations

### For Production Deployment:

1. **Change ALL default passwords:**
   - `MAIN_BACKEND_JWT_SECRET` (most critical)
   - `MODEL_SERVICE_PASS`
   - Admin user passwords

2. **Use strong secrets:**
   ```python
   import secrets
   secrets.token_urlsafe(32)  # Generate secure key
   ```

3. **HTTPS/WSS:** Use secure connections in production

4. **Database backups:** Regularly backup `main_backend.db`

## 🐛 Common Deployment Issues

### Issue: "Signature verification failed" on logout

**Cause:** JWT_SECRET is different between PCs

**Solution:** 
1. Set the same `MAIN_BACKEND_JWT_SECRET` on all machines
2. Or, clear localStorage and login again with new secret

### Issue: "Invalid credentials" after deployment

**Cause:** Database is different on new PC

**Solution:**
1. Copy the `main_backend_data` folder to the new PC
2. Or, create new admin account: `python -m main_backend` and use `/auth/register`

### Issue: Frontend can't connect to backend

**Cause:** Incorrect API URL in config.json

**Solution:** Update `baseURL` in `Authvision_Frontend/public/config.json`

### Issue: Tokens expire immediately

**Cause:** Different JWT_SECRET between login and verification

**Solution:** Ensure `MAIN_BACKEND_JWT_SECRET` is consistent

## 📝 Multi-PC Deployment

When deploying to multiple PCs, you have two options:

### Option 1: Shared Configuration (Recommended)
- Use the **same JWT_SECRET** on all PCs
- Share the **same database file** across machines
- Users can login on any PC and stay logged in

### Option 2: Independent Deployments
- Each PC has its own JWT_SECRET
- Each PC has its own database
- Users must register/login separately on each PC
- Tokens are not transferable between PCs

## 🔄 Updating Deployment

1. **Pull latest code:**
```bash
git pull
```

2. **Update dependencies:**
```bash
pip install -r requirements.txt
cd Authvision_Frontend
npm install
```

3. **Rebuild frontend:**
```bash
npm run build
```

4. **Restart services**

## 📊 Monitoring

Check logs for errors:
- Backend: `main_backend/main.py.log.*`
- Check console output for WebSocket connections
- Monitor API response times in browser DevTools

## 🆘 Need Help?

Contact: ArpanCodec (arpan_202200085@smit.smu.edu.in)
