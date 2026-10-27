/* Quiz: one page per lesson. Questions are embedded in the page; the answer
   check compares SHA-256 hashes of option ids, fetched lazily from keys.json.
   No learner data is collected, stored or transmitted. */
const quiz = document.getElementById('quiz');
const dataEl = document.getElementById('quiz-data');

if (quiz && dataEl) {
  const payload = JSON.parse(dataEl.textContent);
  const form = document.getElementById('quiz-form');
  const notice = document.getElementById('quiz-notice');
  const result = document.getElementById('quiz-result');
  const checkBtn = document.getElementById('quiz-check');
  const resetBtn = document.getElementById('quiz-reset');
  const keysUrl = quiz.dataset.keys;
  const total = payload.questions.length;
  let keys = null;
  let submitted = false;

  const toFa = (n) => String(n).replace(/\d/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[+d]);

  async function sha256Hex(text) {
    if (!(window.crypto && crypto.subtle)) throw new Error('insecure-context');
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
  }

  async function getKeys() {
    if (keys) return keys;
    const res = await fetch(keysUrl, { cache: 'force-cache' });
    if (!res.ok) throw new Error('keys ' + res.status);
    keys = await res.json();
    return keys;
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submitted) return;
    const answers = {};
    for (const q of payload.questions) {
      const picked = form.querySelector(`input[name="${CSS.escape(q.id)}"]:checked`);
      if (picked) answers[q.id] = picked.value;
    }
    const missing = payload.questions.filter((q) => !answers[q.id]);
    if (missing.length) {
      notice.textContent = `لطفاً به همهٔ سؤال‌ها پاسخ دهید. ${toFa(missing.length)} پاسخ باقی مانده است.`;
      return;
    }
    notice.textContent = '';
    checkBtn.disabled = true;

    let keyData;
    try {
      keyData = await getKeys();
    } catch {
      notice.textContent = 'دریافت کلید پاسخ ممکن نشد. صفحه را از یک سرور (http یا https) باز کنید و دوباره تلاش کنید.';
      checkBtn.disabled = false;
      return;
    }

    let score = 0;
    for (const q of payload.questions) {
      const entry = keyData[q.id] || {};
      let verdict = null;
      try {
        if (entry.h) verdict = (await sha256Hex(answers[q.id])) === entry.h;
        else if (entry.k) verdict = answers[q.id] === entry.k;
      } catch {
        notice.textContent = 'مرورگر شما اجازهٔ محاسبهٔ امن پاسخ را نداد. صفحه را از http یا https باز کنید.';
        checkBtn.disabled = false;
        return;
      }
      const correct = verdict === true;
      if (correct) score++;

      const field = form.querySelector(`fieldset[data-question="${CSS.escape(q.id)}"]`);
      const pickedId = answers[q.id];
      field.querySelectorAll('label.choice').forEach((label) => {
        const input = label.querySelector('input');
        const isPicked = input.value === pickedId;
        if (correct && isPicked) label.classList.add('correct');
        else if (!correct && isPicked) label.classList.add('wrong');
        input.disabled = true;
      });
      // Reveal which option was right when the answer was wrong: hash comparison
      // cannot name it directly, so find the option whose hash matches.
      if (!correct) {
        for (const o of q.options) {
          let match = false;
          try { match = entry.h ? (await sha256Hex(o.id)) === entry.h : o.id === entry.k; } catch { match = false; }
          if (match) {
            form.querySelector(`fieldset[data-question="${CSS.escape(q.id)}"] label.choice input[value="${CSS.escape(o.id)}"]`)
              ?.closest('label').classList.add('correct');
          }
        }
      }
      const feedback = document.createElement('div');
      feedback.className = 'feedback';
      const verdictText = correct ? 'درست است.' : 'این پاسخ درست نیست.';
      feedback.innerHTML = `<strong>${verdictText}</strong><span></span>`;
      feedback.querySelector('span').textContent = entry.why || '';
      field.append(feedback);
    }

    submitted = true;
    result.textContent = `امتیاز شما: ${toFa(score)} از ${toFa(total)}`;
    resetBtn.hidden = false;
  });

  resetBtn.addEventListener('click', () => window.location.reload());
  resetBtn.hidden = true;
}
