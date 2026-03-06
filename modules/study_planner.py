"""
study_planner.py
================
Generates a personalised day-by-day study schedule using Pandas.
Outputs:
  - A structured JSON schedule (list of daily task rows)
  - A CSV download (BytesIO) for offline use
  - Visual milestones and phase breakdown

Technologies: Pandas, datetime
"""

import io
import json
import os
from datetime import date, datetime, timedelta
from math import ceil

import pandas as pd


# Subject-specific topic progressions
SUBJECT_TOPICS = {
    "mathematics": [
        "Number Systems & Arithmetic", "Algebra – Equations & Inequalities",
        "Functions & Graphs", "Geometry & Trigonometry",
        "Statistics & Probability", "Calculus – Differentiation",
        "Calculus – Integration", "Practice Problems & Past Papers",
        "Error Analysis & Revision", "Final Mock Exam"
    ],
    "physics": [
        "Mechanics – Kinematics", "Mechanics – Newton's Laws",
        "Energy, Work & Power", "Electricity & Magnetism",
        "Waves & Optics", "Thermodynamics",
        "Modern Physics & Quantum Basics",
        "Practice Problems", "Formula Revision", "Mock Test"
    ],
    "chemistry": [
        "Atomic Structure & Periodic Table", "Chemical Bonding",
        "Stoichiometry & Reactions", "States of Matter",
        "Thermodynamics & Kinetics", "Electrochemistry",
        "Organic Chemistry Basics", "Acid-Base Chemistry",
        "Past Paper Practice", "Full Revision"
    ],
    "biology": [
        "Cell Biology & Organelles", "Genetics & DNA",
        "Photosynthesis & Respiration", "Human Anatomy – Digestive & Circulatory",
        "Human Anatomy – Nervous & Endocrine", "Ecology & Environment",
        "Evolution & Classification", "Biotechnology",
        "Past Papers & MCQ Practice", "Final Revision"
    ],
    "history": [
        "Ancient Civilisations", "Medieval Period",
        "Renaissance & Reformation", "Age of Exploration",
        "Industrial Revolution", "World War I & Causes",
        "World War II & Cold War", "Post-war Modern World",
        "Essay Practice & Source Analysis", "Revision & Mock"
    ],
    "computer_science": [
        "Programming Fundamentals & Python", "Data Structures – Arrays & Linked Lists",
        "Data Structures – Trees & Graphs", "Algorithms – Sorting & Searching",
        "Time & Space Complexity (Big O)", "Databases & SQL",
        "Networking Basics", "Object-Oriented Programming",
        "Past Papers & Coding Practice", "Final Revision"
    ],
    "english": [
        "Reading Comprehension Strategies", "Vocabulary & Word Formation",
        "Grammar – Tenses & Clauses", "Grammar – Punctuation & Style",
        "Essay Writing – Argumentative", "Essay Writing – Descriptive",
        "Literature Analysis – Poetry", "Literature Analysis – Prose",
        "Mock Essays & Timed Practice", "Final Revision"
    ],
    "default": [
        "Introduction & Overview", "Core Concepts Part 1",
        "Core Concepts Part 2", "Applied Theory",
        "Worked Examples & Case Studies", "Deep Dive – Advanced Topics",
        "Practice Questions", "Gap Analysis & Weak Areas",
        "Revision Sprint", "Final Mock & Review"
    ]
}

# Daily activities mapped to hours available
ACTIVITY_TEMPLATES = {
    1: ["Study (45 min)", "Review (15 min)"],
    2: ["Study (60 min)", "Practice Problems (30 min)", "Review (30 min)"],
    3: ["Concept Study (90 min)", "Practice (45 min)", "Review & Notes (45 min)"],
    4: ["Morning Study (90 min)", "Practice Problems (60 min)",
        "Break + Light Reading (30 min)", "Evening Review (60 min)"],
    5: ["Morning Study (120 min)", "Practice (90 min)",
        "Break + Flash Cards (30 min)", "Evening Revision (60 min)", "Recap (30 min)"],
    6: ["Core Study Block (120 min)", "Problem Solving (90 min)",
        "Lunch Break – Podcast (30 min)", "Afternoon Study (90 min)",
        "Evening Practice (45 min)", "End-of-Day Recap (15 min)"],
}


