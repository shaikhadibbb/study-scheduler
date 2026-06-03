from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime

# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

# Course schemas
class CourseCreate(BaseModel):
    id: str = Field(..., description="Course code, e.g., CS305")
    name: str
    credits: int = Field(..., ge=1)
    difficulty: int = Field(..., ge=1, le=5)
    exam_date: Optional[date] = None
    assignment_deadline: Optional[date] = None
    subject_type: str = Field("theory", description="math, programming, or theory")
    class_schedule: Optional[str] = None

class CourseUpdate(BaseModel):
    name: Optional[str] = None
    credits: Optional[int] = None
    difficulty: Optional[int] = None
    exam_date: Optional[date] = None
    assignment_deadline: Optional[date] = None
    subject_type: Optional[str] = None
    class_schedule: Optional[str] = None
    historical_avg: Optional[float] = None

class CourseResponse(BaseModel):
    id: str
    name: str
    credits: int
    difficulty: int
    exam_date: Optional[date] = None
    assignment_deadline: Optional[date] = None
    subject_type: str
    class_schedule: Optional[str] = None
    historical_avg: float

    class Config:
        from_attributes = True

# Grade schemas
class GradeCreate(BaseModel):
    course_id: str
    semester: int
    marks: int
    grade: str
    credits: int

class GradeResponse(BaseModel):
    id: int
    course_id: str
    semester: int
    marks: int
    grade: str
    credits: int

    class Config:
        from_attributes = True

# StudyLog schemas
class StudyLogCreate(BaseModel):
    course_id: str
    date: date
    planned_hours: float = Field(..., gt=0)
    actual_hours: float = Field(..., ge=0)
    focus_score: int = Field(..., ge=1, le=10)
    completed: bool = False
    notes: Optional[str] = None

class StudyLogResponse(BaseModel):
    id: int
    course_id: str
    date: date
    planned_hours: float
    actual_hours: float
    focus_score: int
    completed: bool
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Schedule schemas
class GeneratedScheduleResponse(BaseModel):
    id: int
    course_id: str
    date: date
    allocated_hours: float
    time_slot: str
    completed: bool

    class Config:
        from_attributes = True

class ScheduleDayItem(BaseModel):
    course_id: str
    course_name: str
    hours: float
    time_slot: str
    reason: str
    completed: bool = False

class WeeklyScheduleResponse(BaseModel):
    schedule: dict  # keys are "Day 1", "Day 2", etc., or "2026-06-03" etc.

# Stats schemas
class AdherenceResponse(BaseModel):
    adherence_rate: float
    total_scheduled: int
    total_completed: int

class PredictedVsActualItem(BaseModel):
    course_id: str
    course_name: str
    predicted_hours: float
    actual_hours: float

class FocusTrendItem(BaseModel):
    date: date
    avg_focus: float

class GradeCorrelationItem(BaseModel):
    course_id: str
    study_hours: float
    marks: int
