# 🎓 AI Study Pal

> An intelligent AI-powered study companion built with Flask, ML, Deep Learning, NLP, and deployed to production.

**Status:** ✅ Live & Running | 📊 Full-Stack | 🚀 Production Ready

A complete AI-powered study assistant web application demonstrating all five domains of the AI course curriculum: **Python · ML · Deep Learning · NLP · Web Deployment**

---

## 🗂 Project Structure

```
AI_Study_Pal/
│
├── app.py               ← Flask web server (all routes)
├── ai_engine.py         ← Complete AI / ML brain
├── requirements.txt     ← Python dependencies
├── Procfile             ← Render.com / Gunicorn start command
├── render.yaml          ← Render.com auto-deploy blueprint
├── runtime.txt          ← Python version pin
├── .gitignore
├── README.md
│
├── templates/
│   └── index.html       ← Single-page frontend (Jinja2)
│
├── static/
│   ├── style.css        ← Dark Academic theme
│   └── script.js        ← All frontend JS / API calls
│
└── models/              ← Auto-created; trained models saved here
    ├── quiz_vec.pkl
    ├── quiz_clf.pkl
    ├── topic_km.pkl
    ├── topic_vec.pkl
    ├── summarizer.keras
    └── feedback.keras
```

---

## 🤖 AI / ML Stack (as per capstone specification)

| Feature | Technology | Model |
|---|---|---|
| Study Planner | **Pandas** date ranges | Rule-based scheduling |
| Quiz Generator | **scikit-learn** | TF-IDF + Logistic Regression |
| Topic Clustering | **scikit-learn** | K-means |
| Text Summarizer | **Keras** Dense NN | Sentence importance scoring |
| Motivational Feedback | **Keras** Embedding NN | Score-bucket classifier |
| Study Tips | **NLTK** | Tokenisation + keyword extraction |
| Visualisations | **Matplotlib** | Pie & bar charts → base64 |
| Data Handling | **Pandas** | EDA, scheduling, CSV export |

---

## 🚀 Run Locally (VS Code)

### 1. Clone / unzip the project
```bash
cd AI_Study_Pal
```

### 2. Create a virtual environment (recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```
> ⏳ First install takes ~3–5 minutes (TensorFlow is large).

### 4. Run the app
```bash
python app.py
```

### 5. Open in browser
```
http://127.0.0.1:5000
```

> 💡 On first startup, models are **trained automatically** (~20–30 seconds).
> Subsequent starts load saved models instantly.

---

