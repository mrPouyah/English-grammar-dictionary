# English Grammar — static web site

A static, offline-capable Persian-language English grammar course and dictionary: **228 bilingual
lessons**, **1140 four-option questions** with Persian explanations, colour-coded level browsing
(A1–C2), and Persian/English full-text search.

Built as the web replacement for the Telegram bot. The Telegram transport, the teacher-approval
gate and student monitoring were deliberately dropped — a static host cannot run them. What was
kept is what matters: the content, the level categorisation, search, and the quizzes.

**No learner data is collected, stored or transmitted.** Reading and grading happen in the browser,
so the site is a pure static bundle — no server, no database, no API.

## Layout

```
tools/export_web_data.py     SQLite -> static JSON (read-only; refuses partial exports)
tools/render_pages.py        JSON -> prerendered HTML (236 pages)
tools/check_site.py          pre-publish gate: links, counts, size, secret scan
tools/templates/base.html    document shell
site/                        the published artifact
  index.html  about/  level/<G>/  lesson/<slug>/     236 pages
  assets/     app.css, normalize.js, search.js, quiz.js, fonts/
  data/       manifest, index, courses, keys, lessons/<slug>.json
tests/                       grading oracle + parity test
```

Content is **prerendered**, so lessons read fine without JavaScript. JavaScript is used only for
search refinement and the quiz.

## Build

The source database is private and **must never be committed here**. The build reads it read-only
and writes only into `site/`.

```bash
python tools/export_web_data.py \
  --db "/path/to/english_grammar_fa.sqlite3" \
  --out site/data
python tools/render_pages.py --data site/data --out site --templates tools/templates
python tools/check_site.py --site site --expect-lessons 228
```

`export_web_data.py` runs a long list of integrity gates (lesson count, exactly five exercises per
lesson, every exercise has exactly one answer key whose hash matches exactly one option, no missing
CEFR row, no empty titles) and **aborts without writing** if any fail. It refuses to produce a
partial course.

`--plaintext-keys` switches the export to plain answer ids. Only use it for private/offline copies —
on a public host it publishes every answer in readable form.

For a project Pages site served under `/<repo>/`, pass `--base /<repo>` to `render_pages.py` so the
404 page's root-absolute links point at the right place. (For a user site or custom domain at the
root, omit it.)

## Verify

```bash
node tests/test_grade_parity.mjs      # after: python tests/build_expectations.py
python -m http.server 8000 --directory site
```

`test_grade_parity.mjs` proves that the **published** lesson JSON + hash-only `keys.json` reproduce
the source database's answer key for **all 1140 questions**, using the same SHA-256 primitive the
browser uses. `check_site.py` verifies 228 lesson pages and JSON files, resolves all ~3250 internal
links, and fails if any `.sqlite3`/`.dpapi`/token string leaks into the published tree.

Serve over `http://localhost` or `https://` — `crypto.subtle`, which the quiz needs, is unavailable
in `file://` contexts.

## Grading, honestly

Answers are hashed, not encrypted. Three options per question means the hash can be brute-forced
instantly, so treat the quiz as a study aid and nothing more. A real graded assessment needs a
server; see `WEB_APP_PLAN.md` §9 for that path.

## Deploy

`.github/workflows/pages.yml` publishes `site/` to GitHub Pages on every push to `main`. In the
repository: **Settings → Pages → Source: GitHub Actions**. `site/.nojekyll` stops Jekyll from
processing the files.

Note that a Pages site on a **free** account requires the repository to be **public**, which is why
the exported content — and the hashed answer data — is public by design.

## Licence

Course content is **CC0 1.0**. Third-party sources keep their own licences (Wikipedia CC BY-SA 4.0,
Project Gutenberg public domain in the USA) and are listed per lesson. Fonts are SIL OFL 1.1.
**Read `ATTRIBUTION.md` before reusing any of this.**
