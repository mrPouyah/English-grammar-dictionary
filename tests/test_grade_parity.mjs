/* Grading parity test — run with: node tests/test_grade_parity.mjs
 *
 * Proves that what the site actually publishes (prerendered lesson JSON +
 * sha256-hashed keys.json) reproduces the source database's answer key for all
 * 1140 questions, using the same primitive the browser uses (SHA-256 of the
 * option id). Exits non-zero on any mismatch.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');

const oracle = JSON.parse(readFileSync(join(here, 'expected_grades.json'), 'utf8'));
const keys = JSON.parse(readFileSync(join(root, 'site/data/keys.json'), 'utf8'));
const lessonDir = join(root, 'site/data/lessons');
const sha256 = (s) => createHash('sha256').update(s, 'utf8').digest('hex');

let questions = 0;
let options = 0;
const failures = [];

for (const file of readdirSync(lessonDir)) {
  if (!file.endsWith('.json')) continue;
  const lesson = JSON.parse(readFileSync(join(lessonDir, file), 'utf8'));
  for (const q of lesson.exercises || []) {
    questions++;
    const expected = oracle[q.id];
    if (!expected) { failures.push(`${q.id}: no oracle answer`); continue; }
    const entry = keys[q.id];
    if (!entry) { failures.push(`${q.id}: missing from keys.json`); continue; }
    if ('k' in entry) { failures.push(`${q.id}: keys.json leaks a plaintext answer`); continue; }

    // Which published option does the browser's scheme declare correct?
    const matches = (q.options || []).filter((o) => sha256(o.id) === entry.h);
    options += (q.options || []).length;
    if (matches.length !== 1) {
      failures.push(`${q.id}: ${matches.length} options match the published hash (want exactly 1)`);
      continue;
    }
    if (matches[0].id !== expected) {
      failures.push(`${q.id}: site says ${matches[0].id}, database says ${expected}`);
    }
    // The renderer must also print the explanation for the feedback panel.
    if (typeof entry.why !== 'string' || entry.why.length === 0) {
      failures.push(`${q.id}: no Persian explanation in keys.json`);
    }
  }
}

const orphans = Object.keys(keys).filter((id) => !oracle[id]);
if (orphans.length) failures.push(`${orphans.length} keys.json entries have no database answer`);

console.log(JSON.stringify({
  questions_checked: questions,
  options_hashed: options,
  oracle_answers: Object.keys(oracle).length,
  keys_entries: Object.keys(keys).length,
  failures: failures.slice(0, 20),
  failure_count: failures.length,
}, null, 2));

if (failures.length) {
  console.error(`\nFAILED: ${failures.length} grading mismatch(es).`);
  process.exit(1);
}
console.log('\nOK: the published site grades identically to the source database.');
