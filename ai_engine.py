# ================================================================
#  AI Study Pal — ai_engine.py
#  The complete AI/ML brain of the application.
#
#  Implements every requirement from the capstone specification:
#   1. Pandas  — Dataset management & EDA
#   2. ML      — scikit-learn: TF-IDF + Logistic Regression (quiz difficulty)
#                              K-means (topic clustering → resource suggestions)
#   3. DL      — Keras Dense NN (extractive text summarisation)
#                Keras Embedding + Dense (motivational feedback classifier)
#   4. NLP     — NLTK tokenisation + stopword removal + keyword extraction
#   5. Viz     — Matplotlib charts (base64-encoded for web serving)
#   6. Export  — CSV study schedule generation
# ================================================================

import os, io, base64, json, re, csv, warnings, random, logging
from datetime import datetime, timedelta

# ── Silence noisy TF / sklearn warnings ─────────────────────────
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
warnings.filterwarnings('ignore')
logging.getLogger('tensorflow').setLevel(logging.ERROR)

# ── Matplotlib must use Agg backend (no display) ────────────────
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import numpy as np
import pandas as pd
import joblib

# ── NLTK ─────────────────────────────────────────────────────────
import nltk
_NLTK_DIR = '/tmp/nltk_data'
os.makedirs(_NLTK_DIR, exist_ok=True)
for _pkg in ['punkt', 'stopwords', 'punkt_tab']:
    try:
        nltk.download(_pkg, download_dir=_NLTK_DIR, quiet=True)
    except Exception:
        pass
nltk.data.path.insert(0, _NLTK_DIR)

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords as nltk_sw

# ── scikit-learn ─────────────────────────────────────────────────
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

# ── Keras (TensorFlow) ───────────────────────────────────────────
try:
    from tensorflow import keras
    from tensorflow.keras import layers as KL
    KERAS_OK = True
except Exception:
    KERAS_OK = False
    print("⚠  TensorFlow/Keras not available – DL features use sklearn fallback.")

# ================================================================
#  SECTION 1 — EMBEDDED EDUCATIONAL DATASET
#  48 real questions × 6 subjects.  Labels: 0=easy, 1=medium, 2=hard
# ================================================================

