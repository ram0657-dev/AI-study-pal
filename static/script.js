/* ================================================================
   AI Study Pal — script.js
   Handles all frontend logic: navigation, API calls, UI rendering
================================================================ */

'use strict';

// ── Utility helpers ──────────────────────────────────────────────

const $ = id => document.getElementById(id);

function showToast(msg, type = 'info') {
  const t = $('toast');
  t.textContent = msg;
  t.className = `toast ${type} on`;
  setTimeout(() => t.classList.remove('on'), 3000);
}

function showLoader(msg = 'Processing…') {
  $('ltxt').textContent = msg;
  $('overlay').classList.add('on');
}

function hideLoader() {
  $('overlay').classList.remove('on');
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!text || text.trim() === '') {
    throw new Error('Empty response from server');
  }
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error('Unexpected end of JSON input');
  }
  if (!res.ok) throw new Error(data.error || `Server error ${res.status}`);
  return data;
}

// ── Navigation ───────────────────────────────────────────────────

document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const page = btn.dataset.page;
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $(`page-${page}`).classList.add('active');
    // Close sidebar on mobile
    $('sidebar').classList.remove('open');
  });
});

// Hamburger menu (mobile)
$('ham').addEventListener('click', () => {
  $('sidebar').classList.toggle('open');
});

// ── Study Planner ────────────────────────────────────────────────

$('planHours').addEventListener('input', function () {
  $('hoursLbl').textContent = `${this.value} hrs`;
});

