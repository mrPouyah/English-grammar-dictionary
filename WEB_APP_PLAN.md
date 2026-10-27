# English Grammar App — static web conversion plan (GitHub Pages, free)

Design document only. **No implementation has been started.** Status of this document: proposed, awaiting approval.

Everything marked *(measured)* was verified by reading this project's own databases and files. Everything marked *(documented)* comes from GitHub's own documentation. Anything unverified says so.

---

## 0. Executive summary

The valuable half of this project — 228 bilingual lessons, 1140 quiz questions, 3420 options, 1140 answer keys, 228 expanded-lesson documents, the CEFR mapping, and the CC0 licensing metadata — lives in a SQLite database and a **Telegram-independent** Python module (`course_repository.py`). It converts to a static web app cleanly.

The Telegram layer (`telegram_bot.py` 492 LOC, `teacher_access.py` 226 LOC, transport/secrets) is **not** ported. It is replaced by static pages plus a small JavaScript grader.

**The one hard constraint:** GitHub Pages is a *static* host *(documented)*. It runs no server code. Therefore:

| Existing feature | On GitHub Pages |
|---|---|
| Lesson reading, browsing by level, bilingual search | ✅ Works, better than the bot |
| 5-question quiz with Persian explanations | ✅ Works, graded in the browser |
| Real login / teacher approval / student monitoring / activity reports | ❌ **Impossible** |
| Secret answer keys | ❌ **Impossible** (everything published is public) |

A repository owned by a free account must be **public** for Pages to work *(documented: "If the account that owns the repository uses GitHub Free... the repository must be public")*, and Actions is free for public repositories *(documented)*.

If teacher approval and student monitoring are non-negotiable, stop here and read §9 (backend path) instead — a static host cannot deliver them, and no amount of clever JavaScript changes that.

---

## 1. Decisions to make before Phase 1

### D1 — What happens to the answer keys?

On a static host the grader runs in the student's browser, so the student's browser must know the answer. There is no way around this.

| | Approach | Effect |
|---|---|---|
| **K1** | Publish keys in plain JSON | Simplest. Honest. Anyone can open devtools and read all 1140 answers. |
| **K2** | Publish **SHA-256 hash** of the correct option id; grade by hashing the click | Casual reading of source reveals nothing. Trivial to brute-force (3 options per question), so this is **deterrence, not security**. ~10 lines of code. |
| **K3** | Publish no keys; quiz becomes self-assessment ("reveal answer") | No scores at all. |
| **K4** | Real server-side grading | **Not possible on GitHub Pages.** See §9. |

**Recommendation: K2**, with a visible note on the site and in the README that it deters casual peeking and is not a security boundary. It costs almost nothing and matches this project's own stated intent — `course_metadata.grading` currently reads *"full answer key is server-side data for future apps"* *(measured)*. Do not let K2 create a false sense that the quiz result means anything; it does not.

### D2 — Separate repository, or push the existing one?

**A brand-new public repository. Never publish the current bot repository.**

The current folder contains, all confirmed present *(measured)*:

- `.telegram_runtime/token.dpapi` — the encrypted bot token
- `.telegram_runtime/teacher.dpapi` — the encrypted teacher admin configuration
- `.telegram_runtime/state.sqlite3` — **real student data**: user ids, display names, access requests, activity events, quiz results
- `.telegram_runtime/docker/state.seed.sqlite3`
- `english_grammar.sqlite3` (31 MB) and `english_grammar_fa.sqlite3` (38 MB)
- `.backups/full-rollout-files-20261017/`

`.gitignore` does exclude the runtime directory, so a plain `git push` would not upload it — but the working folder also holds the databases and backups, and one careless `git add -f` on a public repo leaks a teacher config and student records permanently. Keep the content private repository slightly renamed if you like (e.g. `english-grammar-bot`); create a separate **`english-grammar-web`** public repository that contains **only exported artifacts and site code**. The 38 MB SQLite never enters the public repo.

### D3 — Which parts of the content ship?

