#!/usr/bin/env bash
# Phase 2 (v2.4.0) acceptance:
#   1. unittest suite under tests/
#   2. seed-corpus: source.md fires within [hard_fail_min, hard_fail_max]
#   3. seed-corpus: expected.md has 0 HARD_FAIL
#   4. own reference files: 0 HARD_FAIL
#   5. perf budget: <100 ms per 5K-char doc
#
# Exits 0 on full pass, 1 on any failure.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

failures=0
section() { echo; echo "── $1 ──"; }

section "1. Unit tests (unittest discover)"
if python3 -m unittest discover skills/ru-editor/scripts/tests/ -v 2>&1 | tail -5; then
  echo "PASS: unit tests"
else
  echo "FAIL: unit tests"
  failures=$((failures + 1))
fi

section "2. Seed corpus — sources fire within budget"
corpus_failures=0
for d in evals/seed-corpus/[0-9]*; do
  src="$d/source.md"
  brief="$d/brief.toml"
  [[ -f "$src" && -f "$brief" ]] || continue

  result=$(python3 skills/ru-editor/scripts/ru_lint.py check "$src" --format json 2>/dev/null)
  hard=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['hard_fail_count'])")

  expected_min=$(python3 -c "
import tomllib
with open('$brief', 'rb') as f:
    d = tomllib.load(f)
print(d.get('expected_findings', {}).get('hard_fail_min', 0))
")
  expected_max=$(python3 -c "
import tomllib
with open('$brief', 'rb') as f:
    d = tomllib.load(f)
print(d.get('expected_findings', {}).get('hard_fail_max', 999))
")

  if [[ "$hard" -lt "$expected_min" ]] || [[ "$hard" -gt "$expected_max" ]]; then
    echo "FAIL: $d source has $hard HARD_FAIL (expected [$expected_min, $expected_max])"
    corpus_failures=$((corpus_failures + 1))
  fi
done
if [[ "$corpus_failures" -eq 0 ]]; then
  echo "PASS: all seed-corpus sources within budget"
else
  echo "FAIL: $corpus_failures seed-corpus source(s) outside budget"
  failures=$((failures + 1))
fi

section "3. Seed corpus — expected.md has 0 HARD_FAIL (idempotency invariant)"
expected_failures=0
for d in evals/seed-corpus/[0-9]*; do
  exp="$d/expected.md"
  [[ -f "$exp" ]] || continue
  result=$(python3 skills/ru-editor/scripts/ru_lint.py check "$exp" --format json 2>/dev/null)
  hard=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['hard_fail_count'])")
  if [[ "$hard" -ne 0 ]]; then
    echo "FAIL: $d/expected.md has $hard HARD_FAIL"
    expected_failures=$((expected_failures + 1))
  fi
done
if [[ "$expected_failures" -eq 0 ]]; then
  echo "PASS: all seed-corpus expected.md are linter-clean"
else
  echo "FAIL: $expected_failures expected.md violate idempotency"
  failures=$((failures + 1))
fi

section "4. Own reference files — 0 HARD_FAIL (use directives where needed)"
own_failures=0
for f in skills/ru-editor/SKILL.md skills/ru-editor/references/*.md; do
  result=$(python3 skills/ru-editor/scripts/ru_lint.py check "$f" --format json 2>/dev/null)
  hard=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['hard_fail_count'])")
  if [[ "$hard" -ne 0 ]]; then
    echo "FAIL: $f has $hard HARD_FAIL"
    own_failures=$((own_failures + 1))
  fi
done
if [[ "$own_failures" -eq 0 ]]; then
  echo "PASS: 0 HARD_FAIL on own reference files"
else
  echo "FAIL: $own_failures own reference file(s) flagged"
  failures=$((failures + 1))
fi

section "5. Perf budget — <100 ms per 5K-char doc"
sample=$(ls -S skills/ru-editor/references/*.md | head -1)
sample_size=$(wc -c < "$sample")

elapsed=$(python3 -c "
import json, subprocess, time
t0 = time.monotonic()
r = subprocess.run(['python3', 'skills/ru-editor/scripts/ru_lint.py', 'check', '$sample', '--format', 'json'], capture_output=True, text=True)
elapsed_ms = int((time.monotonic() - t0) * 1000)
print(elapsed_ms)
")

normalized=$(python3 -c "print(int($elapsed * 5000 / $sample_size))")
echo "  sample: $sample ($sample_size chars), elapsed: ${elapsed}ms, normalized to 5K: ${normalized}ms"
if [[ "$normalized" -lt 100 ]]; then
  echo "PASS: perf within 100 ms / 5K chars"
else
  echo "FAIL: perf ${normalized} ms / 5K chars exceeds 100 ms budget"
  failures=$((failures + 1))
fi

echo
if [[ "$failures" -eq 0 ]]; then
  echo "── PHASE 2 ACCEPTANCE: ALL PASSED ──"
  exit 0
else
  echo "── PHASE 2 ACCEPTANCE: $failures SECTION(S) FAILED ──"
  exit 1
fi
