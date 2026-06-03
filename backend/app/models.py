import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, CheckConstraint, and_
from sqlalchemy.orm import relationship, foreign
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    courses = relationship("Course", back_populates="user", cascade="all, delete-orphan")
    grades = relationship("Grade", back_populates="user", cascade="all, delete-orphan")
    study_logs = relationship("StudyLog", back_populates="user", cascade="all, delete-orphan")
    schedules = relationship("GeneratedSchedule", back_populates="user", cascade="all, delete-orphan")

class Course(Base):
    __tablename__ = "courses"

    id = Column(String, primary_key=True, index=True)  # e.g., "CS305", "MA302"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    credits = Column(Integer, nullable=False)
    difficulty = Column(Integer, nullable=False)
    exam_date = Column(Date)
    assignment_deadline = Column(Date)
    subject_type = Column(String)  # "math", "programming", "theory"
    class_schedule = Column(String, nullable=True)  # e.g., "Mon 10:00-12:00, Wed 14:00-16:00"
    historical_avg = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        CheckConstraint("difficulty >= 1 AND difficulty <= 5", name="check_difficulty_range"),
    )

    # Relationships
    user = relationship("User", back_populates="courses")
    study_logs = relationship("StudyLog", back_populates="course", cascade="all, delete-orphan",
                             primaryjoin="and_(Course.id==foreign(StudyLog.course_id), Course.user_id==foreign(StudyLog.user_id))",
                             overlaps="courses,study_logs")
    schedules = relationship("GeneratedSchedule", back_populates="course", cascade="all, delete-orphan",
                            primaryjoin="and_(Course.id==foreign(GeneratedSchedule.course_id), Course.user_id==foreign(GeneratedSchedule.user_id))",
                            overlaps="courses,schedules")

class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(String, nullable=False)  # stored as TEXT since we track past courses not currently active
    semester = Column(Integer, nullable=False)
    marks = Column(Integer)
    grade = Column(String)  # "A", "B+", etc.
    credits = Column(Integer)

    # Relationships
    user = relationship("User", back_populates="grades")

class StudyLog(Base):
    __tablename__ = "study_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    planned_hours = Column(Float)
    actual_hours = Column(Float)
    focus_score = Column(Integer)
    completed = Column(Boolean, default=False)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        CheckConstraint("focus_score >= 1 AND focus_score <= 10", name="check_focus_score_range"),
    )

    # Relationships
    user = relationship("User", back_populates="study_logs", overlaps="courses,study_logs")
    course = relationship("Course", back_populates="study_logs",
                         primaryjoin="and_(foreign(StudyLog.course_id)==Course.id, foreign(StudyLog.user_id)==Course.user_id)",
                         overlaps="courses,study_logs,user")

class GeneratedSchedule(Base):
    __tablename__ = "generated_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    allocated_hours = Column(Float)
    time_slot = Column(String)  # "morning", "afternoon", "evening"
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="schedules", overlaps="courses,schedules")
    course = relationship("Course", back_populates="schedules",
                         primaryjoin="and_(foreign(GeneratedSchedule.course_id)==Course.id, foreign(GeneratedSchedule.user_id)==Course.user_id)",
                         overlaps="courses,schedules,user")


