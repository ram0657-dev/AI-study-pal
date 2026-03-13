/* ================================================================
   AI Study Pal — script.js
================================================================ */
'use strict';

const $ = id => document.getElementById(id);

// ── Toast ────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const t = $('toast');
  t.textContent = msg;
  t.className = `toast ${type} on`;
  setTimeout(() => t.classList.remove('on'), 3500);
}

// ── Loader ───────────────────────────────────────────────────────
function showLoader(msg = 'Processing…') {
  $('ltxt').textContent = msg;
  $('overlay').classList.add('on');
}
function hideLoader() { $('overlay').classList.remove('on'); }

// ── Safe JSON fetch ──────────────────────────────────────────────
// Root cause of "Unexpected end of JSON input":
// Flask returns an HTML 500 page when a route crashes.
// This function guards against that and shows the real error.
async function postJSON(url, body) {
  let res;
  try {
    res = await fetch(url, {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify(body),
    });
  } catch (netErr) {
    throw new Error('Network error — is the server running?');
  }

  const text = await res.text();

  // Empty body
  if (!text || text.trim() === '') {
    throw new Error(`Server returned empty response (HTTP ${res.status})`);
  }

  // HTML error page (Flask 500 / Gunicorn crash)
  if (text.trim().startsWith('<!')) {
    throw new Error(`Server error (HTTP ${res.status}) — check Render logs`);
  }

  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error('Invalid JSON from server — check Render logs');
  }

  if (!res.ok) throw new Error(data.error || `Server error ${res.status}`);
  return data;
}

// ── Navigation ───────────────────────────────────────────────────
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $(`page-${btn.dataset.page}`).classList.add('active');
    $('sidebar').classList.remove('open');
  });
});
$('ham').addEventListener('click', () => $('sidebar').classList.toggle('open'));

// ── Pill group helper ────────────────────────────────────────────
function initPillGroup(groupId) {
  const g = $(groupId);
  if (!g) return;
  g.querySelectorAll('.pl').forEach(pl => {
    pl.addEventListener('click', () => {
      g.querySelectorAll('.pl').forEach(p => p.classList.remove('active'));
      pl.classList.add('active');
    });
  });
}
function getActivePill(groupId) {
  const a = document.querySelector(`#${groupId} .pl.active`);
  return a ? a.dataset.val : null;
}

initPillGroup('quizNumQ');
initPillGroup('quizTimer');
initPillGroup('quizDiff');

// ════════════════════════════════════════════════════════════════
//  STUDY PLANNER
// ════════════════════════════════════════════════════════════════
$('planHours').addEventListener('input', function () {
  $('hoursLbl').textContent = `${this.value} hrs`;
});

$('btnPlan').addEventListener('click', async () => {
  const subject  = $('planSubject').value.trim();
  const chapters = $('planChapters').value.trim();
  const hours    = parseFloat($('planHours').value);
  const date     = $('planDate').value;

  if (!subject) { showToast('Please enter a subject.', 'err'); return; }
  if (!date)    { showToast('Please pick an exam date.', 'err'); return; }

  showLoader('Building your study plan…');
  try {
    const d = await postJSON('/study_plan', {
      subject,
      chapters,
      hours_per_day: hours,
      exam_date    : date,
    });
    $('planResult').textContent   = d.plan_text;
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

// ════════════════════════════════════════════════════════════════
//  QUIZ GENERATOR
// ════════════════════════════════════════════════════════════════

// Subject selector
const VALID_SUBJECTS = ['Biology','Mathematics','History','Python','Physics','Chemistry'];
let _selectedSubject = null;

document.querySelectorAll('.subj-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.subj-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    _selectedSubject = btn.dataset.val;
    $('subjHint').style.display = 'none';
  });
});

// Timer state
let _timerInterval = null;
let _timerTotal    = 0;
let _timerEnabled  = false;
let _quizQuestions = [];
const CIRC = 113; // 2π × 18

function stopTimer() {
  if (_timerInterval) { clearInterval(_timerInterval); _timerInterval = null; }
}

