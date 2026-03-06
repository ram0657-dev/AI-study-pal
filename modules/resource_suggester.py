"""
resource_suggester.py
=====================
Resource suggestion system using:
  - K-means clustering (scikit-learn) to group subjects into categories
  - TF-IDF vectorisation to map an input subject to a cluster
  - Curated resource database (study_resources.json)

Pipeline:
  1. Vectorise all known subject keywords using TF-IDF
  2. Cluster with K-means (k = number of categories)
  3. For a new subject, transform + find nearest cluster → return resources
"""

import json
import os
import warnings

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings("ignore")


class ResourceSuggester:
    """K-means-based subject → resource cluster mapper."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.resources_data: dict = {}
        self.cluster_names: list = []     # ordered list of cluster keys
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        self.kmeans = None
        self.cluster_doc_map: dict = {}   # cluster_id → cluster_key

        self._load_and_fit()

    # ── Init ───────────────────────────────────────────────────
    def _load_and_fit(self):
        path = os.path.join(self.data_dir, "study_resources.json")
        with open(path, "r", encoding="utf-8") as f:
            self.resources_data = json.load(f)

        clusters = self.resources_data.get("clusters", {})
        self.cluster_names = list(clusters.keys())

        # Build one document per cluster: cluster label + all keywords
        corpus = []
        for key, val in clusters.items():
            doc = val.get("label", key) + " " + " ".join(val.get("keywords", []))
            corpus.append(doc)

        # Fit TF-IDF
        X = self.vectorizer.fit_transform(corpus)

        # Fit K-means — k = number of clusters (one per category)
        n = len(corpus)
        k = max(2, min(n, 5))
        self.kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        self.kmeans.fit(X)

        # Map each K-means cluster centre → nearest cluster_name
        labels = self.kmeans.labels_
        for km_label in range(k):
            # Find the first corpus document assigned to this KM cluster
            idx = next((i for i, l in enumerate(labels) if l == km_label), 0)
            self.cluster_doc_map[km_label] = self.cluster_names[idx]

    # ── Public API ─────────────────────────────────────────────
    def suggest(self, subject: str, max_resources: int = 5) -> dict:
        """
        Suggest resources for `subject`.
        Returns:
            {
              "cluster": cluster display name,
              "subject": normalised subject,
              "resources": [ {name, url, description}, ... ],
              "general": [ {name, url, description}, ... ]
            }
        """
        # Vectorise the query subject
        q_vec = self.vectorizer.transform([subject])

        # Predict K-means cluster
        km_label = int(self.kmeans.predict(q_vec)[0])
        cluster_key = self.cluster_doc_map.get(km_label, self.cluster_names[0])

        # Also try direct keyword matching for better accuracy
        subj_lower = subject.strip().lower()
        clusters = self.resources_data.get("clusters", {})
        best_match_key = cluster_key

        best_score = -1
        for key, val in clusters.items():
            keywords = val.get("keywords", [])
            score = sum(1 for kw in keywords
                        if kw in subj_lower or subj_lower in kw)
            if score > best_score:
                best_score = score
                best_match_key = key

        # Use keyword match if it gave a clear signal
        if best_score > 0:
            cluster_key = best_match_key

        cluster_data = clusters.get(cluster_key, {})
        resources = cluster_data.get("resources", [])[:max_resources]
        general = self.resources_data.get("general_resources", [])[:3]

        return {
            "cluster": cluster_data.get("label", cluster_key),
            "subject": subject.title(),
            "resources": resources,
            "general": general,
            "km_cluster_id": km_label,
        }
