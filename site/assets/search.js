/* Home-page search and filtering.
   The lesson list is prerendered, so search works without this file (text-only,
   titles/categories). With it, filtering is instant and explanation text is
   searched too, using a lazily fetched index. */
import { normalize, terms } from './normalize.js';

const list = document.getElementById('lessons');
if (list) {
  const search = document.getElementById('search');
  const moduleInput = document.getElementById('module');
  const levelInput = document.getElementById('level');
  const count = document.getElementById('count');
  const cards = [...list.querySelectorAll('.card')];
  let deep = null;          // slug -> haystack, from index.json
  let deepPending = false;

  async function loadDeep() {
    if (deep || deepPending) return;
    deepPending = true;
    try {
      const res = await fetch('data/index.json', { cache: 'force-cache' });
      if (!res.ok) throw new Error(res.status);
      const index = await res.json();
      deep = new Map(index.map((r) => [r.s, r.hay]));
      apply();
    } catch {
      deepPending = false;   // stay text-only; search still works
    }
  }

  function apply() {
    const q = normalize(search.value);
    const parts = terms(q);
    const mod = moduleInput.value;
    const lvl = levelInput.value;
    let shown = 0;
    for (const card of cards) {
      if (mod && card.dataset.module !== mod) { card.hidden = true; continue; }
      if (lvl && card.dataset.level !== lvl) { card.hidden = true; continue; }
      if (parts.length) {
        const slug = card.querySelector('a').getAttribute('href').replace(/^.*lesson\//, '').replace(/\/$/, '');
        const hay = (deep && deep.get(slug)) || card.dataset.hay || '';
        if (!parts.every((t) => hay.includes(t))) { card.hidden = true; continue; }
      }
      card.hidden = false;
      shown++;
    }
    if (shown === 0) {
      count.textContent = 'درسی با این فیلتر پیدا نشد — واژهٔ کوتاه‌تر یا سطح دیگری را امتحان کنید.';
    } else if (shown === cards.length) {
      count.textContent = `نمایش همهٔ ${toFa(cards.length)} درس`;
    } else {
      count.textContent = `نمایش ${toFa(shown)} درس از ${toFa(cards.length)} درس`;
    }
  }

  function toFa(n) { return String(n).replace(/\d/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[+d]); }

  let timer;
  search.addEventListener('input', () => {
    apply();
    if (search.value.trim()) { clearTimeout(timer); timer = setTimeout(loadDeep, 120); }
  });
  moduleInput.addEventListener('change', apply);
  levelInput.addEventListener('change', apply);
  apply();
}