function startTimerForQuestion(idx) {
  stopTimer();
  if (!_timerEnabled || _timerTotal === 0) return;

  const display  = $('quizTimerDisplay');
  const countEl  = $('timerCount');
  const circle   = $('timerCircle');
  const ringEl   = $('timerRingEl');

  display.style.display = 'flex';
  ringEl.className      = 'timer-ring';
  let secs = _timerTotal;
  countEl.textContent = secs;
  circle.style.strokeDashoffset = '0';

  _timerInterval = setInterval(() => {
    secs--;
    countEl.textContent = secs;
    circle.style.strokeDashoffset = String((1 - secs / _timerTotal) * CIRC);

    if (secs <= _timerTotal * 0.25)     ringEl.className = 'timer-ring danger';
    else if (secs <= _timerTotal * 0.5) ringEl.className = 'timer-ring warning';

    if (secs <= 0) {
      stopTimer();
      lockQuestion(idx, true);
      showToast('⏰ Time\'s up!', 'info');
      setTimeout(() => advanceTo(idx + 1), 1500);
    }
  }, 1000);
}

function lockQuestion(idx, timedOut = false) {
  const qcard = document.querySelectorAll('.qcard')[idx];
  if (!qcard || qcard.classList.contains('answered')) return;
  qcard.classList.add('answered');
  const opts = qcard.querySelectorAll('.opt');
  opts.forEach(o => {
    o.style.pointerEvents = 'none';
    if (parseInt(o.dataset.opt) === parseInt(o.dataset.correct)) {
      o.classList.add(timedOut ? 'timed-out' : 'correct');
    }
  });
  const reveal = qcard.querySelector('.ans-reveal');
  if (reveal) reveal.classList.add('show');
  updateProgress();
}

function advanceTo(idx) {
  if (idx >= _quizQuestions.length) {
    stopTimer();
    $('quizTimerDisplay').style.display = 'none';
    showToast('Quiz complete! 🎉', 'ok');
    return;
  }
  const cards = document.querySelectorAll('.qcard');
  if (cards[idx]) cards[idx].scrollIntoView({ behavior: 'smooth', block: 'center' });
  startTimerForQuestion(idx);
}

function updateProgress() {
  const answered = document.querySelectorAll('.qcard.answered').length;
  $('quizProgress').textContent = `${answered} / ${_quizQuestions.length} answered`;
}

function renderQuiz(questions) {
  _quizQuestions = questions;
  const container = $('quizResult');
  container.innerHTML = '';

  questions.forEach((q, i) => {
    const card = document.createElement('div');
    card.className = 'qcard';
    card.innerHTML = `
      <div class="qnum">Question ${i + 1} of ${questions.length}</div>
      <div class="qtext">${q.question}</div>
      <div class="opts">
        ${q.options.map((opt, j) => `
          <div class="opt" data-idx="${i}" data-opt="${j}" data-correct="${q.answer_index}">
            <span class="opt-lt">${String.fromCharCode(65 + j)}</span>
            <span>${opt}</span>
          </div>`).join('')}
      </div>
      <div class="ans-reveal" id="ans-${i}">
        ✅ Correct: <strong>${q.options[q.answer_index]}</strong>
        ${q.explanation ? `<br><span style="opacity:.8;font-size:.85em">${q.explanation}</span>` : ''}
      </div>`;
    container.appendChild(card);
  });

  document.querySelectorAll('.opt').forEach(opt => {
    opt.addEventListener('click', () => {
      const idx     = parseInt(opt.dataset.idx);
      const chosen  = parseInt(opt.dataset.opt);
      const correct = parseInt(opt.dataset.correct);
      const qcard   = opt.closest('.qcard');
      if (qcard.classList.contains('answered')) return;

      stopTimer();
      qcard.classList.add('answered');
      qcard.querySelectorAll('.opt').forEach(o => o.style.pointerEvents = 'none');
      opt.classList.add(chosen === correct ? 'correct' : 'wrong');
      if (chosen !== correct) qcard.querySelectorAll('.opt')[correct].classList.add('correct');
      document.getElementById(`ans-${idx}`).classList.add('show');
      updateProgress();

      if (_timerEnabled) setTimeout(() => advanceTo(idx + 1), 700);
    });
  });

  updateProgress();
}

