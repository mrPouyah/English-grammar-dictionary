#!/usr/bin/env python3
"""Export english_grammar_fa.sqlite3 into static JSON for the grammar web app.

Read-only against the source database. Refuses to write a partial or inconsistent
export: every integrity gate below must pass or nothing is published.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import sqlite3
import unicodedata
from pathlib import Path

EXPECTED_LESSONS = 228
EXPECTED_EXERCISES_PER_LESSON = 5


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def normalize(text: str) -> str:
    """Must stay identical to telegram_bot.normalized() so search feels the same."""
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = text.translate(str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "\u200c": " ", "ـ": ""}))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def dump(path: Path, payload) -> int:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return len(data)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--plaintext-keys", action="store_true",
                    help="Write correct option ids instead of SHA-256 hashes. Do not use on a public host.")
    args = ap.parse_args()

    if not args.db.is_file():
        raise SystemExit(f"Source database not found: {args.db}")
    out: Path = args.out
    db = connect(args.db)

    lessons = [dict(r) for r in db.execute(
        "SELECT * FROM course_lesson_catalog ORDER BY course_order")]
    modules = [dict(r) for r in db.execute(
        "SELECT id,slug,title_en,title_fa,display_order FROM course_modules ORDER BY display_order")]
    levels = {r["topic_id"]: dict(r) for r in db.execute(
        "SELECT topic_id,cefr_level,menu_group FROM course_cefr_levels")}
    expansions = {r["lesson_id"]: json.loads(r["document_json"]) for r in db.execute(
        "SELECT lesson_id,document_json FROM course_lesson_expansions")}

    examples: dict[int, list[str]] = {}
    for r in db.execute("SELECT lesson_id,text_en FROM course_examples ORDER BY lesson_id,ordinal"):
        examples.setdefault(r["lesson_id"], []).append(r["text_en"])

    sources: dict[int, list[dict]] = {}
    for r in db.execute("""SELECT ts.topic_id, s.title, s.url, s.license
                           FROM topic_sources ts JOIN sources s ON s.id = ts.source_id"""):
        sources.setdefault(r["topic_id"], []).append(
            {"title": r["title"], "url": r["url"], "license": r["license"]})

    exercises: dict[int, list[dict]] = {}
    for row in db.execute("SELECT * FROM course_exercises ORDER BY lesson_id, ordinal"):
        q = dict(row)
        q["options"] = [dict(r) for r in db.execute(
            "SELECT id,position,text_en FROM course_exercise_options WHERE exercise_id=? ORDER BY position",
            (q["id"],))]
        exercises.setdefault(q["lesson_id"], []).append(q)

    keys = {}
    for r in db.execute("SELECT exercise_id,correct_option_id,explanation_fa FROM course_answer_keys"):
        value = r["correct_option_id"]
        keys[r["exercise_id"]] = {
            "h" if not args.plaintext_keys else "k":
                hashlib.sha256(value.encode("utf-8")).hexdigest() if not args.plaintext_keys else value,
            "why": r["explanation_fa"],
        }

    # ---------------- integrity gates ----------------
    problems: list[str] = []
    if len(lessons) != EXPECTED_LESSONS:
        problems.append(f"expected {EXPECTED_LESSONS} lessons, found {len(lessons)}")
    slugs = [l["slug"] for l in lessons]
    if len(set(slugs)) != len(slugs):
        problems.append("duplicate lesson slugs would overwrite each other")
    option_counts = {"lessons": len(lessons), "exercises": 0, "options": 0, "keys": 0,
                     "expanded": len(expansions)}
    for l in lessons:
        lid = l["topic_id"]
        qs = exercises.get(lid, [])
        if len(qs) != EXPECTED_EXERCISES_PER_LESSON:
            problems.append(f"lesson {lid} ({l['slug']}) has {len(qs)} exercises")
        for q in qs:
            option_counts["exercises"] += 1
            option_counts["options"] += len(q["options"])
            if len(q["options"]) < 2:
                problems.append(f"exercise {q['id']} has fewer than 2 options")
            if q["id"] not in keys:
                problems.append(f"exercise {q['id']} has no answer key")
            else:
                option_counts["keys"] += 1
                ids = {o["id"] for o in q["options"]}
                if not args.plaintext_keys:
                    match = [o for o in q["options"]
                             if hashlib.sha256(o["id"].encode("utf-8")).hexdigest() == keys[q["id"]]["h"]]
                    if len(match) != 1:
                        problems.append(f"exercise {q['id']} key hash does not match exactly one option")
                elif keys[q["id"]]["k"] not in ids:
                    problems.append(f"exercise {q['id']} key is not one of its options")
        if lid not in levels:
            problems.append(f"lesson {lid} has no CEFR level row")
        if not l["explanation_fa"] or not l["title_en"]:
            problems.append(f"lesson {lid} is missing title or explanation")
    if problems:
        for p in problems[:30]:
            print("INTEGRITY:", p)
        raise SystemExit(f"Export aborted: {len(problems)} integrity problem(s). Nothing was written.")

    # ---------------- per-lesson files ----------------
    total_bytes = 0
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
        total_bytes += dump(out / "lessons" / f"{l['slug']}.json", doc)

    # ---------------- search index ----------------
    index = []
    for l in lessons:
        lid = l["topic_id"]
        index.append({
            "s": l["slug"], "e": l["title_en"], "f": l["title_fa"],
            "lvl": levels.get(lid, {}).get("cefr_level") or "",
            "mod": l["module_fa"] or "",
            "o": l["course_order"],
            "en": l["title_en"], "fa": l["title_fa"],
            "hay": normalize(" ".join([l["title_en"] or "", l["title_fa"] or "",
                                       l["explanation_fa"] or "", l["common_mistake_fa"] or "",
                                       l["pattern_en"] or ""])),
        })
    total_bytes += dump(out / "index.json", index)

    # ---------------- categorization: levels + modules ----------------
    groups: dict[str, list[str]] = {}
    for l in lessons:
        g = levels.get(l["topic_id"], {}).get("menu_group") or l["level_hint"] or "other"
        groups.setdefault(g, []).append(l["slug"])
    level_labels = {}
    for l in lessons:
        lv = levels.get(l["topic_id"], {})
        if lv.get("cefr_level"):
            level_labels[lv["cefr_level"]] = l["level_fa"] or ""
    total_bytes += dump(out / "courses.json", {
        "modules": modules,
        "groups": groups,
        "level_labels": level_labels,
        "group_order": ["B1", "B2", "C1", "C2", "review"],
    })

    total_bytes += dump(out / "keys.json", keys)

    meta = dict(db.execute("SELECT key,value FROM course_metadata"))
    total_bytes += dump(out / "manifest.json", {
        "schema_version": 1,
        "content_version": meta.get("content_version"),
        "license": meta.get("license"),
        "review_status": meta.get("review_status"),
        "level_policy": meta.get("level_policy"),
        "grading": ("plaintext option ids; public on a static host" if args.plaintext_keys
                    else "sha256 of the correct option id, verified in the browser; deterrence only, not security"),
        "counts": option_counts,
        "bytes": total_bytes,
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    })

    db.close()
    print(json.dumps({"counts": option_counts, "bytes": total_bytes,
                      "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
