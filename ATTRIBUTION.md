# Attribution and licensing

This site publishes grammar teaching material and links to third-party sources. Nothing here is a
claim of ownership over third-party content.

## 1. Course content — CC0 1.0

The original bilingual course text, explanations, examples, exercises and answer explanations were
authored for this project and are dedicated to the public domain under **CC0 1.0 Universal**
(https://creativecommons.org/publicdomain/zero/1.0/). This is recorded in the source database's
`course_metadata.license` field and re-exported into `site/data/manifest.json`.

## 2. Review status — please read

The course is a **draft**: authored and structurally checked, but not independently reviewed by a
Persian-speaking English teacher. The level assignments (A1–C2) are editorial study hints and are
**not certified CEFR levels**; a single grammar topic can span several proficiency levels. Every
lesson page carries this notice. Do not present this material as an accredited course.

## 3. Third-party sources

Each lesson lists its background references, and each source's own licence is shown on the page.
Those licences are **not** CC0 and remain in force:

- **Wikipedia articles** — text is attributed to Wikipedia contributors, licensed
  **CC BY-SA 4.0**. Reuse requires attribution and share-alike terms. `sources.history_url` and
  revision metadata are kept in the source database for this purpose.
- **Project Gutenberg books** — public domain **in the USA**; other jurisdictions may differ. The
  Gutenberg licence notices are preserved with the source snapshots.
- **Cambridge / British Council reference links** — titles and URLs only. Their copyrighted lesson
  bodies are not stored or republished here; the links open the publishers' own pages.

The `sources` table in the source database carries `license`, `license_url`, `retrieved_at`,
`revision`, `revision_timestamp`, `history_url` and `snapshot_path` for every source — preserve
those fields when reusing any source text.

## 4. Fonts

Two typefaces are self-hosted in `site/assets/fonts/`, both under the **SIL Open Font License 1.1**,
which permits redistribution and web embedding:

| Font | Copyright | Licence file |
|---|---|---|
| **Vazirmatn** (Persian text, weights 400/600/700/800) | 2015 The Vazirmatn Project Authors — https://github.com/rastikerdar/vazirmatn | `site/assets/fonts/licenses/Vazirmatn-OFL-1.1.txt` |
| **Inter** (Latin/English text, variable 100–900) | 2020 The Inter Project Authors — https://github.com/rsms/inter | `site/assets/fonts/licenses/Inter-OFL-1.1.txt` |

Both licences are redistributed alongside the font binaries, as OFL requires. Font files are
unmodified copies of the published releases.

## 5. Grading

The quiz runs entirely in the visitor's browser. The published answer data is the **SHA-256 hash**
of the correct option id together with the Persian explanation, not the plain answer. This deters
casual inspection of the page source and nothing more: with three options per question the hash is
trivially brute-forced. It is not a security boundary and the score has no assessment value.
See `site/about/index.html` for the learner-facing version of this notice.
