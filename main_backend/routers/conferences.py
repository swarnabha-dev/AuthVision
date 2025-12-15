from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional
import shutil
import os
from pathlib import Path

from ..services.db import get_db
from ..services import models as m
from ..services.auth import require_role
from .. import config

router = APIRouter(prefix="/conferences")

# Ensure arcface_db directory exists (handled by config usually, but check)

@router.post("/create")
def create_conference(
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    start_date: date = Form(...),
    end_date: date = Form(...),
    db: Session = Depends(get_db),
    user = Depends(require_role('admin'))
):
    if db.query(m.Conference).filter(m.Conference.code == code).first():
        raise HTTPException(status_code=400, detail="Conference code already exists")
    
    conf = m.Conference(
        code=code,
        name=name,
        description=description,
        start_date=start_date,
        end_date=end_date,
        is_active=True
    )
    db.add(conf)
    db.commit()
    return {"status": "created", "conference": code}

@router.get("/list")
def list_conferences(db: Session = Depends(get_db), user = Depends(require_role('admin', 'faculty'))):
    confs = db.query(m.Conference).all()
    return [{
        "id": c.id, 
        "code": c.code, 
        "name": c.name, 
        "start_date": c.start_date, 
        "end_date": c.end_date,
        "is_active": c.is_active
    } for c in confs]

@router.post("/{code}/guests/add")
def add_guest(
    code: str,
    name: str = Form(...),
    email: str = Form(""),
    organization: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user = Depends(require_role('admin'))
):
    conf = db.query(m.Conference).filter(m.Conference.code == code).first()
    if not conf:
        raise HTTPException(status_code=404, detail="Conference not found")
    
    # Create Guest Entry first to get ID
    guest = m.Guest(
        name=name, 
        email=email, 
        organization=organization, 
        conference_id=conf.id
    )
    db.add(guest)
    db.commit()
    db.refresh(guest)
    
    # Save Photo
    # Logic: identity will be "guest_{id}"
    identity = f"guest_{guest.id}"
    ext = file.filename.split('.')[-1]
    filename = f"{identity}.{ext}"
    
    # Path: model_service stores DB in arcface_db. 
    # We need to know where arcface_db is.
    # config.ARCFACE_DB_PATH should exist? 
    # Currently config.py in main_backend doesn't define it? 
    # model_service/config.py has it.
    # We assume it is relative to project root or we can hardcode for now based on user context.
    # "c:\Users\swarn\OneDrive - 3602sv\Original Projects\5G LAB CCTV Project\Face Recognition v6\model_service\arcface_db"
    
    # Let's try to deduce it or assume standardized path "../model_service/arcface_db" relative to main_backend?
    # User's project has main_backend and model_service as siblings.
    base_dir = Path(__file__).resolve().parent.parent.parent # main_backend -> services -> routers -> parent
    # Wait, routers is level 1 inside main_backend.
    # __file__ = routers/conferences.py
    # parent = routers
    # parent.parent = main_backend
    # parent.parent.parent = Face Recognition v6
    
    arcface_dir = base_dir / "model_service" / "arcface_db"
    if not arcface_dir.exists():
        # Fallback or error
        # Try finding it?
        pass
    
    save_path = arcface_dir / filename
    
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        guest.photo_path = str(save_path)
        db.commit()
        
        return {"status": "guest added", "guest_id": guest.id, "identity": identity}
    except Exception as e:
        db.delete(guest)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to save photo: {e}")

@router.get("/{code}/guests")
def list_guests(code: str, db: Session = Depends(get_db)):
    conf = db.query(m.Conference).filter(m.Conference.code == code).first()
    if not conf:
        raise HTTPException(status_code=404, detail="Conference not found")
    
    return [
        {"id": g.id, "name": g.name, "organization": g.organization, "identity": f"guest_{g.id}"} 
        for g in conf.guests
    ]

@router.post("/{code}/start-session")
def start_conference_session(code: str, stream_name: str = Form(...), user = Depends(require_role('admin'))):
    from ..services.attendance import AttendanceManager
    mgr = AttendanceManager.get_instance()
    try:
        username = user.username
        session_id = mgr.start_conference_session(stream_name, code, username)
        return {"status": "started", "session_id": session_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