$('btnQuiz').addEventListener('click', async () => {
  if (!_selectedSubject) {
    $('subjHint').style.display = 'block';
    showToast('Please select a subject.', 'err');
    return;
  }

  const chapter   = $('quizChapter').value.trim();
  const difficulty = getActivePill('quizDiff') || 'medium';
  const numQ      = parseInt(getActivePill('quizNumQ') || '10');
  const timerSecs = parseInt(getActivePill('quizTimer') || '0');

  stopTimer();
  _timerEnabled = timerSecs > 0;
  _timerTotal   = timerSecs;

  showLoader('Generating quiz…');
  try {
    const d = await postJSON('/generate_quiz', {
      subject      : _selectedSubject,   // ← subject, not topic
      chapter,
      difficulty,
      num_questions: numQ,
    });

    $('quizSbjTitle').textContent = `${_selectedSubject} Quiz${chapter ? ' · ' + chapter : ''}`;
    renderQuiz(d.questions);
    $('quizOutput').style.display = 'block';

    if (d.chart_b64) {
      $('qChart').src = `data:image/png;base64,${d.chart_b64}`;
      $('qChartWrap').style.display = 'block';
    }

    if (_timerEnabled) {
      $('quizTimerDisplay').style.display = 'flex';
      startTimerForQuestion(0);
    } else {
      $('quizTimerDisplay').style.display = 'none';
    }

    showToast('Quiz ready!', 'ok');
    $('quizOutput').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
});

$('revealAll').addEventListener('click', () => {
  stopTimer();
  $('quizTimerDisplay').style.display = 'none';
  document.querySelectorAll('.qcard').forEach((card, i) => lockQuestion(i));
});

// ════════════════════════════════════════════════════════════════
//  SUMMARIZER
// ════════════════════════════════════════════════════════════════

// Tab switching
document.querySelectorAll('.itab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.itab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const isText = tab.dataset.tab === 'text';
    $('panelText').style.display  = isText ? 'block' : 'none';
    $('panelImage').style.display = isText ? 'none'  : 'block';
  });
});

$('summText').addEventListener('input', function () {
  $('charCount').textContent = `${this.value.length} characters`;
});

$('btnSumm').addEventListener('click', async () => {
  const text = $('summText').value.trim();
  if (text.length < 50) { showToast('Please enter at least 50 characters.', 'err'); return; }
  await runSummarise({ text }, '✏️ Source: Pasted Text');
});

// Image handlers for summarizer
let _summImageB64  = null;
let _summStream    = null;

function summSetPreview(src, name) {
  _summImageB64 = src;
  $('summNotePreview').src           = src;
  $('summNotePreview').style.display = 'block';
  $('summCameraPlaceholder').style.display = 'none';
  $('summImageName').textContent     = name || '';
  $('summImageActions').style.display = 'flex';
}
function summClearImage() {
  _summImageB64 = null;
  $('summNotePreview').style.display      = 'none';
  $('summCameraPlaceholder').style.display = 'block';
  $('summImageActions').style.display     = 'none';
  $('summImageName').textContent          = '';
  $('summFileInput').value                = '';
}
function summStopCamera() {
  if (_summStream) { _summStream.getTracks().forEach(t => t.stop()); _summStream = null; }
  $('summCaptureControls').style.display = 'none';
  $('summCameraFeed').srcObject = null;
}

$('summBtnBrowse').addEventListener('click', () => $('summFileInput').click());
$('summFileInput').addEventListener('change', function () {
  const f = this.files[0];
  if (!f || !f.type.startsWith('image/')) return;
  const r = new FileReader();
  r.onload = e => summSetPreview(e.target.result, f.name);
  r.readAsDataURL(f);
});
$('summBtnCamera').addEventListener('click', async () => {
  try {
    _summStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    $('summCameraFeed').srcObject         = _summStream;
    $('summCaptureControls').style.display = 'block';
    $('summCameraPlaceholder').style.display = 'none';
  } catch { showToast('Camera not available. Try uploading a file.', 'err'); }
});
$('summBtnSnap').addEventListener('click', () => {
  const v = $('summCameraFeed'), c = $('summSnapCanvas');
  c.width = v.videoWidth; c.height = v.videoHeight;
  c.getContext('2d').drawImage(v, 0, 0);
  const url = c.toDataURL('image/jpeg', 0.92);
  summStopCamera();
  summSetPreview(url, 'camera-capture.jpg');
});
$('summBtnCancelCam').addEventListener('click', () => {
  summStopCamera();
  $('summCameraPlaceholder').style.display = 'block';
});
$('summBtnClearImage').addEventListener('click', summClearImage);