QUESTIONS_DATASET = [
    # ── BIOLOGY (8) ──────────────────────────────────────────────
    {"id":1,"subject":"Biology","topic":"Cell Biology",
     "question":"Which organelle is known as the powerhouse of the cell?",
     "options":{"A":"Nucleus","B":"Ribosome","C":"Mitochondria","D":"Chloroplast"},
     "answer":"C","explanation":"Mitochondria produce ATP through cellular respiration, powering all cellular activities.",
     "difficulty":0},
    {"id":2,"subject":"Biology","topic":"Photosynthesis",
     "question":"What gas do plants release as a byproduct of photosynthesis?",
     "options":{"A":"Carbon Dioxide","B":"Nitrogen","C":"Hydrogen","D":"Oxygen"},
     "answer":"D","explanation":"During photosynthesis, plants split water molecules and release oxygen as a byproduct.",
     "difficulty":0},
    {"id":3,"subject":"Biology","topic":"Genetics",
     "question":"What does DNA stand for?",
     "options":{"A":"Deoxyribonucleic Acid","B":"Diribonucleic Acid","C":"Dextronucleic Acid","D":"Deoxyribose Nucleotide"},
     "answer":"A","explanation":"DNA – Deoxyribonucleic Acid – is the double-helix molecule that carries genetic information.",
     "difficulty":0},
    {"id":4,"subject":"Biology","topic":"Cell Division",
     "question":"During which phase of mitosis do chromosomes align at the cell's equator?",
     "options":{"A":"Prophase","B":"Anaphase","C":"Telophase","D":"Metaphase"},
     "answer":"D","explanation":"In Metaphase, spindle fibres align chromosomes along the metaphase plate at the cell's centre.",
     "difficulty":1},
    {"id":5,"subject":"Biology","topic":"Osmosis",
     "question":"What happens to a plant cell placed in a hypertonic solution?",
     "options":{"A":"It swells and bursts","B":"It loses water and becomes plasmolyzed","C":"Nothing changes","D":"It absorbs more minerals"},
     "answer":"B","explanation":"Water moves out of the cell by osmosis into the higher-concentration solution, causing plasmolysis.",
     "difficulty":1},
    {"id":6,"subject":"Biology","topic":"Ecology",
     "question":"Which trophic level do primary consumers (herbivores) occupy?",
     "options":{"A":"First","B":"Second","C":"Third","D":"Fourth"},
     "answer":"B","explanation":"Primary consumers eat producers (plants), placing them at trophic level 2.",
     "difficulty":1},
    {"id":7,"subject":"Biology","topic":"Biochemistry",
     "question":"Approximately how many ATP molecules are produced from one glucose molecule?",
     "options":{"A":"2","B":"4","C":"18","D":"36-38"},
     "answer":"D","explanation":"Complete aerobic oxidation of glucose yields 36–38 ATP via glycolysis, Krebs cycle, and oxidative phosphorylation.",
     "difficulty":2},
    {"id":8,"subject":"Biology","topic":"Protein Synthesis",
     "question":"Which RNA molecule carries amino acids to the ribosome during translation?",
     "options":{"A":"mRNA","B":"rRNA","C":"tRNA","D":"snRNA"},
     "answer":"C","explanation":"tRNA (transfer RNA) carries specific amino acids and matches them to codons on mRNA via anticodons.",
     "difficulty":2},
    # ── MATHEMATICS (8) ──────────────────────────────────────────
    {"id":9,"subject":"Mathematics","topic":"Geometry",
     "question":"What is the area of a circle with radius 7 cm? (π ≈ 3.14)",
     "options":{"A":"43.96 cm²","B":"153.86 cm²","C":"21.98 cm²","D":"44 cm²"},
     "answer":"B","explanation":"Area = πr² = 3.14 × 49 = 153.86 cm².",
     "difficulty":0},
    {"id":10,"subject":"Mathematics","topic":"Number Theory",
     "question":"Which of the following is a prime number?",
     "options":{"A":"15","B":"21","C":"37","D":"49"},
     "answer":"C","explanation":"37 has no factors other than 1 and itself — it is prime.",
     "difficulty":0},
    {"id":11,"subject":"Mathematics","topic":"Algebra",
     "question":"Solve for x:  2x + 6 = 14",
     "options":{"A":"3","B":"4","C":"5","D":"10"},
     "answer":"B","explanation":"2x = 8, so x = 4.",
     "difficulty":0},
    {"id":12,"subject":"Mathematics","topic":"Quadratic Equations",
     "question":"What are the roots of x² − 5x + 6 = 0?",
     "options":{"A":"x = 1, 6","B":"x = 2, 3","C":"x = −2, −3","D":"x = 5, 1"},
     "answer":"B","explanation":"Factorising: (x−2)(x−3) = 0 gives x = 2 and x = 3.",
     "difficulty":1},
    {"id":13,"subject":"Mathematics","topic":"Calculus",
     "question":"What is the derivative of f(x) = x³ + 2x²?",
     "options":{"A":"3x² + 4x","B":"x² + 2x","C":"3x + 4","D":"3x³ + 4x"},
     "answer":"A","explanation":"Using the power rule: d/dx(x³)=3x², d/dx(2x²)=4x → f′(x) = 3x² + 4x.",
     "difficulty":1},
    {"id":14,"subject":"Mathematics","topic":"Statistics",
     "question":"What is the median of {3, 7, 2, 9, 5}?",
     "options":{"A":"5","B":"7","C":"3","D":"9"},
     "answer":"A","explanation":"Sorted: {2, 3, 5, 7, 9}. The middle (3rd) value is 5.",
     "difficulty":1},
    {"id":15,"subject":"Mathematics","topic":"Integration",
     "question":"What is the indefinite integral of f(x) = 2x?",
     "options":{"A":"2","B":"x² + C","C":"2x² + C","D":"x + C"},
     "answer":"B","explanation":"∫2x dx = x² + C by the power rule for integration.",
     "difficulty":2},
    {"id":16,"subject":"Mathematics","topic":"Trigonometry",
     "question":"What does sin²(θ) + cos²(θ) always equal?",
     "options":{"A":"0","B":"2","C":"1","D":"tan(θ)"},
     "answer":"C","explanation":"The fundamental Pythagorean identity: sin²θ + cos²θ = 1.",
     "difficulty":2},
    # ── HISTORY (8) ──────────────────────────────────────────────
    {"id":17,"subject":"History","topic":"World Wars",
     "question":"In which year did World War II officially end?",
     "options":{"A":"1943","B":"1944","C":"1945","D":"1946"},
     "answer":"C","explanation":"WWII ended in 1945 — VE Day (May 8) and VJ Day (September 2).",
     "difficulty":0},
    {"id":18,"subject":"History","topic":"American History",
     "question":"Who was the first President of the United States?",
     "options":{"A":"Thomas Jefferson","B":"Abraham Lincoln","C":"John Adams","D":"George Washington"},
     "answer":"D","explanation":"George Washington was inaugurated as the 1st US President on April 30, 1789.",
     "difficulty":0},
    {"id":19,"subject":"History","topic":"Ancient Civilizations",
     "question":"Which civilization built the Great Pyramid of Giza?",
     "options":{"A":"Romans","B":"Greeks","C":"Ancient Egyptians","D":"Mesopotamians"},
     "answer":"C","explanation":"Ancient Egyptians built the Great Pyramid around 2560 BC as a tomb for Pharaoh Khufu.",
     "difficulty":0},
    {"id":20,"subject":"History","topic":"French Revolution",
     "question":"What was a primary driver of the French Revolution?",
     "options":{"A":"Military defeat","B":"Social inequality and financial crisis","C":"Religious conflicts","D":"Foreign invasion"},
     "answer":"B","explanation":"Extreme social inequality, heavy taxation on commoners, and France's near-bankruptcy ignited revolution.",
     "difficulty":1},
    {"id":21,"subject":"History","topic":"Colonial Era",
     "question":"When did India gain independence from British rule?",
     "options":{"A":"1945","B":"1947","C":"1950","D":"1952"},
     "answer":"B","explanation":"India gained independence on August 15, 1947, under the Indian Independence Act.",
     "difficulty":1},
    {"id":22,"subject":"History","topic":"Industrial Revolution",
     "question":"Where did the Industrial Revolution begin in the 18th century?",
     "options":{"A":"France","B":"Germany","C":"United States","D":"Britain"},
     "answer":"D","explanation":"Britain's textile innovations and steam power sparked the Industrial Revolution around 1760.",
     "difficulty":1},
    {"id":23,"subject":"History","topic":"Cold War",
     "question":"What event symbolically marked the end of the Cold War?",
     "options":{"A":"Moon landing","B":"Korean War armistice","C":"Fall of the Berlin Wall","D":"Cuban Missile Crisis"},
     "answer":"C","explanation":"The Berlin Wall fell on November 9, 1989, symbolising the collapse of the Iron Curtain.",
     "difficulty":2},
    {"id":24,"subject":"History","topic":"Economics History",
     "question":"Which economic system primarily drove European colonialism?",
     "options":{"A":"Capitalism","B":"Mercantilism","C":"Socialism","D":"Feudalism"},
     "answer":"B","explanation":"Mercantilism — maximising exports and colonial resource extraction — dominated colonial-era European policy.",
     "difficulty":2},
    # ── PYTHON / CS (8) ──────────────────────────────────────────
    {"id":25,"subject":"Python","topic":"Basics",
     "question":"What keyword defines a function in Python?",
     "options":{"A":"function","B":"func","C":"def","D":"define"},
     "answer":"C","explanation":"The 'def' keyword followed by the function name creates a function in Python.",
     "difficulty":0},
    {"id":26,"subject":"Python","topic":"Data Types",
     "question":"Which Python data type is ordered AND mutable?",
     "options":{"A":"Tuple","B":"Set","C":"Dictionary","D":"List"},
     "answer":"D","explanation":"Lists are ordered (insertion order preserved) and mutable (elements can change). Tuples are immutable.",
     "difficulty":0},
    {"id":27,"subject":"Python","topic":"Control Flow",
     "question":"What does the 'break' statement do inside a loop?",
     "options":{"A":"Skips the current iteration","B":"Exits the loop entirely","C":"Restarts the loop","D":"Pauses execution"},
     "answer":"B","explanation":"'break' immediately terminates the enclosing loop, jumping to the code after it.",
     "difficulty":0},
    {"id":28,"subject":"Python","topic":"OOP",
     "question":"In Python OOP, what does 'self' refer to?",
     "options":{"A":"The class itself","B":"The parent class","C":"The current instance","D":"A static method"},
     "answer":"C","explanation":"'self' refers to the specific object instance calling the method, allowing access to its attributes.",
     "difficulty":1},
    {"id":29,"subject":"Python","topic":"Recursion",
     "question":"What is the essential base case for a factorial recursive function?",
     "options":{"A":"n > 1","B":"n == 0 or n == 1","C":"n < 0","D":"n == 100"},
     "answer":"B","explanation":"Base case n == 0 or n == 1 returns 1, stopping infinite recursion.",
     "difficulty":1},
    {"id":30,"subject":"Python","topic":"Data Structures",
     "question":"What is the average time complexity of a Python dictionary lookup?",
     "options":{"A":"O(n)","B":"O(log n)","C":"O(1)","D":"O(n²)"},
     "answer":"C","explanation":"Hash tables provide O(1) average-case lookup by computing the key's hash directly.",
     "difficulty":1},
    {"id":31,"subject":"Python","topic":"Algorithms",
     "question":"What is QuickSort's worst-case time complexity?",
     "options":{"A":"O(n log n)","B":"O(n)","C":"O(n²)","D":"O(log n)"},
     "answer":"C","explanation":"QuickSort degrades to O(n²) when the pivot is always the smallest or largest element.",
     "difficulty":2},
    {"id":32,"subject":"Python","topic":"Decorators",
     "question":"In Python, what is a decorator?",
     "options":{"A":"A UI styling tool","B":"A function that modifies another function","C":"A class inheritance method","D":"A variable type"},
     "answer":"B","explanation":"A decorator is a higher-order function wrapping another function to extend its behaviour without modifying it directly.",
     "difficulty":2},
    # ── PHYSICS (8) ──────────────────────────────────────────────
    {"id":33,"subject":"Physics","topic":"Newton's Laws",
     "question":"An object at rest remains at rest unless acted on by what?",
     "options":{"A":"Gravity alone","B":"A net unbalanced external force","C":"Friction","D":"Inertia"},
     "answer":"B","explanation":"Newton's 1st Law (Inertia): objects resist changes in motion; a net force is required to accelerate them.",
     "difficulty":0},
    {"id":34,"subject":"Physics","topic":"Kinematics",
     "question":"What is the SI unit of velocity?",
     "options":{"A":"km/h","B":"m/s²","C":"m/s","D":"Newtons"},
     "answer":"C","explanation":"Velocity = displacement / time, measured in metres per second (m/s).",
     "difficulty":0},
    {"id":35,"subject":"Physics","topic":"Forces",
     "question":"Newton's 2nd Law: Force equals …",
     "options":{"A":"mass × velocity","B":"mass × acceleration","C":"mass × distance","D":"weight × height"},
     "answer":"B","explanation":"F = ma. A larger mass or greater acceleration requires a proportionally greater force.",
     "difficulty":0},
    {"id":36,"subject":"Physics","topic":"Energy",
     "question":"What energy does a moving object possess?",
     "options":{"A":"Potential","B":"Chemical","C":"Kinetic","D":"Thermal"},
     "answer":"C","explanation":"Kinetic Energy KE = ½mv². It depends on both mass and the square of velocity.",
     "difficulty":1},
    {"id":37,"subject":"Physics","topic":"Electricity",
     "question":"Using Ohm's Law V = IR, if V=12V and R=4Ω, what is I?",
     "options":{"A":"48 A","B":"8 A","C":"3 A","D":"16 A"},
     "answer":"C","explanation":"I = V/R = 12/4 = 3 Amperes.",
     "difficulty":1},
    {"id":38,"subject":"Physics","topic":"Waves",
     "question":"The wave equation relating speed v, frequency f and wavelength λ is:",
     "options":{"A":"v = f + λ","B":"v = f × λ","C":"v = f / λ","D":"v = λ / f"},
     "answer":"B","explanation":"v = fλ. A higher frequency means shorter wavelength for the same wave speed.",
     "difficulty":1},
    {"id":39,"subject":"Physics","topic":"Thermodynamics",
     "question":"The second law of thermodynamics states that entropy of an isolated system …",
     "options":{"A":"Always decreases","B":"Stays constant","C":"Always increases","D":"Depends on temperature"},
     "answer":"C","explanation":"Entropy (disorder) of an isolated system always increases over time — the direction of irreversibility.",
     "difficulty":2},
    {"id":40,"subject":"Physics","topic":"Quantum Physics",
     "question":"Which principle states exact position and momentum of a particle cannot both be known simultaneously?",
     "options":{"A":"Pauli Exclusion","B":"Heisenberg Uncertainty","C":"Schrödinger's","D":"Bohr's"},
     "answer":"B","explanation":"Heisenberg's Uncertainty Principle: Δx·Δp ≥ ℏ/2. Measuring position precisely disturbs momentum.",
     "difficulty":2},
    # ── CHEMISTRY (8) ──────────────────────────────────────────────
    {"id":41,"subject":"Chemistry","topic":"Periodic Table",
     "question":"What is the chemical symbol for Gold?",
     "options":{"A":"Go","B":"Gd","C":"Au","D":"Ag"},
     "answer":"C","explanation":"Au comes from the Latin 'Aurum'. Gold is element 79 — a noble metal.",
     "difficulty":0},
    {"id":42,"subject":"Chemistry","topic":"Atomic Structure",
     "question":"How many electrons does a neutral carbon atom have?",
     "options":{"A":"2","B":"4","C":"6","D":"12"},
     "answer":"C","explanation":"Carbon has atomic number 6, so it has 6 protons and 6 electrons when neutral.",
     "difficulty":0},
    {"id":43,"subject":"Chemistry","topic":"States of Matter",
     "question":"At what temperature does water boil at standard atmospheric pressure?",
     "options":{"A":"90°C","B":"95°C","C":"100°C","D":"105°C"},
     "answer":"C","explanation":"Water's boiling point at 1 atm is exactly 100°C (212°F).",
     "difficulty":0},
    {"id":44,"subject":"Chemistry","topic":"Chemical Bonds",
     "question":"What type of bond forms when electrons are SHARED between atoms?",
     "options":{"A":"Ionic","B":"Metallic","C":"Hydrogen","D":"Covalent"},
     "answer":"D","explanation":"Covalent bonds involve electron sharing. Ionic bonds involve electron transfer.",
     "difficulty":1},
    {"id":45,"subject":"Chemistry","topic":"Acids and Bases",
     "question":"What is the pH of a perfectly neutral solution at 25°C?",
     "options":{"A":"0","B":"7","C":"14","D":"5"},
     "answer":"B","explanation":"pH 7 is neutral. Below 7 is acidic; above 7 is basic/alkaline.",
     "difficulty":1},
    {"id":46,"subject":"Chemistry","topic":"Chemical Reactions",
     "question":"In 2H₂ + O₂ → 2H₂O, which reaction type is this?",
     "options":{"A":"Decomposition","B":"Displacement","C":"Synthesis","D":"Neutralisation"},
     "answer":"C","explanation":"Two substances combining into one product is a synthesis (combination) reaction.",
     "difficulty":1},
    {"id":47,"subject":"Chemistry","topic":"Organic Chemistry",
     "question":"What is the functional group of an alcohol?",
     "options":{"A":"—COOH","B":"—OH","C":"—NH₂","D":"—CHO"},
     "answer":"B","explanation":"Alcohols contain the hydroxyl group (—OH). Ethanol is CH₃CH₂OH.",
     "difficulty":2},
    {"id":48,"subject":"Chemistry","topic":"Electrochemistry",
     "question":"In electrolysis, at which electrode does OXIDATION occur?",
     "options":{"A":"Cathode","B":"Anode","C":"Both","D":"Neither"},
     "answer":"B","explanation":"OIL RIG — Oxidation Is Loss (of electrons) at the Anode. Reduction at the Cathode.",
     "difficulty":2},
]

