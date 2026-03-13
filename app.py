# ================================================================
#  AI Study Pal — app.py
# ================================================================
import os, base64, traceback
from flask import Flask, request, jsonify, render_template, Response, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ai-study-pal-secret-2026')

print("\n🚀  AI Study Pal — initialising models …")
try:
    from ai_engine import (
        initialize_models, generate_quiz, summarize_text,
        generate_study_plan, get_study_tips, generate_feedback,
        get_resources, generate_csv, chart_subject_distribution,
        chart_difficulty_distribution, chart_study_schedule,
    )
    initialize_models()
    print("✅  All models ready.\n")
except Exception as e:
    print(f"❌  Model init error: {e}")
    traceback.print_exc()


# ── Helpers ─────────────────────────────────────────────────────
def safe_json(fn):
    """Decorator: wraps route in try/except so we always return JSON."""
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            traceback.print_exc()
            return jsonify(error=str(exc)), 500
    return wrapper


@app.route('/')
def index():
    return render_template('index.html')


# ── Study Plan ──────────────────────────────────────────────────
@app.route('/study_plan', methods=['POST'])
@safe_json
def study_plan():
    data     = request.get_json(silent=True) or {}
    subject  = str(data.get('subject', '')).strip()
    chapters = str(data.get('chapters', '')).strip()
    hours    = float(data.get('hours_per_day', 2))
    date     = str(data.get('exam_date', '')).strip()

    if not subject: return jsonify(error='Please enter a subject.'), 400
    if not date:    return jsonify(error='Please provide an exam date.'), 400

    chapter_list = [c.strip() for c in chapters.splitlines() if c.strip()]
    result = generate_study_plan(subject, hours, date, chapters=chapter_list)
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


# ── Quiz Generator ───────────────────────────────────────────────
@app.route('/generate_quiz', methods=['POST'])
@safe_json
def quiz():
    VALID_SUBJECTS = {'Biology','Mathematics','History','Python','Physics','Chemistry'}

    data          = request.get_json(silent=True) or {}
    subject       = str(data.get('subject', '')).strip()
    chapter       = str(data.get('chapter', '')).strip()
    difficulty    = str(data.get('difficulty', 'medium')).strip().lower()
    num_questions = int(data.get('num_questions', 10))
    num_questions = max(5, min(num_questions, 20))

    if not subject:
        return jsonify(error='Please select a subject.'), 400
    if subject not in VALID_SUBJECTS:
        return jsonify(error=f'Invalid subject. Choose from: {", ".join(sorted(VALID_SUBJECTS))}'), 400

    result = generate_quiz(subject, difficulty, chapter=chapter, num_questions=num_questions)
    chart  = chart_difficulty_distribution(result['difficulty_counts'])

    return jsonify(
        subject          =result['subject'],
        questions        =result['questions'],
        difficulty_counts=result['difficulty_counts'],
        chart_b64        =chart,
    )


# ── Summarizer ───────────────────────────────────────────────────
@app.route('/summarize', methods=['POST'])
@safe_json
def summarize():
    data       = request.get_json(silent=True) or {}
    text       = str(data.get('text', '')).strip()
    image_data = data.get('image_data', '')

    if image_data:
        try:
            img_bytes = base64.b64decode(image_data)
        except Exception:
            return jsonify(error='Invalid image data.'), 400
        result = summarize_text('', image_bytes=img_bytes)
    else:
        if len(text) < 50:
            return jsonify(error='Please provide at least 50 characters of text.'), 400
        result = summarize_text(text)

    return jsonify(
        summary      =result['summary'],
        keywords     =result['keywords'],
        bullet_points=result['bullet_points'],
    )


# ── Study Tips ───────────────────────────────────────────────────
@app.route('/study_tips', methods=['POST'])
@safe_json
def study_tips():
    data    = request.get_json(silent=True) or {}
    subject = str(data.get('subject', '')).strip()
    text    = str(data.get('text', '')).strip()
    if not subject and not text:
        return jsonify(error='Please provide a subject or some text.'), 400
    result = get_study_tips(subject=subject, text=text)
    return jsonify(subject=result['subject'], tips=result['tips'], keywords=result['keywords'])


# ── Feedback (image-based, no marks) ────────────────────────────
@app.route('/feedback', methods=['POST'])
@safe_json
def feedback():
    data         = request.get_json(silent=True) or {}
    subject      = str(data.get('subject', 'General')).strip()
    student_name = str(data.get('student_name', 'Student')).strip() or 'Student'
    image_data   = data.get('image_data', '')

    img_bytes = None
    if image_data:
        try:
            img_bytes = base64.b64decode(image_data)
        except Exception:
            return jsonify(error='Invalid image data.'), 400

    result = generate_feedback(subject, student_name, image_bytes=img_bytes)

    return jsonify(
        greeting  =result.get('greeting', ''),
        message   =result['message'],
        next_step =result['next_step'],
        strategies=result.get('strategies', []),
    )


# ── Resources ────────────────────────────────────────────────────
@app.route('/resources', methods=['POST'])
@safe_json
def resources():
    data    = request.get_json(silent=True) or {}
    subject = str(data.get('subject', '')).strip()
    if not subject: return jsonify(error='Please enter a subject.'), 400
    result = get_resources(subject)
    return jsonify(
        subject      =result['subject'],
        resources    =result['resources'],
        cluster_label=result['cluster_label'],
    )


# ── Charts ───────────────────────────────────────────────────────
@app.route('/chart/<chart_type>', methods=['GET'])
@safe_json
def chart(chart_type):
    if chart_type == 'distribution':
        return jsonify(chart_b64=chart_subject_distribution())
    return jsonify(error='Unknown chart type.'), 400


# ── CSV download ─────────────────────────────────────────────────
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
