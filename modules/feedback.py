"""
feedback.py
===========
Motivational feedback generator using:
  - Pre-defined feedback templates organised by sentiment and subject
  - TF-IDF cosine similarity (simulating GloVe-style semantic matching)
    to select the most contextually relevant encouragement message
  - scikit-learn TfidfVectorizer for embedding computation
"""

import random
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ── Feedback bank ───────────────────────────────────────────────
# Organised by performance tier: excellent / good / needs_work
FEEDBACK_BANK = {
    "excellent": [
        "Outstanding work! You're demonstrating a deep understanding of the material. Keep pushing your limits — excellence is a habit, not a one-time event.",
        "Brilliant performance! Your dedication is clearly paying off. You have what it takes to ace this exam with flying colours.",
        "Exceptional results! You're operating at a high level. Challenge yourself with harder problems now to consolidate this mastery.",
        "Top-tier work! Your commitment to learning is inspiring. Make sure you teach others — sharing knowledge deepens your own understanding.",
        "Remarkable progress! You're proving that consistent effort leads to excellence. Stay focused and trust your preparation.",
        "You are absolutely crushing this topic! Your results reflect real understanding, not just memorisation. Keep going!",
        "Superb! You are in an elite group of learners who truly grasp the fundamentals. The exam is going to be your moment to shine.",
    ],
    "good": [
        "Good job! You are making solid progress. Identify the questions you missed and revisit those topics — you're almost there.",
        "Well done — you are on the right track! Consistent practice at this level will push you into the top tier very soon.",
        "Nice work! Every correct answer shows you are building real understanding. Review your errors carefully and you'll improve further.",
        "Keep it up! You are doing better than you think. A focused revision of weak areas this week will make a huge difference.",
        "Solid effort! You are clearly engaging with the material. Try explaining these concepts aloud to test true understanding.",
        "Good progress! The key now is pinpointing your specific weak spots and drilling them relentlessly. You have the foundation.",
        "You are learning and growing with every practice session. Stay consistent — results compound over time.",
    ],
    "needs_work": [
        "Don't be discouraged — every expert was once a beginner. Identify the core concepts causing difficulty and tackle them one by one.",
        "It's okay to struggle — that's where the learning happens. Break the topic into smaller chunks and master each piece.",
        "Every mistake is a lesson. Review what went wrong, understand WHY, and try again. Progress is never linear.",
        "Keep going! This subject challenges many students. With daily, focused practice you will see significant improvement.",
        "You're at the beginning of your learning curve — the hardest part is starting. Each session gets you closer to understanding.",
        "Believe in the process. Students who struggle most at the start often finish strongest. Stay consistent and ask for help when needed.",
        "This is where champions are made — through persistence and resilience. Break your study into tiny daily goals and celebrate each win.",
    ],
    "general": [
        "Learning is a journey, not a destination. Every minute you invest in studying today pays dividends in your future.",
        "Your brain is like a muscle — it grows stronger every time you challenge it with new knowledge.",
        "Stay curious, stay persistent, and trust the process. Great things take time to build.",
        "The fact that you are studying and seeking improvement already puts you ahead of most people.",
        "Progress may be invisible day-to-day, but look back a month from now and you will be amazed at how far you have come.",
        "Be patient with yourself. Learning deeply takes time, but the knowledge you build this way will last a lifetime.",
        "Small consistent steps beat occasional giant leaps every single time. Show up, study, repeat.",
    ]
}

# Subject-aware encouragement prefixes
SUBJECT_ENCOURAGEMENT = {
    "mathematics": "Mathematics rewards patience and practice above all else.",
    "physics": "Physics connects the laws of the universe — your efforts reveal the elegance beneath.",
    "chemistry": "Chemistry is the language of matter — you are learning to read the world at its deepest level.",
    "biology": "Biology is the study of life itself — every fact you learn connects to the living world around you.",
    "history": "History is humanity's greatest teacher — understanding it makes you a wiser thinker.",
    "computer_science": "Computer science is a superpower — the skills you build here will shape the future.",
    "english": "Mastering language is mastering communication — the most powerful human skill.",
    "default": "Every subject you master opens new doors of opportunity and understanding.",
}


class FeedbackGenerator:
    """
    Generates contextually relevant motivational feedback using
    TF-IDF vector similarity to match input context to the best message.
    """

    def __init__(self):
        # Flatten all messages for vectorisation
        self._all_messages = []
        self._message_tiers = []
        for tier, messages in FEEDBACK_BANK.items():
            for msg in messages:
                self._all_messages.append(msg)
                self._message_tiers.append(tier)

        # Fit TF-IDF on the feedback corpus
        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            max_features=300
        )
        self._message_vectors = self._vectorizer.fit_transform(self._all_messages)

    # ── Public API ─────────────────────────────────────────────
    def generate_feedback(self, subject: str, score: float = None,
                          context: str = "") -> dict:
        """
        Generate motivational feedback.
        Parameters:
            subject  : subject name (str)
            score    : optional quiz score 0-100 (float)
            context  : any user-provided context string
        Returns:
            dict with message, tier, subject_note, emoji
        """
        # Determine performance tier
        if score is not None:
            if score >= 80:
                tier = "excellent"
                emoji = "🏆"
            elif score >= 60:
                tier = "good"
                emoji = "👍"
            else:
                tier = "needs_work"
                emoji = "💪"
        else:
            tier = "general"
            emoji = "✨"

        # Build query from context + subject
        query = f"{subject} {context} {tier} study learning"

        # Use TF-IDF similarity to select most relevant message in tier
        try:
            query_vec = self._vectorizer.transform([query])
            sims = cosine_similarity(query_vec, self._message_vectors)[0]

            # Filter to only messages in the desired tier
            tier_indices = [i for i, t in enumerate(self._message_tiers) if t == tier]
            if tier_indices:
                best_idx = max(tier_indices, key=lambda i: sims[i])
                # Add slight randomness: pick from top-3 candidates
                top_candidates = sorted(tier_indices, key=lambda i: sims[i], reverse=True)[:3]
                chosen_idx = random.choice(top_candidates)
                message = self._all_messages[chosen_idx]
            else:
                message = random.choice(FEEDBACK_BANK["general"])
        except Exception:
            message = random.choice(FEEDBACK_BANK.get(tier, FEEDBACK_BANK["general"]))

        # Subject-specific note
        subj_lower = subject.strip().lower()
        subject_note = SUBJECT_ENCOURAGEMENT.get("default")
        for k, v in SUBJECT_ENCOURAGEMENT.items():
            if k in subj_lower or subj_lower in k:
                subject_note = v
                break

        # Score summary line
        score_line = ""
        if score is not None:
            correct = round((score / 100) * 5)    # out of 5 questions
            score_line = f"You scored {correct}/5 ({score:.0f}%)."

        return {
            "message": message,
            "subject_note": subject_note,
            "score_summary": score_line,
            "tier": tier,
            "emoji": emoji,
        }