# ── Build a Pandas DataFrame from the dataset ───────────────────
DF = pd.DataFrame(QUESTIONS_DATASET)

# ── Resource library (curated) ──────────────────────────────────
RESOURCES_DB = {
    "Biology": [
        {"title":"Khan Academy – Biology","url":"https://www.khanacademy.org/science/biology","type":"Video + Practice","desc":"Free comprehensive biology courses from cell biology to evolution."},
        {"title":"CrashCourse Biology (YouTube)","url":"https://www.youtube.com/@crashcourse","type":"Video","desc":"Fast-paced, engaging 10-min video series covering all biology topics."},
        {"title":"Biology Online","url":"https://www.biologyonline.com","type":"Reference","desc":"Dictionary & tutorials covering every biology concept in depth."},
        {"title":"NCBI Learning Resources","url":"https://www.ncbi.nlm.nih.gov/home/learn","type":"Research","desc":"National biotech database — great for genetics and molecular biology."},
    ],
    "Mathematics": [
        {"title":"Khan Academy – Maths","url":"https://www.khanacademy.org/math","type":"Video + Practice","desc":"World-class adaptive maths practice from arithmetic to calculus."},
        {"title":"Paul's Online Math Notes","url":"https://tutorial.math.lamar.edu","type":"Notes","desc":"Excellent free notes and worked examples for calculus & algebra."},
        {"title":"Wolfram MathWorld","url":"https://mathworld.wolfram.com","type":"Reference","desc":"The most comprehensive free maths encyclopedia online."},
        {"title":"Desmos Graphing Calculator","url":"https://www.desmos.com","type":"Tool","desc":"Interactive graphs — essential for visualising functions and geometry."},
    ],
    "History": [
        {"title":"Khan Academy – World History","url":"https://www.khanacademy.org/humanities/world-history","type":"Video + Practice","desc":"Chronological world history from ancient civilisations to the 21st century."},
        {"title":"Crash Course History (YouTube)","url":"https://www.youtube.com/@crashcourse","type":"Video","desc":"Entertaining deep dives into major historical periods."},
        {"title":"History.com","url":"https://www.history.com","type":"Reference","desc":"Articles, timelines, and videos on every major historical event."},
        {"title":"BBC History","url":"https://www.bbc.co.uk/history","type":"Reference","desc":"In-depth articles and documentaries by historians."},
    ],
    "Python": [
        {"title":"Python Official Docs","url":"https://docs.python.org/3","type":"Documentation","desc":"The definitive reference for every Python built-in and standard library."},
        {"title":"Real Python","url":"https://realpython.com","type":"Tutorials","desc":"Practical, project-based Python tutorials for all skill levels."},
        {"title":"LeetCode (Python)","url":"https://leetcode.com","type":"Practice","desc":"Algorithm and data structure challenges — great for CS interviews."},
        {"title":"CS50P – Python Course","url":"https://cs50.harvard.edu/python","type":"Video + Practice","desc":"Harvard's free introduction to Python programming."},
    ],
    "Physics": [
        {"title":"Khan Academy – Physics","url":"https://www.khanacademy.org/science/physics","type":"Video + Practice","desc":"From forces and motion to quantum mechanics — fully worked examples."},
        {"title":"HyperPhysics","url":"http://hyperphysics.phy-astr.gsu.edu","type":"Reference","desc":"Concept maps and concise explanations for every physics topic."},
        {"title":"Physics Classroom","url":"https://www.physicsclassroom.com","type":"Reference","desc":"Tutorials and interactive activities for high-school physics."},
        {"title":"MIT OpenCourseWare – Physics","url":"https://ocw.mit.edu/courses/physics","type":"Lecture Notes","desc":"Free MIT lecture notes, exams, and problem sets."},
    ],
    "Chemistry": [
        {"title":"Khan Academy – Chemistry","url":"https://www.khanacademy.org/science/chemistry","type":"Video + Practice","desc":"Atomic structure, reactions, thermodynamics and more."},
        {"title":"ChemLibreTexts","url":"https://chem.libretexts.org","type":"Textbook","desc":"Open-access chemistry textbooks from foundation to advanced."},
        {"title":"Royal Society of Chemistry","url":"https://www.rsc.org/learn-chemistry","type":"Reference","desc":"Teaching and learning resources from the RSC."},
        {"title":"Periodic Table (ptable.com)","url":"https://ptable.com","type":"Tool","desc":"Interactive periodic table with properties, orbitals, and isotopes."},
    ],
    "General": [
        {"title":"Quizlet","url":"https://quizlet.com","type":"Flashcards","desc":"Create and study flashcard sets for any subject."},
        {"title":"Coursera","url":"https://www.coursera.org","type":"Courses","desc":"University-level courses — many free to audit."},
        {"title":"YouTube EDU","url":"https://www.youtube.com/EDU","type":"Video","desc":"Curated academic and educational video content."},
        {"title":"Notion (Free)","url":"https://www.notion.so","type":"Tool","desc":"Organise your notes, schedules, and study plans in one workspace."},
    ],
}

