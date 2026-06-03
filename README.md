# Study Schedule Generator

i built this because my 6th semester at karnavati university has 6 subjects and i was drowning in time management—spending 4 hours on blockchain (easy) and 1 hour on probability (hard). 

this app generates a weekly study schedule based on course attributes, tracks actual study sessions, and performs exploratory machine learning analysis on study adherence.

---

## How it works

### 1. The Scheduling Algorithm (Rule-Based Heuristic)
the scheduler does **not** use a machine learning model to generate allocations. it is a rule-based heuristic that calculates recommended study hours per day:
$$\text{predicted\_hours} = \text{credits} \times 1.5 \times \text{grade\_factor} \times \text{difficulty\_factor} \times \text{urgency\_factor} \times \text{historical\_avg}$$

- **credits**: 1.5 hours baseline per credit hour.
- **grade\_factor**: scales inversely with past performance: $\max(0.5, \frac{100 - \text{past\_grade}}{50})$. if you got a 90, you need less prep; if you got a 60, you need more.
- **difficulty\_factor**: normalized around 3.0: $\frac{\text{difficulty}}{3}$.
- **urgency\_factor**: inverse of days until closest exam/deadline, capped at 2.0x and floored at 0.25x: $\max(0.25, \min(2.0, \frac{14}{\text{days\_until\_deadline}}))$.
- **historical\_avg**: a course-specific coefficient updated by the feedback loop.

### 2. Feedback Loop (Exponential Smoothing)
when you log a study session, the system adjusts that course's `historical_avg` multiplier. this is **not** true online learning (which would update model parameter weights via gradient descent). instead, it is a simple **exponential smoothing** update with a decay factor of $\alpha = 0.3$:
$$\text{new\_historical\_avg} = (1 - \alpha) \times \text{previous\_average\_ratio} + \alpha \times \text{recent\_session\_ratio}$$
where ratio is $\frac{\text{actual\_hours}}{\text{planned\_hours}}$. this adjusts future schedule allocations up or down based on your actual pace.

---

## Exploratory Parameter Sweep (Floor Tuning)

instead of claiming a rigorous A/B test (which was impossible since $n=1$ and there was no control group), i tuned the urgency floor weight parameter manually by sweeping 3 values over 3 weeks:

| Parameter Sweep | Urgency Floor | Adherence Range | Mean Adherence |
| :--- | :---: | :---: | :---: |
| **Week 1** | 0.0 | 30% - 60% | 45% |
| **Week 2** | 0.25 | 50% - 85% | 78% |
| **Week 3** | 0.5 | 40% - 70% | 55% |

- **observations**: a floor of 0.25 performed best because it kept study blocks reasonable. a floor of 0.0 caused too much variance (allocating 0 hours when exams were far, leading to cramming), and a floor of 0.5 forced too many hours too early, causing fatigue.
- **limitations**: because $n=1$ (self-tracked), these results are highly exploratory, noisy, and subject to high individual variance and external confounds (like changing exam density).

![Parameter Sweep](docs/plots/parameter_sweep.png)

---

## Exploratory Machine Learning Analysis

to see if study adherence can be predicted, i implemented a simple **linear regression** model using `scikit-learn` on 3 weeks of self-tracked logs ($n=42$ sessions).

### features:
- `sleep_hours` (hours of sleep the night before)
- `difficulty` (subject difficulty rating, 1 to 5)
- `planned_hours` (allocated hours in the schedule)
- `is_weekend` (binary flag for Saturday/Sunday)

### target variable:
- `adherence`: $\frac{\text{actual\_hours}}{\text{planned\_hours}}$ (capped at 1.5x)

### model coefficients & fit:
- **Sample Size (n)**: 42
- **Intercept**: 0.3018
- **R² Score**: 0.2754 (underfits significantly)
- **Coefficients**:
  - `sleep_hours`: **+0.0732** (extra hour of sleep correlates with +7.3% adherence)
  - `difficulty`: **-0.0387** (harder courses correlate with -3.8% adherence per rating point)
  - `planned_hours`: **-0.0479** (longer planned study blocks correlate with -4.8% adherence per hour)
  - `is_weekend`: **-0.0368** (weekends reduce adherence by -3.6%)

### interview discussion:
- **underfitting**: the $R^2$ score is low (~0.275), meaning features only explain ~27% of the variance in study adherence. this is expected for human behavioral data. factors like mood, coffee intake, or specific assignment blockers are not captured.
- **exploratory signs**: despite the noise, the coefficient signs align with intuitive behavior: sleep improves focus, while high difficulty and overly long planned sessions degrade adherence.
- **sample size**: fitting regression on 42 rows is purely exploratory. a reliable predictive model would require at least 100+ days of logs.

![Model Fit](docs/plots/predicted_vs_actual.png)

---

## Why Not True ML for Scheduling?

an interviewer might ask: *why use a heuristic instead of a neural network or random forest to generate schedules?*
1. **cold start**: a new user has zero study history. a heuristic works instantly on day one, whereas an ML scheduler would require months of training data.
2. **explainability**: with a heuristic, i can explain exactly why a study block was scheduled (e.g. "exam is in 3 days"). a black-box model would make random-looking adjustments that frustrate the user.
3. **resource constraints**: running uvicorn + sqlite on free hosting or local machines requires minimal memory. running deep learning models for schedule generation is overkill.

---

## Tech Stack
- **backend**: FastAPI, SQLAlchemy, SQLite, Scikit-learn, Pandas, Matplotlib
- **frontend**: Vanilla HTML5, CSS Grid, Flexbox, Chart.js. (No frameworks to showcase vanilla JS capability).

---

## Setup

1. install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. seed the database and generate analysis plots:
   ```bash
   python seed.py
   python backend/app/ml_analysis.py
   ```
3. run the backend API server:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```
4. run the frontend static server:
   ```bash
   cd frontend
   python -m http.server 8080
   ```
5. open `http://localhost:8080` in your browser.