| Set | Raw size *(measured)* | Ship it? |
|---|---|---|
| 228 bilingual lessons (core fields) | 524 KB | ✅ Always |
| 228 expanded-lesson JSON documents | 1.46 MB | ✅ Always |
| 1140 exercises + 3420 options | 425 KB | ✅ Always |
| 1824 English examples | 84 KB | ✅ Always |
| 1824 bilingual examples (EN/FA/note) | 406 KB | ✅ Always |
| 1140 answer keys + explanations | 127 KB | ✅ Per D1 |
| CEFR mapping + 22 modules | 5 KB | ✅ Always |
| 223 topic→source references | 28 KB | ✅ Always (attribution) |
| English library: 228 topics | 55 KB | ✅ Optional, Phase 7 |
| English library: 1085 reference links | small | ✅ Optional, Phase 7 |
| English library: 4239 passages / 150 documents | **10.2 MB** | ⚠️ Lazy-load per document, Phase 7 only |
| Raw SQLite databases | 69 MB | ❌ Never |

**Total course payload ≈ 3.2 MB raw, ~600 KB gzipped over the wire** *(measured: the existing `farsi_course.public.json` is 4.25 MB and gzips to 594 KB)*.

### D4 — Tech stack

| Concern | Choice | Why |
|---|---|---|
| Hosting | GitHub Pages, deployed by a GitHub Actions workflow | Free; Actions workflow removes the 10-builds/hour cap *(documented)* |
| Runtime | Static HTML + CSS + **vanilla JS ES modules** | Content is static; 228 pages need no framework. Zero npm runtime dependencies = zero supply chain risk on a public site. |
| Build | **Python 3** (`tools/*.py`) | Already the project's language; already installed; needs no Node |
| Templating | Python `str.replace` on a template, like the existing `farsi_course_template.html` / `browser_template.html` | Matches the proven pattern in this repo |
| Search | Prebuilt inverted index in JSON + scoring in the browser, reusing this project's exact Persian normalization | Same behaviour as the bot's search |
| Quiz grading | `assets/quiz.js`, mirroring `CourseRepository.grade()` | The authoritative grader already exists and is tested |
| Offline | Service worker + web app manifest (PWA) | Optional, Phase 6 |
| Analytics | None | Keeps the site honest about not tracking learners |

**Rejected: `sql.js` / SQLite-in-the-browser.** It would mean downloading the 38 MB database to every visitor. At GitHub's 100 GB/month soft bandwidth limit *(documented)* that is roughly **2,600 visits/month**; the per-lesson JSON model is roughly **30 KB per lesson view, or tens of thousands of visits**. *(I attempted to verify sql.js's exact asset sizes and the network calls failed — but this design does not need it, so the unverified number does not affect the plan.)*

**Rejected: React/Vite/Next.** A build chain, a `node_modules` tree, and a framework upgrade treadmill in exchange for rendering 228 static documents. Not justified.

---

## 2. Database structure

### 2.1 Source of truth stays SQLite

`english_grammar_fa.sqlite3` remains the authoring database. A build step exports it to JSON. This means: you keep editing content the way you already do, and the website is a build artifact — exactly the pattern already used by `build_farsi_course.py` → `farsi_course.public.json`.

### 2.2 Verified schema (fields confirmed by `PRAGMA table_info`, *(measured)*)

```
course_modules          id, slug, title_en, title_fa, display_order            (22 rows)
course_lessons          topic_id, slug, module_id, title_en, title_fa, language,
                        level_hint, level_fa, course_order, objective_fa,
                        explanation_fa, pattern_en, common_mistake_fa,
                        review_status, content_version, updated_at             (228 rows)
course_lesson_expansions  lesson_id, document_json                            (228 rows)
course_exercises        id, lesson_id, ordinal, type, prompt_fa, stem_en,
                        points                                                (1140 rows)
course_exercise_options id, exercise_id, position, text_en                    (3420 rows)
course_examples         id, lesson_id, ordinal, text_en                       (1824 rows)
course_bilingual_examples  lesson_id, ordinal, text_en, text_fa, note_fa      (1824 rows)
course_answer_keys      exercise_id, correct_option_id, explanation_fa        (1140 rows)
course_cefr_levels      topic_id, cefr_level, menu_group,
                        classification_version, status                        (228 rows)
course_metadata         key, value                                            (12 rows)

view course_lesson_catalog = course_lessons + module_en, module_fa, exercise_count

topics                  id, category, title, level_hint, explanation, example,
                        wiki_topic, review_status                              (228 rows)
sources                 id, title, url, publisher, authors, license, license_url,
                        retrieved_at, revision, revision_timestamp, history_url,
                        kind, usage_note, snapshot_path, sha256               (150 rows)
topic_sources           topic_id, source_id, relationship                     (223 rows)
reference_links         id, title, url, publisher, discovered_from,
                        retrieved_at, content_stored                          (1085 rows)
documents               id, source_id, title, text, word_count, historical    (150 rows)
passages                id, document_id, ordinal, text                        (4239 rows)
metadata, import_events, topic_search / passage_search / course_search (FTS5)
```