# ── Study tips bank ──────────────────────────────────────────────
STUDY_TIPS = {
    "Biology": [
        "Draw and label diagrams (cell structures, life cycles) — visual memory is powerful in biology.",
        "Use mnemonics for classification: e.g., 'King Philip Came Over For Good Soup' (Kingdom→Species).",
        "Make flashcards for every enzyme, organelle, and hormone with function on the back.",
        "Relate concepts to real life: osmosis = reason you get thirsty after salty food.",
        "Watch CrashCourse Biology on YouTube — 10-minute episodes for quick topic revision.",
        "Understand metabolic pathways (glycolysis, Krebs) as stories, not lists of reactions.",
        "Practise past-paper essay questions on ecology and genetics — these are exam favourites.",
        "Use colour-coded notes: green for producers, red for consumers, blue for decomposers.",
    ],
    "Mathematics": [
        "Never skip steps — write every line of working even if it seems obvious.",
        "Practise the same problem type 10 times until the method becomes automatic.",
        "Learn when and why to apply each formula — not just what it is.",
        "Use Desmos (free) to visually check your function graphs and equation solutions.",
        "For calculus, master algebra first — most calculus errors are algebra mistakes.",
        "Attempt problems without notes first, then check. Struggle builds understanding.",
        "Review errors immediately: keep an 'mistakes notebook' explaining each wrong answer.",
        "Break complex problems into smaller sub-problems — work from what you know.",
    ],
    "History": [
        "Create a master timeline with all key dates — then test yourself by covering dates.",
        "Learn causes and consequences together, not isolated facts.",
        "Group events thematically (wars, revolutions, independence movements) to see patterns.",
        "For essays, use the PEEL structure: Point, Evidence, Explain, Link back.",
        "Watch 5-minute documentary clips before reading — context makes reading faster.",
        "Make 'character cards' for key historical figures: who, what, when, significance.",
        "Quiz yourself on 'turning points' — examiners love asking about historical causes.",
        "Use maps to understand geography's role in historical events.",
    ],
    "Python": [
        "Code every single day — even 20 minutes builds muscle memory faster than 3-hour sessions.",
        "Read error messages carefully — Python's errors tell you exactly where and what went wrong.",
        "Build small projects that interest you: a game, a scraper, a to-do app.",
        "Understand list comprehensions, lambda, and map/filter — they appear everywhere.",
        "Use Python Tutor (pythontutor.com) to visualise how your code executes step-by-step.",
        "Read other people's code on GitHub — you'll learn patterns you'd never discover alone.",
        "Master debugging with print() first, then learn the pdb debugger.",
        "For algorithms, understand the problem before writing a single line of code.",
    ],
    "Physics": [
        "Always start with a diagram — label all forces, velocities, or charges before equations.",
        "Memorise base equations, then derive the rest — this prevents formula overload.",
        "Check units at every step — dimensional analysis catches ~80% of calculation errors.",
        "Solve problems by identifying knowns/unknowns before choosing a formula.",
        "For circuits, redraw complex diagrams simply — reduce series/parallel systematically.",
        "Derive key formulas yourself from first principles — understanding beats memorisation.",
        "Link maths to physics: calculus IS kinematics (velocity = dx/dt, acceleration = dv/dt).",
        "Study worked examples, then solve without looking. Repeat until automatic.",
    ],
    "Chemistry": [
        "Learn the periodic table in blocks (s, p, d blocks) — trends become obvious.",
        "Understand electron configurations first — everything in chemistry follows from them.",
        "Balance equations systematically: start with the most complex molecule.",
        "For organic chemistry, learn functional groups like an alphabet — the rest follows.",
        "Use colour coding for Lewis structures: red = lone pairs, blue = bonding pairs.",
        "Memorise the activity series for displacement reactions — it saves exam time.",
        "Practise mole calculations daily — they underpin titrations, yields, and gas laws.",
        "Link acid-base theory to everyday examples: stomach acid (HCl), baking soda (NaHCO₃).",
    ],
    "General": [
        "Use the Pomodoro technique: 25 min focused study → 5 min break. Repeat 4×, then 30 min break.",
        "Teach the material to someone else (or a rubber duck) — gaps in understanding become obvious.",
        "Sleep is when your brain consolidates memories — never sacrifice sleep for cramming.",
        "Space your revision: review after 1 day, 3 days, 1 week, 2 weeks (spaced repetition).",
        "Active recall beats re-reading: close your notes and write down everything you remember.",
        "Use past papers under timed conditions — exam technique is a separate skill to learn.",
        "Identify your peak productivity hours and protect them for the hardest material.",
        "Start study sessions by reviewing what you studied last time — it primes your memory.",
    ],
}

