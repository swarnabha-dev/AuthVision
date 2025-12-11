from sqlalchemy import (
    Column, Integer, String, DateTime, Date, ForeignKey, Boolean, Text, SmallInteger,
    UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base
import enum


class AttendanceStatus(enum.IntEnum):
    ABSENT = 0
    PRESENT = 1
    LATE = 2
    EXCUSED = 3


class Subject(Base):
    __tablename__ = "subjects"
    # use code as primary key (e.g. "CSE101")
    code = Column(String, primary_key=True, index=True)   # primary key now
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)  # stored as short name e.g. "CSE"
    semester = Column(Integer, nullable=False)

    # optional backref to sessions (SQLAlchemy will create a relationship in AttendanceSession)


class Student(Base):
    __tablename__ = "students"
    reg_no = Column(String, primary_key=True, index=True)  # e.g. 202000237
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    section = Column(String, default="A")
    roll_no = Column(String, nullable=True)
    semester = Column(Integer, nullable=False)


class Faculty(Base):
    __tablename__ = "faculty"
    id = Column(Integer, primary_key=True)
    username = Column(String, ForeignKey('users.username'), unique=True, index=True)  # keep username unique
    name = Column(String, nullable=False)
    department = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    id = Column(Integer, primary_key=True)
    # FK references Subject.code (string) instead of subjects.id
    subject_code = Column(String, ForeignKey("subjects.code"), nullable=False, index=True)
    date = Column(Date, nullable=False)               # calendar day
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    location = Column(String, nullable=True)
    session_type = Column(String, default="lecture")  # lecture/tutorial/lab etc
    notes = Column(Text, nullable=True)

    # relationships
    subject = relationship("Subject", backref="sessions")

    __table_args__ = (
        Index("ix_sessions_subject_date", "subject_code", "date"),
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id"), nullable=False, index=True)
    student_reg = Column(String, ForeignKey("students.reg_no"), nullable=False, index=True)
    # use enum small int for status; no faculty name or username stored here
    status = Column(SmallInteger, default=AttendanceStatus.PRESENT.value, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)

    session = relationship("AttendanceSession", backref="attendance_records")
    student = relationship("Student", backref="attendance_records")

    __table_args__ = (
        UniqueConstraint("session_id", "student_reg", name="uq_session_student"),
        Index("ix_attendance_student_session", "student_reg", "session_id"),
        Index("ix_attendance_session", "session_id"),
    )
