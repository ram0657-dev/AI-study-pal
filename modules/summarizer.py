"""
summarizer.py
=============
Text summarisation pipeline using:
  - NLTK  – sentence tokenisation, stopword removal, word-frequency scoring
  - Keras – lightweight Dense neural network to re-score sentence importance
             (trained synthetically from the educational_texts dataset)

Output: paragraph summary + bullet-point key ideas.
"""

import json
import os
import re
import warnings

import numpy as np

warnings.filterwarnings("ignore")

# ── NLTK lazy imports (downloaded at app startup) ───────────────
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords


class TextSummarizer:
    """
    Extractive text summariser.
    1. Scores sentences by word-frequency + position + length features.
    2. Passes feature vectors through a trained Keras Dense model to get
       a refined importance score.
    3. Returns top-N sentences as summary + keyword bullet points.
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.stop_words = set(stopwords.words("english"))
        self.model = None          # Keras model (trained below)
        self.is_model_ready = False
        self._train_keras_model()

    # ── Keras model ────────────────────────────────────────────
    def _train_keras_model(self):
        """
        Build and train a small Keras Dense network on synthetic sentence-
        quality data derived from the educational texts.
        Input features (4):  normalised position, word count ratio,
                             keyword density, frequency score.
        Output (1):          importance score in [0, 1].
        """
        try:
            # Import Keras inside function to fail gracefully
            import tensorflow as tf
            from tensorflow import keras

            tf.get_logger().setLevel("ERROR")
            os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

            # ── Build training data from educational texts ──────
            texts_path = os.path.join(self.data_dir, "educational_texts.json")
            with open(texts_path, "r", encoding="utf-8") as f:
                corpus = json.load(f)["texts"]

            X_train, y_train = [], []
            for item in corpus:
                feats, labels = self._extract_training_pairs(item["content"])
                X_train.extend(feats)
                y_train.extend(labels)

            X_arr = np.array(X_train, dtype="float32")
            y_arr = np.array(y_train, dtype="float32")

            if len(X_arr) < 5:
                return       # not enough data – fall back to NLTK only

            # ── Define model: 4 → 16 → 8 → 1 Dense ────────────
            model = keras.Sequential([
                keras.layers.Input(shape=(4,)),
                keras.layers.Dense(16, activation="relu"),
                keras.layers.Dropout(0.2),
                keras.layers.Dense(8, activation="relu"),
                keras.layers.Dense(1, activation="sigmoid"),
            ])
            model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=0.01),
                loss="mse",
                metrics=["mae"]
            )

            # Train on synthetic data (fast – small dataset)
            model.fit(
                X_arr, y_arr,
                epochs=30,
                batch_size=8,
                verbose=0,
                validation_split=0.15
            )

            self.model = model
            self.is_model_ready = True

        except Exception:
            # Keras not available or error – fall back to pure NLTK
            self.is_model_ready = False

    def _extract_training_pairs(self, text: str):
        """
        Generate (feature_vector, quality_score) pairs from a text.
        Quality heuristic:
          - First sentence → 0.95
          - Last sentence → 0.85
          - Very short sentences → 0.2
          - Medium sentences with high keyword density → 0.7–0.8
          - Others → 0.4–0.6
        """
        sentences = sent_tokenize(text)
        n = len(sentences)
        if n < 3:
            return [], []

        word_freq = self._word_frequencies(text)
        features, labels = [], []

        for i, sent in enumerate(sentences):
            fv = self._feature_vector(sent, i, n, word_freq)
            # Synthetic label
            if i == 0:
                label = 0.95
            elif i == n - 1:
                label = 0.80
            elif fv[2] > 0.6:          # high keyword density
                label = 0.75
            elif fv[1] > 0.7:          # long sentence
                label = 0.65
            else:
                label = 0.45
            features.append(fv)
            labels.append(label)

        return features, labels

    # ── Core feature extraction ────────────────────────────────
    def _word_frequencies(self, text: str) -> dict:
        """Compute normalised word frequency (excluding stopwords)."""
        words = word_tokenize(text.lower())
        freq = {}
        for w in words:
            if w.isalpha() and w not in self.stop_words:
                freq[w] = freq.get(w, 0) + 1
        max_f = max(freq.values()) if freq else 1
        return {w: v / max_f for w, v in freq.items()}

    def _feature_vector(self, sentence: str, position: int,
                        total: int, word_freq: dict) -> list:
        """
        Returns [norm_position, word_count_ratio, keyword_density, freq_score].
        """
        words = word_tokenize(sentence.lower())
        content_words = [w for w in words if w.isalpha() and w not in self.stop_words]

        norm_position = 1 - (position / max(total - 1, 1))  # earlier = higher score
        wc_ratio = min(len(words) / 40.0, 1.0)             # normalise by 40 words
        keyword_density = (len(content_words) / max(len(words), 1))
        freq_score = (sum(word_freq.get(w, 0) for w in content_words)
                      / max(len(content_words), 1))

        return [norm_position, wc_ratio, keyword_density, freq_score]

    # ── Public API ─────────────────────────────────────────────
    def summarize(self, text: str, num_sentences: int = 4) -> dict:
        """
        Summarise `text`.
        Returns:
            {
              "summary": "Paragraph summary text...",
              "key_points": ["Point 1", "Point 2", ...],
              "word_count_original": int,
              "word_count_summary": int,
              "compression_ratio": float
            }
        """
        # Preprocess
        text = re.sub(r"\s+", " ", text).strip()
        sentences = sent_tokenize(text)

        if len(sentences) <= 3:
            # Too short to summarise meaningfully
            return {
                "summary": text,
                "key_points": self._extract_keywords(text),
                "word_count_original": len(text.split()),
                "word_count_summary": len(text.split()),
                "compression_ratio": 1.0,
            }

        word_freq = self._word_frequencies(text)
        n = len(sentences)

        # Score each sentence
        scores = {}
        for i, sent in enumerate(sentences):
            fv = self._feature_vector(sent, i, n, word_freq)

            if self.is_model_ready:
                # Use Keras model for refined scoring
                arr = np.array([fv], dtype="float32")
                score = float(self.model.predict(arr, verbose=0)[0][0])
            else:
                # Fall back to weighted average of features
                score = 0.3 * fv[0] + 0.1 * fv[1] + 0.2 * fv[2] + 0.4 * fv[3]

            scores[i] = score

        # Select top sentences, preserve original order
        top_indices = sorted(
            sorted(scores, key=scores.get, reverse=True)[:num_sentences]
        )
        summary_sentences = [sentences[i] for i in top_indices]
        summary_text = " ".join(summary_sentences)

        # Extract keyword bullet points
        key_points = self._extract_keywords(text, top_n=7)

        orig_wc = len(text.split())
        summ_wc = len(summary_text.split())

        return {
            "summary": summary_text,
            "key_points": key_points,
            "word_count_original": orig_wc,
            "word_count_summary": summ_wc,
            "compression_ratio": round(summ_wc / max(orig_wc, 1), 2),
        }

    def _extract_keywords(self, text: str, top_n: int = 7) -> list:
        """Extract top-N keywords using word frequency (NLTK)."""
        word_freq = self._word_frequencies(text)
        sorted_words = sorted(word_freq, key=word_freq.get, reverse=True)

        keywords = []
        seen = set()
        for word in sorted_words:
            if word not in seen and len(word) > 3:
                keywords.append(word.capitalize())
                seen.add(word)
                if len(keywords) >= top_n:
                    break

        # Convert to short bullet sentences
        sentences = sent_tokenize(text)
        keyword_points = []
        for kw in keywords:
            for sent in sentences:
                if kw.lower() in sent.lower():
                    # Extract a clean, short point
                    short = sent.strip()
                    if len(short.split()) > 25:
                        short = " ".join(short.split()[:25]) + "…"
                    if short not in keyword_points:
                        keyword_points.append(short)
                        break

        return keyword_points[:top_n]