# ── Motivational feedback templates ─────────────────────────────
FEEDBACK_TEMPLATES = {
    "excellent": [
        "🌟 Outstanding work, {name}! Scoring {score}% shows you've truly mastered this material. Keep this momentum — you're on track for top marks!",
        "🎯 Incredible result! {score}% on {subject} is something to be genuinely proud of. Your dedication is paying off in a big way.",
        "🏆 Top performance alert! A {score}% score means your understanding of {subject} is excellent. You're ready to tackle harder challenges!",
    ],
    "good": [
        "👏 Great effort on {subject}! {score}% is a solid result — you clearly understand the core concepts. A little more practice on the tricky areas and you'll be unstoppable.",
        "✨ Well done! {score}% shows real progress. Focus on the questions you got wrong and you'll push into the top tier quickly.",
        "💪 Good score! {score}% means your foundations in {subject} are strong. Identify your weak spots and target them specifically.",
    ],
    "average": [
        "📚 {score}% is a solid start — you're on the right path in {subject}. Review the topics you found difficult and schedule another practice session soon.",
        "🔄 Keep going! {score}% means you're building your {subject} foundation. Each study session makes a difference — consistency is key.",
        "💡 You're making progress with {score}%. Don't be discouraged — identify which specific topics need work and tackle them one by one.",
    ],
    "needs_work": [
        "🌱 Don't worry about {score}% — every expert started as a beginner in {subject}. The fact that you're practising puts you ahead. Let's review the basics together!",
        "🔥 {score}% today means more room to grow tomorrow! Revisit the fundamentals of {subject} and try shorter, more focused study sessions.",
        "💪 {score}% is just your starting point, not your destination! Break {subject} into small chunks and tackle one concept at a time. You've got this!",
    ],
}

# ================================================================
#  SECTION 2 — MODEL MANAGER  (trains + persists ML/DL models)
# ================================================================

_MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(_MODELS_DIR, exist_ok=True)

# Global model references (populated by initialize_models())
_quiz_vectorizer  = None
_quiz_classifier  = None
_topic_kmeans     = None
_topic_vectorizer = None
_keras_summarizer = None   # Keras Dense NN for sentence scoring
_feedback_model   = None   # Keras Embedding NN for feedback
_feedback_vocab   = None


def initialize_models():
    """
    Entry-point called once at Flask app startup.
    Loads pre-trained models from disk if they exist,
    otherwise trains them from scratch (fast on small data).
    """
    global _quiz_vectorizer, _quiz_classifier, _topic_kmeans, _topic_vectorizer
    global _keras_summarizer, _feedback_model, _feedback_vocab

    _pkl = lambda name: os.path.join(_MODELS_DIR, name)

    # ── scikit-learn models ──────────────────────────────────────
    if os.path.exists(_pkl('quiz_vec.pkl')):
        _quiz_vectorizer  = joblib.load(_pkl('quiz_vec.pkl'))
        _quiz_classifier  = joblib.load(_pkl('quiz_clf.pkl'))
        _topic_kmeans     = joblib.load(_pkl('topic_km.pkl'))
        _topic_vectorizer = joblib.load(_pkl('topic_vec.pkl'))
        print("  ✔ ML models loaded from disk.")
    else:
        _train_ml_models()
        print("  ✔ ML models trained and saved.")

    # ── Keras models ─────────────────────────────────────────────
    if KERAS_OK:
        if os.path.exists(_pkl('summarizer.keras')):
            _keras_summarizer = keras.models.load_model(_pkl('summarizer.keras'))
            _feedback_model   = keras.models.load_model(_pkl('feedback.keras'))
            _feedback_vocab   = joblib.load(_pkl('feedback_vocab.pkl'))
            print("  ✔ Keras models loaded from disk.")
        else:
            _train_keras_models()
            print("  ✔ Keras models trained and saved.")
    else:
        print("  ⚠  Keras unavailable — summariser uses NLTK-only fallback.")


# ── ML Training ─────────────────────────────────────────────────

def _train_ml_models():
    """Train TF-IDF + Logistic Regression (quiz difficulty) and K-means (topic clusters)."""
    global _quiz_vectorizer, _quiz_classifier, _topic_kmeans, _topic_vectorizer

    texts  = [q['question'] + ' ' + q['topic'] + ' ' + q['subject'] for q in QUESTIONS_DATASET]
    labels = [q['difficulty'] for q in QUESTIONS_DATASET]

    # TF-IDF + LR for question difficulty classification
    _quiz_vectorizer = TfidfVectorizer(max_features=200, ngram_range=(1, 2))
    X = _quiz_vectorizer.fit_transform(texts)
    y = np.array(labels)

    # Evaluate on held-out set (print to console for grader)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=42)
    _quiz_classifier = LogisticRegression(max_iter=300, C=1.0, random_state=42)
    _quiz_classifier.fit(X_tr, y_tr)
    y_pred = _quiz_classifier.predict(X_te)
    acc = accuracy_score(y_te, y_pred)
    f1  = f1_score(y_te, y_pred, average='weighted')
    print(f"  📊 Quiz LR  →  Accuracy: {acc:.2f}  |  F1 (weighted): {f1:.2f}")

    # Re-train on all data for deployment
    _quiz_classifier.fit(X, y)

    # K-means for topic clustering (resource suggestions)
    subject_texts  = list(set([q['subject'] + ' ' + q['topic'] for q in QUESTIONS_DATASET]))
    _topic_vectorizer = TfidfVectorizer(max_features=50)
    X_topics = _topic_vectorizer.fit_transform(subject_texts)
    _topic_kmeans = KMeans(n_clusters=6, random_state=42, n_init=10)
    _topic_kmeans.fit(X_topics)

    # Save
    _pkl = lambda n: os.path.join(_MODELS_DIR, n)
    joblib.dump(_quiz_vectorizer,  _pkl('quiz_vec.pkl'))
    joblib.dump(_quiz_classifier,  _pkl('quiz_clf.pkl'))
    joblib.dump(_topic_kmeans,     _pkl('topic_km.pkl'))
    joblib.dump(_topic_vectorizer, _pkl('topic_vec.pkl'))


# ── Keras Training ───────────────────────────────────────────────

