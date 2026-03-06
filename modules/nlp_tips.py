"""
nlp_tips.py
===========
NLP-powered study tips generator using NLTK:
  - Sentence tokenisation (punkt)
  - Word tokenisation
  - Stopword removal
  - Keyword extraction via term-frequency
  - Mapping keywords → subject-specific study advice
"""

import re
from collections import Counter

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize


# ── Subject-specific tip templates ─────────────────────────────
SUBJECT_TIPS = {
    "mathematics": [
        "Practice problems every day — maths is learnt by doing, not just reading.",
        "Work through each step methodically; never skip steps when solving problems.",
        "Create a formula sheet and review it daily — memorisation + understanding.",
        "Use past exam papers to spot recurring question types and mark schemes.",
        "When stuck, work backwards from the answer to understand the process.",
        "Study in focused 45-minute blocks using the Pomodoro technique.",
        "Form study groups to explain concepts to peers — teaching reinforces learning.",
        "Use Desmos or GeoGebra to visualise function graphs interactively.",
        "Keep an error log — record every mistake and the correct approach.",
        "Relate abstract concepts to real-world examples (e.g., calculus in physics).",
    ],
    "physics": [
        "Always start with a diagram — visual representation clarifies problems.",
        "Master the fundamental equations before tackling complex problems.",
        "Understand units and dimensional analysis to verify answers.",
        "Use PhET simulations to visualise forces, waves, and electricity.",
        "Practice derivations from memory — it deepens conceptual understanding.",
        "Connect theory to everyday phenomena (e.g., Newton's laws in car braking).",
        "Solve past papers under timed conditions to build exam stamina.",
        "Create a comprehensive formula sheet organised by topic.",
        "Watch 3Blue1Brown or Michel van Biezen videos for visual explanations.",
        "Focus on understanding WHY a formula works, not just memorising it.",
    ],
    "chemistry": [
        "Build a colour-coded periodic table summary for quick reference.",
        "Practice balancing equations daily until it becomes automatic.",
        "Use molecular model kits or online 3D viewers to understand bonding.",
        "Create flashcards for chemical reactions, trends, and functional groups.",
        "Memorise key constants (Avogadro, Faraday, gas constant) with mnemonics.",
        "Understand electron configurations as the basis for all periodic trends.",
        "Work through stoichiometry problems step-by-step using the mole concept.",
        "Watch ChemLibreTexts videos for organic chemistry reaction mechanisms.",
        "Link chemical concepts to real applications (e.g., pH in medicine).",
        "Review past papers to identify question patterns and mark allocations.",
    ],
    "biology": [
        "Draw and label diagrams repeatedly — visual memory is powerful in biology.",
        "Use spaced repetition (Anki) for terminology, processes, and definitions.",
        "Connect processes at the molecular, cellular, and organism levels.",
        "Create process flowcharts (e.g., photosynthesis, DNA replication steps).",
        "Use the Cornell note-taking method to summarise and self-quiz.",
        "Watch videos on YouTube (Amoeba Sisters, Khan Academy) for animations.",
        "Practise explaining processes out loud in your own words.",
        "Group similar topics (e.g., all cell organelles and their functions together).",
        "Create comparison tables (e.g., mitosis vs. meiosis, aerobic vs. anaerobic).",
        "Review past mark schemes to understand exactly what examiners want.",
    ],
    "history": [
        "Build chronological timelines for each period or theme you study.",
        "Use the PEEL method (Point, Evidence, Explain, Link) for essay answers.",
        "Practise source analysis using CONTENT, ORIGIN, PURPOSE, LIMITATIONS.",
        "Link causes and consequences — history is about understanding 'why'.",
        "Create mind maps connecting events, people, and ideologies.",
        "Read primary sources to understand historical perspectives directly.",
        "Discuss historical arguments with peers to develop analytical thinking.",
        "Practice timed essays — exam success depends on structured, quick writing.",
        "Use flashcards for dates, key figures, and turning points.",
        "Watch documentaries and historical films critically as supplementary sources.",
    ],
    "computer_science": [
        "Code every day, even if only for 20 minutes — consistency builds skill.",
        "Implement data structures from scratch before using built-in libraries.",
        "Practice on LeetCode or HackerRank daily to sharpen algorithmic thinking.",
        "Read other people's code on GitHub to learn different approaches.",
        "Build projects — portfolio work cements knowledge better than theory alone.",
        "Use rubber duck debugging: explain your code line-by-line to find bugs.",
        "Master Big O analysis — it's essential for understanding efficiency.",
        "Study CS50 on edX for foundational concepts explained brilliantly.",
        "Keep a coding journal of problems solved and patterns identified.",
        "Understand WHY an algorithm works before memorising its implementation.",
    ],
    "english": [
        "Read widely — fiction, non-fiction, newspapers — to build vocabulary.",
        "Keep a vocabulary journal; write new words in sentences, not just lists.",
        "Practise timed writing to improve speed and structure under pressure.",
        "Use the PEEL paragraph structure for all analytical writing.",
        "Read published model essays to understand what distinction-level work looks like.",
        "Analyse language choices — always ask WHY the author used specific words.",
        "Practise précis writing to sharpen comprehension and concision.",
        "Re-read key texts multiple times — you notice new things every read-through.",
        "Use Purdue OWL for grammar and citation reference.",
        "Record yourself reading passages aloud to improve fluency and comprehension.",
    ],
    "default": [
        "Use active recall instead of re-reading — test yourself without looking at notes.",
        "Employ spaced repetition: review material at increasing intervals over time.",
        "Study in focused blocks of 45 minutes with 10-minute breaks (Pomodoro).",
        "Teach the subject to a friend or pet — explaining tests and deepens understanding.",
        "Create a distraction-free study environment — phone away, notifications off.",
        "Begin each session by reviewing yesterday's material before studying new content.",
        "Use multi-modal resources: videos, textbooks, and practice questions.",
        "Set specific daily goals: 'complete Chapter 3' rather than 'study for 2 hours'.",
        "Get adequate sleep — memory consolidation happens during REM sleep.",
        "Practice past exam papers under timed, exam conditions regularly.",
    ]
}

