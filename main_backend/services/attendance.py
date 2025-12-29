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

    def start_session(self, stream_name: str, subject_code: str, department_name: str, semester: int, section: str, user_username: str, session_id: int = None):
        with self._lock:
            if self.current_session:
                raise ValueError(f"Session already running")
            
            # verify stream exists
            try:
                stream_srv.get_capturer(stream_name)
            except Exception:
                raise ValueError(f"Stream {stream_name} not found")

            # Create or resume Database Session Entry
            db = SessionLocal()
            try:
                if session_id:
                    # resume an existing session by id
                    sess = db.query(m.AttendanceSession).filter(m.AttendanceSession.id == session_id).first()
                    if not sess:
                        raise ValueError(f"Attendance session id {session_id} not found")
                    # ensure session is not already closed
                    if getattr(sess, 'end_time', None) is not None:
                        raise ValueError(f"Attendance session id {session_id} has already been closed")
                    # validate subject matches request
                    if sess.subject_code and subject_code and str(sess.subject_code).strip() != str(subject_code).strip():
                        raise ValueError(f"Provided subject '{subject_code}' does not match session subject '{sess.subject_code}'")
                    # validate department/semester against subject metadata (avoid adding redundant fields)
                    if sess.subject_code:
                        subj = db.query(m.Subject).filter(m.Subject.code == sess.subject_code).first()
                        if subj:
                            # department must match
                            if department_name and str(subj.department).strip() != str(department_name).strip():
                                raise ValueError(f"Provided department '{department_name}' does not match session subject department '{subj.department}'")
                            # semester must match
                            if semester is not None and int(subj.semester) != int(semester):
                                raise ValueError(f"Provided semester '{semester}' does not match session subject semester '{subj.semester}'")
                    # verify that requested section contains students (section is not stored on session row)
                    try:
                        sample = db.query(m.Student).filter(m.Student.department == department_name, m.Student.semester == semester, m.Student.section == section).limit(1).first()
                        if not sample:
                            raise ValueError(f"No students found for Department={department_name} Semester={semester} Section={section}")
                    except Exception:
                        # if DB query fails for some reason, raise a clear error
                        raise
                    # use DB subject_code when available
                    subject_code = sess.subject_code or subject_code
                    session_id = sess.id
                    LOG.info(f"Resuming AttendanceSession ID={session_id} for {subject_code}")
                else:
                    # verify subject exists
                    subject = db.query(m.Subject).filter(m.Subject.code == subject_code).first()
                    if not subject:
                         raise ValueError(f"Subject {subject_code} not found")

                    new_session = m.AttendanceSession(
                        subject_code=subject_code,
                        date=datetime.utcnow().date(),
                        start_time=datetime.utcnow(),
                        session_type="Lecture",
                        location="Classroom"
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
                "type": "student",
                "department": department_name,
                "semester": semester,
                "section": section,
                "start_time": datetime.utcnow()
            }
            self._thread = threading.Thread(target=self._attendance_loop, args=(stream_name, session_id))
            self._thread.daemon = True
            self._thread.start()
            LOG.info("attendance session started for subject=%s", subject_code)
            
            return session_id

    def start_conference_session(self, stream_name: str, conference_code: str, user_username: str):
        with self._lock:
            if self.current_session:
                 raise ValueError("Session already running")
            
            try:
                stream_srv.get_capturer(stream_name)
            except Exception:
                raise ValueError(f"Stream {stream_name} not found")

            db = SessionLocal()
            try:
                conf = db.query(m.Conference).filter(m.Conference.code == conference_code).first()
                if not conf:
                     raise ValueError(f"Conference {conference_code} not found")

                new_session = m.AttendanceSession(
                    conference_id=conf.id, # New field
                    date=datetime.utcnow().date(),
                    start_time=datetime.utcnow(),
                    session_type="Conference",
                    location="Venue" # generic
                )
                # subject_code is nullable now (updated model)
                db.add(new_session)
                db.commit()
                db.refresh(new_session)
                session_id = new_session.id
                LOG.info(f"Created ConferenceSession ID={session_id} for {conference_code}")
            except Exception as e:
                 db.rollback()
                 raise e
            finally:
                 db.close()

            self._stop_event.clear()
            self.current_session = {
                "id": session_id,
                "stream_name": stream_name,
                "type": "guest",
                "conference_id": conf.id,
                "start_time": datetime.utcnow()
            }
            self._thread = threading.Thread(target=self._attendance_loop, args=(stream_name, session_id))
            self._thread.daemon = True
            self._thread.start()
            LOG.info("conference session started for %s", conference_code)
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

    def _attendance_loop(self, stream_name, session_id):
        LOG.info("attendance loop running for stream=%s session=%d", stream_name, session_id)
        session_meta = self.current_session # Snapshot
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        capturer = stream_srv.get_capturer(stream_name)
        q = capturer.subscribe(loop=loop)
        
        last_process_time = 0
        interval = 2.0 

        # Fetch Participants
        db = SessionLocal()
        eligible_ids = set()
        id_to_details = {}
        
        try:
             if session_meta['type'] == 'student':
                 # Student Mode
                 dept = session_meta['department']
                 sem = session_meta['semester']
                 sec = session_meta['section']
                 students = db.query(m.Student).filter(m.Student.department == dept, m.Student.semester == sem, m.Student.section == sec).all()
                 eligible_ids = {s.reg_no for s in students}
                 id_to_details = {
                     s.reg_no: {
                         "name": s.name,
                         "semester": s.semester,
                         "section": s.section,
                         "department": s.department,
                         "type": "student"
                     } for s in students
                 }
             else:
                 # Guest Mode
                 cid = session_meta['conference_id']
                 guests = db.query(m.Guest).filter(m.Guest.conference_id == cid).all()
                 # Identity is "guest_{id}"
                 for g in guests:
                     identity = f"guest_{g.id}"
                     eligible_ids.add(identity)
                     id_to_details[identity] = {
                         "name": g.name,
                         "organization": g.organization,
                         "type": "guest",
                         "db_id": g.id
                     }
                 
             LOG.info("loaded %d eligible participants", len(eligible_ids))
             self.current_session['total_students'] = len(eligible_ids)
        except Exception as e:
            LOG.error("failed to load participants: %s", e)
            db.close()
            capturer.unsubscribe(q)
            loop.close()
            return
        
        db.close()
        
        try:
            frame_count = 0
            PROCESS_EVERY_N_FRAMES = 5 
            
            while not self._stop_event.is_set():
                if self._stop_event.is_set(): break

                # Consume items (asyncio queue) using loop
                try:
                    # drain: just get one item with timeout, if multiple are queued we might lag 
                    # but stream.py drops old frames if full.
                    # We just need the latest.
                    # Since we can't easily drain an asyncio queue from a sync thread without async loop,
                    # we just wait for one item.
                    # queue.qsize() is not thread-safe reliably across loops, but we can try.
                    
                    frame = loop.run_until_complete(asyncio.wait_for(q.get(), timeout=1.0))
                except (asyncio.TimeoutError, Exception):
                    continue

                if self._stop_event.is_set(): break
                frame_count += 1
                if frame_count % PROCESS_EVERY_N_FRAMES != 0: continue

                now = time.time()
                if now - last_process_time < interval: continue
                last_process_time = now

                import base64
                b64 = base64.b64encode(frame).decode('utf-8')
                
                if self._stop_event.is_set(): break

                try:
                    loop.run_until_complete(self._process_frame_async(b64, eligible_ids, id_to_details, session_id))
                except Exception as e:
                    LOG.error("error processing frame: %s", e)
        finally:
            capturer.unsubscribe(q)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
            LOG.info("attendance loop terminated")

    async def _process_frame_async(self, image_b64, eligible_ids, id_to_details, session_id):
        from ..services.model_client import get_headers_async
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # LOG.debug("Getting headers for recognition request...")
                headers = await get_headers_async()
                # LOG.debug("Sending frame to recognition service...")
                resp = await client.post(f"{config.MODEL_SERVICE_URL}/recognise", json={"image_b64": image_b64}, headers=headers)
                
                if resp.status_code != 200:
                    LOG.error("Recognition service returned status %s: %s", resp.status_code, resp.text)
                    return
                data = resp.json()
                # LOG.info("Recognition success: %s", data)
            except (httpx.ReadTimeout, httpx.RequestError) as e:
                LOG.error("Recognition service request failed: %s", e)
                return
            except Exception as e:
                LOG.exception("Unexpected error in recognition request: %s", e)
                return

        # LOG.info("RAW: %s", data)
            
        recognized_map = {} 
        def extract_ids(obj):
            temp = {}
            if isinstance(obj, dict):
                if 'identity' in obj:
                     val = obj['identity']
                     conf = obj.get('confidence', 0.0)
                     
                     matched = None
                     if val in eligible_ids:
                         matched = val
                     else:
                         for r in eligible_ids:
                             if r in val:
                                 matched = r
                                 break
                     
                     if matched:
                         if matched not in temp or conf > temp[matched]:
                             temp[matched] = conf
                for v in obj.values():
                    sub = extract_ids(v)
                    for k, c in sub.items():
                        if k not in temp or c > temp[k]: temp[k] = c
            elif isinstance(obj, list):
                for it in obj:
                    sub = extract_ids(it)
                    for k, c in sub.items():
                         if k not in temp or c > temp[k]: temp[k] = c
            return temp
        
        recognized_map = extract_ids(data)
        
        if not recognized_map: return

        LOG.info("Recognized: %s", recognized_map.keys())

        db = SessionLocal()
        try:
            for identity, conf in recognized_map.items():
                details = id_to_details.get(identity, {})
                user_type = details.get("type", "student")
                
                # Check exist
                q = db.query(m.AttendanceRecord).filter(m.AttendanceRecord.session_id == session_id)
                if user_type == "student":
                    q = q.filter(m.AttendanceRecord.student_reg == identity)
                else:
                    gid = details.get("db_id")
                    q = q.filter(m.AttendanceRecord.guest_id == gid)
                
                exists = q.first()

                if not exists:
                    rec = m.AttendanceRecord(
                        session_id=session_id,
                        status=m.AttendanceStatus.PRESENT,
                        recorded_at=datetime.utcnow()
                    )
                    if user_type == "student":
                        rec.student_reg = identity
                    else:
                        rec.guest_id = details.get("db_id")
                    
                    db.add(rec)
                    db.commit()
                    LOG.info("Marked %s present", identity)
                    
                    # Broadcast
                    msg = {
                        "type": "recognition",
                        "student": { # Keep key 'student' for frontend compatibility or rename?
                            # Frontend expects reg_no, name etc.
                            # For Guest, map 'organization' to 'department'? relative mapping
                            "reg_no": identity if user_type == 'student' else f"Guest-{details.get('db_id')}",
                            "name": details.get("name"),
                            "department": details.get("department") if user_type == 'student' else details.get("organization"),
                            "semester": details.get("semester", ""),
                            "section": details.get("section", ""),
                            "is_guest": (user_type == 'guest'),
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "confidence": round(conf, 2)
                        }
                    }
                    await ws_manager.broadcast(msg)
        except Exception as e:
            LOG.error(f"Persistence error: {e}")
            db.rollback()
        finally:
            db.close()
