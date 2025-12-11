import threading
import time
import logging
import httpx
import asyncio
from datetime import datetime
from .. import config
from ..services.db import SessionLocal
from ..services import models as m
from ..services import stream as stream_srv
from ..services.ws_manager import manager as ws_manager

LOG = logging.getLogger("main_backend.attendance_srv")

class AttendanceManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.current_session = None
        self._thread = None
        self._stop_event = threading.Event()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def start_session(self, stream_name: str, subject_code: str, department_name: str, semester: int, section: str, user_username: str):
        with self._lock:
            if self.current_session:
                raise ValueError(f"Session already running for {self.current_session['subject_code']}")
            
            # verify stream exists
            try:
                stream_srv.get_capturer(stream_name)
            except Exception:
                raise ValueError(f"Stream {stream_name} not found")

            # Create Database Session Entry
            db = SessionLocal()
            try:
                # verify subject exists
                subject = db.query(m.Subject).filter(m.Subject.code == subject_code).first()
                if not subject:
                     raise ValueError(f"Subject {subject_code} not found")

                new_session = m.AttendanceSession(
                    subject_code=subject_code,
                    date=datetime.utcnow().date(),
                    start_time=datetime.utcnow(),
                    session_type="Lecture", # Default
                    location="Classroom" # Default or passed param
                )
                db.add(new_session)
                db.commit()
                db.refresh(new_session)
                session_id = new_session.id
                LOG.info(f"Created AttendanceSession ID={session_id} for {subject_code}")
            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()

            self._stop_event.clear()
            self.current_session = {
                "id": session_id,
                "stream_name": stream_name,
                "subject_code": subject_code,
                "department": department_name,
                "semester": semester,
                "section": section,
                "started_by": user_username,
                "start_time": datetime.utcnow()
            }
            self._thread = threading.Thread(target=self._attendance_loop, args=(stream_name, session_id, department_name, semester, section))
            self._thread.daemon = True
            self._thread.start()
            LOG.info("attendance session started for subject=%s dept=%s sem=%s", subject_code, department_name, semester)
            
            return session_id

    def stop_session(self):
        with self._lock:
            if not self.current_session:
                return False
            
            # Update end time
            session_id = self.current_session.get("id")
            if session_id:
                db = SessionLocal()
                try:
                    sess = db.query(m.AttendanceSession).filter(m.AttendanceSession.id == session_id).first()
                    if sess:
                        sess.end_time = datetime.utcnow()
                        db.commit()
                except Exception as e:
                    LOG.error(f"Failed to update session end time: {e}")
                finally:
                    db.close()

            self._stop_event.set()
            if self._thread:
                self._thread.join(timeout=2.0)
            self.current_session = None
            LOG.info("attendance session stopped")
            return True

    def _attendance_loop(self, stream_name, session_id, department, semester, section):
        LOG.info("attendance loop running for stream=%s session=%d", stream_name, session_id)
        
        # Async loop for WebSocket broadcasting and Async HTTP
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # subscribe to stream
        capturer = stream_srv.get_capturer(stream_name)
        q = capturer.subscribe()
        
        last_process_time = 0
        interval = 2.0 # Faster recognition interval

        # Fetch eligible students once
        db = SessionLocal()
        eligible_regs = set()
        reg_to_name = {}
        try:
             students = db.query(m.Student).filter(m.Student.department == department, m.Student.semester == semester, m.Student.section == section).all()
             eligible_regs = {s.reg_no for s in students}
             reg_to_name = {s.reg_no: s.name for s in students}
             LOG.info("loaded %d eligible students for attendance", len(eligible_regs))
        except Exception as e:
            LOG.error("failed to load students for attendance: %s", e)
            db.close()
            capturer.unsubscribe(q)
            loop.close()
            return
        
        db.close()
        
        try:
            frame_count = 0
            PROCESS_EVERY_N_FRAMES = 5 
            
            # Reuse client? Better to use context manager per request or long-lived?
            # Long-lived is better for connection pooling.
            
            while not self._stop_event.is_set():
                if self._stop_event.is_set(): break

                # Drain queue
                if not q.empty():
                     while not q.empty():
                         if self._stop_event.is_set(): break
                         try: frame = q.get_nowait()
                         except Exception: break
                else:
                    try: frame = q.get(timeout=1.0)
                    except Exception: continue 

                if self._stop_event.is_set(): break

                frame_count += 1
                if frame_count % PROCESS_EVERY_N_FRAMES != 0: continue

                now = time.time()
                if now - last_process_time < interval: continue
                
                last_process_time = now

                # process frame
                import base64
                b64 = base64.b64encode(frame).decode('utf-8')
                
                if self._stop_event.is_set(): break

                try:
                    # Run async process in the loop
                    loop.run_until_complete(self._process_frame_async(b64, eligible_regs, reg_to_name, session_id))
                except Exception as e:
                    LOG.error("error processing attendance frame: %s", e)
        finally:
            capturer.unsubscribe(q)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
            LOG.info("attendance loop terminated")

    async def _process_frame_async(self, image_b64, eligible_regs, reg_to_name, session_id):
        from ..services.model_client import get_headers_sync
        
        # 1. Call Model Service (Async)
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                headers = get_headers_sync()
                # Use await
                resp = await client.post(f"{config.MODEL_SERVICE_URL}/recognise", json={"image_b64": image_b64}, headers=headers)
                
                if resp.status_code != 200:
                    LOG.warning("model service error: %d %s", resp.status_code, resp.text)
                    return
                
                data = resp.json()
            except httpx.ReadTimeout:
                LOG.warning("Model service timed out (10s)")
                return
            except httpx.RequestError as e:
                LOG.warning(f"Model service request failed: {e}")
                return
            except Exception as e:
                LOG.error(f"Model service unexpected error: {e}")
                return

        # LOG RAW RESPONSE to debug "missing logs"
        LOG.info("RAW RECOGNITION DATA: %s", data)
            
        # 2. Extract Identities
        recognized = set()
        def extract_ids(obj):
            ids = set()
            if isinstance(obj, dict):
                if 'identity' in obj:
                     val = obj['identity']
                     # Filter by eligible
                     if val in eligible_regs:
                         ids.add(val)
                     else:
                         for r in eligible_regs:
                             if r in val:
                                 ids.add(r)
                for v in obj.values():
                    ids |= extract_ids(v)
            elif isinstance(obj, list):
                for it in obj:
                    ids |= extract_ids(it)
            return ids
        
        recognized = extract_ids(data)

        if not recognized:
            LOG.info("No eligible students recognized in this frame.")
            return

        LOG.info("Recognized Eligible: %s", recognized)

        # 3. Record in DB and Broadcast
        db = SessionLocal()
        try:
            for reg in recognized:
                exists = db.query(m.AttendanceRecord).filter(
                    m.AttendanceRecord.session_id == session_id,
                    m.AttendanceRecord.student_reg == reg
                ).first()

                if not exists:
                    rec = m.AttendanceRecord(
                        session_id=session_id,
                        student_reg=reg,
                        status=m.AttendanceStatus.PRESENT,
                        recorded_at=datetime.utcnow()
                    )
                    db.add(rec)
                    db.commit()
                    LOG.info("Marked %s present in session %d", reg, session_id)
                    
                    # Broadcast
                    student_name = reg_to_name.get(reg, "Unknown")
                    msg = {
                        "type": "recognition",
                        "student": {
                            "reg_no": reg,
                            "name": student_name,
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        }
                    }
                    await ws_manager.broadcast(msg)
                else:
                     # Already present, maybe we still want to broadcast "Latest Seen"?
                     # For now, only broadcast ONCE upon marking. 
                     # If user wants "Live Feed" showing every detection, we can move broadcast outside `if not exists`.
                     pass
        except Exception as commit_err:
            LOG.error(f"DB/Broadcast failed: {commit_err}")
            db.rollback()
        finally:
            db.close()
