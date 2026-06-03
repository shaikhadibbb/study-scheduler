# Study Schedule Generator

I built this because my 6th semester has 6 subjects and I was spending 4 hours on Blockchain (easy) and 1 hour on Probability (hard). That was stupid.

## How it works

It takes your credits, your past grade, how hard you think the subject is, and how close the exam is. Then it spits out how many hours you should study.

After each session you log what you actually did. If you always take 1.5x longer on math, the model learns that and adjusts.

## Tech

FastAPI + vanilla JS. No React because I wanted to show I can build without frameworks. SQLite because it's easy. Will switch to Postgres when I deploy for real.

## Known Issues

- schedule sometimes doesn't refresh after logging. reload the page.
- focus slider is weird on mobile. didn't test it.
- class schedule conflicts not handled. it might tell you to study during class.

## Setup

1. `cd backend && uvicorn main:app --reload`
2. `cd frontend && python -m http.server 8080`
3. open `localhost:8080`

## Why I Built This

I was drowning in Semester 6. 6 subjects, no time, bad at prioritizing. This fixed my time allocation. My adherence went from 45% to 78% after tuning urgency weights.

## Why it looks polished

I spent extra time on the UI because I'm applying for UI/UX internships. The backend is the real work (scheduler.py), but I wanted the frontend to show I understand design principles. I used CSS Grid and Flexbox, no frameworks. The dark theme is because I code at night.

It's not perfect. It works for me. Your mileage may vary.
