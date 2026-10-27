#!/usr/bin/env python3
"""Render the static grammar site: home, level pages, 228 lesson pages, about, 404.

Content is prerendered (works without JavaScript). JavaScript is used only for
search refinement and the quiz. Asset and link paths are relative, so the site
works at a domain root, under /<repo>/, or from a local file server.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

BASE = "tools/templates"
DRAFT_NOTE = ("این درس پیش‌نویس آموزشی است و بازبینی مستقل مدرس ندارد. "
              "سطح‌بندی، پیشنهاد مطالعه است و گواهی CEFR نیست.")


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def js_json(payload) -> str:
    """Embed JSON safely inside a <script> block."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def shell(template: str, *, rel: str, title: str, desc: str, body: str) -> str:
    return (template
            .replace("{{REL}}", rel)
            .replace("{{TITLE}}", esc(title))
            .replace("{{DESC}}", esc(desc))
            .replace("{{BODY}}", body))


def write(path: Path, text: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def fa_num(n) -> str:
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


# --------------------------------------------------------------------------- lesson body
def render_lesson_content(lesson: dict) -> str:
    out: list[str] = []
    expanded = lesson.get("expanded") or None

    if expanded:
        out.append("<h3 class=\"sec\">آموزش و ساختار</h3>")
        explanation = expanded.get("explanation_fa") or lesson.get("explanation_fa") or ""
        for para in [p for p in explanation.split("\n\n") if p.strip()]:
            out.append(f"<p class=\"explanation\">{esc(para)}</p>")
        for p in expanded.get("patterns") or []:
            out.append(f"<h4>{esc(p.get('label_fa'))}</h4>")
            if p.get("pattern_en"):
                out.append(f"<div class=\"pattern english\">{esc(p['pattern_en'])}</div>")
            if p.get("example_en"):
                out.append(f"<p class=\"example english\">{esc(p['example_en'])}</p>")
            if p.get("translation_fa"):
                out.append(f"<p class=\"explanation\">{esc(p['translation_fa'])}</p>")
        for page in expanded.get("teaching_pages") or []:
            body = page.get("body_fa") or ""
            if not body.strip():
                continue
            out.append(f"<h3 class=\"sec\">{esc(page.get('title_fa'))}</h3>")
            for para in [p for p in body.split("\n\n") if p.strip()]:
                out.append(f"<p class=\"explanation\">{esc(para)}</p>")

        examples = expanded.get("examples") or []
        if examples:
            out.append("<h3 class=\"sec\">مثال‌های دوزبانه</h3>")
            for e in examples:
                out.append("<section class=\"bilingual-example\">")
                out.append(f"<h4>مثال {fa_num(e.get('ordinal', ''))}</h4>")
                out.append(f"<p class=\"example english\">{esc(e.get('text_en'))}</p>")
                out.append(f"<p class=\"explanation\">{esc(e.get('text_fa'))}</p>")
                if e.get("note_fa"):
                    out.append(f"<p class=\"note\">{esc(e['note_fa'])}</p>")
                out.append("</section>")

        mistakes = expanded.get("mistakes") or []
        if mistakes:
            out.append("<h3 class=\"sec\">اشتباهات رایج فارسی‌زبان‌ها</h3>")
            for m in mistakes:
                out.append("<section class=\"mistake-box\">")
                out.append("<h4 class=\"bad\">نادرست</h4>")
                out.append(f"<p class=\"example english\">{esc(m.get('incorrect_en'))}</p>")
                out.append("<h4 class=\"good\">درست</h4>")
                out.append(f"<p class=\"example english\">{esc(m.get('correct_en'))}</p>")
                if m.get("reason_fa"):
                    out.append(f"<p class=\"note\">{esc(m['reason_fa'])}</p>")
                out.append("</section>")

        for c in expanded.get("comparisons") or []:
            out.append(f"<h3 class=\"sec\">{esc(c.get('title_fa'))}</h3>")
            for item in c.get("items") or []:
                out.append(f"<p class=\"example english\">{esc(item.get('text_en'))}</p>")
                out.append(f"<p class=\"explanation\">{esc(item.get('text_fa'))}</p>")
            if c.get("note_fa"):
                out.append(f"<p class=\"note\">{esc(c['note_fa'])}</p>")
    else:
        out.append("<h3 class=\"sec\">توضیح درس</h3>")
        for para in [p for p in (lesson.get("explanation_fa") or "").split("\n\n") if p.strip()]:
            out.append(f"<p class=\"explanation\">{esc(para)}</p>")
        if lesson.get("pattern_en"):
            out.append("<h3 class=\"sec\">الگوی انگلیسی</h3>")
            out.append(f"<div class=\"pattern english\">{esc(lesson['pattern_en'])}</div>")
        if lesson.get("examples_en"):
            out.append("<h3 class=\"sec\">مثال</h3>")
            for ex in lesson["examples_en"]:
                out.append(f"<p class=\"example english\">{esc(ex)}</p>")
        if lesson.get("common_mistake_fa"):
            out.append("<h3 class=\"sec\">نکتهٔ مهم برای فارسی‌زبان‌ها</h3>")
            out.append(f"<p class=\"note\">{esc(lesson['common_mistake_fa'])}</p>")

    sources = lesson.get("sources") or []
    if sources:
        out.append("<h3 class=\"sec\">منابع زمینه‌ای</h3>")
        for s in sources:
            url = s.get("url") or ""
            label = esc(s.get("title"))
            link = (f"<a href=\"{esc(url)}\" target=\"_blank\" rel=\"noopener noreferrer\">{label}</a>"
                    if url.startswith(("http://", "https://")) else label)
            license_note = f" — <span class=\"lic\">{esc(s.get('license'))}</span>" if s.get("license") else ""
            out.append(f"<p class=\"source\">{link}{license_note}</p>")
    return "\n".join(out)


def render_quiz(lesson: dict) -> str:
    exercises = lesson.get("exercises") or []
    if not exercises:
        return "<p class=\"note\">برای این درس تمرینی ثبت نشده است.</p>"
    rows = []
    for q in exercises:
        options = []
        for o in q.get("options") or []:
            oid = esc(o.get("id"))
            options.append(
                "<label class=\"choice\">"
                f"<input type=\"radio\" name=\"{esc(q.get('id'))}\" value=\"{oid}\">"
                f"<span class=\"english\">{esc(o.get('text_en'))}</span></label>")
        rows.append(
            f"<fieldset class=\"q\" data-question=\"{esc(q.get('id'))}\">"
            f"<legend>سؤال {fa_num(q.get('ordinal', ''))} از {fa_num(len(exercises))}</legend>"
            f"<p class=\"stem english\">{esc(q.get('stem_en'))}</p>"
            + "".join(options) + "</fieldset>")
    return f"""
<form id="quiz-form" novalidate>
  <p class="hint">برای هر سؤال یک گزینه انتخاب کنید. پاسخ‌ها پس از ثبت همهٔ پاسخ‌ها بررسی می‌شوند.</p>
  {''.join(rows)}
  <p id="quiz-notice" class="notice" role="status"></p>
  <div id="quiz-result" class="status" role="status"></div>
  <div class="actions">
    <button type="submit" class="primary" id="quiz-check">بررسی پاسخ‌ها</button>
    <button type="button" class="secondary" id="quiz-reset">شروع دوباره</button>
  </div>
</form>"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--templates", type=Path, default=Path(BASE))
    ap.add_argument("--base", default="",
                    help="Site root path for the 404 page, e.g. /english-grammar-web for a project "
                         "Pages site. Empty = served at the domain root.")
    args = ap.parse_args()

    data, out = args.data, args.out
    template = (args.templates / "base.html").read_text(encoding="utf-8")
    index = load(data / "index.json")
    courses = load(data / "courses.json")
    manifest = load(data / "manifest.json")
    total = len(index)
    counts = manifest.get("counts") or {}
    label_for = {"B1": "گرامرهای B1", "B2": "گرامرهای B2", "C1": "گرامرهای C1",
                 "C2": "گرامرهای C2", "review": "مرور مبانی A1–A2"}
    groups = courses.get("groups") or {}
    order = [g for g in (courses.get("group_order") or []) if g in groups]
    order += [g for g in groups if g not in order]

    lessons: dict[str, dict] = {}
    for rec in index:
        lessons[rec["s"]] = load(data / "lessons" / f"{rec['s']}.json")

    written = 0

    # ---------------- home ----------------
    cards = []
    for rec in index:
        lid = rec["s"]
        hay = f"{rec['e']} {rec['f']} {rec.get('mod','')} {rec.get('lvl','')}".lower()
        cards.append(
            f"<li class=\"card\" data-level=\"{esc(rec.get('lvl'))}\" "
            f"data-module=\"{esc(rec.get('mod'))}\" data-hay=\"{esc(hay)}\">"
            f"<a href=\"lesson/{esc(lid)}/\">"
            f"<span class=\"row\"><b class=\"english\">{esc(rec['e'])}</b>"
            f"<span class=\"lvl\">{esc(rec.get('lvl'))}</span></span>"
            f"<span class=\"fa\">{esc(rec['f'])}</span>"
            f"<small><span>{esc(rec.get('mod'))}</span><span>درس {fa_num(rec['o'])}</span></small>"
            "</a></li>")
    module_options = "".join(
        f"<option value=\"{esc(m['title_fa'])}\">{esc(m['title_fa'])}</option>"
        for m in courses.get("modules") or [])
    level_options = "".join(
        f"<option value=\"{esc(lv)}\">{esc(lv)} — {esc(courses.get('level_labels', {}).get(lv, ''))}</option>"
        for lv in ["A1", "A2", "B1", "B2", "C1", "C2"])
    level_code_for = {"B1": "B1", "B2": "B2", "C1": "C1", "C2": "C2", "review": "A1–A2"}
    level_links = "".join(
        f"<a class=\"pill pill-{esc(g)}\" href=\"level/{esc(g)}/\">"
        f"<span class=\"lvl-code\">{esc(level_code_for.get(g, g))}</span>"
        f"{esc(label_for.get(g, g))}</a>" for g in order)

    home_body = f"""
<section class="hero">
  <div class="hero-eyebrow">
    <span>{fa_num(total)} درس دوزبانه</span>
    <span class="sep">·</span>
    <span>{fa_num(counts.get('exercises', 0))} پرسش تمرینی</span>
    <span class="sep">·</span>
    <span>سطح‌های A1 تا C2</span>
  </div>
  <h1>مرجع و فرهنگ گرامر زبان انگلیسی<span class="en-sub english">Bilingual English Grammar Reference &amp; Practice</span></h1>
  <p>درس‌نامهٔ ساختاریافتهٔ گرامر انگلیسی با توضیح فارسی، الگوهای جمله‌سازی، اشتباهات رایج فارسی‌زبان‌ها و آزمون پنج‌سؤالی در پایان هر مبحث.</p>
  <div class="pills">{level_links}</div>
</section>
<section class="controls" aria-label="جست‌وجو و فیلتر">
  <div class="search-box">
    <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
    <input id="search" type="search" placeholder="جست‌وجوی عنوان یا مبحث به فارسی یا انگلیسی (مثلاً present perfect یا حال کامل)..." aria-label="جست‌وجوی گرامر">
  </div>
  <select id="module" aria-label="دسته‌بندی"><option value="">همهٔ سرفصل‌ها</option>{module_options}</select>
  <select id="level" aria-label="سطح"><option value="">همهٔ سطح‌ها</option>{level_options}</select>
</section>
<div class="toolbar-meta">
  <p id="count" class="count" role="status"></p>
</div>
<ul id="lessons" class="cards">{''.join(cards)}</ul>
<script type="module" src="assets/search.js"></script>
"""
    written += write(out / "index.html", shell(
        template, rel="", title="فرهنگ و دورهٔ گرامر انگلیسی",
        desc=f"{total} درس دوزبانهٔ گرامر انگلیسی با توضیح فارسی، مثال و آزمون.",
        body=home_body))

    # ---------------- level pages ----------------
    for g in order:
        slugs = groups[g]
        rows = []
        for slug in slugs:
            l = lessons[slug]
            rows.append(
                f"<li class=\"card\" data-level=\"{esc(l.get('cefr_level'))}\">"
                f"<a href=\"../../lesson/{esc(slug)}/\">"
                f"<span class=\"row\"><b class=\"english\">{esc(l['title_en'])}</b>"
                f"<span class=\"lvl\">{esc(l.get('cefr_level'))}</span></span>"
                f"<span class=\"fa\">{esc(l['title_fa'])}</span>"
                f"<small><span>{esc(l.get('module_fa'))}</span><span>درس {fa_num(l['course_order'])}</span></small>"
                "</a></li>")
        body = f"""
<section class="hero">
  <h1>{esc(label_for.get(g, g))}</h1>
  <p>{fa_num(len(slugs))} درس · فهرست بر پایهٔ ترتیب دوره</p>
  <div class="pills"><a class="pill" href="../../index.html">خانه</a></div>
</section>
<ul class="cards">{''.join(rows)}</ul>
"""
        written += write(out / "level" / g / "index.html", shell(
            template, rel="../../", title=f"{label_for.get(g, g)} — گرامر انگلیسی",
            desc=f"{len(slugs)} درس گرامر انگلیسی در گروه {g}.", body=body))

    # ---------------- lesson pages ----------------
    for rec in index:
        slug = rec["s"]
        l = lessons[slug]
        group = l.get("menu_group") if l.get("menu_group") in groups else None
        siblings = groups.get(group, []) if group else [slug]
        pos = siblings.index(slug) if slug in siblings else 0
        nav = []
        if pos > 0:
            prev_slug = siblings[pos - 1]
            nav.append(f"<a class=\"secondary\" href=\"../{esc(prev_slug)}/\">درس قبلی: "
                       f"{esc(lessons[prev_slug]['title_en'])}</a>")
        if pos + 1 < len(siblings):
            next_slug = siblings[pos + 1]
            nav.append(f"<a class=\"secondary\" href=\"../{esc(next_slug)}/\">درس بعدی: "
                       f"{esc(lessons[next_slug]['title_en'])}</a>")
        back = (f"<a class=\"pill\" href=\"../../level/{esc(group)}/\">{esc(label_for.get(group, group))}</a>"
                if group else "<a class=\"pill\" href=\"../../index.html\">خانه</a>")

        body = f"""
<article class="lesson">
  <div class="tags">
    <span class="tag">{esc(l.get('module_fa'))}</span>
    <span class="tag">سطح {esc(l.get('cefr_level'))} — {esc(l.get('level_fa'))}</span>
    <span class="tag">درس {fa_num(l.get('course_order'))}</span>
  </div>
  <h1 class="english title">{esc(l['title_en'])}</h1>
  <p class="subtitle">{esc(l['title_fa'])}</p>
  <p class="draft">{esc(DRAFT_NOTE)}</p>
  {render_lesson_content(l)}
</article>
<section class="quiz" id="quiz" data-keys="../../data/keys.json" data-total="{len(l.get('exercises') or [])}">
  <h2>آزمون</h2>
  {render_quiz(l)}
</section>
<nav class="lesson-nav">{''.join(nav)}</nav>
<p class="back">{back}</p>
<script type="application/json" id="quiz-data">{js_json({
    "slug": slug, "title_en": l["title_en"],
    "questions": [{"id": q["id"], "ordinal": q.get("ordinal"),
                   "options": [{"id": o["id"], "text_en": o["text_en"]} for o in (q.get("options") or [])]}
                  for q in (l.get("exercises") or [])]})}</script>
<script type="module" src="../../assets/quiz.js"></script>
"""
        written += write(out / "lesson" / slug / "index.html", shell(
            template, rel="../../",
            title=f"{l['title_en']} — {l['title_fa']} | گرامر انگلیسی",
            desc=(l.get("explanation_fa") or "")[:180], body=body))

    # ---------------- about ----------------
    counts = manifest.get("counts", {})
    about_body = f"""
<article class="lesson">
  <h1>دربارهٔ این سایت، مجوز و روش نمره‌دهی</h1>
  <h3 class="sec">محتوا</h3>
  <p class="explanation">{fa_num(counts.get('lessons', 0))} درس گرامر انگلیسی با توضیح فارسی،
     {fa_num(counts.get('exercises', 0))} پرسش و {fa_num(counts.get('expanded', 0))} درس با بخش‌های تکمیلی.
     نسخهٔ محتوا: {esc(manifest.get('content_version'))}.</p>
  <p class="draft">{esc(manifest.get('review_status') or '')}</p>
  <h3 class="sec">مجوز</h3>
  <p class="explanation">{esc(manifest.get('license') or '')}</p>
  <p class="explanation">متن مقاله‌ها و کتاب‌های مرجع نقل‌شده در بخش «منابع» تابع مجوز خودشان است و
     در هر منبع ذکر شده است. توجه به شرط اشتراک‌گذاری همان مجوزها الزامی است.</p>
  <h3 class="sec">روش نمره‌دهی — مهم</h3>
  <p class="notice">{esc(manifest.get('grading') or '')}</p>
  <p class="explanation">این سایت روی یک میزبان استاتیک اجرا می‌شود؛ به همین دلیل بررسی پاسخ‌ها در مرورگر
     خودِ شما انجام می‌شود و هیچ داده‌ای از شما جمع‌آوری، ارسال یا ذخیره نمی‌شود. نتیجهٔ آزمون فقط برای
     تمرین شخصی است و ارزش ارزیابی رسمی ندارد. داربست‌فروشی با ابزار توسعه‌دهنده ممکن است و
     این روش فقط یک بازدارندهٔ ساده است، نه یک مرز امنیتی.</p>
  <h3 class="sec">سطح‌بندی</h3>
  <p class="explanation">{esc(manifest.get('level_policy') or '')}</p>
  <p class="back"><a class="pill" href="../index.html">خانه</a></p>
</article>
"""
    written += write(out / "about" / "index.html", shell(
        template, rel="../", title="درباره، مجوز و نمره‌دهی",
        desc="مجوز محتوا و توضیح روش نمره‌دهی در مرورگر.", body=about_body))

    # ---------------- 404 ----------------
    # The 404 handler answers URLs at any depth, so its links must be root-absolute
    # and therefore need to know the site's base path (project Pages sites are
    # served under /<repo>/, not at the domain root).
    rel404 = (args.base.rstrip("/") + "/") if args.base else "/"
    written += write(out / "404.html", shell(
        template, rel=rel404, title="صفحه پیدا نشد",
        desc="صفحهٔ مورد نظر پیدا نشد.",
        body="<article class=\"lesson\"><h1>صفحه پیدا نشد</h1>"
             "<p class=\"explanation\">نشانی را بررسی کنید یا از فهرست درس‌ها شروع کنید.</p>"
             f"<p><a class=\"pill\" href=\"{rel404}index.html\">خانه</a></p></article>"))

    print(json.dumps({"html_files": 1 + len(order) + len(index) + 2, "bytes": written,
                      "groups": order, "levels_page": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
