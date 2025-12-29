# 🚀 Quick Deployment Reference

## Problem: "Signature verification failed" on other PC

### Root Cause
JWT tokens are signed with a secret key. If different PCs use different secrets, tokens won't verify.

### Quick Fix (3 Steps)

#### Step 1: Get JWT Secret from Main PC
On your working PC, check the current secret:
```powershell
echo $env:MAIN_BACKEND_JWT_SECRET
```

If empty, generate one:
```powershell
.\setup-deployment.ps1
```
**Save the secret that's displayed!**

#### Step 2: Set JWT Secret on Deployment PC
On the other PC, set the same secret:
```powershell
$env:MAIN_BACKEND_JWT_SECRET="paste-secret-from-step-1-here"
```

To make it permanent:
```powershell
[Environment]::SetEnvironmentVariable("MAIN_BACKEND_JWT_SECRET", "paste-secret-here", "User")
```

#### Step 3: Restart Backend
```powershell
# Stop the backend (Ctrl+C)
# Start it again
python -m main_backend
```

### Alternative: Use Setup Script
Run this on each PC:
```powershell
.\setup-deployment.ps1
```
Choose option 2 and paste the secret from your main PC.

---

## Common Scenarios

### Scenario 1: Fresh Deployment (First PC)
```powershell
# Generate new secret
.\setup-deployment.ps1
# Choose option 1
# Save the displayed secret!
```

### Scenario 2: Additional PC (Second, Third PC, etc.)
```powershell
# Use existing secret from first PC
.\setup-deployment.ps1
# Choose option 2
# Paste the secret from first PC
```

### Scenario 3: Different Secrets (Independent Deployments)
- Each PC has its own database and users
- Users login separately on each PC
- No token sharing between PCs
- **Action:** Nothing needed, use default config

---

## Verification

Check if JWT_SECRET is set:
```powershell
echo $env:MAIN_BACKEND_JWT_SECRET
```

Test logout (should NOT show signature errors):
```powershell
# Login to app, then logout
# Check backend logs - no "Signature verification failed"
```

---

## Files to Check

| File | Purpose | Important Setting |
|------|---------|-------------------|
| `main_backend/config.py` | Backend config | `JWT_SECRET` default value |
| `DEPLOYMENT.md` | Full deployment guide | All deployment steps |
| `setup-deployment.ps1` | Windows setup script | Auto-configuration |
| `setup-deployment.sh` | Linux/Mac setup script | Auto-configuration |

---

## Environment Variables Reference

```powershell
# Essential
$env:MAIN_BACKEND_JWT_SECRET="your-secret-key"

# Optional
$env:MAIN_BACKEND_DATABASE_URL="sqlite:///path/to/db.db"
$env:MAIN_BACKEND_ACCESS_EXPIRES="3600"
$env:MAIN_BACKEND_REFRESH_EXPIRES="2592000"
```

---

## Need Help?

1. Check [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guide
2. Verify JWT_SECRET is identical on all PCs
3. Clear browser localStorage and login again
4. Contact: arpan_202200085@smit.smu.edu.in