$('btnPlan').addEventListener('click', async () => {
  const subject = $('planSubject').value.trim();
  const hours   = parseFloat($('planHours').value);
  const date    = $('planDate').value;

  if (!subject) { showToast('Please enter a subject.', 'err'); return; }
  if (!date)    { showToast('Please pick an exam date.', 'err'); return; }

  showLoader('Building your study plan…');
  try {
    const d = await postJSON('/study_plan', { subject, hours_per_day: hours, exam_date: date });

    $('planResult').textContent = d.plan_text;
    $('planOutput').style.display = 'block';

    if (d.chart_b64) {
      $('planChart').src = `data:image/png;base64,${d.chart_b64}`;
      $('planChartWrap').style.display = 'block';
    }
    showToast('Study plan ready!', 'ok');
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
});

// ── Quiz Generator ───────────────────────────────────────────────

// Difficulty pill selection
document.querySelectorAll('#quizDiff .pl').forEach(pl => {
  pl.addEventListener('click', () => {
    document.querySelectorAll('#quizDiff .pl').forEach(p => p.classList.remove('active'));
    pl.classList.add('active');
  });
});

function getQuizDifficulty() {
  const active = document.querySelector('#quizDiff .pl.active');
  return active ? active.dataset.val : 'medium';
}

function renderQuiz(questions) {
  const container = $('quizResult');
  container.innerHTML = '';
  questions.forEach((q, i) => {
    const card = document.createElement('div');
    card.className = 'qcard';
    card.innerHTML = `
      <div class="qnum">Question ${i + 1}</div>
      <div class="qtext">${q.question}</div>
      <div class="opts" id="opts-${i}">
        ${q.options.map((opt, j) => `
          <div class="opt" data-idx="${i}" data-opt="${j}" data-correct="${q.answer_index}">
            <span class="opt-lt">${String.fromCharCode(65 + j)}</span>
            <span>${opt}</span>
          </div>`).join('')}
      </div>
      <div class="ans-reveal" id="ans-${i}">
        ✅ Correct answer: <strong>${q.options[q.answer_index]}</strong>
        ${q.explanation ? `<br><span style="opacity:.8">${q.explanation}</span>` : ''}
      </div>`;
    container.appendChild(card);
  });

  // Click handlers
  document.querySelectorAll('.opt').forEach(opt => {
    opt.addEventListener('click', () => {
      const idx     = opt.dataset.idx;
      const chosen  = parseInt(opt.dataset.opt);
      const correct = parseInt(opt.dataset.correct);
      const group   = document.querySelectorAll(`.opt[data-idx="${idx}"]`);
      group.forEach(o => o.style.pointerEvents = 'none');
      opt.classList.add(chosen === correct ? 'correct' : 'wrong');
      if (chosen !== correct) {
        group[correct].classList.add('correct');
      }
      $(`ans-${idx}`).classList.add('show');
    });
  });
}

$('btnQuiz').addEventListener('click', async () => {
  const topic      = $('quizTopic').value.trim();
  const difficulty = getQuizDifficulty();
  if (!topic) { showToast('Please enter a topic.', 'err'); return; }

  showLoader('Generating quiz questions…');
  try {
    const d = await postJSON('/generate_quiz', { topic, difficulty });

    $('quizSbjTitle').textContent = `Quiz — ${d.subject}`;
    renderQuiz(d.questions);
    $('quizMNote').textContent = `Model: ${d.model_used}`;
    $('quizOutput').style.display = 'block';

    if (d.chart_b64) {
      $('qChart').src = `data:image/png;base64,${d.chart_b64}`;
      $('qChartWrap').style.display = 'block';
    }
    showToast('Quiz ready!', 'ok');
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
});

$('revealAll').addEventListener('click', () => {
  document.querySelectorAll('.ans-reveal').forEach(el => el.classList.add('show'));
  document.querySelectorAll('.opt').forEach(opt => {
    opt.style.pointerEvents = 'none';
    if (parseInt(opt.dataset.opt) === parseInt(opt.dataset.correct)) {
      opt.classList.add('correct');
    }
  });
});

// ── Text Summarizer ──────────────────────────────────────────────

$('summText').addEventListener('input', function () {
  $('charCount').textContent = `${this.value.length} characters`;
});

$('btnSumm').addEventListener('click', async () => {
  const text = $('summText').value.trim();
  if (text.length < 50) { showToast('Please enter at least 50 characters.', 'err'); return; }

  showLoader('Summarising with Keras NN…');
  try {
    const d = await postJSON('/summarize', { text });

    $('summResult').textContent = d.summary;

    const kwEl = $('kwResult');
    kwEl.innerHTML = d.keywords.map(k => `<span class="kw">${k}</span>`).join('');

    const bpEl = $('bpResult');
    bpEl.innerHTML = d.bullet_points.map(b => `<li>${b}</li>`).join('');

    $('summMNote').textContent = `Model: ${d.model_used}`;
    $('summOutput').style.display = 'block';
    showToast('Summary ready!', 'ok');
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
});

// ── Study Tips ───────────────────────────────────────────────────

$('btnTips').addEventListener('click', async () => {
  const subject = $('tipsSubject').value.trim();
  const text    = $('tipsText').value.trim();
  if (!subject && !text) { showToast('Please enter a subject or some text.', 'err'); return; }

  showLoader('Extracting tips with NLTK…');
  try {
    const d = await postJSON('/study_tips', { subject, text });

    const kwEl = $('tipsKw');
    kwEl.innerHTML = (d.keywords || []).map(k => `<span class="kw">${k}</span>`).join('');

    const listEl = $('tipsList');
    listEl.innerHTML = (d.tips || []).map(t => `<li>${t}</li>`).join('');

    $('tipsOutput').style.display = 'block';
    showToast('Tips generated!', 'ok');
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
});

// ── Feedback ─────────────────────────────────────────────────────

$('fbScore').addEventListener('input', function () {
  $('scoreLbl').textContent = `${this.value}%`;
});

$('btnFb').addEventListener('click', async () => {
  const student_name = $('fbName').value.trim() || 'Student';
  const subject      = $('fbSubject').value.trim() || 'General';
  const quiz_score   = parseInt($('fbScore').value);

  showLoader('Generating personalised feedback…');
  try {
    const d = await postJSON('/feedback', { student_name, subject, quiz_score });

    $('scoreNum').textContent = d.score;
    $('scoreRing').style.borderColor =
      d.score >= 75 ? 'var(--green)' : d.score >= 50 ? 'var(--gold)' : 'var(--red)';
    $('fbMsg').textContent  = d.message;
    $('fbNext').textContent = d.next_step;
    $('fbMNote').textContent = `Model: ${d.model_used}`;
    $('fbOutput').style.display = 'block';
    showToast('Feedback ready!', 'ok');
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
});

// ── Resources ────────────────────────────────────────────────────

$('btnEda').addEventListener('click', async () => {
  showLoader('Loading Matplotlib chart…');
  try {
    const res  = await fetch('/chart/distribution');
    const text = await res.text();
    if (!text || text.trim() === '') throw new Error('Empty response');
    const d = JSON.parse(text);
    if (d.chart_b64) {
      $('edaImg').src = `data:image/png;base64,${d.chart_b64}`;
      $('edaImg').style.display = 'block';
    }
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
});

$('btnRes').addEventListener('click', async () => {
  const subject = $('resSubject').value.trim();
  if (!subject) { showToast('Please enter a subject.', 'err'); return; }

  showLoader('Clustering resources with K-means…');
  try {
    const d = await postJSON('/resources', { subject });

    $('resSbjTitle').textContent = `Resources — ${d.subject}`;
    $('resMNote').textContent    = `Cluster: ${d.cluster_label} · Model: ${d.model_used}`;

    const grid = $('resGrid');
    grid.innerHTML = (d.resources || []).map(r => `
      <a class="res-card" href="${r.url || '#'}" target="_blank" rel="noopener">
        <div class="res-type">${r.type || 'Resource'}</div>
        <div class="res-title">${r.title}</div>
        <div class="res-desc">${r.description || ''}</div>
      </a>`).join('');

    $('resOutput').style.display = 'block';
    showToast('Resources found!', 'ok');
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
});
