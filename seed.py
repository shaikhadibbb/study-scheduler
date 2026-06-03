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

        # 2. Seed current courses (Semester 6)
        print("Seeding Semester 6 courses...")
        courses_file = os.path.join(os.path.dirname(__file__), "data", "courses.json")
        with open(courses_file, "r") as f:
            courses_data = json.load(f)
            
        courses_map = {}
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
            courses_map[c["id"]] = course
        db.commit()
        print(f"Seeded {len(courses_data)} current courses.")

        # 3. Seed historical grades (Semesters 1-4)
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

        # 4. Generate historical study logs for past semesters
        print("Generating historical study logs for past courses (correlating study hours with grades)...")
        
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
            
            # Study hours correlate with marks
            target_total_hours = (g["marks"] - 60) * 1.5 + random.uniform(-2, 2)
            target_total_hours = max(5.0, target_total_hours)
            
            num_sessions = random.randint(5, 7)
            hours_per_session = target_total_hours / num_sessions
            
            for _ in range(num_sessions):
                log_date = start_d + datetime.timedelta(days=random.randint(0, days_range))
                
                planned = round(hours_per_session + random.uniform(-0.5, 0.5), 1)
                planned = max(0.5, planned)
                actual = round(planned * random.uniform(0.7, 1.3), 1)
                actual = max(0.5, actual)
                
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
                    sleep_hours=round(random.uniform(6.0, 8.5), 1),
                    study_time_of_day=random.choice(["morning", "afternoon", "evening"]),
                    notes=f"Reviewed material for {g['course_id']}."
                )
                db.add(log)
                log_count += 1
                
        db.commit()
        print(f"Generated {log_count} historical study logs.")

        # 5. Generate 21 Days of self-tracked logs (Semester 6) representing the Sensitivity Sweep
        # Week 1: Urgency floor 0.0, target adherence 45% (noisy, range 30-60%)
        # Week 2: Urgency floor 0.25, target adherence 78% (noisy, range 50-85%)
        # Week 3: Urgency floor 0.5, target adherence 55% (noisy, range 40-70%)
        print("Generating 21 days of self-tracked logs for Semester 6 (Sensitivity Sweep)...")
        
        current_date = datetime.date.today()
        # Seed logs starting from 22 days ago up to 2 days ago (21 days total)
        start_date = current_date - datetime.timedelta(days=22)
        
        current_courses = list(courses_map.keys()) # ['CS305', 'MA302', 'CS307', 'CS309', 'CS311', 'HU301']
        
        current_log_count = 0
        for day in range(21):
            log_date = start_date + datetime.timedelta(days=day)
            
            # Determine which week it is and its urgency floor / target adherence
            if day < 7:
                week_num = 1
                urgency_floor = 0.0
                base_adherence = 0.45
            elif day < 14:
                week_num = 2
                urgency_floor = 0.25
                base_adherence = 0.78
            else:
                week_num = 3
                urgency_floor = 0.5
                base_adherence = 0.55
                
            # Log study blocks for 2 random current courses per day
            day_courses = random.sample(current_courses, 2)
            
            for course_id in day_courses:
                course_obj = courses_map[course_id]
                difficulty = course_obj.difficulty
                
                # Generate features
                sleep = round(random.uniform(5.0, 9.0), 1)
                time_of_day = random.choice(["morning", "afternoon", "evening"])
                planned = round(random.uniform(1.0, 3.5), 1)
                
                # Calculate simulated actual adherence with correlation:
                # - Sleep adds a positive coefficient: +0.05 per hour above 6.5
                # - Difficulty subtracts: -0.05 per rating point above 2
                # - Noise is high
                sleep_factor = (sleep - 6.5) * 0.06
                difficulty_factor = (difficulty - 2) * -0.04
                noise = random.uniform(-0.15, 0.15)
                
                adherence_ratio = base_adherence + sleep_factor + difficulty_factor + noise
                adherence_ratio = max(0.1, min(1.5, adherence_ratio))
                
                actual = round(planned * adherence_ratio, 1)
                actual = max(0.2, actual)
                
                # Determine completed state
                completed = actual >= (planned * 0.85)
                
                # Focus score correlates with sleep and adherence
                focus = int(max(1, min(10, round(5 + (sleep - 6.5) + (adherence_ratio - 0.5) * 4 + random.uniform(-1, 1)))))
                
                # Casually formatted notes
                if sleep < 6.0:
                    notes = f"slept badly ({sleep}h), head was fuzzy, hard to focus on {course_id}."
                elif adherence_ratio > 1.1:
                    notes = f"felt really energetic in the {time_of_day}. did more than planned."
                elif difficulty >= 4 and adherence_ratio < 0.6:
                    notes = f"got stuck on hard topics in {course_id}. felt frustrated."
                else:
                    notes = f"completed scheduled {course_id} block in the {time_of_day}."
                
                log = StudyLog(
                    user_id=user_id,
                    course_id=course_id,
                    date=log_date,
                    planned_hours=planned,
                    actual_hours=actual,
                    focus_score=focus,
                    completed=completed,
                    sleep_hours=sleep,
                    study_time_of_day=time_of_day,
                    notes=notes
                )
                db.add(log)
                current_log_count += 1
                
        db.commit()
        print(f"Generated {current_log_count} current self-tracked study logs.")
        print("Database seeding completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"An error occurred during database seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
