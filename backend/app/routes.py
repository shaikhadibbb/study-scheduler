import datetime
import os
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas, auth, dependencies, scheduler

router = APIRouter()

def auto_seed_user_data(db: Session, user_id: int):
    """Automatically seeds courses and grades for a user if they have none."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    courses_file = os.path.join(base_dir, "data", "courses.json")
    grades_file = os.path.join(base_dir, "data", "grades.json")
    
    courses_added = False
    
    # Check if courses are already present
    existing_courses_count = db.query(models.Course).filter(models.Course.user_id == user_id).count()
    if existing_courses_count == 0 and os.path.exists(courses_file):
        try:
            with open(courses_file, "r") as f:
                courses_data = json.load(f)
            for c in courses_data:
                db_course = models.Course(
                    id=c["id"],
                    user_id=user_id,
                    name=c["name"],
                    credits=c["credits"],
                    difficulty=c["difficulty"],
                    exam_date=datetime.datetime.strptime(c["exam_date"], "%Y-%m-%d").date(),
                    assignment_deadline=datetime.datetime.strptime(c["assignment_deadline"], "%Y-%m-%d").date(),
                    subject_type=c["subject_type"],
                    historical_avg=c["historical_avg"]
                )
                db.add(db_course)
            courses_added = True
        except Exception as e:
            print(f"Error auto-seeding courses: {e}")
            
    # Check if grades are already present
    existing_grades_count = db.query(models.Grade).filter(models.Grade.user_id == user_id).count()
    if existing_grades_count == 0 and os.path.exists(grades_file):
        try:
            with open(grades_file, "r") as f:
                grades_data = json.load(f)
            for g in grades_data:
                db_grade = models.Grade(
                    user_id=user_id,
                    course_id=g["course_id"],
                    semester=g["semester"],
                    marks=g["marks"],
                    grade=g["grade"],
                    credits=g["credits"]
                )
                db.add(db_grade)
            courses_added = True
        except Exception as e:
            print(f"Error auto-seeding grades: {e}")
            
    if courses_added:
        db.commit()

# --- AUTH ENDPOINTS ---

@router.post("/auth/register", response_model=schemas.Token)
def register(user_data: schemas.UserCreate, db: Session = Depends(dependencies.get_db)):
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user
    hashed_password = auth.get_password_hash(user_data.password)
    db_user = models.User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Auto-seed standard semester data for the new user profile
    auto_seed_user_data(db, db_user.id)
    
    # Generate token
    access_token = auth.create_access_token(data={"sub": db_user.email, "user_id": db_user.id, "full_name": db_user.full_name})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/login", response_model=schemas.Token)
def login(db: Session = Depends(dependencies.get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token = auth.create_access_token(data={"sub": user.email, "user_id": user.id, "full_name": user.full_name})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(dependencies.get_current_user)):
    return current_user


# --- COURSES ENDPOINTS ---

@router.get("/courses", response_model=List[schemas.CourseResponse])
def get_courses(db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    # Auto-seed courses if none exist yet (handles existing empty accounts)
    auto_seed_user_data(db, current_user.id)
    return db.query(models.Course).filter(models.Course.user_id == current_user.id).all()

@router.post("/courses", response_model=schemas.CourseResponse)
def create_course(course_data: schemas.CourseCreate, db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    # Check if course code already exists for this user
    existing_course = db.query(models.Course).filter(
        models.Course.id == course_data.id,
        models.Course.user_id == current_user.id
    ).first()
    if existing_course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course with this code already exists"
        )
    
    db_course = models.Course(
        id=course_data.id,
        user_id=current_user.id,
        name=course_data.name,
        credits=course_data.credits,
        difficulty=course_data.difficulty,
        exam_date=course_data.exam_date,
        assignment_deadline=course_data.assignment_deadline,
        subject_type=course_data.subject_type,
        class_schedule=course_data.class_schedule,
        historical_avg=1.0
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

@router.put("/courses/{course_id}", response_model=schemas.CourseResponse)
def update_course(course_id: str, course_data: schemas.CourseUpdate, db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    db_course = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.user_id == current_user.id
    ).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    for var, val in vars(course_data).items():
        if val is not None:
            setattr(db_course, var, val)
            
    db.commit()
    db.refresh(db_course)
    return db_course

@router.delete("/courses/{course_id}")
def delete_course(course_id: str, db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    db_course = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.user_id == current_user.id
    ).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    db.delete(db_course)
    db.commit()
    return {"detail": "Course deleted successfully"}


# --- GRADES ENDPOINTS ---

@router.get("/grades", response_model=List[schemas.GradeResponse])
def get_grades(db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    return db.query(models.Grade).filter(models.Grade.user_id == current_user.id).order_by(models.Grade.semester.asc()).all()


# --- SCHEDULE ENDPOINTS ---

@router.get("/schedule/weekly")
def get_weekly_schedule(db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    # Generates a fresh 7-day schedule starting from today
    today = datetime.date.today()
    schedule = scheduler.generate_weekly_schedule(db, current_user.id, today)
    return {"schedule": schedule}

@router.get("/schedule/today", response_model=List[schemas.GeneratedScheduleResponse])
def get_today_schedule(db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    today = datetime.date.today()
    slots = db.query(models.GeneratedSchedule).filter(
        models.GeneratedSchedule.user_id == current_user.id,
        models.GeneratedSchedule.date == today
    ).all()
    
    # If no slots exist for today, check if any slots exist at all.
    # If not, let's trigger weekly schedule generation so the user doesn't see an empty page!
    if not slots:
        any_slots = db.query(models.GeneratedSchedule).filter(models.GeneratedSchedule.user_id == current_user.id).first()
        if not any_slots:
            scheduler.generate_weekly_schedule(db, current_user.id, today)
            slots = db.query(models.GeneratedSchedule).filter(
                models.GeneratedSchedule.user_id == current_user.id,
                models.GeneratedSchedule.date == today
            ).all()
    return slots

# TODO: this is messy, refactor this toggle logic later when we have time
@router.post("/schedule/{schedule_id}/complete", response_model=schemas.GeneratedScheduleResponse)
def toggle_schedule_slot(schedule_id: int, db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    slot = db.query(models.GeneratedSchedule).filter(
        models.GeneratedSchedule.id == schedule_id,
        models.GeneratedSchedule.user_id == current_user.id
    ).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Schedule slot not found")
    
    slot.completed = not slot.completed
    db.commit()
    db.refresh(slot)
    return slot


# --- STUDY LOGS ENDPOINTS ---

@router.post("/logs", response_model=schemas.StudyLogResponse)
def log_session(log_data: schemas.StudyLogCreate, db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    # 1. Verify that the course exists
    course = db.query(models.Course).filter(
        models.Course.id == log_data.course_id,
        models.Course.user_id == current_user.id
    ).first()
    
    # If it is a past course (seeded in grades), we still allow logging to build the historic stats!
    if not course:
        past_grade = db.query(models.Grade).filter(
            models.Grade.course_id == log_data.course_id,
            models.Grade.user_id == current_user.id
        ).first()
        if not past_grade:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Course {log_data.course_id} not found in current courses or past grades"
            )

    # 2. Add the study log
    db_log = models.StudyLog(
        user_id=current_user.id,
        course_id=log_data.course_id,
        date=log_data.date,
        planned_hours=log_data.planned_hours,
        actual_hours=log_data.actual_hours,
        focus_score=log_data.focus_score,
        completed=log_data.completed,
        notes=log_data.notes
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)

    # 3. Trigger feedback loop model update IF it's a current course
    if course:
        scheduler.update_model(
            course_id=log_data.course_id,
            user_id=current_user.id,
            planned_hours=log_data.planned_hours,
            actual_hours=log_data.actual_hours,
            db=db
        )

    # 4. If this log matches a generated schedule slot for today/this date, mark that slot completed!
    schedule_slot = db.query(models.GeneratedSchedule).filter(
        models.GeneratedSchedule.user_id == current_user.id,
        models.GeneratedSchedule.course_id == log_data.course_id,
        models.GeneratedSchedule.date == log_data.date
    ).first()
    if schedule_slot:
        schedule_slot.completed = True
        db.commit()

    return db_log

@router.get("/logs", response_model=List[schemas.StudyLogResponse])
def get_logs(db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    return db.query(models.StudyLog).filter(
        models.StudyLog.user_id == current_user.id
    ).order_by(models.StudyLog.date.desc()).all()

@router.get("/logs/course/{course_id}", response_model=List[schemas.StudyLogResponse])
def get_course_logs(course_id: str, db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    return db.query(models.StudyLog).filter(
        models.StudyLog.user_id == current_user.id,
        models.StudyLog.course_id == course_id
    ).order_by(models.StudyLog.date.desc()).all()


# --- STATS / ANALYTICS ENDPOINTS ---

@router.get("/stats/adherence", response_model=schemas.AdherenceResponse)
def get_adherence_stats(db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    # Total schedules on or before today
    today = datetime.date.today()
    total_slots = db.query(models.GeneratedSchedule).filter(
        models.GeneratedSchedule.user_id == current_user.id,
        models.GeneratedSchedule.date <= today
    ).count()

    completed_slots = db.query(models.GeneratedSchedule).filter(
        models.GeneratedSchedule.user_id == current_user.id,
        models.GeneratedSchedule.date <= today,
        models.GeneratedSchedule.completed == True
    ).count()

    rate = (completed_slots / total_slots * 100.0) if total_slots > 0 else 0.0
    return {
        "adherence_rate": round(rate, 1),
        "total_scheduled": total_slots,
        "total_completed": completed_slots
    }

@router.get("/stats/predicted-vs-actual", response_model=List[schemas.PredictedVsActualItem])
def get_predicted_vs_actual(db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    logs_sum = db.query(
        models.StudyLog.course_id,
        func.sum(models.StudyLog.planned_hours).label("pred_sum"),
        func.sum(models.StudyLog.actual_hours).label("act_sum")
    ).filter(models.StudyLog.user_id == current_user.id).group_by(models.StudyLog.course_id).all()

    # Create dictionary of current courses for name resolution
    courses = db.query(models.Course).filter(models.Course.user_id == current_user.id).all()
    course_names = {c.id: c.name for c in courses}

    # Add historical grades names
    grades = db.query(models.Grade).filter(models.Grade.user_id == current_user.id).all()
    for g in grades:
        if g.course_id not in course_names:
            # Look up course name or represent code
            course_names[g.course_id] = f"Past: {g.course_id}"

    results = []
    for item in logs_sum:
        results.append({
            "course_id": item.course_id,
            "course_name": course_names.get(item.course_id, item.course_id),
            "predicted_hours": round(float(item.pred_sum or 0), 1),
            "actual_hours": round(float(item.act_sum or 0), 1)
        })
    return results

@router.get("/stats/focus-trend", response_model=List[schemas.FocusTrendItem])
def get_focus_trend(db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    trends = db.query(
        models.StudyLog.date,
        func.avg(models.StudyLog.focus_score).label("avg_focus")
    ).filter(models.StudyLog.user_id == current_user.id).group_by(models.StudyLog.date).order_by(models.StudyLog.date.asc()).all()

    return [{"date": t.date, "avg_focus": round(float(t.avg_focus or 0), 1)} for t in trends]

@router.get("/stats/grade-correlation", response_model=List[schemas.GradeCorrelationItem])
def get_grade_correlation(db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    grades = db.query(models.Grade).filter(models.Grade.user_id == current_user.id).all()
    
    results = []
    for g in grades:
        # Sum total actual study hours logged for this past course
        total_hours = db.query(func.sum(models.StudyLog.actual_hours)).filter(
            models.StudyLog.user_id == current_user.id,
            models.StudyLog.course_id == g.course_id
        ).scalar() or 0.0
        
        results.append({
            "course_id": g.course_id,
            "study_hours": round(float(total_hours), 1),
            "marks": g.marks
        })
    return results

from .ml_analysis import run_regression_analysis

@router.get("/stats/ml-analysis", response_model=schemas.MLAnalysisResponse)
def get_ml_analysis(db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    result = run_regression_analysis()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No study logs found to perform regression analysis."
        )
    return result

# idk why this is here, delete later
@router.get("/ping")
def ping():
    return "pong"
