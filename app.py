# ================================================================
#  AI Study Pal — app.py
#  Flask web application.  Cross-platform (local + Render.com).
#
#  Routes:
#    GET  /                  → serve SPA
#    POST /study_plan        → AI study plan + Pandas schedule
#    POST /generate_quiz     → ML quiz (LR + TF-IDF)
#    POST /summarize         → DL summarisation (Keras)
#    POST /study_tips        → NLP tips (NLTK)
#    POST /feedback          → Motivational feedback (Keras)
#    POST /resources         → Resource suggestions (K-means)
#    GET  /chart/<type>      → Matplotlib chart base64
#    GET  /download_csv      → Download schedule as .csv
# ================================================================

import os
from flask import (Flask, request, jsonify, render_template,
                   Response, session)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ai-study-pal-secret-2026')

# ── Load / train all AI models at startup ────────────────────────
print("\n🚀  AI Study Pal — initialising models …")
from ai_engine import (
    initialize_models, generate_quiz, summarize_text,
    generate_study_plan, get_study_tips, generate_feedback,
    get_resources, generate_csv, chart_subject_distribution,
    chart_difficulty_distribution, chart_study_schedule,
)
initialize_models()
print("✅  All models ready.  App is running!\n")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/study_plan', methods=['POST'])
def study_plan():
    data    = request.get_json(silent=True) or {}
    subject = str(data.get('subject', '')).strip()
    hours   = float(data.get('hours_per_day', 2))
    date    = str(data.get('exam_date', '')).strip()
    if not subject: return jsonify(error='Please enter a subject.'), 400
    if not date:    return jsonify(error='Please provide an exam date.'), 400

    result = generate_study_plan(subject, hours, date)
    chart  = chart_study_schedule(result['weekly_hours'])
    session['last_plan_csv']  = generate_csv(result['plan_rows'])
    session['last_plan_name'] = f"{result['subject']}_study_schedule.csv"

    return jsonify(
        plan_text   =result['plan_text'],
        weekly_hours=result['weekly_hours'],
        subject     =result['subject'],
        days_left   =result['days_left'],
        total_hours =result['total_hours'],
        chart_b64   =chart,
    )


@app.route('/generate_quiz', methods=['POST'])
def quiz():
    data       = request.get_json(silent=True) or {}
    topic      = str(data.get('topic', '')).strip()
    difficulty = str(data.get('difficulty', 'medium')).strip().lower()
    if not topic: return jsonify(error='Please enter a topic.'), 400

    result = generate_quiz(topic, difficulty)
    chart  = chart_difficulty_distribution(result['difficulty_counts'])
    return jsonify(
        subject          =result['subject'],
        questions        =result['questions'],
        difficulty_counts=result['difficulty_counts'],
        model_used       =result['model_used'],
        chart_b64        =chart,
    )


@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.get_json(silent=True) or {}
    text = str(data.get('text', '')).strip()
    if len(text) < 50:
        return jsonify(error='Please provide at least 50 characters of text.'), 400
    result = summarize_text(text)
    return jsonify(
        summary      =result['summary'],
        keywords     =result['keywords'],
        bullet_points=result['bullet_points'],
        model_used   =result['model_used'],
    )


@app.route('/study_tips', methods=['POST'])
def study_tips():
    data    = request.get_json(silent=True) or {}
    subject = str(data.get('subject', '')).strip()
    text    = str(data.get('text', '')).strip()
    if not subject and not text:
        return jsonify(error='Please provide a subject or some text.'), 400
    result = get_study_tips(subject=subject, text=text)
    return jsonify(subject=result['subject'], tips=result['tips'], keywords=result['keywords'])


@app.route('/feedback', methods=['POST'])
def feedback():
    data         = request.get_json(silent=True) or {}
    subject      = str(data.get('subject', 'General')).strip()
    quiz_score   = int(data.get('quiz_score', 50))
    student_name = str(data.get('student_name', 'Student')).strip() or 'Student'
    result = generate_feedback(subject, quiz_score, student_name)
    return jsonify(
        message   =result['message'],
        category  =result['category'],
        score     =result['score'],
        next_step =result['next_step'],
        model_used=result['model_used'],
    )


@app.route('/resources', methods=['POST'])
def resources():
    data    = request.get_json(silent=True) or {}
    subject = str(data.get('subject', '')).strip()
    if not subject: return jsonify(error='Please enter a subject.'), 400
    result = get_resources(subject)
    return jsonify(
        subject      =result['subject'],
        resources    =result['resources'],
        cluster_label=result['cluster_label'],
        model_used   =result['model_used'],
    )


@app.route('/chart/<chart_type>', methods=['GET'])
def chart(chart_type):
    if chart_type == 'distribution':
        return jsonify(chart_b64=chart_subject_distribution())
    return jsonify(error='Unknown chart type.'), 400


@app.route('/download_csv', methods=['GET'])
def download_csv():
    csv_data  = session.get('last_plan_csv', '')
    file_name = session.get('last_plan_name', 'study_schedule.csv')
    if not csv_data:
        return "No schedule generated yet.", 404
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{file_name}"'}
    )


@app.route('/health')
def health():
    return jsonify(status='ok', app='AI Study Pal'), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐  Open  http://127.0.0.1:{port}  in your browser")
    app.run(host='0.0.0.0', port=port, debug=False)