### 2.3 Expansion JSON document shape

`course_lesson_expansions.document_json` is nested JSON. Shape inferred from `lesson_sections.py` and `farsi_course_template.html` *(measured by reading both)*:

```json
{
  "explanation_fa": "...",
  "patterns":           [{"label_fa","pattern_en","example_en","translation_fa"}],
  "teaching_pages":     [{"title_fa","body_fa","use_explanation","include_patterns"}],
  "examples":           [{"ordinal","text_en","text_fa","note_fa"}],
  "mistakes":           [{"incorrect_en","correct_en","reason_fa"}],
  "comparisons":        [{"title_fa","items":[{"text_en","text_fa"}],"note_fa"}],
  "sources":            [{"title","url","license"}]
}
```

Note: `expansions.examples` and `course_bilingual_examples` cover the same ground. Ship the expansion when present, fall back to the flat tables otherwise — that is already the logic in `farsi_course_template.html`.

### 2.4 Published data files (the "web database")

```
site/data/
  manifest.json             schema/content version, counts, build time, license
  courses.json              22 modules + level→lesson-slug grouping (B1,B2,C1,C2,review)
  index.json                search index: one compact record per lesson
  lessons/<slug>.json       228 files, avg 13.6 KB, max 19.8 KB *(measured)*
  keys.json                 1140 entries: exercise id → sha256(correct option id)
                             + explanation_fa                      (per D1 = K2)
  library/topics.json       Phase 7
  library/links.json        Phase 7
  library/docs/<id>.json    Phase 7, lazy per document
```

`lessons/<slug>.json` shape:

```json
{
  "topic_id": 1, "slug": "parts-of-speech", "course_order": 1,
  "title_en": "Parts of speech", "title_fa": "اجزای کلام",
  "module_id": 3, "module_en": "Foundations", "module_fa": "مبانی جمله و واژه",
  "level_hint": "Beginner", "level_fa": "مقدماتی",
  "cefr_level": "A1", "menu_group": "review",
  "objective_fa": "...", "explanation_fa": "...",
  "pattern_en": "...", "common_mistake_fa": "...",
  "review_status": "draft", "content_version": "fa-course-1",
  "examples_en": ["..."],
  "expanded": { "...per 2.3, or null..." },
  "sources": [{"title":"...","url":"...","license":"..."}],
  "exercises": [
    { "id": "fa-l001-q1", "ordinal": 1, "prompt_fa": "...", "stem_en": "...",
      "points": 1,
      "options": [{"id":"fa-l001-q1-8f0a2cdf0f","position":1,"text_en":"..."}] }
  ]
}
```

`keys.json` (K2 form) — the explanation stays readable, the answer does not:

```json
{ "fa-l001-q1": { "h": "9f2c…sha256 of the correct option id…", "why": "واژهٔ cook عملِ فاعل را بیان می‌کند، پس فعل است." } }
```

### 2.5 Search index

`index.json` carries one record per lesson: `slug`, `title_en`, `title_fa`, `level`, `module_fa`, plus a normalized `hay` string built from title + explanation + common mistake + pattern. Filtering 228 records in memory is instant; the existing `farsi_course.html` already does exactly this and works. If it ever feels slow, add a term→slug inverted index as a Phase 3 optimization — do not do it up front.

