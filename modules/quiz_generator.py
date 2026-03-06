"""
quiz_generator.py
=================
ML-based quiz generator using:
  - Bag-of-Words / TF-IDF for text vectorisation  (scikit-learn)
  - Logistic Regression for difficulty classification (scikit-learn)
  - K-means for topic grouping               (scikit-learn)

Evaluation metrics: Accuracy and F1-score are computed and stored.
"""

import json
import os
import random
import warnings

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")


class QuizGenerator:
    """Generates subject-specific MCQ quizzes with ML-driven difficulty handling."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.questions: list = []
        self.accuracy: float = 0.0
        self.f1: float = 0.0
        self.n_clusters: int = 7          # one per subject
        self.is_trained: bool = False

        # Scikit-learn models
        self.vectorizer = TfidfVectorizer(
            max_features=800,
            ngram_range=(1, 2),
            stop_words="english"
        )
        self.classifier = LogisticRegression(
            C=1.0,
            max_iter=1000,
            solver="lbfgs",
            multi_class="auto"
        )
        self.label_encoder = LabelEncoder()
        self.kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)

        self._load_and_train()

    # ── Initialisation ─────────────────────────────────────────
    def _load_and_train(self):
        """Load question bank then train classifier and clusterer."""
        path = os.path.join(self.data_dir, "questions_bank.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.questions = data["questions"]

        # ── Build a rich text representation for each question ──
        texts = []
        for q in self.questions:
            kw = " ".join(q.get("keywords", []))
            texts.append(f"{q['question']} {q['subject']} {kw}")

        # Difficulty labels
        labels = [q["difficulty"] for q in self.questions]

        # Fit vectoriser on all texts
        X = self.vectorizer.fit_transform(texts)

        # ── Train Logistic Regression (difficulty classifier) ───
        if len(set(labels)) > 1:
            y = self.label_encoder.fit_transform(labels)
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.25, random_state=42, stratify=y
            )
            self.classifier.fit(X_train, y_train)
            y_pred = self.classifier.predict(X_test)
            self.accuracy = round(accuracy_score(y_test, y_pred) * 100, 2)
            self.f1 = round(f1_score(y_test, y_pred, average="weighted") * 100, 2)
            self.is_trained = True

        # ── Train K-means (topic clustering) ───────────────────
        self.kmeans.fit(X)
        # Store cluster id for each question
        clusters = self.kmeans.predict(X)
        for i, q in enumerate(self.questions):
            q["_cluster"] = int(clusters[i])

    # ── Public API ─────────────────────────────────────────────
    def generate_quiz(self, topic: str, difficulty: str = "medium",
                      num_questions: int = 5) -> list:
        """
        Return up to `num_questions` MCQs relevant to `topic` at `difficulty`.
        Uses TF-IDF cosine similarity + keyword matching for relevance.
        Falls back to any questions when exact matches are insufficient.
        """
        topic_lower = topic.lower()

        # Vectorise the topic query
        topic_vec = self.vectorizer.transform([topic])

        scored = []
        for q in self.questions:
            # Compute cosine similarity with question text
            q_text = f"{q['question']} {q['subject']} {' '.join(q.get('keywords', []))}"
            q_vec = self.vectorizer.transform([q_text])
            sim = (topic_vec * q_vec.T).toarray()[0][0]

            # Bonus for keyword / subject keyword match
            kw_match = any(
                topic_lower in kw.lower() or kw.lower() in topic_lower
                for kw in q.get("keywords", []) + [q.get("subject", "")]
            )
            if kw_match:
                sim += 0.6

            # Bonus if difficulty matches request
            if q["difficulty"] == difficulty:
                sim += 0.4

            scored.append((sim, q))

        # Sort by relevance descending
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [q for _, q in scored[:num_questions]]

        # Shuffle options order to avoid answer always being first
        result = []
        for q in selected:
            opts = list(q["options"].items())     # [('A', text), ...]
            random.shuffle(opts)

            # Remap letters A-D after shuffle
            new_opts = {}
            new_answer = q["answer"]
            old_answer_text = q["options"][q["answer"]]
            for idx, (_, text) in enumerate(opts):
                new_letter = chr(ord("A") + idx)
                new_opts[new_letter] = text
                if text == old_answer_text:
                    new_answer = new_letter

            result.append({
                "question": q["question"],
                "options": new_opts,
                "answer": new_answer,
                "explanation": q.get("explanation", ""),
                "subject": q["subject"],
                "difficulty": q["difficulty"],
            })

        return result

    def classify_difficulty(self, text: str) -> str:
        """Predict the difficulty of a custom question string."""
        if not self.is_trained:
            return "medium"
        vec = self.vectorizer.transform([text])
        pred = self.classifier.predict(vec)[0]
        return self.label_encoder.inverse_transform([pred])[0]

    def get_metrics(self) -> dict:
        return {
            "model": "Logistic Regression + TF-IDF (Bag-of-Words)",
            "accuracy": self.accuracy,
            "f1_score": self.f1,
            "total_questions": len(self.questions),
            "clusters": self.n_clusters,
        }