## ☁️ Deploy to Render.com (Free — works from any browser worldwide)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "AI Study Pal capstone"
git remote add origin https://github.com/YOUR_USERNAME/ai-study-pal.git
git push -u origin main
```

### Step 2 — Create a Render Web Service
1. Go to **https://render.com** → Sign up free
2. Click **New** → **Web Service**
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — click **Apply**
5. Wait ~5 minutes for the first build

### Step 3 — Your app is live!
```
https://ai-study-pal.onrender.com
```
> Share this URL with anyone worldwide — no installation needed.

---

## 📊 Dataset

48 hand-crafted questions across 6 subjects:
**Biology · Mathematics · History · Python · Physics · Chemistry**

Each question has: subject, topic, difficulty (easy/medium/hard),
4 options, correct answer, and explanation.

Stored in `ai_engine.py` as `QUESTIONS_DATASET` — no external files needed.

---

## 📈 Evaluation Metrics

The app prints ML metrics to the console on first startup:

```
📊 Quiz LR  →  Accuracy: 0.75  |  F1 (weighted): 0.73
```

---

## 📦 Deliverables Checklist

- [x] Cleaned dataset (48 questions, Pandas DataFrame)
- [x] Simple EDA visualisation (subject pie chart)
- [x] ML-based quiz generator (TF-IDF + Logistic Regression + K-means)
- [x] DL text summariser (Keras Dense NN)
- [x] NLP study tips (NLTK keyword extraction)
- [x] Motivational feedback (Keras Embedding NN)
- [x] Flask web app with all 6 features
- [x] Downloadable CSV study schedules
- [x] Matplotlib charts in-browser
- [x] Render.com deployment config

---

## 🛠 Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Slow first startup | Normal — models are training. Wait 30s |
| Port 5000 in use | Run `python app.py` — it auto-picks `$PORT` |
| TensorFlow install fails | Try `pip install tensorflow-cpu==2.15.0` |
| NLTK download error | App auto-downloads to `/tmp/nltk_data` |

---

## 🎯 Key Features

### ✨ Study Planner
- **AI-Generated Schedule** - Creates personalized study plans based on exam date and available hours
- **CSV Export** - Download your schedule as a spreadsheet
- **Pandas Integration** - Intelligent date range distribution

### 🧠 Quiz Generator  
- **ML-Powered Questions** - TF-IDF vectorization + Logistic Regression
- **Difficulty Levels** - Easy, Medium, Hard classifications
- **Performance Metrics** - Real-time accuracy tracking

### 📖 Text Summarizer
- **Deep Learning** - Keras neural network with embedding layers
- **Smart Extraction** - Identifies most important sentences
- **Quick Learning** - Perfect for revision before exams

### 💡 Study Tips
- **NLP-Driven** - NLTK-based keyword extraction
- **Context-Aware** - Tailored suggestions based on topics
- **Personalized** - Different tips for different subjects

### 🎯 Resource Suggester
- **ML Clustering** - K-means algorithm groups similar resources
- **Smart Recommendations** - Discover related learning materials
- **Cross-Subject** - Find connections between topics

### 🎉 Motivational Feedback
- **Neural Network** - Keras embedding + classification
- **Performance-Based** - Adjusts tone based on quiz scores
- **Encouraging** - Boosts confidence for continued learning

---

## 🔄 How the App Works

```
User Input → Flask Route → AI Engine → ML/DL Model → JSON Response → UI Update
```

**Example Flow (Quiz Generator):**
1. User selects a topic
2. Flask receives POST request
3. `ai_engine.py` loads the trained classifier
4. TF-IDF vectorizes the query
5. Logistic Regression predicts difficulty
6. App returns curated questions
7. Frontend displays interactively

---

## 📊 Technology Breakdown

### Backend (Python)
- **Framework:** Flask 3.0.0
- **Data:** Pandas 2.1.4, NumPy 1.26.4
- **ML:** scikit-learn 1.3.2
- **DL:** TensorFlow 2.16.1, Keras
- **NLP:** NLTK 3.8.1
- **Plots:** Matplotlib 3.8.2
- **Server:** Gunicorn 21.2.0

### Frontend
- Pure HTML5 + CSS3 + JavaScript
- No framework dependencies (Vue, React, Angular)
- Dark academic theme
- Fully responsive design

### Deployment
- **Local:** Flask dev server
- **Production:** Gunicorn WSGI
- **Cloud:** Render.com (free tier)
- **Version Control:** Git + GitHub

---

## 📈 Project Metrics

- **Lines of Code:** ~2,500+
- **ML Models:** 6 (various types)
- **API Endpoints:** 8
- **Components:** Modular architecture
- **Test Coverage:** Manual testing on all features
- **Performance:** <500ms for most requests

---

## 🚀 Next Steps & Enhancements

### Phase 2 (Future)
- [ ] User authentication (Firebase)
- [ ] Progress tracking & statistics
- [ ] Spaced repetition algorithm
- [ ] Mobile app (React Native)
- [ ] Video recommendations
- [ ] Group study features
- [ ] Real-time collaboration
- [ ] Advanced analytics dashboard

### Improvements
- Better ML models with more training data
- Transformer-based NLP (BERT)
- Distributed training on larger datasets
- Advanced difficulty adaptation
- Real-time progress visualization

---

## 👨‍💻 About the Author

**Vishal Kothar**
- GitHub: [@ram0657-dev](https://github.com/ram0657-dev)
- Email: ram0657@gmail.com
- **Project:** LaunchED Global Capstone (January 2026)
- **Focus:** Full-stack AI development with production deployment

---

## 📚 Learning Outcomes

✅ **Python** - Built complete backend application  
✅ **Machine Learning** - TF-IDF, Logistic Regression, K-means  
✅ **Deep Learning** - Neural networks for text summarization & feedback  
✅ **NLP** - NLTK tokenization, keyword extraction  
✅ **Web Development** - Flask, HTML/CSS/JavaScript  
✅ **Deployment** - Production-ready Render.com deployment  
✅ **Git & GitHub** - Version control & collaboration  
✅ **Data Processing** - Pandas, NumPy, data cleaning  

---

## 📝 License

MIT License - Feel free to fork, modify, and use for your projects!

---

## 🤝 Contributing

Found a bug? Have an idea? 

1. **Fork** the repository
2. **Create** a feature branch
3. **Commit** your changes
4. **Push** and create a Pull Request
5. **Report** issues in the GitHub Issues section

---

## 📞 Support & Questions

- 📧 **Email:** ram0657@gmail.com
- 🐛 **Issues:** [GitHub Issues](https://github.com/ram0657-dev/AI-study-pal/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/ram0657-dev/AI-study-pal/discussions)

---

## 🎓 Resources Used

- **Flask Documentation:** https://flask.palletsprojects.com
- **scikit-learn Guide:** https://scikit-learn.org
- **TensorFlow/Keras:** https://www.tensorflow.org
- **NLTK Handbook:** https://www.nltk.org/book/
- **LaunchED Global:** Capstone curriculum

---

**Built with passion for education and learning. Help students achieve their potential! 🚀**

*Last Updated: March 6, 2026*