**Normalization must be copied exactly** from `telegram_bot.py`'s `normalized()` (NFKC → lowercase → `ي/ى→ی`, `ك→ک`, ZWNJ→space, strip combining marks) so that Persian search behaves identically to the bot.

---

## 3. Site architecture

```
english-grammar-web/                  PUBLIC repo
├─ .github/workflows/pages.yml        build + deploy
├─ site/                              ← the artifact that gets published
│  ├─ index.html                      home: levels, search box, lesson list
│  ├─ level/B1/index.html             4 level pages + review/A1-A2
│  ├─ lesson/<slug>/index.html         228 prerendered pages
│  ├─ quiz.html                        quiz shell, hydrates from data
│  ├─ about/index.html                 license, attribution, "how grading works"
│  ├─ 404.html
│  ├─ assets/app.css, app.js, quiz.js, normalize.js, search.js
│  ├─ assets/icons/…, manifest.webmanifest, sw.js
│  └─ data/…                          (section 2.4)
├─ tools/
│  ├─ export_web_data.py              SQLite → JSON + key hashing + counters
│  ├─ render_pages.py                 JSON → prerendered HTML
│  ├─ check_site.py                    integrity + link + size gate
│  └─ templates/{base,lesson,level}.html
├─ tests/
│  ├─ test_export.py                  counts and shape
│  └─ test_grade_parity.py            JS grader == SQLite grader
├─ README.md  LICENSE  ATTRIBUTION.md
```

**Why prerender 228 HTML pages instead of one JS app:** content is static, so lesson text works with JavaScript disabled, loads in one round-trip, and is linkable/shareable (`…/lesson/present-perfect/`). JavaScript is needed only for the quiz. This is strictly better than the existing 6.6 MB monolithic `farsi_course.html` *(measured)*.

**RTL and typography:** reuse the design language of `farsi_course_template.html` — `dir="rtl"`, Tahoma/Segoe UI stack, English examples set `direction:ltr`, Persian numerals via `Intl.NumberFormat('fa-IR')`. Do not redesign from scratch; that template already works and is already Persian-correct.

### Bandwidth budget *(documented limit: 100 GB/month soft)*

| Model | Per visit | Visits before the soft limit |
|---|---|---|
| Per-lesson JSON + HTML (recommended) | ~30 KB | tens of thousands |
| Existing monolithic `farsi_course.html` | 6.6 MB | ~15,000 |
| Raw SQLite via `sql.js` | 38 MB | ~2,600 |

---

## 4. Phase-by-phase plan

Each phase is a milestone: I stop at the end, report, and wait for your approval before the next.

### Phase 0 — Repository separation (small, do this first)
1. Create public repo `english-grammar-web`.
2. `git init` fresh inside a new empty folder. **Do not** clone or copy the bot repo's history.
3. Add `LICENSE` (CC0 1.0 for the original course text, matching `course_metadata.license`) and `ATTRIBUTION.md`.
4. `.gitignore` the exporter's inputs so a database never lands in the public repo: `*.sqlite3`, `*.dpapi`, `.telegram_runtime/`, `*.backup`.

**Acceptance:** repo exists, is public, contains no `.sqlite3`, no `.dpapi`, no runtime state. Verify with `git ls-files | grep -Ei 'sqlite|dpapi'` → empty.
**Recovery:** nothing irreversible; delete the repo.

### Phase 1 — Exporter
`tools/export_web_data.py` — opens the DB read-only (`mode=ro`, the same URI trick `CourseRepository` uses), writes `site/data/`, hashes the keys, and prints counters.