class StudyPlanner:
    """Generates Pandas-backed study schedules."""

    def __init__(self):
        pass

    # ── Public API ─────────────────────────────────────────────
    def generate_plan(self, subject: str, hours_per_day: int,
                      exam_date_str: str) -> dict:
        """
        Build a full study schedule.
        Returns a dict with:
          - schedule (list of row dicts)
          - phases (list of phase summaries)
          - overview (string paragraph)
          - total_days, study_days, total_hours
        """
        # Parse exam date
        exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
        today = date.today()
        total_days = (exam_date - today).days

        if total_days <= 0:
            raise ValueError("Exam date must be in the future.")

        hours_per_day = max(1, min(12, hours_per_day))
        total_hours = total_days * hours_per_day

        # Retrieve topic list for subject
        subj_key = subject.strip().lower().replace(" ", "_")
        # Fuzzy match
        matched_key = "default"
        for k in SUBJECT_TOPICS:
            if k in subj_key or subj_key in k:
                matched_key = k
                break
        topics = SUBJECT_TOPICS[matched_key]

        # ── Phase breakdown ────────────────────────────────────
        # Foundation 20% | Core 50% | Practice 20% | Revision 10%
        phase_weights = [0.20, 0.50, 0.20, 0.10]
        phase_names   = ["🌱 Foundation", "📚 Core Learning",
                          "🧪 Practice & Application", "🔁 Final Revision"]
        phase_days = [max(1, round(total_days * w)) for w in phase_weights]
        # Adjust so they sum to total_days
        diff = total_days - sum(phase_days)
        phase_days[1] += diff           # absorb remainder into Core

        # ── Build schedule DataFrame ───────────────────────────
        rows = []
        current_date = today
        topic_idx = 0
        phase_start_idx = 0

        for phase_num, (phase_name, days_in_phase) in enumerate(
                zip(phase_names, phase_days)):
            for day_in_phase in range(days_in_phase):
                if current_date >= exam_date:
                    break

                # Pick topic (cycle through)
                topic = topics[topic_idx % len(topics)]

                # Activities based on hours available
                hr_key = min(hours_per_day, 6)
                activities = ACTIVITY_TEMPLATES.get(hr_key, ACTIVITY_TEMPLATES[3])

                # Special markings
                is_weekend = current_date.weekday() >= 5
                is_last_day = current_date == exam_date - timedelta(days=1)

                if is_last_day:
                    topic = "🎯 Final Review & Rest"
                    activities = ["Light review (30 min)", "Rest and prepare"]

                rows.append({
                    "Day": len(rows) + 1,
                    "Date": current_date.strftime("%Y-%m-%d"),
                    "Day_Name": current_date.strftime("%A"),
                    "Phase": phase_name,
                    "Topic": topic,
                    "Hours": hours_per_day if not is_last_day else 1,
                    "Activities": " | ".join(activities),
                    "Status": "Weekend – Lighter Study" if is_weekend else "Study Day",
                    "Milestone": self._milestone(day_in_phase, days_in_phase),
                })

                current_date += timedelta(days=1)
                topic_idx += 1

        # Build DataFrame (Pandas)
        df = pd.DataFrame(rows)

        # ── Phase summaries ────────────────────────────────────
        phases = []
        for phase_name in phase_names:
            phase_df = df[df["Phase"] == phase_name]
            if not phase_df.empty:
                phases.append({
                    "name": phase_name,
                    "days": len(phase_df),
                    "hours": int(phase_df["Hours"].sum()),
                    "start": phase_df.iloc[0]["Date"],
                    "end": phase_df.iloc[-1]["Date"],
                })

        overview = (
            f"Your {subject.title()} study plan spans {total_days} days "
            f"({today.strftime('%d %b %Y')} → {exam_date.strftime('%d %b %Y')}) "
            f"with {hours_per_day} hour(s) per day — {total_hours} total study hours. "
            f"The plan is structured in 4 progressive phases: "
            f"Foundation, Core Learning, Practice, and Final Revision. "
            f"Aim to complete each topic before moving on, and revisit "
            f"difficult sections during the Practice phase."
        )

        return {
            "schedule": df.to_dict(orient="records"),
            "phases": phases,
            "overview": overview,
            "total_days": total_days,
            "study_days": len(df),
            "total_hours": total_hours,
            "subject": subject.title(),
            "exam_date": exam_date_str,
        }

    def to_csv_bytes(self, schedule_data: dict) -> bytes:
        """Convert schedule list to CSV bytes for download."""
        df = pd.DataFrame(schedule_data["schedule"])
        # Drop internal columns
        df = df.drop(columns=["Milestone"], errors="ignore")
        buf = io.BytesIO()
        df.to_csv(buf, index=False, encoding="utf-8")
        return buf.getvalue()

    # ── Helper ─────────────────────────────────────────────────
    @staticmethod
    def _milestone(day_in_phase: int, total_in_phase: int) -> str:
        pct = (day_in_phase + 1) / total_in_phase
        if pct >= 1.0:
            return "✅ Phase Complete"
        if pct >= 0.5:
            return "⚡ Halfway"
        return ""
