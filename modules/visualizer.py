"""
visualizer.py
=============
Generates Matplotlib charts as base64-encoded PNG images for
embedding directly in HTML (no file I/O required — cloud-safe).

Charts provided:
  1. Dataset EDA – subject distribution pie chart
  2. Study hours bar chart (from a study plan)
  3. Quiz score gauge / bar chart
  4. Phase timeline chart (from study plan phases)
"""

import base64
import io
import json
import os

import matplotlib
matplotlib.use("Agg")         # Non-interactive backend — works on any server
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# ── Colour palette (matches the app's dark academic theme) ─────
PALETTE = {
    "bg":      "#0E1320",
    "card":    "#141D2E",
    "accent":  "#E8A838",
    "accent2": "#5DADE2",
    "accent3": "#58D68D",
    "accent4": "#EC407A",
    "accent5": "#AB47BC",
    "text":    "#CBD5E0",
    "muted":   "#4A5568",
}

SUBJECT_COLOURS = [
    PALETTE["accent"], PALETTE["accent2"], PALETTE["accent3"],
    PALETTE["accent4"], PALETTE["accent5"], "#FF7043", "#26C6DA"
]


def _fig_to_base64(fig) -> str:
    """Convert a Matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{img_b64}"


def _apply_dark_style(fig, ax):
    """Apply the dark academic style to fig/ax."""
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["card"])
    ax.tick_params(colors=PALETTE["text"], labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(PALETTE["muted"])
    ax.title.set_color(PALETTE["text"])
    ax.xaxis.label.set_color(PALETTE["text"])
    ax.yaxis.label.set_color(PALETTE["text"])


# ── Chart 1: EDA – Subject distribution pie ────────────────────
def subject_distribution_pie(data_dir: str) -> str:
    """
    Reads questions_bank.json and plots a subject distribution pie chart.
    Returns base64 PNG string.
    """
    path = os.path.join(data_dir, "questions_bank.json")
    with open(path, "r", encoding="utf-8") as f:
        questions = json.load(f)["questions"]

    # Count per subject
    counts: dict = {}
    for q in questions:
        subj = q["subject"].replace("_", " ").title()
        counts[subj] = counts.get(subj, 0) + 1

    labels = list(counts.keys())
    sizes  = list(counts.values())
    colours = SUBJECT_COLOURS[:len(labels)]

    fig, ax = plt.subplots(figsize=(6, 5))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["bg"])

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=None,
        colors=colours,
        autopct="%1.0f%%",
        startangle=140,
        pctdistance=0.82,
        wedgeprops=dict(width=0.55, edgecolor=PALETTE["bg"], linewidth=2)
    )
    for at in autotexts:
        at.set_color(PALETTE["bg"])
        at.set_fontsize(7)
        at.set_fontweight("bold")

    ax.legend(
        wedges, [f"{l} ({s})" for l, s in zip(labels, sizes)],
        loc="lower center", bbox_to_anchor=(0.5, -0.22),
        ncol=2, fontsize=7,
        facecolor=PALETTE["card"], labelcolor=PALETTE["text"],
        edgecolor=PALETTE["muted"]
    )
    ax.set_title("Question Bank — Subject Distribution",
                 color=PALETTE["text"], fontsize=10, pad=12, fontweight="bold")

    plt.tight_layout()
    return _fig_to_base64(fig)


# ── Chart 2: Study hours bar chart ─────────────────────────────
def study_hours_bar(phases: list) -> str:
    """
    Bar chart of total study hours per phase.
    `phases` is the list returned by StudyPlanner.generate_plan().
    """
    if not phases:
        return ""

    names  = [p["name"] for p in phases]
    hours  = [p["hours"] for p in phases]
    colours = SUBJECT_COLOURS[:len(names)]

    fig, ax = plt.subplots(figsize=(7, 4))
    _apply_dark_style(fig, ax)

    bars = ax.bar(names, hours, color=colours, width=0.55,
                  edgecolor=PALETTE["bg"], linewidth=1.5)

    # Value labels on bars
    for bar, h in zip(bars, hours):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{h}h", ha="center", va="bottom",
                fontsize=8, color=PALETTE["text"], fontweight="bold")

    ax.set_ylabel("Total Hours", fontsize=8)
    ax.set_title("Study Hours per Phase", fontsize=10, fontweight="bold")
    ax.tick_params(axis="x", rotation=15, labelsize=7)
    ax.set_ylim(0, max(hours) * 1.2 if hours else 10)
    ax.grid(axis="y", color=PALETTE["muted"], alpha=0.3, linestyle="--")

    plt.tight_layout()
    return _fig_to_base64(fig)


# ── Chart 3: Quiz score gauge ─────────────────────────────────
def quiz_score_chart(score: float, subject: str = "Quiz") -> str:
    """
    Horizontal bar gauge showing quiz score.
    `score` is 0-100.
    """
    fig, ax = plt.subplots(figsize=(6, 2.5))
    _apply_dark_style(fig, ax)

    # Background bar
    ax.barh(["Score"], [100], color=PALETTE["muted"], height=0.4)

    # Score bar
    colour = (PALETTE["accent3"] if score >= 70
              else PALETTE["accent"] if score >= 50
              else PALETTE["accent4"])
    ax.barh(["Score"], [score], color=colour, height=0.4)

    ax.set_xlim(0, 100)
    ax.set_xlabel("Score (%)", fontsize=8)
    ax.set_title(f"{subject} — Quiz Result: {score:.0f}%",
                 fontsize=10, fontweight="bold")

    # Tick lines
    for x in [50, 70, 100]:
        ax.axvline(x, color=PALETTE["muted"], linestyle="--", linewidth=0.7, alpha=0.6)
    ax.text(score, 0, f"  {score:.0f}%", va="center",
            fontsize=9, fontweight="bold", color=PALETTE["bg"] if score > 10 else PALETTE["text"])

    # Legend
    labels = ["Needs Work (<50%)", "Good (50-70%)", "Excellent (>70%)"]
    colours_leg = [PALETTE["accent4"], PALETTE["accent"], PALETTE["accent3"]]
    patches = [mpatches.Patch(color=c, label=l) for c, l in zip(colours_leg, labels)]
    ax.legend(handles=patches, loc="lower right", fontsize=6,
              facecolor=PALETTE["card"], labelcolor=PALETTE["text"],
              edgecolor=PALETTE["muted"])

    plt.tight_layout()
    return _fig_to_base64(fig)


# ── Chart 4: Difficulty distribution from quiz bank ─────────────
def difficulty_distribution(data_dir: str) -> str:
    """Bar chart showing easy/medium/hard split in the question bank."""
    path = os.path.join(data_dir, "questions_bank.json")
    with open(path, "r", encoding="utf-8") as f:
        questions = json.load(f)["questions"]

    diffs = {"easy": 0, "medium": 0, "hard": 0}
    for q in questions:
        d = q.get("difficulty", "medium")
        diffs[d] = diffs.get(d, 0) + 1

    fig, ax = plt.subplots(figsize=(5, 3.5))
    _apply_dark_style(fig, ax)

    colours = [PALETTE["accent3"], PALETTE["accent"], PALETTE["accent4"]]
    bars = ax.bar(list(diffs.keys()), list(diffs.values()),
                  color=colours, width=0.5, edgecolor=PALETTE["bg"], linewidth=1.5)

    for bar, (k, v) in zip(bars, diffs.items()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(v), ha="center", fontsize=9,
                color=PALETTE["text"], fontweight="bold")

    ax.set_ylabel("Number of Questions", fontsize=8)
    ax.set_title("Question Bank — Difficulty Distribution",
                 fontsize=10, fontweight="bold")
    ax.set_ylim(0, max(diffs.values()) * 1.25)
    ax.grid(axis="y", color=PALETTE["muted"], alpha=0.3, linestyle="--")

    plt.tight_layout()
    return _fig_to_base64(fig)
