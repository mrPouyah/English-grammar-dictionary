#!/usr/bin/env python3
"""Verify the built site before it is published. Exits non-zero on any problem.

Checks: expected lesson-page count, every internal link resolves, every lesson
JSON parses, no secrets or databases leaked into the published tree, and size gates.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

FORBIDDEN = ("sqlite3", "sqlite", "dpapi", "TELEGRAM_BOT_TOKEN", "teacher.dpapi",
             "state.sqlite3", "token.dpapi", "BEGIN PRIVATE KEY")
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_SITE_BYTES = 50 * 1024 * 1024


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site", type=Path, required=True)
    ap.add_argument("--expect-lessons", type=int, default=228)
    args = ap.parse_args()
    site: Path = args.site
    problems: list[str] = []
    notes: list[str] = []

    if not site.is_dir():
        raise SystemExit(f"Site directory not found: {site}")

    lesson_pages = sorted((site / "lesson").glob("*/index.html"))
    if len(lesson_pages) != args.expect_lessons:
        problems.append(f"expected {args.expect_lessons} lesson pages, found {len(lesson_pages)}")

    manifest_path = site / "data" / "manifest.json"
    if not manifest_path.is_file():
        problems.append("data/manifest.json is missing")
        manifest = {}
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        counts = manifest.get("counts", {})
        for key in ("lessons", "exercises", "options", "keys"):
            if not counts.get(key):
                problems.append(f"manifest count '{key}' is missing or zero")
        if counts.get("lessons") != args.expect_lessons:
            problems.append(f"manifest says {counts.get('lessons')} lessons, expected {args.expect_lessons}")

    lesson_jsons = sorted((site / "data" / "lessons").glob("*.json"))
    if len(lesson_jsons) != args.expect_lessons:
        problems.append(f"expected {args.expect_lessons} lesson JSON files, found {len(lesson_jsons)}")
    for path in lesson_jsons:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            problems.append(f"{path.name}: invalid JSON ({exc})")

    # keys.json must not contain readable option ids (K2: hashed)
    keys_path = site / "data" / "keys.json"
    if keys_path.is_file():
        raw = keys_path.read_text(encoding="utf-8")
        if '"k":' in raw:
            notes.append("WARNING: keys.json contains plaintext option ids (K1 mode)")
        entries = json.loads(raw)
        if not entries:
            problems.append("data/keys.json is empty")
        for key, entry in list(entries.items())[:50]:
            if "h" not in entry and "k" not in entry:
                problems.append(f"keys.json entry {key} has no answer field")
                break
    else:
        problems.append("data/keys.json is missing")

    # internal links
    total_bytes = 0
    checked = 0
    for page in list(site.rglob("*.html")):
        total_bytes += page.stat().st_size
        text = page.read_text(encoding="utf-8")
        base = page.parent
        for href in set(re.findall(r'(?:href|src)="([^"#]+)"', text)):
            if href.startswith(("http://", "https://", "mailto:", "data:", "//")):
                continue
            path_only = urlparse(href).path
            # A leading slash is root-relative to the SITE, not to the filesystem.
            base_dir = site if path_only.startswith("/") else base
            target = (base_dir / path_only.lstrip("/")).resolve()
            if href.endswith("/") or target.is_dir():
                target = target / "index.html"
            elif target.suffix == "":
                target = Path(str(target) + "/index.html")
            if not target.exists():
                problems.append(f"{page.relative_to(site)} -> broken link {href}")
            checked += 1

    for path in site.rglob("*"):
        if not path.is_file():
            continue
        size = path.stat().st_size
        total_bytes += 0 if path.suffix == ".html" else size
        if size > MAX_FILE_BYTES:
            problems.append(f"{path.relative_to(site)} is {size/1e6:.1f} MB (limit {MAX_FILE_BYTES/1e6:.0f} MB)")
        if path.suffix in {".html", ".json", ".js", ".css", ".md", ".txt"}:
            blob = path.read_text(encoding="utf-8", errors="ignore")
            for needle in FORBIDDEN:
                if needle in blob:
                    problems.append(f"{path.relative_to(site)} contains forbidden string '{needle}'")

    if total_bytes > MAX_SITE_BYTES:
        problems.append(f"published site is {total_bytes/1e6:.1f} MB (limit {MAX_SITE_BYTES/1e6:.0f} MB)")

    print(json.dumps({"site_bytes": total_bytes, "site_mb": round(total_bytes / 1e6, 2),
                      "lesson_pages": len(lesson_pages), "lesson_json": len(lesson_jsons),
                      "links_checked": checked, "manifest_counts": manifest.get("counts", {}),
                      "grading": manifest.get("grading"), "notes": notes,
                      "problems": problems[:40], "problem_count": len(problems)},
                     ensure_ascii=False, indent=2))
    if problems:
        print(f"\nFAILED: {len(problems)} problem(s). Do not publish.", file=sys.stderr)
        return 1
    print("\nOK: all checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
