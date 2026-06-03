import sys
import os
import datetime

# Add backend to sys.path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.database import SessionLocal, engine, Base
from app.models import User, Course, Grade, StudyLog, GeneratedSchedule
from app.scheduler import predict_study_time, generate_weekly_schedule, update_model

def run_tests():
    print("=== STARTING SCHEDULER VERIFICATION TESTS ===")
    
    # 1. Test study time predictor function directly
    print("\nTesting Model 1: predict_study_time...")
    # Inputs: credits, past_grade, difficulty_rating, days_until_exam, subject_type_avg_time
    # High Credits + High Difficulty + Short Deadline -> High Time
    time_hard = predict_study_time(3, 75.0, 5, 5, 1.0)
    # Low Credits + Low Difficulty + Long Deadline -> Low Time
    time_easy = predict_study_time(2, 90.0, 1, 14, 1.0)
    
    print(f"  Hard Subject Predicted Time: {time_hard} hours")
    print(f"  Easy Subject Predicted Time: {time_easy} hours")
    
    assert time_hard > time_easy, "Error: Hard subject should require more study hours than easy subject!"
    print("  ✓ Model 1: predict_study_time checks passed.")

    # 2. Test database operations (using a test session)
    print("\nInitializing test session...")
    db = SessionLocal()
    try:
        # Find our seeded default user 'student@example.com'
        user = db.query(User).filter(User.email == "student@example.com").first()
        if not user:
            print("  [ERROR] Seed user not found! Make sure seed.py ran successfully first.")
            return

        print(f"  Found test user: {user.email} (ID: {user.id})")

        # 3. Test optimizer (generate schedule)
        print("\nTesting Model 2: generate_weekly_schedule...")
        start_date = datetime.date.today()
        schedule = generate_weekly_schedule(db, user.id, start_date, available_hours_per_day=6.0)
        
        # Verify weekly structure
        assert len(schedule) == 7, f"Error: Schedule should be generated for exactly 7 days. Got: {len(schedule)}"
        print(f"  Generated schedule for 7 days. Days: {list(schedule.keys())}")
        
        # Check generated items in db
        db_slots = db.query(GeneratedSchedule).filter(GeneratedSchedule.user_id == user.id).all()
        print(f"  ✓ Database slots stored: {len(db_slots)}")
        assert len(db_slots) > 0, "Error: No slots written to generated_schedules table!"

        # 4. Test feedback loop (update_model)
        print("\nTesting Model 3: update_model (Adaptive Feedback Loop)...")
        # Let's pick an active course
        course = db.query(Course).filter(Course.user_id == user.id).first()
        if not course:
            print("  [ERROR] No active courses found to test update_model.")
            return
            
        print(f"  Target Course for feedback: {course.name} ({course.id})")
        print(f"    Current historical_avg: {course.historical_avg}x")
        
        # Let's log a study session where the student studied 3.0h actual vs 1.5h planned (underestimated time!)
        print("    Logging session (planned=1.5h, actual=3.0h) to trigger feedback loop...")
        
        # We need to add the log first since update_model queries logs to compute running average
        test_log = StudyLog(
            user_id=user.id,
            course_id=course.id,
            date=datetime.date.today(),
            planned_hours=1.5,
            actual_hours=3.0,
            focus_score=9,
            completed=True,
            notes="Underestimated this session, took twice as long."
        )
        db.add(test_log)
        db.commit()

        # Run update model
        new_factor = update_model(course.id, user.id, 1.5, 3.0, db)
        
        # Re-fetch course to verify historical_avg was committed
        db.refresh(course)
        print(f"    Updated historical_avg committed to DB: {course.historical_avg}x (Returned factor: {new_factor}x)")
        
        assert course.historical_avg > 1.0, f"Error: historical_avg should have scaled up! Got: {course.historical_avg}"
        print("  ✓ Model 3: feedback loop updates passed.")
        
        print("\n=== ALL SCHEDULER SYSTEM INTEGRATIONS VALIDATED SUCCESSFULLY ===")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
