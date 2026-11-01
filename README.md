Jakarta Running Festival (JRF) Analytics API – Complete Race Telemetry
This API provides programmatic access to the complete, highly granular race results and pacing telemetry from the Jakarta Running Festival (JRF). Covering a massive cohort of 36,306 registered runners, this dataset is designed for sports data analysts, running coaches, fitness app developers, and athletic brands looking to benchmark performance, analyze pacing degradation, or build predictive marathon models.
Event Coverage
The dataset encompasses all four major race distances from the festival, capturing a wide spectrum of athletic performance from elite marathoners to recreational 5K participants:
Marathon (42.195 KM)
Half Marathon (21.1 KM)
10K
5K
Data Schema & Returned Fields
Each runner's record returns a comprehensive JSON object detailing their identity, demographic background, and race performance. The API exposes the following core fields:
position: The runner's overall finishing rank within their event.
status: The final race state of the runner (e.g., FINISHED, DNF - Did Not Finish, DNS - Did Not Start).
bib_no: The unique alphanumeric bib identifier assigned to the runner.
name: The runner's registered full name.
time: The official net finish time (HH:MM:SS).
category: The competitive division (e.g., Open, National, Masters, Age Groups).
gender: Biological sex/gender category.
country: The runner's registered nationality.
splits: A nested object containing granular interval timings (e.g., KM 5, KM 10, KM 15, KM 21.1, KM 30). This is the most valuable feature for pacing and fatigue analysis, allowing developers to see exactly where runners accelerated or "hit the wall."
Primary Use Cases
Performance Benchmarking: Compare individual athlete splits against the top 100 finishers or national-level competitors.
Fatigue & DNF Analysis: Identify the exact kilometer marks where the highest volume of runners slowed down or dropped out of the race.
App Integration: Power pacing calculators, finish-time predictors, or personalized training dashboards using real-world Southeast Asian demographic data.
Market Research: Analyze participation rates, gender distribution, and international draw across different race distances.
