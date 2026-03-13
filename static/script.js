/* ================================================================
   AI Study Pal — script.js
   Updated with:
     1. Study Plan  → Chapters & Topics input
     2. Quiz        → Chapter/Topic, No. of Questions, Per-question Timer
     3. Feedback    → Marks-based score + Chapter improvement strategies
     4. Summarizer  → Camera / image upload + OCR summarisation
================================================================ */

'use strict';

// ── Utility helpers ──────────────────────────────────────────────

const $ = id => document.getElementById(id);

function showToast(msg, type = 'info') {
  const t = $('toast');
  t.textContent = msg;
  t.className = `toast ${type} on`;
  setTimeout(() => t.classList.remove('on'), 3500);
}

function showLoader(msg = 'Processing…') {
  $('ltxt').textContent = msg;
  $('overlay').classList.add('on');
}

function hideLoader() {
  $('overlay').classList.remove('on');
}

async function postJSON(url, body) {
  const res  = await fetch(url, {
    method : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body   : JSON.stringify(body),
  });
  const text = await res.text();
  if (!text || text.trim() === '') throw new Error('Empty response from server');
  let data;
  try { data = JSON.parse(text); }
  catch { throw new Error('Unexpected end of JSON input — check server logs'); }
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

function initPillGroup(groupId, onChange) {
  const group = $(groupId);
  if (!group) return;
  group.querySelectorAll('.pl').forEach(pl => {
    pl.addEventListener('click', () => {
      group.querySelectorAll('.pl').forEach(p => p.classList.remove('active'));
      pl.classList.add('active');
      if (onChange) onChange(pl.dataset.val);
    });
  });
}

function getActivePill(groupId) {
  const active = document.querySelector(`#${groupId} .pl.active`);
  return active ? active.dataset.val : null;
}

// ════════════════════════════════════════════════════════════════
//  1. STUDY PLANNER
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
      chapters,          // ← NEW: chapter list
      hours_per_day: hours,
      exam_date: date,
    });

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

// ════════════════════════════════════════════════════════════════
//  2. QUIZ GENERATOR  (chapter, num questions, timer)
// ════════════════════════════════════════════════════════════════

initPillGroup('quizDiff');
initPillGroup('quizNumQ');
initPillGroup('quizTimer');

// ── Per-question timer state ──────────────────────────────────
let _timerInterval = null;
let _timerSecs     = 0;
let _timerTotal    = 0;
let _currentQIdx   = 0;
let _quizQuestions = [];
let _timerEnabled  = false;

const CIRC = 2 * Math.PI * 18; // svg circle circumference (r=18)

function stopTimer() {
  if (_timerInterval) { clearInterval(_timerInterval); _timerInterval = null; }
}

function startTimerForQuestion(idx) {
  stopTimer();
  if (!_timerEnabled || _timerTotal === 0) return;

  const ring    = $('quizTimerDisplay');
  const countEl = $('timerCount');
  const circle  = $('timerCircle');
  const ringEl  = ring.querySelector('.timer-ring');

  ring.style.display = 'flex';
  ringEl.className   = 'timer-ring';
  _timerSecs         = _timerTotal;
  countEl.textContent = _timerSecs;
  circle.style.strokeDashoffset = 0;

  _timerInterval = setInterval(() => {
    _timerSecs--;
    countEl.textContent = _timerSecs;

    // Shrink the ring arc
    const progress = 1 - (_timerSecs / _timerTotal);
    circle.style.strokeDashoffset = progress * CIRC;

    // Colour warnings
    if (_timerSecs <= _timerTotal * 0.25) {
      ringEl.className = 'timer-ring danger';
    } else if (_timerSecs <= _timerTotal * 0.5) {
      ringEl.className = 'timer-ring warning';
    }

    if (_timerSecs <= 0) {
      stopTimer();
      // Auto-lock unanswered question
      const opts = document.querySelectorAll(`.opt[data-idx="${idx}"]`);
      if (opts.length && !opts[0].closest('.qcard').classList.contains('answered')) {
        opts.forEach(o => {
          o.style.pointerEvents = 'none';
          if (parseInt(o.dataset.opt) === parseInt(o.dataset.correct)) {
            o.classList.add('timed-out');
          }
        });
        $(`ans-${idx}`).classList.add('show');
        const qcard = opts[0].closest('.qcard');
        qcard.classList.add('answered');
        showToast(`⏰ Time's up! Moving on…`, 'info');

        // Auto-advance to next question after 1.5s
        setTimeout(() => {
          const next = idx + 1;
          if (next < _quizQuestions.length) {
            _currentQIdx = next;
            updateProgress();
            startTimerForQuestion(next);
            // Scroll to next question
            const nextCard = document.querySelectorAll('.qcard')[next];
            if (nextCard) nextCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
          } else {
            stopTimer();
            $('quizTimerDisplay').style.display = 'none';
            showToast('Quiz complete!', 'ok');
          }
        }, 1500);
      }
    }
  }, 1000);
}