# Difficulty-specific meta-tips
DIFFICULTY_TIPS = {
    "easy": [
        "Since you're finding this manageable, push deeper into advanced subtopics.",
        "Challenge yourself with harder practice questions and past exam papers.",
        "Use your confidence in this subject to help peers — teaching reinforces mastery.",
    ],
    "medium": [
        "Focus on the topics you find most confusing first each session.",
        "Don't skip 'easy' topics — they often underpin harder concepts.",
        "Track your progress weekly and celebrate small wins to maintain momentum.",
    ],
    "hard": [
        "Break overwhelming topics into tiny chunks — master one concept before the next.",
        "Seek help early: office hours, online forums (Reddit, Stack Exchange), tutors.",
        "Accept that struggle means growth — difficulty is a sign you're learning.",
    ]
}


class NLPStudyTips:
    """
    Generates personalised study tips by:
    1. Tokenising and cleaning input text with NLTK
    2. Extracting top keywords by term frequency
    3. Matching keywords to subject-specific and difficulty-specific advice
    """

    def __init__(self):
        self.stop_words = set(stopwords.words("english"))

    # ── Public API ─────────────────────────────────────────────
    def generate_tips(self, subject: str, difficulty: str = "medium",
                      user_text: str = "") -> dict:
        """
        Returns:
            {
              "subject_tips": [...],      # subject-matched tips
              "difficulty_tips": [...],   # difficulty-adaptive tips
              "keywords": [...],          # extracted from user_text
              "total": int
            }
        """
        # Normalise subject
        subj_lower = subject.strip().lower()
        matched_key = "default"
        for k in SUBJECT_TIPS:
            if k in subj_lower or subj_lower in k:
                matched_key = k
                break

        # Select subject tips
        subject_tips = list(SUBJECT_TIPS.get(matched_key, SUBJECT_TIPS["default"]))

        # If user_text provided, extract keywords and personalise
        keywords = []
        if user_text.strip():
            keywords = self._extract_keywords(user_text, top_n=5)
            # Insert keyword-aware tip at the front
            if keywords:
                kw_str = ", ".join(keywords[:3])
                subject_tips.insert(0,
                    f"Your notes highlight key themes: {kw_str}. "
                    f"Prioritise these in your revision sessions.")

        difficulty_tips = DIFFICULTY_TIPS.get(difficulty.lower(),
                                              DIFFICULTY_TIPS["medium"])

        return {
            "subject": subject.title(),
            "matched_category": matched_key.replace("_", " ").title(),
            "difficulty": difficulty.title(),
            "subject_tips": subject_tips[:8],
            "difficulty_tips": difficulty_tips,
            "keywords": keywords,
            "total": len(subject_tips[:8]) + len(difficulty_tips),
        }

    # ── NLP keyword extraction ─────────────────────────────────
    def _extract_keywords(self, text: str, top_n: int = 5) -> list:
        """
        Tokenise text, remove stopwords and non-alphabetic tokens,
        then return the top-N most frequent meaningful words.
        """
        # Tokenise with NLTK
        tokens = word_tokenize(text.lower())

        # Filter: alpha-only, not a stopword, length > 3
        filtered = [
            t for t in tokens
            if t.isalpha() and t not in self.stop_words and len(t) > 3
        ]

        # Count frequencies
        freq = Counter(filtered)
        top_words = [word.capitalize() for word, _ in freq.most_common(top_n)]
        return top_words
