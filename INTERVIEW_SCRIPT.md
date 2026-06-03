ok so i built this because i was dying in semester 5. 6 subjects, no time, spending 4 hours on blockchain (easy) and 1 hour on probability (hard). 

the scheduler takes credits + past grade + difficulty rating + days until exam. spits out hours. 

the feedback loop: i log what i actually did. if i always take 1.5x longer on math, it learns that. 

tech: fastapi + vanilla js. no react because i wanted to show i can build without frameworks. 

result: adherence went from 45% to 78% after tuning urgency weights. 

lesson: interpretable models > black boxes for personal tools. i can explain every weight. 

things that are broken:
- class schedule conflicts not handled
- sqlite in docker is a bad idea
- ui is pretty but backend is the real work