// Drag & drop
const scz = $('summCameraZone');
scz.addEventListener('dragover', e => { e.preventDefault(); scz.classList.add('drag-over'); });
scz.addEventListener('dragleave', () => scz.classList.remove('drag-over'));
scz.addEventListener('drop', e => {
  e.preventDefault(); scz.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f && f.type.startsWith('image/')) {
    const r = new FileReader();
    r.onload = ev => summSetPreview(ev.target.result, f.name);
    r.readAsDataURL(f);
  }
});

$('btnSummImage').addEventListener('click', async () => {
  if (!_summImageB64) { showToast('Please upload or capture an image.', 'err'); return; }
  const b64 = _summImageB64.split(',')[1];
  await runSummarise({ image_data: b64 }, '📷 Source: Uploaded Image');
});

async function runSummarise(payload, sourceLabel) {
  showLoader('Analysing & summarising…');
  try {
    const d = await postJSON('/summarize', payload);
    $('summResult').textContent = d.summary;
    $('kwResult').innerHTML     = (d.keywords || []).map(k => `<span class="kw">${k}</span>`).join('');
    $('bpResult').innerHTML     = (d.bullet_points || []).map(b => `<li>${b}</li>`).join('');
    $('summSourceBadge').textContent = sourceLabel || '';
    $('summOutput').style.display   = 'block';
    showToast('Summary ready!', 'ok');
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
}

// ════════════════════════════════════════════════════════════════
//  STUDY TIPS
// ════════════════════════════════════════════════════════════════
$('btnTips').addEventListener('click', async () => {
  const subject = $('tipsSubject').value.trim();
  const text    = $('tipsText').value.trim();
  if (!subject && !text) { showToast('Please enter a subject or some text.', 'err'); return; }
  showLoader('Generating tips…');
  try {
    const d = await postJSON('/study_tips', { subject, text });
    $('tipsKw').innerHTML   = (d.keywords || []).map(k => `<span class="kw">${k}</span>`).join('');
    $('tipsList').innerHTML = (d.tips || []).map(t => `<li>${t}</li>`).join('');
    $('tipsOutput').style.display = 'block';
    showToast('Tips ready!', 'ok');
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
});

// ════════════════════════════════════════════════════════════════
//  FEEDBACK  (image upload — no marks)
// ════════════════════════════════════════════════════════════════
let _fbImageB64 = null;
let _fbStream   = null;

function fbSetPreview(src, name) {
  _fbImageB64 = src;
  $('fbPaperPreview').src           = src;
  $('fbPaperPreview').style.display = 'block';
  $('fbCameraPlaceholder').style.display = 'none';
  $('fbImageName').textContent      = name || '';
  $('fbImageActions').style.display = 'flex';
}
function fbClearImage() {
  _fbImageB64 = null;
  $('fbPaperPreview').style.display      = 'none';
  $('fbCameraPlaceholder').style.display = 'block';
  $('fbImageActions').style.display      = 'none';
  $('fbImageName').textContent           = '';
  $('fbFileInput').value                 = '';
}
function fbStopCamera() {
  if (_fbStream) { _fbStream.getTracks().forEach(t => t.stop()); _fbStream = null; }
  $('fbCaptureControls').style.display = 'none';
  $('fbCameraFeed').srcObject = null;
}

$('fbBtnBrowse').addEventListener('click', () => $('fbFileInput').click());
$('fbFileInput').addEventListener('change', function () {
  const f = this.files[0];
  if (!f || !f.type.startsWith('image/')) return;
  const r = new FileReader();
  r.onload = e => fbSetPreview(e.target.result, f.name);
  r.readAsDataURL(f);
});
$('fbBtnCamera').addEventListener('click', async () => {
  try {
    _fbStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    $('fbCameraFeed').srcObject          = _fbStream;
    $('fbCaptureControls').style.display = 'block';
    $('fbCameraPlaceholder').style.display = 'none';
  } catch { showToast('Camera not available. Try uploading a file.', 'err'); }
});
$('fbBtnSnap').addEventListener('click', () => {
  const v = $('fbCameraFeed'), c = $('fbSnapCanvas');
  c.width = v.videoWidth; c.height = v.videoHeight;
  c.getContext('2d').drawImage(v, 0, 0);
  const url = c.toDataURL('image/jpeg', 0.92);
  fbStopCamera();
  fbSetPreview(url, 'question-paper.jpg');
});
$('fbBtnCancelCam').addEventListener('click', () => {
  fbStopCamera();
  $('fbCameraPlaceholder').style.display = 'block';
});
$('fbBtnClearImage').addEventListener('click', fbClearImage);

// Drag & drop feedback zone
const fbcz = $('fbCameraZone');
fbcz.addEventListener('dragover', e => { e.preventDefault(); fbcz.classList.add('drag-over'); });
fbcz.addEventListener('dragleave', () => fbcz.classList.remove('drag-over'));
fbcz.addEventListener('drop', e => {
  e.preventDefault(); fbcz.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f && f.type.startsWith('image/')) {
    const r = new FileReader();
    r.onload = ev => fbSetPreview(ev.target.result, f.name);
    r.readAsDataURL(f);
  }
});

$('btnFb').addEventListener('click', async () => {
  const name    = $('fbName').value.trim() || 'Student';
  const subject = $('fbSubject').value.trim() || 'General';

  if (!_fbImageB64) {
    showToast('Please upload or capture your question paper.', 'err');
    return;
  }

  const b64 = _fbImageB64.split(',')[1];

  showLoader('Analysing your question paper…');
  try {
    const d = await postJSON('/feedback', {
      student_name : name,
      subject,
      image_data   : b64,   // ← image, no marks
    });

    $('fbTitle').textContent   = `Feedback for ${name}`;
    $('fbGreeting').textContent = d.greeting || '';
    $('fbMsg').textContent     = d.message;

    // Strategies / topics to focus
    const wrap = $('fbStrategiesWrap');
    if (d.strategies && d.strategies.length > 0) {
      $('fbStrategies').innerHTML = d.strategies.map(s => `
        <div class="strategy-card">
          <div class="strategy-chapter">📖 ${s.chapter}</div>
          <div class="strategy-body">
            <p>${s.weakness}</p>
            <ul>${(s.tips || []).map(t => `<li>${t}</li>`).join('')}</ul>
          </div>
        </div>`).join('');
      wrap.style.display = 'block';
    } else {
      wrap.style.display = 'none';
    }

    // Next step
    if (d.next_step) {
      $('fbNext').textContent      = d.next_step;
      $('fbNextWrap').style.display = 'block';
    }

    $('fbOutput').style.display = 'block';
    showToast('Feedback ready!', 'ok');
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
});

// ════════════════════════════════════════════════════════════════
//  RESOURCES
// ════════════════════════════════════════════════════════════════
$('btnEda').addEventListener('click', async () => {
  showLoader('Loading chart…');
  try {
    const res  = await fetch('/chart/distribution');
    const text = await res.text();
    if (!text || text.trim() === '' || text.trim().startsWith('<!'))
      throw new Error('Chart unavailable');
    const d = JSON.parse(text);
    if (d.chart_b64) {
      $('edaImg').src = `data:image/png;base64,${d.chart_b64}`;
      $('edaImg').style.display = 'block';
    }
  } catch (e) { showToast(e.message, 'err'); }
  finally { hideLoader(); }
});

$('btnRes').addEventListener('click', async () => {
  const subject = $('resSubject').value.trim();
  if (!subject) { showToast('Please enter a subject.', 'err'); return; }
  showLoader('Finding resources…');
  try {
    const d = await postJSON('/resources', { subject });
    $('resSbjTitle').textContent = `Resources — ${d.subject}`;
    $('resGrid').innerHTML = (d.resources || []).map(r => `
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