Skeleton (adapt freely; it mirrors `course_repository.py`'s proven access pattern):

```python
#!/usr/bin/env python3
"""Export english_grammar_fa.sqlite3 into static JSON for the web app."""
from __future__ import annotations
import argparse, hashlib, json, sqlite3, datetime as dt
from pathlib import Path

def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=Path("english_grammar_fa.sqlite3"))
    ap.add_argument("--out", type=Path, default=Path("site/data"))
    ap.add_argument("--plaintext-keys", action="store_true",
                    help="D1=K1: write correct option ids instead of SHA-256 hashes")
    args = ap.parse_args()

    db = connect(args.db)
    (args.out / "lessons").mkdir(parents=True, exist_ok=True)

    modules = [dict(r) for r in db.execute(
        "SELECT id,slug,title_en,title_fa,display_order FROM course_modules ORDER BY display_order")]
    levels = {r["topic_id"]: dict(r) for r in db.execute(
        "SELECT topic_id,cefr_level,menu_group FROM course_cefr_levels")}

    lessons = [dict(r) for r in db.execute("SELECT * FROM course_lesson_catalog ORDER BY course_order")]
    lessons_by_id = {l["topic_id"]: l for l in lessons}

    def group(lesson_id: int, *sql_args) -> list[dict]:
        rows = db.execute(*sql_args).fetchall()
        return [dict(r) for r in rows]

    examples = {}
    for r in db.execute("SELECT lesson_id,ordinal,text_en FROM course_examples ORDER BY lesson_id,ordinal"):
        examples.setdefault(r["lesson_id"], []).append(r["text_en"])

    expansions = {r["lesson_id"]: json.loads(r["document_json"])
                  for r in db.execute("SELECT lesson_id,document_json FROM course_lesson_expansions")}

    sources = {}
    for r in db.execute("""SELECT ts.topic_id, s.title, s.url, s.license
                           FROM topic_sources ts JOIN sources s ON s.id = ts.source_id"""):
        sources.setdefault(r["topic_id"], []).append(
            {"title": r["title"], "url": r["url"], "license": r["license"]})

    exercises, keys, counts = {}, {}, {"lessons": 0, "exercises": 0, "options": 0, "keys": 0}
    for row in db.execute("""SELECT * FROM course_exercises
                             ORDER BY lesson_id, ordinal"""):
        q = dict(row)
        opts = [dict(r) for r in db.execute(
            """SELECT id,position,text_en FROM course_exercise_options
               WHERE exercise_id=? ORDER BY position""", (q["id"],))]
        q["options"] = opts
        exercises.setdefault(q["lesson_id"], []).append(q)
        counts["exercises"] += 1
        counts["options"] += len(opts)

    for r in db.execute("SELECT exercise_id,correct_option_id,explanation_fa FROM course_answer_keys"):
        key = r["correct_option_id"]
        keys[r["exercise_id"]] = {
            "h": hashlib.sha256(key.encode("utf-8")).hexdigest(),
            "why": r["explanation_fa"],
        }
        counts["keys"] += 1

    counts["lessons"] = len(lessons)

    # --- integrity gate: refuse to publish a partial course -------------------
    expected = {"lessons": 228, "exercises": 1140, "options": 3420, "keys": 1140}
    if counts != expected:
        raise SystemExit(f"Export aborted, counts differ from expectations:\n got {counts}\n want {expected}")

    # --- per-lesson files ----------------------------------------------------
    for l in lessons:
        lid = l["topic_id"]
        lv = levels.get(lid, {})
        doc = {
            "topic_id": lid, "slug": l["slug"], "course_order": l["course_order"],
            "title_en": l["title_en"], "title_fa": l["title_fa"],
            "module_id": l["module_id"], "module_en": l["module_en"], "module_fa": l["module_fa"],
            "level_hint": l["level_hint"], "level_fa": l["level_fa"],
            "cefr_level": lv.get("cefr_level"), "menu_group": lv.get("menu_group"),
            "objective_fa": l["objective_fa"], "explanation_fa": l["explanation_fa"],
            "pattern_en": l["pattern_en"], "common_mistake_fa": l["common_mistake_fa"],
            "review_status": l["review_status"], "content_version": l["content_version"],
            "examples_en": examples.get(lid, []),
            "expanded": expansions.get(lid),
            "sources": sources.get(lid, []),
            "exercises": exercises.get(lid, []),
        }
        (args.out / "lessons" / f"{l['slug']}.json").write_text(
            json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # --- index / courses / manifest -----------------------------------------
    def normalize(text: str) -> str:
        import unicodedata
        text = unicodedata.normalize("NFKC", text).lower()
        text = text.translate(str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "\u200c": " ", "ـ": ""}))
        return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())

    index = []
    for l in lessons:
        lid = l["topic_id"]
        index.append({
            "s": l["slug"], "e": l["title_en"], "f": l["title_fa"],
            "lvl": levels.get(lid, {}).get("cefr_level"),
            "mod": l["module_fa"], "o": l["course_order"],
            "hay": normalize(" ".join([l["title_en"], l["title_fa"], l["explanation_fa"],
                                       l["common_mistake_fa"], l["pattern_en"]])),
        })
    (args.out / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    groups: dict[str, list[str]] = {}
    for l in lessons:
        g = levels.get(l["topic_id"], {}).get("menu_group") or l["level_hint"]
        groups.setdefault(g, []).append(l["slug"])
    (args.out / "courses.json").write_text(json.dumps(
        {"modules": modules, "groups": groups}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    (args.out / "keys.json").write_text(
        json.dumps(keys, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    meta = dict(db.execute("SELECT key,value FROM course_metadata"))
    (args.out / "manifest.json").write_text(json.dumps({
        "schema_version": 1, "content_version": meta.get("content_version"),
        "license": meta.get("license"), "review_status": meta.get("review_status"),
        "grading": "sha256(option id), client-side, deterrence only" if not args.plaintext_keys else "plaintext",
        "counts": counts, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(counts, ensure_ascii=True))
    db.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

**Acceptance:** run it; it prints `{"lessons": 228, "exercises": 1140, "options": 3420, "keys": 1140}`; the same numbers survive a manual `sqlite3` count; total `site/data` ≈ 3.2 MB; `keys.json` contains no `correct_option_id` strings (grep it).
**Recovery:** `rm -rf site/data`, re-run. The database is opened read-only, so the source cannot be damaged.

### Phase 2 — Shell and prerendered pages
`tools/render_pages.py` builds `index.html`, the level pages, and 228 lesson pages from `templates/`. The lesson template renders tags, title, explanation, patterns, bilingual examples, common mistakes, comparisons, and sources — the same order as `farsi_course_template.html`'s `renderExpanded()`, so the content reads the way you already approved.

**Acceptance:** local `python -m http.server` shows the home page, every level, and any lesson; `check_site.py` finds 228 lesson pages; visibly correct RTL and LTR-mixed typography in a browser.
**Recovery:** regenerate; pages are derived files.

### Phase 3 — Search
`assets/search.js` loads `index.json` once, normalizes the query with the copied rules, and ranks: exact title → title contains → all terms in title → all terms in `hay`. Same ladder as `Catalog.search()` in `telegram_bot.py`, so results feel familiar.

**Acceptance:** searching `present perfect` and `حال کامل` both find the expected lessons; Arabic `ي`/`ك` spellings and ZWNJ variants match; results link to the right pages.

### Phase 4 — Quiz
`assets/quiz.js` renders one question at a time from the lesson JSON, and on submit hashes the chosen option id with `crypto.subtle.digest('SHA-256', …)` and compares against `keys.json`. Feedback shows the correct choice and `explanation_fa`, exactly like the bot's `feedback_view`. Score out of 5. Progress kept in `localStorage` only — **no learner data leaves the browser, and none is collected.**
A `tests/test_grade_parity.py`-style test must prove the JS grader and SQLite's `CourseRepository.grade()` agree on all 1140 questions.

**Acceptance:** correct and incorrect full runs for a sample of lessons produce the same scores as `CourseRepository.grade()`; a brute-force check confirms hashing reveals no answer in the shipped files; `localStorage` is the only storage used.
**Recovery:** remove the quiz link; lessons still work.

### Phase 5 — Deploy to GitHub Pages
```yaml
# .github/workflows/pages.yml
name: Deploy site to GitHub Pages
on:
  push: { branches: [main] }
  workflow_dispatch:
permissions: { contents: read, pages: write, id-token: write }
concurrency: { group: pages, cancel-in-progress: true }
jobs:
  build-deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - name: Verify the exported data is present and complete
        run: python tools/check_site.py --site site --expect-lessons 228
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with: { path: site }
      - id: deploy
        uses: actions/deploy-pages@v4
```
Then in the repository: **Settings → Pages → Source: GitHub Actions**. Add `site/.nojekyll` so Jekyll does not touch the files *(documented)*.

Because the exporter is *not* run in CI (the database stays private), the JSON must be committed to the public repo. That is deliberate: it keeps the DB private and makes the deploy deterministic. If you would rather export in CI, the DB would have to be published — do not do that.

**Acceptance:** the workflow goes green; `https://<user>.github.io/english-grammar-web/` serves the home page; a lesson URL and the quiz work on the live site; refresh on a deep link returns 200, not 404.
**Recovery:** revert the commit; Pages keeps serving the previous build.

### Phase 6 — Polish
PWA manifest + service worker (the site works fully offline after one visit), `about/index.html` with the license, the CC0 dedication, Wikipedia CC BY-SA attribution for any reused source text, and a plain statement that grading is client-side and answers are effectively public. Accessibility pass: keyboard navigation, visible focus rings (the existing templates already do this), `lang`/`dir` correctness, contrast.

### Phase 7 — Optional: the English library
`topics` (55 KB) and `reference_links` ship as one page each. The 150 documents / 4239 passages (10.2 MB) ship as `library/docs/<id>.json`, fetched only when a reader opens that document — never as one bundle.

### Phase 8 — Optional: real backend
Only if you decide teacher approval, monitoring, and hidden keys actually matter. See §9.

---

## 5. Step-by-step developer tutorial

Mostly a condensed version of §4 with exact commands. Assumes `python --version` ≥ 3.10 (this machine has 3.11.16 *(measured)*, and the project already needs nothing else).

```bash
# --- 5.1  create the public repo and a clean folder -------------------------
mkdir -p "E:/my projects 1/english-grammar-web" && cd "E:/my projects 1/english-grammar-web"
git init -b main
mkdir -p site/data/lessons site/assets site/lesson tools/templates tests
touch site/.nojekyll

# --- 5.2  copy in the code (from this plan) --------------------------------
#   tools/export_web_data.py      §4 Phase 1
#   tools/render_pages.py         §4 Phase 2
#   tools/check_site.py           §4 Phase 2
#   tools/templates/*.html        adapted from farsi_course_template.html
#   site/assets/*.js, app.css     adapted from farsi_course_template.html

# --- 5.3  export the content ----------------------------------------------
python tools/export_web_data.py \
  --db "E:/my projects 1/english grammar dictionaries bot/english_grammar_fa.sqlite3" \
  --out site/data
#   expected: {"lessons": 228, "exercises": 1140, "options": 3420, "keys": 1140}
ls -la site/data && du -sh site/data

# --- 5.4  render pages and check ------------------------------------------
python tools/render_pages.py --data site/data --out site --templates tools/templates
python tools/check_site.py --site site --expect-lessons 228

# --- 5.5  run locally -----------------------------------------------
python -m http.server 8000 --directory site
#   open http://localhost:8000  (do not open index.html via file:// — fetch() is blocked)

# --- 5.6  commit and publish -----------------------------------------------
git add -A && git commit -m "Static grammar site: data export, pages, quiz"
git remote add origin https://github.com/<you>/english-grammar-web.git
git push -u origin main
#   then: Settings -> Pages -> Source: GitHub Actions; run the workflow or push again
```

**Verifying the deploy is real** (do not trust a green check alone):
```bash
curl -sI https://<you>.github.io/english-grammar-web/lesson/present-perfect/ | head -1
curl -s  https://<you>.github.io/english-grammar-web/data/manifest.json | python -m json.tool | head -20
```
The manifest's `counts` must match §4 Phase 1's output. If a deep link 404s, `.nojekyll` is missing or the artifact was not uploaded from `site/`.

**Local sanity checks worth keeping:**
```bash
grep -rEi 'sqlite3|dpapi|token' site/ --include='*.json' | head      # must be empty
grep -c 'correct_option_id' site/data/keys.json                        # must be 0 (K2)
du -sh site/                                                           # should be well under 100 MB
```

---

## 6. Testing

| Test | What it proves |
|---|---|
| `tests/test_export.py` | counts are 228/1140/3420/1140, IDs unique, every option belongs to its exercise (the DB has a trigger for this already), no `correct_option_id` in `keys.json` under K2 |
| `tests/test_grade_parity.py` | for all 1140 questions, the client-side algorithm yields the same correctness verdict as `CourseRepository.grade()` |
| `tools/check_site.py` | 228 lesson pages exist, every internal link resolves, every `lessons/<slug>.json` is parseable, largest file < 5 MB, total < 50 MB, no `.sqlite3`/`.dpapi`/`token` strings anywhere in `site/` |
| `tests/test_search.py` | the ported normalization matches the bot's on a corpus of Persian variants (ي/ك/ZWNJ/combining marks) |

The existing `test_farsi_course.py` already proves `CourseRepository.grade()` is correct *(measured: it asserts full-correct = 5 and all-wrong = 0)*. Reuse it as the reference oracle for parity — do not rewrite the expectation.

---

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Accidentally publishing secrets/student data | Medium | **Severe, permanent** | Separate repo (§D2); `check_site.py` fails on `sqlite3`/`dpapi`/`token`; never `git add -f` |
| Assuming the quiz is "secure" | High | Medium | State plainly on the site and in README that K2 is deterrence only |
| Bandwidth blowout | Low | Medium | Per-lesson files (§2.4); lazy-load the 10.2 MB library |
| Site repo bloat over time | Medium | Low | Regenerate rather than accumulate; repo recommended limit 1 GB; site limit 1 GB *(documented)* |
| Licensing: Wikipedia text is CC BY-SA, not CC0 | Medium | Medium | `ATTRIBUTION.md` + per-source license shown on each lesson (the DB already carries `sources.license`) — required, not optional |
| Content is `review_status = draft` *(measured)* | Certain | Medium | Keep the existing "draft, not independently reviewed" disclaimer visible; the bot's README already says this |
| Pages ToS: not for commercial/SaaS use, no sensitive transactions *(documented)* | Low | — | This site is free educational content; stay non-commercial |
| Losing the bot's teacher workflow | Certain | Depends on you | Decide D1 now; see §9 if it matters |

---

## 8. What is lost, stated plainly

Converting to a static site means giving up, permanently and by architecture:

1. **Teacher approval.** No gate, no `/admin`, no `/students`, no access requests. Anyone with the URL reads everything.
2. **Student monitoring and reports.** No `activity_events`, no daily Tehran summaries, no retention policy to enforce — because no learner data is collected at all. (Arguably a privacy improvement, but it is a real feature loss.)
3. **Hidden answer keys.** Per D1.
4. **Per-student durable quiz history.** `localStorage` only; clearing the browser erases it.

What you gain: no server, no token, no Docker, no Windows-only DPAPI, no poller to babysit, a shareable link, SEO, and an app that works offline.

---

## 9. If you later need the teacher features back

GitHub Pages cannot host them. The cheapest path that keeps this front-end almost unchanged:

- **Cloudflare Pages** (static hosting, free) + **Pages Functions** (serverless, free tier) + **D1** (SQLite, free tier) — the same repository layout, with `/api/grade`, `/api/auth`, `/api/teacher/*` added and `keys.json` moved server-side. Alternatively Supabase (Postgres + auth + row-level security) or Firebase.
- Keep this document's Phase 1–4 front-end as-is: only `quiz.js`'s grading call and the access gate change.
- Do **not** try to bolt auth onto GitHub Pages with client-side checks — that is security theatre, and it would also collect user data on a host whose terms discourage exactly that *(documented)*.

---

## 10. Open questions for you

1. **D1 — answer keys:** K1 (public), K2 (hashed, recommended), K3 (no scoring), or K4 (needs a backend)?
2. **D2 — repo name and account:** is `english-grammar-web` the right public repo name, and which GitHub account/organisation?
3. **D3 — scope:** course-only first (3.2 MB), or include the English library (Phase 7) in the first release?
4. **D4 — language of the site UI:** the bot was Persian-first with English titles. Keep Persian-first RTL, or add an English UI toggle?
5. **Custom domain** now, or `github.io` to start?
