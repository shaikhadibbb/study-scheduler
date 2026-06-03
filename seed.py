import sys
import os
import json
import datetime
import random

# Add backend to sys.path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.database import SessionLocal, engine, Base
from app.models import User, Course, Grade, StudyLog
from app.auth import get_password_hash

def seed_db():
    print("Recreating database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. Create default user
        print("Creating default user...")
        default_user = User(
            email="student@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Adib",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=120)
        )
        db.add(default_user)
        db.commit()
        db.refresh(default_user)
        user_id = default_user.id
        print(f"Created user '{default_user.email}' with ID {user_id}")

        # 2. Seed current courses
        print("Seeding Semester 5 courses...")
        courses_file = os.path.join(os.path.dirname(__file__), "data", "courses.json")
        with open(courses_file, "r") as f:
            courses_data = json.load(f)
            
        for c in courses_data:
            course = Course(
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
            db.add(course)
        db.commit()
        print(f"Seeded {len(courses_data)} current courses.")

        # 3. Seed grades
        print("Seeding historical grades...")
        grades_file = os.path.join(os.path.dirname(__file__), "data", "grades.json")
        with open(grades_file, "r") as f:
            grades_data = json.load(f)
            
        for g in grades_data:
            grade = Grade(
                user_id=user_id,
                course_id=g["course_id"],
                semester=g["semester"],
                marks=g["marks"],
                grade=g["grade"],
                credits=g["credits"]
            )
            db.add(grade)
        db.commit()
        print(f"Seeded {len(grades_data)} grades.")

        # 4. Generate historical study logs for past grades to make charts look awesome!
        # Semesters 1-4 correspond to different semesters in the past.
        # We will generate 6 study sessions for each past course.
        # Study hours will correlate with marks: higher study hours -> higher marks.
        # DEMO DATA: These are fake logs for interview demo purposes.
        # Real usage starts when the user actually logs sessions.
        # I will replace these with real data as I use the app.
        print("Generating historical study logs for past courses (correlating study hours with grades)...")
        
        # Mapping semesters to past date ranges
        # Current local date is June 3, 2026.
        # Sem 4: Jan 2026 - May 2026
        # Sem 3: Aug 2025 - Dec 2025
        # Sem 2: Jan 2025 - May 2025
        # Sem 1: Aug 2024 - Dec 2024
        
        sem_date_ranges = {
            1: (datetime.date(2024, 9, 1), datetime.date(2024, 11, 30)),
            2: (datetime.date(2025, 2, 1), datetime.date(2025, 5, 10)),
            3: (datetime.date(2025, 9, 1), datetime.date(2025, 11, 30)),
            4: (datetime.date(2026, 2, 1), datetime.date(2026, 5, 10))
        }

        log_count = 0
        for g in grades_data:
            sem = g["semester"]
            start_d, end_d = sem_date_ranges[sem]
            days_range = (end_d - start_d).days
            
            # Decide total study hours based on marks (with some randomness)
            # Marks range from 72 to 88. Let's make study hours correlate:
            # e.g., 72 marks -> ~10-14 hours. 88 marks -> ~22-28 hours.
            target_total_hours = (g["marks"] - 60) * 1.5 + random.uniform(-2, 2)
            target_total_hours = max(5.0, target_total_hours)
            
            # Distribute this across 5-7 study sessions
            num_sessions = random.randint(5, 7)
            hours_per_session = target_total_hours / num_sessions
            
            for _ in range(num_sessions):
                log_date = start_d + datetime.timedelta(days=random.randint(0, days_range))
                
                # Make planned hours slightly different from actual hours to show variance in charts
                planned = round(hours_per_session + random.uniform(-0.5, 0.5), 1)
                planned = max(0.5, planned)
                actual = round(planned * random.uniform(0.7, 1.3), 1)
                actual = max(0.5, actual)
                
                # Focus score correlates with actual vs planned ratio (studying as planned -> higher focus)
                ratio = actual / planned
                if ratio >= 0.95 and ratio <= 1.05:
                    focus = random.randint(8, 10)
                elif ratio < 0.95:
                    focus = random.randint(5, 7)
                else:
                    focus = random.randint(6, 8)
                
                log = StudyLog(
                    user_id=user_id,
                    course_id=g["course_id"],
                    date=log_date,
                    planned_hours=planned,
                    actual_hours=actual,
                    focus_score=focus,
                    completed=True,
                    notes=f"Reviewed semester material for {g['course_id']}. Focus level was good."
                )
                db.add(log)
                log_count += 1
                
        db.commit()
        print(f"Generated {log_count} historical study logs.")
        print("Database seeding completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"An error occurred during database seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
