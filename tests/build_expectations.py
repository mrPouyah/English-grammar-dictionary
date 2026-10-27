#!/usr/bin/env python3
"""Build the grading oracle from the SOURCE database (test fixture, never published).

Writes tests/expected_grades.json: exercise_id -> correct option id, read straight
from course_answer_keys. tests/test_grade_parity.mjs then proves that the published
lesson JSON + keys.json + the browser's SHA-256 scheme agree with this oracle for
every single question.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB = Path(sys.argv[1] if len(sys.argv) > 1 else
          "E:/my projects 1/english grammar dictionaries bot/english_grammar_fa.sqlite3")
OUT = Path(__file__).with_name("expected_grades.json")

db = sqlite3.connect(DB.resolve().as_uri() + "?mode=ro", uri=True)
oracle = {r[0]: r[1] for r in db.execute("SELECT exercise_id, correct_option_id FROM course_answer_keys")}
db.close()
OUT.write_text(json.dumps(oracle, ensure_ascii=False, indent=0), encoding="utf-8")
print(f"oracle: {len(oracle)} answers -> {OUT}")

# One worked example, so a human can hand-verify the end-to-end path.
print("parts-of-speech correct option ids (for the live browser check):")
for key, value in oracle.items():
    if key.startswith("fa-l001-"):
        print(f"  {key} = {value}")
