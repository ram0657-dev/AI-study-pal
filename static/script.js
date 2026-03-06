/* ================================================================
   AI Study Pal — script.js
   All frontend logic: navigation, API calls, DOM rendering.
================================================================ */

/* ── Tiny helpers ────────────────────────────────────────────── */
const $  = id => document.getElementById(id);
const esc = s  => String(s)
  .replace(/&/g,'&amp;').replace(/</g,'&lt;')
  .replace(/>/g,'&gt;').replace(/"/g,'&quot;');

/* ── Loading overlay ─────────────────────────────────────────── */
function loader(msg = 'Processing…') {
  $('overlay').classList.add('on');
  $('ltxt').textContent = msg;
}
function hideLoader() { $('overlay').classList.remove('on'); }

/* ── Toast ───────────────────────────────────────────────────── */
let toastTimer;
function toast(msg, type = 'info') {
  const t = $('toast');
  t.textContent = msg;
  t.className   = `toast on ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('on'), 4500);
}

/* ── Generic fetch helper ────────────────────────────────────── */
async function api(url, body, loadMsg) {
  loader(loadMsg);
  try {
    const r = await fetch(url, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || 'Server error');
    return d;
  } catch (e) {
    toast(e.message, 'err');
    return null;
  } finally {
    hideLoader();
  }
}

/* ── Show base64 chart image ─────────────────────────────────── */
function showChart(imgId, wrapId, b64) {
  if (!b64) return;
  $(imgId).src = `data:image/png;base64,${b64}`;
  $(wrapId).style.display = 'block';
}

/* ════════════════════════════════════════════════════════════════
   NAVIGATION
════════════════════════════════════════════════════════════════ */
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`page-${btn.dataset.page}`).classList.add('active');
    $('sidebar').classList.remove('open');
  });
});

$('ham').addEventListener('click', () => $('sidebar').classList.toggle('open'));

/* ════════════════════════════════════════════════════════════════
   1.  STUDY PLANNER
   Backend: /study_plan  →  Pandas date range + Matplotlib chart
════════════════════════════════════════════════════════════════ */
const hoursRange = $('planHours');
const hoursLbl   = $('hoursLbl');
hoursRange.addEventListener('input', () => {
  hoursLbl.textContent = `${hoursRange.value} hrs`;
});

// Prevent selecting dates in the past
$('planDate').min = new Date().toISOString().split('T')[0];

$('btnPlan').addEventListener('click', async () => {
  const subject = $('planSubject').value.trim();
  const hours   = parseFloat(hoursRange.value);
  const date    = $('planDate').value;

  if (!subject) { toast('Please enter a subject.', 'err'); return; }
  if (!date)    { toast('Please select an exam date.', 'err'); return; }

  const data = await api(
    '/study_plan',
    { subject, hours_per_day: hours, exam_date: date },
    'Building your personalised study plan with Pandas…'
  );
  if (!data) return;

  // Render plain-text schedule (monospace)
  $('planResult').textContent = data.plan_text;
  $('planOutput').style.display = 'block';

  // Matplotlib weekly-hours chart
  showChart('planChart', 'planChartWrap', data.chart_b64);

  $('planOutput').scrollIntoView({ behavior: 'smooth', block: 'start' });
  toast(`✅  ${data.days_left} days · ${Math.round(data.total_hours)}h total — schedule ready!`, 'ok');
});

/* ════════════════════════════════════════════════════════════════
   2.  QUIZ GENERATOR
   Backend: /generate_quiz  →  TF-IDF + Logistic Regression
════════════════════════════════════════════════════════════════ */
document.querySelectorAll('#quizDiff .pl').forEach(p => {
  p.addEventListener('click', () => {
    document.querySelectorAll('#quizDiff .pl').forEach(x => x.classList.remove('active'));
    p.classList.add('active');
  });
});

$('btnQuiz').addEventListener('click', async () => {
  const topic = $('quizTopic').value.trim();
  const diff  = document.querySelector('#quizDiff .pl.active')?.dataset.val || 'medium';

  if (!topic) { toast('Please enter a topic.', 'err'); return; }

  const data = await api(
    '/generate_quiz',
    { topic, difficulty: diff },
    'Classifying difficulty with Logistic Regression…'
  );
  if (!data) return;

  $('quizSbjTitle').textContent = `${data.subject} Quiz`;
  renderQuiz(data.questions);
  $('quizMNote').textContent = `🤖 Model: ${data.model_used}`;

  showChart('qChart', 'qChartWrap', data.chart_b64);

  $('quizOutput').style.display = 'block';
  $('quizOutput').scrollIntoView({ behavior: 'smooth', block: 'start' });
  toast('🎯 Quiz ready — click an option to answer!', 'ok');
});

/**
 * renderQuiz — builds interactive question cards.
 * Each card: question text → 4 options (click to reveal) → explanation.
 */
function renderQuiz(questions) {
  const container = $('quizResult');
  container.innerHTML = '';

  questions.forEach((q, idx) => {
    const card = document.createElement('div');
    card.className = 'qcard';
    card.dataset.answered = '0';

    const optsHtml = Object.entries(q.options).map(([letter, text]) => `
      <div class="opt" data-letter="${letter}" data-correct="${q.answer}">
        <span class="opt-lt">${letter}</span>
        <span>${esc(text)}</span>
      </div>`).join('');

    card.innerHTML = `
      <div class="qnum">Question ${idx + 1} &nbsp;·&nbsp; ${esc(q.subject)} &nbsp;·&nbsp; ${esc(q.difficulty)}</div>
      <div class="qtext">${esc(q.question)}</div>
      <div class="opts">${optsHtml}</div>
      <div class="ans-reveal" id="ans-${idx}">
        ✓ <strong>Correct answer: ${esc(q.answer)}) ${esc(q.options[q.answer])}</strong><br>
        ${esc(q.explanation)}
      </div>`;

    // Click handler — reveal answer on first click only
    card.querySelectorAll('.opt').forEach(opt => {
      opt.addEventListener('click', () => {
        if (card.dataset.answered === '1') return;
        card.dataset.answered = '1';

        const chosen  = opt.dataset.letter;
        const correct = opt.dataset.correct;

        card.querySelectorAll('.opt').forEach(o => {
          o.style.cursor = 'default';
          if (o.dataset.letter === correct)  o.classList.add('correct');
          else if (o.dataset.letter === chosen) o.classList.add('wrong');
        });
        document.getElementById(`ans-${idx}`).classList.add('show');
      });
    });

    container.appendChild(card);
  });

  // "Reveal All Answers" button
  $('revealAll').onclick = () => {
    document.querySelectorAll('.qcard').forEach((card, i) => {
      card.dataset.answered = '1';
      const correct = card.querySelector('.opt')?.dataset.correct;
      card.querySelectorAll('.opt').forEach(o => {
        o.style.cursor = 'default';
        if (o.dataset.letter === correct) o.classList.add('correct');
      });
      const reveal = document.getElementById(`ans-${i}`);
      if (reveal) reveal.classList.add('show');
    });
    $('revealAll').textContent = '✓ All Revealed';
    $('revealAll').disabled = true;
  };

  // Reset reveal button state for fresh quiz
  $('revealAll').textContent = 'Reveal All';
  $('revealAll').disabled = false;
}

/* ════════════════════════════════════════════════════════════════
   3.  TEXT SUMMARIZER
   Backend: /summarize  →  Keras Dense NN + NLTK
════════════════════════════════════════════════════════════════ */
const summTextEl = $('summText');
const charCountEl = $('charCount');

summTextEl.addEventListener('input', () => {
  const n = summTextEl.value.length;
  charCountEl.textContent = `${n.toLocaleString()} character${n !== 1 ? 's' : ''}`;
});

$('btnSumm').addEventListener('click', async () => {
  const text = summTextEl.value.trim();
  if (text.length < 50) { toast('Please paste at least 50 characters of text.', 'err'); return; }

  const data = await api(
    '/summarize',
    { text },
    'Scoring sentences with Keras Dense NN…'
  );
  if (!data) return;

  // Summary paragraph
  $('summResult').textContent = data.summary;

  // Keyword chips (NLTK)
  $('kwResult').innerHTML = data.keywords
    .map(kw => `<span class="kw">${esc(kw)}</span>`)
    .join('');

  // Bullet points
  $('bpResult').innerHTML = data.bullet_points
    .map(bp => `<li>${esc(bp)}</li>`)
    .join('');

  $('summMNote').textContent = `🧠 Model: ${data.model_used}`;
  $('summOutput').style.display = 'block';
  $('summOutput').scrollIntoView({ behavior: 'smooth', block: 'start' });
  toast('📝 Summary complete!', 'ok');
});

/* ════════════════════════════════════════════════════════════════
   4.  STUDY TIPS
   Backend: /study_tips  →  NLTK keyword extraction
════════════════════════════════════════════════════════════════ */
$('btnTips').addEventListener('click', async () => {
  const subject = $('tipsSubject').value.trim();
  const text    = $('tipsText').value.trim();

  if (!subject && !text) { toast('Enter a subject or paste some text.', 'err'); return; }

  const data = await api(
    '/study_tips',
    { subject, text },
    'Extracting keywords with NLTK…'
  );
  if (!data) return;

  // Keyword chips
  $('tipsKw').innerHTML = data.keywords.length
    ? data.keywords.map(kw => `<span class="kw">${esc(kw)}</span>`).join('')
    : `<span class="kw">${esc(data.subject)}</span>`;

  // Numbered tips list
  $('tipsList').innerHTML = data.tips
    .map(tip => `<li>${esc(tip)}</li>`)
    .join('');

  $('tipsOutput').style.display = 'block';
  $('tipsOutput').scrollIntoView({ behavior: 'smooth', block: 'start' });
  toast(`💡 ${data.tips.length} tips for ${data.subject}!`, 'ok');
});

/* ════════════════════════════════════════════════════════════════
   5.  MOTIVATIONAL FEEDBACK
   Backend: /feedback  →  Keras Embedding + Dense NN
════════════════════════════════════════════════════════════════ */
const scoreRange = $('fbScore');
const scoreLbl   = $('scoreLbl');
scoreRange.addEventListener('input', () => {
  scoreLbl.textContent = `${scoreRange.value}%`;
});

// Colour the score ring based on category
const RING_COLORS = {
  excellent: '#22C55E',
  good:      '#3B82F6',
  average:   '#E8A23A',
  needs_work:'#F87171',
};

$('btnFb').addEventListener('click', async () => {
  const name    = $('fbName').value.trim()    || 'Student';
  const subject = $('fbSubject').value.trim() || 'General';
  const score   = parseInt(scoreRange.value);

  const data = await api(
    '/feedback',
    { student_name: name, subject, quiz_score: score },
    'Classifying score with Keras Embedding NN…'
  );
  if (!data) return;

  // Update score ring
  const ringColor = RING_COLORS[data.category] || '#E8A23A';
  const ring = $('scoreRing');
  ring.style.borderColor = ringColor;
  ring.style.boxShadow   = `0 0 20px ${ringColor}55`;
  $('scoreNum').textContent  = data.score;
  $('scoreNum').style.color  = ringColor;

  $('fbMsg').textContent      = data.message;
  $('fbNext').innerHTML       = `<strong>Next Step →</strong> ${esc(data.next_step)}`;
  $('fbMNote').textContent    = `💬 Model: ${data.model_used}`;

  $('fbOutput').style.display = 'block';
  $('fbOutput').scrollIntoView({ behavior: 'smooth', block: 'start' });
  toast('🌟 Feedback generated!', 'ok');
});

/* ════════════════════════════════════════════════════════════════
   6.  RESOURCE SUGGESTIONS
   Backend: /resources  →  TF-IDF + K-means clustering
════════════════════════════════════════════════════════════════ */
$('btnRes').addEventListener('click', async () => {
  const subject = $('resSubject').value.trim();
  if (!subject) { toast('Please enter a subject.', 'err'); return; }

  const data = await api(
    '/resources',
    { subject },
    'Clustering topic with K-means…'
  );
  if (!data) return;

  $('resSbjTitle').textContent = `${data.subject} Resources`;
  $('resMNote').textContent    = `🔍 ${data.model_used}  ·  Cluster: ${data.cluster_label ?? 'N/A'}`;

  $('resGrid').innerHTML = data.resources.map(r => `
    <a class="res-card" href="${esc(r.url)}" target="_blank" rel="noopener">
      <div class="res-type">${esc(r.type)}</div>
      <div class="res-title">${esc(r.title)}</div>
      <div class="res-desc">${esc(r.desc)}</div>
    </a>`).join('');

  $('resOutput').style.display = 'block';
  $('resOutput').scrollIntoView({ behavior: 'smooth', block: 'start' });
  toast(`🔗 ${data.resources.length} resources for ${data.subject}!`, 'ok');
});

/* ── EDA Chart (Dataset distribution pie chart) ────────────────── */
$('btnEda').addEventListener('click', async () => {
  loader('Generating Matplotlib EDA chart…');
  try {
    const r = await fetch('/chart/distribution');
    const d = await r.json();
    if (d.chart_b64) {
      const img = $('edaImg');
      img.src   = `data:image/png;base64,${d.chart_b64}`;
      img.style.display = 'block';
      $('btnEda').textContent = '✓ Chart Loaded';
      $('btnEda').disabled    = true;
      toast('📊 EDA chart loaded!', 'ok');
    }
  } catch (e) {
    toast('Failed to load chart.', 'err');
  } finally {
    hideLoader();
  }
});
