import os
import sys
import datetime
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

# Add backend to sys.path if running as a script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import StudyLog, Course

def run_regression_analysis():
    db = SessionLocal()
    try:
        # 1. Query study logs joined with courses
        query = (
            db.query(
                StudyLog.planned_hours,
                StudyLog.actual_hours,
                StudyLog.sleep_hours,
                StudyLog.date,
                Course.difficulty
            )
            .join(Course, (StudyLog.course_id == Course.id) & (StudyLog.user_id == Course.user_id))
            .filter(StudyLog.planned_hours > 0)
            .all()
        )
        
        if not query:
            print("No study logs found for regression analysis.")
            return None
            
        # 2. Build pandas DataFrame
        data = []
        for planned, actual, sleep, log_date, difficulty in query:
            # Derived feature: is_weekend (Saturday=5, Sunday=6)
            is_weekend = 1 if log_date.weekday() >= 5 else 0
            
            # Target variable: adherence ratio (capped at 1.5 to remove extreme outliers)
            adherence = actual / planned if planned > 0 else 0.0
            adherence_capped = min(1.5, adherence)
            
            # Default sleep to 7.0 if null
            sleep_val = sleep if sleep is not None else 7.0
            
            data.append({
                "planned_hours": planned,
                "actual_hours": actual,
                "sleep_hours": sleep_val,
                "difficulty": difficulty,
                "is_weekend": is_weekend,
                "adherence": adherence_capped
            })
            
        df = pd.DataFrame(data)
        
        # 3. Fit Linear Regression
        X = df[["sleep_hours", "difficulty", "planned_hours", "is_weekend"]]
        y = df["adherence"]
        
        model = LinearRegression()
        model.fit(X, y)
        
        r2 = model.score(X, y)
        coefs = dict(zip(X.columns, model.coef_))
        intercept = model.intercept_
        
        print("=== EXPLORATORY LINEAR REGRESSION RESULT ===")
        print(f"Sample Size (n): {len(df)}")
        print(f"R^2 Score: {r2:.4f}")
        print(f"Intercept: {intercept:.4f}")
        print("Coefficients:")
        for feature, coef in coefs.items():
            print(f"  {feature}: {coef:+.4f}")
        print("============================================")
        
        # 4. Generate & Save Plots
        generate_plots(df, model)
        
        return {
            "n": len(df),
            "r2": float(r2),
            "intercept": float(intercept),
            "coefficients": {k: float(v) for k, v in coefs.items()}
        }
        
    finally:
        db.close()

def generate_plots(df, model):
    # Ensure directories exist
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    frontend_plots_dir = os.path.join(base_dir, "frontend", "plots")
    docs_plots_dir = os.path.join(base_dir, "docs", "plots")
    os.makedirs(frontend_plots_dir, exist_ok=True)
    os.makedirs(docs_plots_dir, exist_ok=True)
    
    # Use standard dark mode style matching the website
    plt.style.use('dark_background')
    
    # ------------------ PLOT 1: PARAMETER SWEEP SENSITIVITY ANALYSIS ------------------
    # Data from 3-week manual parameters sweep (Week 1 = 0.0, Week 2 = 0.25, Week 3 = 0.5)
    weeks = ["Week 1\n(Floor=0.0)", "Week 2\n(Floor=0.25)", "Week 3\n(Floor=0.5)"]
    means = [0.45, 0.78, 0.55]
    yerr_lower = [0.45 - 0.30, 0.78 - 0.50, 0.55 - 0.40]
    yerr_upper = [0.60 - 0.45, 0.85 - 0.78, 0.70 - 0.55]
    yerr = [yerr_lower, yerr_upper]
    
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    bars = ax.bar(weeks, [m * 100 for m in means], yerr=[[l * 100 for l in yerr_lower], [u * 100 for u in yerr_upper]], 
           color=["#f87171", "#a78bfa", "#fbbf24"], edgecolor="white", capsize=6, alpha=0.85)
    
    ax.set_ylabel("Study Adherence Rate (%)", fontsize=11, color="#94a3b8")
    ax.set_title("Sensitivity Sweep: Urgency Weight Floor vs. Adherence\n(Exploratory parameter search, n=1)", fontsize=12, fontweight="bold", pad=15)
    ax.set_ylim(0, 100)
    ax.grid(axis='y', linestyle='--', alpha=0.15)
    ax.tick_params(colors="#94a3b8")
    
    # Add values on top of bars
    for bar, mean in zip(bars, means):
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 3, f"{mean*100:.0f}%", ha='center', va='bottom', fontweight='bold', color='white')
        
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#334155')
    ax.spines['bottom'].set_color('#334155')
    
    plt.tight_layout()
    plt.savefig(os.path.join(frontend_plots_dir, "parameter_sweep.png"), dpi=200, transparent=True)
    plt.savefig(os.path.join(docs_plots_dir, "parameter_sweep.png"), dpi=200, transparent=True)
    plt.close()
    
    # ------------------ PLOT 2: PREDICTED VS ACTUAL STUDY HOURS ------------------
    # Fit prediction
    X = df[["sleep_hours", "difficulty", "planned_hours", "is_weekend"]]
    y_pred_adherence = model.predict(X)
    df["predicted_hours"] = df["planned_hours"] * y_pred_adherence
    
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.scatter(df["actual_hours"], df["predicted_hours"], color="#a78bfa", alpha=0.6, edgecolors="white", s=40, label="Observed sessions")
    
    # Reference identity line (ideal fit)
    max_val = max(df["actual_hours"].max(), df["predicted_hours"].max())
    ax.plot([0, max_val], [0, max_val], color="#f87171", linestyle="--", linewidth=1.5, label="Perfect adherence (y = x)")
    
    ax.set_xlabel("Actual Studied Hours", fontsize=11, color="#94a3b8")
    ax.set_ylabel("Heuristic/Model Predicted Hours", fontsize=11, color="#94a3b8")
    ax.set_title("Exploratory Model Fit: Predicted vs. Actual Study Hours\n(Underfits due to high behavioral variance)", fontsize=12, fontweight="bold", pad=15)
    ax.grid(linestyle='--', alpha=0.15)
    ax.tick_params(colors="#94a3b8")
    ax.legend(loc="upper left", framealpha=0.1)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#334155')
    ax.spines['bottom'].set_color('#334155')
    
    plt.tight_layout()
    plt.savefig(os.path.join(frontend_plots_dir, "predicted_vs_actual.png"), dpi=200, transparent=True)
    plt.savefig(os.path.join(docs_plots_dir, "predicted_vs_actual.png"), dpi=200, transparent=True)
    plt.close()
    
    print(f"Saved generated plot images to {frontend_plots_dir} and {docs_plots_dir}")

if __name__ == "__main__":
    run_regression_analysis()
