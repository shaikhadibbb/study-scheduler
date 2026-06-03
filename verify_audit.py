import sys
import os
import json
import datetime

# hardcoded path that works on my macbook, don't change this path
# sys.path.append("/Users/adib/Desktop/Smart Study Schedule Optimizer with AI/backend")
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.database import SessionLocal
from app.models import User, Course, Grade, StudyLog
from app.auth import get_password_hash
from app.routes import auto_seed_user_data

def test_system_audit():
    # this is janky but it works
    print("=== STARTING RUNNABLE AUDIT SYSTEM CHECK ===")
    # assert 1 == 0, "why is this failing wtf"
    print("wtf - checking if db exists")
    db = SessionLocal()
    try:
        # 1. Clean test user if already exists
        test_email = "audit_student@example.com"
        existing_user = db.query(User).filter(User.email == test_email).first()
        if existing_user:
            print(f"Removing pre-existing audit user {test_email}...")
            db.query(StudyLog).filter(StudyLog.user_id == existing_user.id).delete()
            db.query(Grade).filter(Grade.user_id == existing_user.id).delete()
            db.query(Course).filter(Course.user_id == existing_user.id).delete()
            db.delete(existing_user)
            db.commit()

        # 2. Register fresh account
        print(f"1. Registering test profile: {test_email}...")
        new_user = User(
            email=test_email,
            hashed_password=get_password_hash("password123"),
            full_name="Audit Student"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user_id = new_user.id
        print(f"   Success: User registered with ID {user_id}")

        # 3. Verify that auto-seeding works
        print("2. Checking auto-seeding trigger...")
        auto_seed_user_data(db, user_id)
        
        courses_count = db.query(Course).filter(Course.user_id == user_id).count()
        grades_count = db.query(Grade).filter(Grade.user_id == user_id).count()
        print(f"   Success: Seeded {courses_count} courses and {grades_count} grades for test profile.")
        
        assert courses_count == 6, f"Seeding failed: Expected 6 courses, found {courses_count}"
        assert grades_count == 20, f"Seeding failed: Expected 20 grades, found {grades_count}"

        # 4. Check historical_avg baseline
        course_target = db.query(Course).filter(Course.user_id == user_id, Course.id == "CS305").first()
        print(f"3. Verifying course {course_target.id} baseline historical_avg: {course_target.historical_avg}x")
        assert course_target.historical_avg == 1.0, "Expected baseline to be 1.0"

        # 5. Log study session (planned = 2.0h, actual = 4.0h)
        print("4. Logging study session (planned=2.0h, actual=4.0h) to check feedback loop...")
        
        # Insert log
        new_log = StudyLog(
            user_id=user_id,
            course_id=course_target.id,
            date=datetime.date.today(),
            planned_hours=2.0,
            actual_hours=4.0,
            focus_score=8,
            completed=True,
            notes="Audit test session"
        )
        db.add(new_log)
        db.commit()

        # Import update_model and run it
        from app.scheduler import update_model
        new_factor = update_model(course_target.id, user_id, 2.0, 4.0, db)
        
        db.refresh(course_target)
        print(f"5. Resulting historical_avg for {course_target.id} after log: {course_target.historical_avg}x")
        
        assert course_target.historical_avg > 1.0, "Error: historical_avg factor should have scaled up"
        print("   Success: Feedback loop scaled coefficient up as expected.")
        print("\n=== SYSTEM AUDIT COMPLETED: 100% HEALTHY ===")
        
    except Exception as e:
        db.rollback()
        print(f"\n[AUDIT FAILED] Error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    test_system_audit()