function updateProgress() {
  const answered = document.querySelectorAll('.qcard.answered').length;
  $('quizProgress').textContent = `${answered} / ${_quizQuestions.length} answered`;
}

function renderQuiz(questions) {
  _quizQuestions = questions;
  _currentQIdx   = 0;
  const container = $('quizResult');
  container.innerHTML = '';

  questions.forEach((q, i) => {
    const card = document.createElement('div');
    card.className = 'qcard';
    card.innerHTML = `
      <div class="qnum">Question ${i + 1} of ${questions.length}</div>
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
      const idx     = parseInt(opt.dataset.idx);
      const chosen  = parseInt(opt.dataset.opt);
      const correct = parseInt(opt.dataset.correct);
      const qcard   = opt.closest('.qcard');
      if (qcard.classList.contains('answered')) return;

      stopTimer();
      qcard.classList.add('answered');
      const group = document.querySelectorAll(`.opt[data-idx="${idx}"]`);
      group.forEach(o => o.style.pointerEvents = 'none');
      opt.classList.add(chosen === correct ? 'correct' : 'wrong');
      if (chosen !== correct) group[correct].classList.add('correct');
      $(`ans-${idx}`).classList.add('show');

      updateProgress();

      // Auto-advance to next if timer mode
      if (_timerEnabled) {
        const next = idx + 1;
        setTimeout(() => {
          if (next < _quizQuestions.length) {
            _currentQIdx = next;
            startTimerForQuestion(next);
            const nextCard = document.querySelectorAll('.qcard')[next];
            if (nextCard) nextCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
          } else {
            $('quizTimerDisplay').style.display = 'none';
            showToast('Quiz complete! 🎉', 'ok');
          }
        }, 800);
      }
    });
  });

  updateProgress();
  $('quizProgress').textContent = `0 / ${questions.length} answered`;
}

$('btnQuiz').addEventListener('click', async () => {
  const topic      = $('quizTopic').value.trim();
  const chapter    = $('quizChapter').value.trim();   // ← NEW
  const difficulty = getActivePill('quizDiff') || 'medium';
  const numQ       = parseInt(getActivePill('quizNumQ') || '10'); // ← NEW
  const timerSecs  = parseInt(getActivePill('quizTimer') || '30'); // ← NEW

  if (!topic) { showToast('Please enter a topic.', 'err'); return; }

  stopTimer();
  _timerEnabled = timerSecs > 0;
  _timerTotal   = timerSecs;

  showLoader('Generating quiz questions…');
  try {
    const d = await postJSON('/generate_quiz', {
      topic,
      chapter,                    // ← NEW
      difficulty,
      num_questions: numQ,        // ← NEW
    });

    $('quizSbjTitle').textContent = `Quiz — ${d.subject}${chapter ? ' · ' + chapter : ''}`;
    renderQuiz(d.questions);
    $('quizMNote').textContent = `Model: ${d.model_used}`;
    $('quizOutput').style.display = 'block';

    if (d.chart_b64) {
      $('qChart').src = `data:image/png;base64,${d.chart_b64}`;
      $('qChartWrap').style.display = 'block';
    }

    // Start timer for question 0
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
  document.querySelectorAll('.ans-reveal').forEach(el => el.classList.add('show'));
  document.querySelectorAll('.opt').forEach(opt => {
    opt.style.pointerEvents = 'none';
    const qcard = opt.closest('.qcard');
    if (!qcard.classList.contains('answered')) {
      qcard.classList.add('answered');
      if (parseInt(opt.dataset.opt) === parseInt(opt.dataset.correct)) {
        opt.classList.add('correct');
      }
    }
  });
  $('quizTimerDisplay').style.display = 'none';
  updateProgress();
});

// ════════════════════════════════════════════════════════════════
//  3. TEXT SUMMARIZER  (text tab + image/camera tab)
// ════════════════════════════════════════════════════════════════

// ── Tab switching ──────────────────────────────────────────────
document.querySelectorAll('.itab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.itab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const isText = tab.dataset.tab === 'text';
    $('panelText').style.display  = isText ? 'block' : 'none';
    $('panelImage').style.display = isText ? 'none'  : 'block';
  });
});

// ── Character counter ──────────────────────────────────────────
$('summText').addEventListener('input', function () {
  $('charCount').textContent = `${this.value.length} characters`;
});

// ── Text summarise ─────────────────────────────────────────────
$('btnSumm').addEventListener('click', async () => {
  const text = $('summText').value.trim();
  if (text.length < 50) { showToast('Please enter at least 50 characters.', 'err'); return; }
  await runSummarise({ text });
});

// ── Image upload / camera state ────────────────────────────────
let _capturedImageB64 = null;
let _cameraStream     = null;

function setImagePreview(src, name) {
  _capturedImageB64 = src;
  $('notePreview').src           = src;
  $('notePreview').style.display = 'block';
  $('cameraPlaceholder').style.display = 'none';
  $('imageName').textContent     = name || '';
  $('imageActions').style.display = 'flex';
}

function clearImage() {
  _capturedImageB64 = null;
  $('notePreview').style.display      = 'none';
  $('cameraPlaceholder').style.display = 'block';
  $('imageActions').style.display     = 'none';
  $('imageName').textContent          = '';
  $('fileInput').value                = '';
}

// Browse file
$('btnBrowse').addEventListener('click', () => $('fileInput').click());
$('fileInput').addEventListener('change', function () {
  const file = this.files[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) { showToast('Please select an image file.', 'err'); return; }
  const reader = new FileReader();
  reader.onload = e => setImagePreview(e.target.result, file.name);
  reader.readAsDataURL(file);
});

// Drag & drop
const cz = $('cameraZone');
cz.addEventListener('dragover', e => { e.preventDefault(); cz.classList.add('drag-over'); });
cz.addEventListener('dragleave', () => cz.classList.remove('drag-over'));
cz.addEventListener('drop', e => {
  e.preventDefault();
  cz.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) {
    const reader = new FileReader();
    reader.onload = ev => setImagePreview(ev.target.result, file.name);
    reader.readAsDataURL(file);
  }
});

// Camera
$('btnCamera').addEventListener('click', async () => {
  try {
    _cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    $('cameraFeed').srcObject      = _cameraStream;
    $('captureControls').style.display = 'block';
    $('cameraPlaceholder').style.display = 'none';
  } catch {
    showToast('Camera not available. Try uploading a file instead.', 'err');
  }
});

$('btnSnap').addEventListener('click', () => {
  const video  = $('cameraFeed');
  const canvas = $('snapCanvas');
  canvas.width  = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
  stopCamera();
  setImagePreview(dataUrl, 'camera-capture.jpg');
});

$('btnCancelCam').addEventListener('click', () => {
  stopCamera();
  $('cameraPlaceholder').style.display = 'block';
});

function stopCamera() {
  if (_cameraStream) { _cameraStream.getTracks().forEach(t => t.stop()); _cameraStream = null; }
  $('captureControls').style.display = 'none';
  $('cameraFeed').srcObject = null;
}

$('btnClearImage').addEventListener('click', clearImage);

// Summarise from image
$('btnSummImage').addEventListener('click', async () => {
  if (!_capturedImageB64) { showToast('Please upload or capture an image of your notes.', 'err'); return; }
  // Strip the data:image/...;base64, prefix → send pure base64
  const b64 = _capturedImageB64.split(',')[1];
  await runSummarise({ image_data: b64 });
});

// ── Shared summarise logic ─────────────────────────────────────
async function runSummarise(payload) {
  showLoader('Analysing & summarising…');
  try {
    const d = await postJSON('/summarize', payload);
    $('summResult').textContent = d.summary;

    $('kwResult').innerHTML = (d.keywords || [])
      .map(k => `<span class="kw">${k}</span>`).join('');

    $('bpResult').innerHTML = (d.bullet_points || [])
      .map(b => `<li>${b}</li>`).join('');

    $('summMNote').textContent = `Model: ${d.model_used}`;
    $('summSourceBadge').textContent = payload.image_data
      ? '📷 Source: Uploaded / Captured Notes Image'
      : '✏️ Source: Pasted Text';
    $('summOutput').style.display = 'block';
    showToast('Summary ready!', 'ok');
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
}

// ════════════════════════════════════════════════════════════════
//  4. STUDY TIPS
// ════════════════════════════════════════════════════════════════

$('btnTips').addEventListener('click', async () => {
  const subject = $('tipsSubject').value.trim();
  const text    = $('tipsText').value.trim();
  if (!subject && !text) { showToast('Please enter a subject or some text.', 'err'); return; }

  showLoader('Extracting tips with NLTK…');
  try {
    const d = await postJSON('/study_tips', { subject, text });

    $('tipsKw').innerHTML = (d.keywords || [])
      .map(k => `<span class="kw">${k}</span>`).join('');

    $('tipsList').innerHTML = (d.tips || []).map(t => `<li>${t}</li>`).join('');

    $('tipsOutput').style.display = 'block';
    showToast('Tips generated!', 'ok');
  } catch (e) {
    showToast(e.message, 'err');
  } finally {
    hideLoader();
  }
});

// ════════════════════════════════════════════════════════════════
//  5. FEEDBACK  (marks-based score + chapter strategies)
// ════════════════════════════════════════════════════════════════

function calcPct() {
  const obtained = parseFloat($('fbScoreObtained').value);
  const total    = parseFloat($('fbScoreTotal').value);
  if (!isNaN(obtained) && !isNaN(total) && total > 0) {
    const pct = Math.round((obtained / total) * 100);
    $('fbScorePct').textContent = `${pct}%`;
    return pct;
  }
  $('fbScorePct').textContent = '—';
  return null;
}

$('fbScoreObtained').addEventListener('input', calcPct);
$('fbScoreTotal').addEventListener('input', calcPct);

$('btnFb').addEventListener('click', async () => {
  const student_name = $('fbName').value.trim() || 'Student';
  const subject      = $('fbSubject').value.trim() || 'General';
  const obtained     = parseFloat($('fbScoreObtained').value);
  const total        = parseFloat($('fbScoreTotal').value);
  const chapter      = $('fbChapter').value.trim();  // ← NEW

  if (isNaN(obtained) || isNaN(total) || total <= 0) {
    showToast('Please enter valid score and total marks.', 'err');
    return;
  }
  const quiz_score = Math.round((obtained / total) * 100);

  showLoader('Generating personalised feedback…');
  try {
    const d = await postJSON('/feedback', {
      student_name,
      subject,
      quiz_score,
      score_obtained: obtained,   // ← NEW: raw marks
      score_total   : total,      // ← NEW: total marks
      chapter_topic : chapter,    // ← NEW: chapter focus
    });

    // Score display
    $('scoreNum').textContent  = `${obtained}`;
    $('scoreDenom').textContent = `/${total}`;
    $('scorePctBadge').textContent = `${quiz_score}%`;

    const ring = $('scoreRing');
    ring.style.borderColor = quiz_score >= 75
      ? 'var(--green)' : quiz_score >= 50
      ? 'var(--gold)'  : 'var(--red)';
    ring.style.boxShadow = quiz_score >= 75
      ? '0 0 20px var(--green)' : quiz_score >= 50
      ? '0 0 20px var(--gold-glow)' : '0 0 20px rgba(248,113,113,.4)';

    $('fbMsg').textContent  = d.message;
    $('fbNext').textContent = d.next_step;
    $('fbMNote').textContent = `Model: ${d.model_used}`;

    // ← NEW: Chapter improvement strategies
    const strategiesWrap = $('fbStrategiesWrap');
    const strategiesEl   = $('fbStrategies');

    if (d.strategies && d.strategies.length > 0) {
      strategiesEl.innerHTML = d.strategies.map(s => `
        <div class="strategy-card">
          <div class="strategy-chapter">📖 ${s.chapter}</div>
          <div class="strategy-body">
            <p>${s.weakness}</p>
            <ul>${s.tips.map(t => `<li>${t}</li>`).join('')}</ul>
          </div>
        </div>`).join('');
      strategiesWrap.style.display = 'block';
    } else {
      strategiesWrap.style.display = 'none';
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
//  6. RESOURCES
// ════════════════════════════════════════════════════════════════

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