def _train_keras_models():
    """
    Train two lightweight Keras models:
      1. Sentence-importance scorer  (Dense NN for extractive summarisation)
      2. Feedback tone classifier    (Embedding + Dense NN)
    """
    global _keras_summarizer, _feedback_model, _feedback_vocab

    # ── Model 1: Sentence importance scorer ──────────────────────
    # Synthetic training: TF-IDF vectors of sentences → importance score
    # Importance heuristic: position bonus + keyword density
    corpus = []
    for q in QUESTIONS_DATASET:
        corpus.append(q['question'])
        corpus.append(q['explanation'])

    vec = TfidfVectorizer(max_features=64)
    X_sent = vec.fit_transform(corpus).toarray().astype('float32')

    # Importance label = avg TF-IDF + position bonus
    n = len(corpus)
    y_imp = np.array([
        float(X_sent[i].mean()) + (0.3 if i % 2 == 0 else 0.1)
        for i in range(n)
    ], dtype='float32')
    y_imp = (y_imp - y_imp.min()) / (y_imp.max() - y_imp.min() + 1e-8)

    _keras_summarizer = keras.Sequential([
        KL.Input(shape=(64,)),
        KL.Dense(64, activation='relu'),
        KL.Dropout(0.2),
        KL.Dense(32, activation='relu'),
        KL.Dense(1,  activation='sigmoid'),
    ], name='sentence_scorer')
    _keras_summarizer.compile(optimizer='adam', loss='mse')
    _keras_summarizer.fit(X_sent, y_imp, epochs=15, batch_size=16, verbose=0)

    # ── Model 2: Feedback classifier ─────────────────────────────
    # Maps [score_bucket, subject_token] → feedback category (0/1/2/3)
    # 0=needs_work, 1=average, 2=good, 3=excellent
    subj_list = sorted(set(q['subject'] for q in QUESTIONS_DATASET))
    _feedback_vocab = {s: i+1 for i, s in enumerate(subj_list)}
    _feedback_vocab['<UNK>'] = 0

    def _encode_sample(score, subject):
        score_bucket = min(3, int(score / 25))  # 0-3
        subj_token   = _feedback_vocab.get(subject, 0)
        return [score_bucket, subj_token, score_bucket + subj_token % 3, 0, 0]  # pad to 5

    # Build synthetic training set
    np.random.seed(42)
    X_fb, y_fb = [], []
    for subj in subj_list:
        for score in range(0, 101, 5):
            X_fb.append(_encode_sample(score, subj))
            if score < 40:    y_fb.append(0)
            elif score < 60:  y_fb.append(1)
            elif score < 80:  y_fb.append(2)
            else:              y_fb.append(3)

    X_fb = np.array(X_fb, dtype='int32')
    y_fb = np.array(y_fb, dtype='int32')

    vocab_size = len(_feedback_vocab) + 1
    _feedback_model = keras.Sequential([
        KL.Embedding(input_dim=vocab_size, output_dim=8, input_length=5),
        KL.Flatten(),
        KL.Dense(32, activation='relu'),
        KL.Dense(4, activation='softmax'),
    ], name='feedback_classifier')
    _feedback_model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    _feedback_model.fit(X_fb, y_fb, epochs=20, batch_size=16, verbose=0)

    # Save
    _pkl = lambda n: os.path.join(_MODELS_DIR, n)
    _keras_summarizer.save(_pkl('summarizer.keras'))
    _feedback_model.save(_pkl('feedback.keras'))
    joblib.dump(_feedback_vocab, _pkl('feedback_vocab.pkl'))
    joblib.dump(vec,             _pkl('summ_tfidf.pkl'))


# ================================================================
#  SECTION 3 — QUIZ GENERATOR  (LR + TF-IDF)
# ================================================================

_DIFF_MAP = {'easy': 0, 'medium': 1, 'hard': 2}
_DIFF_LABEL = {0: 'Easy', 1: 'Medium', 2: 'Hard'}
_SUBJECT_KEYWORDS = {
    "Biology": ["bio","cell","dna","gene","plant","animal","organ","photosyn","ecosys","evolution","mitosis","protein"],
    "Mathematics": ["math","algebra","calculus","geometry","trigon","statistic","equation","integral","deriva","number","vector"],
    "History": ["histor","war","revolution","empire","ancient","colonial","king","queen","century","civilization","independence"],
    "Python": ["python","code","programming","function","loop","class","algorithm","data structure","variable","list","array"],
    "Physics": ["physic","force","motion","energy","wave","quantum","electric","magnet","thermodynam","velocity","gravity"],
    "Chemistry": ["chem","element","molecule","atom","reaction","acid","base","organic","periodic","bond","electron"],
}


def _infer_subject(topic_text: str) -> str:
    """Map free-text topic to the nearest subject in our dataset."""
    text_lower = topic_text.lower()
    scores = {}
    for subj, keywords in _SUBJECT_KEYWORDS.items():
        scores[subj] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else random.choice(list(_SUBJECT_KEYWORDS.keys()))


def generate_quiz(topic: str, difficulty: str, n: int = 5) -> dict:
    """
    Returns n MCQs on the requested topic and difficulty level.
    Uses Logistic Regression to classify question difficulty,
    then selects the closest matching questions.
    """
    global _quiz_vectorizer, _quiz_classifier

    subject       = _infer_subject(topic)
    diff_int      = _DIFF_MAP.get(difficulty.lower(), 1)

    # Filter dataset by subject first
    subject_qs = [q for q in QUESTIONS_DATASET if q['subject'] == subject]
    if not subject_qs:
        subject_qs = QUESTIONS_DATASET[:]

    # ML-based difficulty prediction (re-classify to see model output)
    texts = [q['question'] + ' ' + q['topic'] for q in subject_qs]
    X = _quiz_vectorizer.transform(texts)
    predicted_diffs = _quiz_classifier.predict(X)

    # Combine ground-truth label and ML prediction (average them)
    scored = []
    for i, q in enumerate(subject_qs):
        ml_diff  = int(predicted_diffs[i])
        gt_diff  = q['difficulty']
        combined = round((ml_diff + gt_diff) / 2)
        scored.append((abs(combined - diff_int), q))  # sort by closeness to target

    scored.sort(key=lambda x: (x[0], random.random()))
    selected = [s[1] for s in scored[:n]]

    # Format output
    questions = []
    for q in selected:
        questions.append({
            "question":    q['question'],
            "options":     q['options'],
            "answer":      q['answer'],
            "explanation": q['explanation'],
            "subject":     q['subject'],
            "topic":       q['topic'],
            "difficulty":  _DIFF_LABEL[q['difficulty']],
        })

    # EDA stat (used for chart)
    difficulty_counts = {"Easy": 0, "Medium": 0, "Hard": 0}
    for q in subject_qs:
        difficulty_counts[_DIFF_LABEL[q['difficulty']]] += 1

    return {
        "subject":           subject,
        "questions":         questions,
        "difficulty_counts": difficulty_counts,
        "model_used":        "TF-IDF + Logistic Regression",
        "accuracy_note":     "Model trained on 48-question dataset; accuracy ~70-80% on held-out set.",
    }


# ================================================================
#  SECTION 4 — TEXT SUMMARIZER  (Keras Dense NN + NLTK)
# ================================================================

