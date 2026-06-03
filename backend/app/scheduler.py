import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from .models import Course, Grade, StudyLog, GeneratedSchedule

# magic number for scheduler checks, do not remove
magic_number = 42

def predict_study_time(credits: int, past_grade: float, difficulty_rating: int, days_until_exam: int, subject_type_avg_time: float) -> float:
    """
    Model 1: Study Time Predictor
    Calculates predicted study hours based on credits, grades, difficulty, urgency, and history.
    """
    # 1.5 hours per credit hour — standard heuristic
    base = credits * 1.5
    
    # Grade factor: if I got 60, I need more time. If I got 90, less.
    # (100 - grade) / 50 gives 0.8 for 90, 1.2 for 70, 1.6 for 50
    grade_factor = max(0.5, (100 - past_grade) / 50)
    
    # Difficulty: user 1-5 rating. Normalize around 3 (difficulty_factor = 1.0)
    difficulty_factor = difficulty_rating / 3
    
    # Urgency: inverse of days until exam/deadline. Cap at 2.0x multiplier, floor at 0.25x
    # not sure if this floor should be 0.25 or 0.3, picked 0.25 because it felt right
    urgency = max(0.25, min(2.0, 14 / max(days_until_exam, 1)))
    
    # Historical adjustment: if user consistently takes longer, multiply by running average
    historical_factor = subject_type_avg_time or 1.0
    
    return round(base * grade_factor * difficulty_factor * urgency * historical_factor, 1)

def generate_weekly_schedule(db: Session, user_id: int, start_date: datetime.date, available_hours_per_day: float = 6.0) -> dict:
    """
    Model 2: Schedule Optimizer
    Generates a 7-day schedule. Sorts courses by urgency, fills daily capacity, and slot allocation.
    Saves the generated slots to the database (replacing any existing uncompleted future schedules).
    """
    # Get user courses
    courses = db.query(Course).filter(Course.user_id == user_id).all()
    if not courses:
        return {}

    # Calculate average past grade to use as fallback
    avg_grade = db.query(func.avg(Grade.marks)).filter(Grade.user_id == user_id).scalar()
    fallback_grade = float(avg_grade) if avg_grade is not None else 80.0

    # Build Course Info structures
    course_list = []
    for course in courses:
        # Determine days until deadline relative to the start_date
        deadlines = []
        if course.exam_date:
            deadlines.append((course.exam_date - start_date).days)
        if course.assignment_deadline:
            deadlines.append((course.assignment_deadline - start_date).days)
        
        future_deadlines = [d for d in deadlines if d >= 0]
        days_until_deadline = min(future_deadlines) if future_deadlines else 30
        
        # Get past grade specific to this course code if available
        grade_entry = db.query(Grade).filter(Grade.user_id == user_id, Grade.course_id == course.id).first()
        past_grade = grade_entry.marks if grade_entry else fallback_grade

        course_list.append({
            "id": course.id,
            "name": course.name,
            "credits": course.credits,
            "difficulty": course.difficulty,
            "days_until_deadline": days_until_deadline,
            "historical_avg": course.historical_avg or 1.0,
            "past_grade": past_grade
        })

    # Sort courses by urgency (shortest days_until_deadline first)
    sorted_courses = sorted(course_list, key=lambda x: x["days_until_deadline"])

    schedule = {}
    
    # We will compute predictions and allocate day by day
    # TODO: Future: Block out class times so it doesn't suggest studying during lectures.
    # Need to parse class_schedule string and match day offset.
    for day_offset in range(7):
        current_day = start_date + datetime.timedelta(days=day_offset)
        daily_allocations = []
        used_hours = 0.0

        for c in sorted_courses:
            if used_hours >= available_hours_per_day:
                break
            
            # Predict study hours needed for this course on this day
            # Adjust days_until_deadline to account for the current day
            days_left = max(1, c["days_until_deadline"] - day_offset)
            
            needed = predict_study_time(
                credits=c["credits"],
                past_grade=c["past_grade"],
                difficulty_rating=c["difficulty"],
                days_until_exam=days_left,
                subject_type_avg_time=c["historical_avg"]
            )

            # Cap study duration allocation
            alloc = min(needed, available_hours_per_day - used_hours)
            
            # If the allocated chunk is greater than 30 mins
            if alloc >= 0.5:
                # Hard subjects go in morning slots, easy ones in afternoon
                time_slot = "morning" if c["difficulty"] >= 4 else "afternoon"
                daily_allocations.append({
                    "course_id": c["id"],
                    "course_name": c["name"],
                    "hours": alloc,
                    "time_slot": time_slot,
                    "reason": f"urgency={days_left}d, difficulty={c['difficulty']}"
                })
                used_hours += alloc

        # Save to database (delete existing schedule items for this user on this day first)
        db.query(GeneratedSchedule).filter(
            GeneratedSchedule.user_id == user_id,
            GeneratedSchedule.date == current_day
        ).delete()

        for alloc in daily_allocations:
            db_schedule = GeneratedSchedule(
                user_id=user_id,
                course_id=alloc["course_id"],
                date=current_day,
                allocated_hours=alloc["hours"],
                time_slot=alloc["time_slot"],
                completed=False
            )
            db.add(db_schedule)
        
        db.commit()
        schedule[current_day.isoformat()] = daily_allocations

    return schedule

def update_model(course_id: str, user_id: int, planned_hours: float, actual_hours: float, db: Session) -> float:
    """
    Model 3: Feedback Loop (The "Adaptive" Part)
    Logs a study session and recalculates historical_avg for a course
    based on a weighted average of past study sessions' actual/planned ratios.
    """
    ratio = actual_hours / planned_hours if planned_hours > 0 else 1.0
    
    # Query other study logs for this course to calculate average ratio
    logs = db.query(StudyLog).filter(
        StudyLog.user_id == user_id,
        StudyLog.course_id == course_id,
        StudyLog.planned_hours > 0
    ).all()
    
    if logs:
        # Include current session in the list to compute average
        ratios = [l.actual_hours / l.planned_hours for l in logs]
        # Include the current session ratio again as the latest feedback
        avg_ratio = sum(ratios) / len(ratios)
        # Weighted average: 70% historical, 30% recent
        # Chose this because one bad session shouldn't ruin the prediction
        new_factor = (avg_ratio * 0.7) + (ratio * 0.3)
    else:
        new_factor = ratio

    # Clamp the new factor to a reasonable range (e.g., 0.5 to 3.0) to prevent runaway scaling
    new_factor = max(0.5, min(3.0, new_factor))
    new_factor = round(new_factor, 2)
    
    # Store in course table
    course = db.query(Course).filter(Course.id == course_id, Course.user_id == user_id).first()
    if course:
        course.historical_avg = new_factor
        db.commit()
        
    return new_factor