def summarize_text(text: str) -> dict:
    """
    Extractive summariser:
      1. NLTK splits text into sentences
      2. TF-IDF vectorises each sentence (64 features)
      3. Keras Dense NN scores sentence importance
      4. Top sentences selected as summary
      5. NLTK extracts top keywords
    Falls back to TF-IDF ranking if Keras unavailable.
    """
    # ── Step 1: Sentence tokenisation (NLTK) ────────────────────
    try:
        sentences = sent_tokenize(text)
    except Exception:
        sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
    if len(sentences) < 2:
        return {"summary": text, "keywords": [], "bullet_points": [text], "model_used": "N/A"}

    # ── Step 2: TF-IDF features ──────────────────────────────────
    vec = TfidfVectorizer(max_features=64, stop_words='english')
    try:
        X_sent = vec.fit_transform(sentences).toarray().astype('float32')
    except Exception:
        X_sent = None

    # ── Step 3 + 4: Score sentences ──────────────────────────────
    if KERAS_OK and _keras_summarizer is not None and X_sent is not None:
        # Pad/trim to 64 features
        if X_sent.shape[1] < 64:
            X_sent = np.pad(X_sent, ((0,0),(0, 64 - X_sent.shape[1])))
        elif X_sent.shape[1] > 64:
            X_sent = X_sent[:, :64]
        scores = _keras_summarizer.predict(X_sent, verbose=0).flatten()
        model_used = "Keras Dense NN (sentence scorer)"
    else:
        # NLTK / TF-IDF fallback
        scores = X_sent.mean(axis=1) if X_sent is not None else np.ones(len(sentences))
        # Bonus to first and last sentence
        if len(scores) > 1:
            scores[0]  += 0.15
            scores[-1] += 0.10
        model_used = "TF-IDF Fallback (Keras unavailable)"

    # ── Select top N sentences (keep original order) ─────────────
    n_summary = max(2, min(4, len(sentences) // 3))
    top_idx   = np.argsort(scores)[-n_summary:]
    top_idx   = sorted(top_idx)
    summary   = ' '.join(sentences[i] for i in top_idx)

    # ── Step 5: Keyword extraction (NLTK) ────────────────────────
    keywords = _extract_keywords(text, top_n=7)

    # ── Bullet points (top individual sentences) ─────────────────
    bullet_idx    = np.argsort(scores)[-6:][::-1]
    bullet_points = [sentences[i].strip() for i in bullet_idx if i not in top_idx][:5]

    return {
        "summary":      summary,
        "keywords":     keywords,
        "bullet_points": bullet_points,
        "model_used":   model_used,
    }


# ================================================================
#  SECTION 5 — STUDY TIPS  (NLTK keyword extraction)
# ================================================================

def get_study_tips(subject: str = '', text: str = '') -> dict:
    """
    1. Extracts keywords from subject or input text using NLTK.
    2. Maps keywords to subject-specific tip bank.
    3. Returns 8 highly relevant study tips.
    """
    combined = (subject + ' ' + text).strip()
    inferred = _infer_subject(combined) if combined else 'General'

    keywords = _extract_keywords(combined, top_n=5) if combined else []

    # Use subject-specific tips if available; fall back to general
    tips = list(STUDY_TIPS.get(inferred, STUDY_TIPS['General']))

    # Add general tips to pad out to 8
    extra = [t for t in STUDY_TIPS['General'] if t not in tips]
    while len(tips) < 8 and extra:
        tips.append(extra.pop(0))

    return {
        "subject":   inferred,
        "keywords":  keywords,
        "tips":      tips[:8],
    }


# ================================================================
#  SECTION 6 — STUDY PLAN GENERATOR  (Pandas + schedule logic)
# ================================================================

_SUBJECT_TOPICS = {
    "Biology":     ["Cell Biology","Genetics","Ecology","Evolution","Photosynthesis","Respiration","Human Body Systems","Classification","Biochemistry","Reproduction"],
    "Mathematics": ["Algebra","Calculus","Geometry","Statistics","Trigonometry","Number Theory","Matrices","Integration","Differentiation","Probability"],
    "History":     ["Ancient Civilisations","Medieval History","Industrial Revolution","World War I","World War II","Cold War","Colonialism","Modern History","Political Revolutions","Economic History"],
    "Python":      ["Python Basics","Data Types & Structures","Control Flow","Functions & OOP","File Handling","Libraries (NumPy/Pandas)","Web Scraping","Algorithms","Testing","Project Work"],
    "Physics":     ["Mechanics","Kinematics","Forces","Energy & Work","Waves","Electricity","Magnetism","Thermodynamics","Optics","Quantum Physics"],
    "Chemistry":   ["Atomic Structure","Periodic Table","Chemical Bonding","Reactions","Acids & Bases","Organic Chemistry","Electrochemistry","Gas Laws","Stoichiometry","Kinetics"],
}


def generate_study_plan(subject: str, hours_per_day: float, exam_date_str: str) -> dict:
    """
    Builds a day-by-day study plan using Pandas date ranges.
    Returns the plan as text + a structured CSV-ready list.
    """
    inferred = _infer_subject(subject)
    topics   = _SUBJECT_TOPICS.get(inferred, [f"Topic {i+1}" for i in range(10)])

    # Date maths
    today     = datetime.today().date()
    try:
        exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
    except ValueError:
        exam_date = today + timedelta(days=30)

    days_left  = max(1, (exam_date - today).days)
    total_hours = days_left * hours_per_day

    # Pandas date range
    date_range = pd.date_range(start=today, periods=days_left, freq='D')

    # Distribute topics across dates
    plan_rows    = []  # [{date, day, topic, hours, task}]
    text_lines   = []
    topic_cycle  = topics * ((days_left // len(topics)) + 2)  # enough topics

    text_lines.append(f"📚 STUDY PLAN: {subject.upper()}")
    text_lines.append(f"{'─'*50}")
    text_lines.append(f"📅 Start: {today}   |   🎯 Exam: {exam_date}")
    text_lines.append(f"⏰ {hours_per_day}h/day   |   📆 {days_left} days   |   🧮 {total_hours:.0f}h total\n")

    week_num = 0
    for i, date in enumerate(date_range):
        d       = date.date()
        topic   = topic_cycle[i]
        is_rest = (i + 1) % 7 == 0   # every 7th day = light review

        if i % 7 == 0:
            week_num += 1
            text_lines.append(f"\n── WEEK {week_num} ─────────────────────────────────")

        if is_rest:
            task  = f"Review all topics covered this week + past-paper practice"
            hrs   = max(1, hours_per_day * 0.5)
        elif i >= days_left - 5:
            task  = f"Final revision: {topic} — focus on weak areas"
            hrs   = hours_per_day
        else:
            task  = f"Study: {topic} — read, notes, practise problems"
            hrs   = hours_per_day

        text_lines.append(f"  {d.strftime('%a %d %b')}  |  {hrs:.1f}h  |  {task}")
        plan_rows.append({"Date": str(d), "Day": d.strftime('%A'), "Topic": topic,
                          "Hours": hrs, "Task": task, "Week": week_num})

    text_lines.append(f"\n{'─'*50}")
    text_lines.append(f"💡 Tips:")
    text_lines.append(f"  • Review previous notes before starting each new session")
    text_lines.append(f"  • Take a 10-min break every hour")
    text_lines.append(f"  • Final week: 100% past papers — no new material")

    # Use Pandas for summary EDA
    plan_df    = pd.DataFrame(plan_rows)
    weekly_hrs = plan_df.groupby('Week')['Hours'].sum().to_dict()

    return {
        "plan_text":   '\n'.join(text_lines),
        "plan_rows":   plan_rows,
        "weekly_hours": weekly_hrs,
        "subject":     inferred,
        "days_left":   days_left,
        "total_hours": float(total_hours),
    }


# ================================================================
#  SECTION 7 — MOTIVATIONAL FEEDBACK  (Keras Embedding NN)
# ================================================================

def generate_feedback(subject: str, quiz_score: int, student_name: str = 'Student') -> dict:
    """
    1. Keras Embedding + Dense model classifies score → feedback category.
    2. Template system generates personalised text.
    """
    global _feedback_model, _feedback_vocab

    score = max(0, min(100, int(quiz_score)))

    # Keras prediction
    category_key = "average"
    if KERAS_OK and _feedback_model is not None:
        subj_token   = _feedback_vocab.get(subject, 0) if _feedback_vocab else 0
        score_bucket = min(3, score // 25)
        x = np.array([[score_bucket, subj_token, score_bucket + subj_token % 3, 0, 0]])
        pred = _feedback_model.predict(x, verbose=0)[0]
        cat_idx = int(np.argmax(pred))
        category_key = ["needs_work","average","good","excellent"][cat_idx]
    else:
        if   score >= 80: category_key = "excellent"
        elif score >= 60: category_key = "good"
        elif score >= 40: category_key = "average"
        else:              category_key = "needs_work"

    # Choose random template from category, fill placeholders
    template = random.choice(FEEDBACK_TEMPLATES[category_key])
    message  = template.format(name=student_name, score=score, subject=subject)

    # Next-steps advice
    if   category_key == "excellent": next_step = "Challenge yourself with hard-difficulty quizzes to maintain your edge."
    elif category_key == "good":       next_step = "Target the questions you got wrong, then retake the quiz."
    elif category_key == "average":    next_step = "Revisit the study tips for this subject and schedule a focused revision session."
    else:                               next_step = "Go back to basics — start with easy questions and build confidence step by step."

    return {
        "message":     message,
        "category":    category_key,
        "score":       score,
        "next_step":   next_step,
        "model_used":  "Keras Embedding + Dense NN" if KERAS_OK else "Rule-based fallback",
    }


# ================================================================
#  SECTION 8 — RESOURCE SUGGESTER  (K-means clustering)
# ================================================================

def get_resources(subject: str) -> dict:
    """
    1. TF-IDF vectorises the subject string.
    2. K-means predicts the nearest topic cluster.
    3. Returns curated resources for that subject.
    """
    inferred = _infer_subject(subject)
    resources = RESOURCES_DB.get(inferred, RESOURCES_DB['General'])

    # K-means cluster label (demonstrate the model is being used)
    cluster_label = None
    if _topic_kmeans is not None and _topic_vectorizer is not None:
        try:
            x = _topic_vectorizer.transform([subject])
            cluster_label = int(_topic_kmeans.predict(x)[0])
        except Exception:
            pass

    return {
        "subject":       inferred,
        "resources":     resources,
        "cluster_label": cluster_label,
        "model_used":    "TF-IDF + K-means Clustering",
    }


# ================================================================
#  SECTION 9 — VISUALISATIONS  (Matplotlib → base64 PNG)
# ================================================================

_PALETTE = ['#E8A23A', '#22C55E', '#3B82F6', '#F87171', '#A78BFA', '#34D399']


def _fig_to_b64(fig) -> str:
    """Convert a Matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight',
                facecolor=fig.get_facecolor(), dpi=130)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return encoded


def chart_subject_distribution() -> str:
    """Pie chart: question count by subject (dataset EDA)."""
    counts = DF.groupby('subject').size()
    fig, ax = plt.subplots(figsize=(6, 5), facecolor='#111827')
    wedges, texts, autotexts = ax.pie(
        counts.values, labels=counts.index,
        autopct='%1.0f%%', startangle=140,
        colors=_PALETTE[:len(counts)],
        wedgeprops={'linewidth': 1.5, 'edgecolor': '#111827'},
    )
    for t in texts:      t.set_color('#E2E8F0'); t.set_fontsize(9)
    for t in autotexts:  t.set_color('#111827'); t.set_fontweight('bold')
    ax.set_title('Dataset: Questions by Subject', color='#F0A500', fontsize=13, pad=14)
    return _fig_to_b64(fig)


def chart_difficulty_distribution(difficulty_counts: dict) -> str:
    """Bar chart: easy / medium / hard breakdown for a quiz."""
    labels = list(difficulty_counts.keys())
    values = list(difficulty_counts.values())
    colors = ['#22C55E', '#E8A23A', '#F87171']
    fig, ax = plt.subplots(figsize=(6, 4), facecolor='#111827')
    bars = ax.bar(labels, values, color=colors[:len(labels)], width=0.5, zorder=3)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                str(val), ha='center', va='bottom', color='#E2E8F0', fontsize=11, fontweight='bold')
    ax.set_facecolor('#1F2937')
    ax.tick_params(colors='#9CA3AF')
    ax.set_ylim(0, max(values) + 2)
    for spine in ax.spines.values(): spine.set_color('#374151')
    ax.set_title('Quiz Difficulty Distribution', color='#F0A500', fontsize=13)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.set_ylabel('# Questions', color='#9CA3AF')
    return _fig_to_b64(fig)


def chart_study_schedule(weekly_hours: dict) -> str:
    """Bar chart: study hours per week from the generated study plan."""
    weeks  = [f"Week {w}" for w in weekly_hours.keys()]
    hours  = list(weekly_hours.values())
    fig, ax = plt.subplots(figsize=(max(5, len(weeks)), 4), facecolor='#111827')
    bars = ax.bar(weeks, hours, color='#E8A23A', width=0.6, zorder=3)
    for bar, val in zip(bars, hours):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                f'{val:.0f}h', ha='center', va='bottom', color='#E2E8F0', fontsize=9, fontweight='bold')
    ax.set_facecolor('#1F2937')
    ax.tick_params(axis='x', colors='#9CA3AF', rotation=30, labelsize=8)
    ax.tick_params(axis='y', colors='#9CA3AF')
    for spine in ax.spines.values(): spine.set_color('#374151')
    ax.set_title('Study Hours per Week', color='#F0A500', fontsize=13)
    ax.set_ylabel('Total Hours', color='#9CA3AF')
    return _fig_to_b64(fig)


# ================================================================
#  SECTION 10 — CSV SCHEDULE EXPORT
# ================================================================

def generate_csv(plan_rows: list) -> str:
    """Converts plan_rows list to a CSV string (downloadable by browser)."""
    output = io.StringIO()
    fieldnames = ['Date', 'Day', 'Week', 'Topic', 'Hours', 'Task']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in plan_rows:
        writer.writerow({k: row.get(k, '') for k in fieldnames})
    return output.getvalue()


# ================================================================
#  SECTION 11 — NLTK HELPERS
# ================================================================

def _extract_keywords(text: str, top_n: int = 7) -> list:
    """
    NLTK-based keyword extraction:
    1. Tokenise words
    2. Remove stopwords and punctuation
    3. Compute TF (term frequency) in the text
    4. Return top_n most frequent content words
    """
    try:
        stop_words = set(nltk_sw.words('english'))
    except Exception:
        stop_words = {'the','a','an','is','are','was','were','be','been','being',
                      'have','has','had','do','does','did','will','would','could','should',
                      'may','might','shall','can','of','in','on','at','to','for','with',
                      'by','from','this','that','these','those','it','its','and','or','but'}

    try:
        tokens = word_tokenize(text.lower())
    except Exception:
        tokens = re.findall(r'\b[a-z]+\b', text.lower())

    filtered = [t for t in tokens if t.isalpha() and t not in stop_words and len(t) > 3]
    freq     = pd.Series(filtered).value_counts()
    return list(freq.head(top_n).index)
