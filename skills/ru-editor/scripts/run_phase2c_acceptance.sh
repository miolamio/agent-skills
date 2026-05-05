#!/usr/bin/env bash
# Phase 2C–2G (v2.8.0) acceptance for found-samples corpus:
#   1. brief.toml schema valid for every sample
#   2. ru_lint.py check on source.md fires within [hard_fail_min, hard_fail_max]
#   3. ru_lint.py check on edited.md has 0 HARD_FAIL (smoke-test invariant)
#   4. checks_must_fire are present in source.md findings
#   5. checks_must_not_fire_on_edited are absent from edited.md findings
#
# Exits 0 on full pass, 1 on any failure.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

failures=0
section() { echo; echo "── $1 ──"; }

CORPUS_DIR="evals/found-samples"
LINTER="skills/ru-editor/scripts/ru_lint.py"

section "1. brief.toml present and valid for every sample"
schema_failures=0
for d in "$CORPUS_DIR"/[0-9]*; do
  brief="$d/brief.toml"
  if [[ ! -f "$brief" ]]; then
    echo "FAIL: $d missing brief.toml"
    schema_failures=$((schema_failures + 1))
    continue
  fi
  python3 -c "
import tomllib, sys
with open('$brief', 'rb') as f:
    d = tomllib.load(f)
assert d['meta']['schema_version'] == '1.0', 'schema_version mismatch'
assert 'genre' in d['meta'], 'meta.genre missing'
ef = d['expected_findings']
assert ef['hard_fail_min'] <= ef['hard_fail_max'], 'hard_fail bounds inverted'
assert ef['warn_min'] <= ef['warn_max'], 'warn bounds inverted'
assert isinstance(ef.get('checks_must_fire', []), list)
assert isinstance(ef.get('checks_must_not_fire_on_edited', []), list)
" 2>&1 | grep -q . && {
    echo "FAIL: $brief schema validation failed"
    python3 -c "
import tomllib
with open('$brief', 'rb') as f:
    d = tomllib.load(f)
ef = d['expected_findings']
assert ef['hard_fail_min'] <= ef['hard_fail_max']
" 2>&1 | head -3
    schema_failures=$((schema_failures + 1))
  }
done
if [[ "$schema_failures" -eq 0 ]]; then
  echo "PASS: all brief.toml valid"
else
  echo "FAIL: $schema_failures brief.toml file(s) invalid"
  failures=$((failures + 1))
fi

section "2. source.md fires within [hard_fail_min, hard_fail_max]"
budget_failures=0
for d in "$CORPUS_DIR"/[0-9]*; do
  src="$d/source.md"
  brief="$d/brief.toml"
  [[ -f "$src" && -f "$brief" ]] || continue

  result=$(python3 "$LINTER" check "$src" --format json 2>/dev/null)
  hard=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['hard_fail_count'])")

  read -r hmin hmax <<< "$(python3 -c "
import tomllib
with open('$brief', 'rb') as f:
    d = tomllib.load(f)
ef = d['expected_findings']
print(ef['hard_fail_min'], ef['hard_fail_max'])
")"

  if [[ "$hard" -lt "$hmin" ]] || [[ "$hard" -gt "$hmax" ]]; then
    echo "FAIL: $d source has $hard HARD_FAIL (expected [$hmin, $hmax])"
    budget_failures=$((budget_failures + 1))
  fi
done
if [[ "$budget_failures" -eq 0 ]]; then
  echo "PASS: all source.md within budget"
else
  failures=$((failures + 1))
fi

section "3. edited.md has 0 HARD_FAIL (smoke-test invariant)"
edited_failures=0
for d in "$CORPUS_DIR"/[0-9]*; do
  edited="$d/edited.md"
  [[ -f "$edited" ]] || continue
  result=$(python3 "$LINTER" check "$edited" --format json 2>/dev/null)
  hard=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['hard_fail_count'])")
  if [[ "$hard" -ne 0 ]]; then
    echo "FAIL: $d/edited.md has $hard HARD_FAIL"
    edited_failures=$((edited_failures + 1))
  fi
done
if [[ "$edited_failures" -eq 0 ]]; then
  echo "PASS: all edited.md are linter-clean (0 HARD_FAIL)"
else
  failures=$((failures + 1))
fi

section "4. checks_must_fire present in source.md findings"
must_fire_failures=0
for d in "$CORPUS_DIR"/[0-9]*; do
  src="$d/source.md"
  brief="$d/brief.toml"
  [[ -f "$src" && -f "$brief" ]] || continue

  must_fire=$(python3 -c "
import tomllib
with open('$brief', 'rb') as f:
    d = tomllib.load(f)
print(' '.join(d['expected_findings'].get('checks_must_fire', [])))
")
  [[ -z "$must_fire" ]] && continue

  fired=$(python3 "$LINTER" check "$src" --format json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(' '.join(sorted(set(f['check'] for f in d['findings']))))
")

  for check in $must_fire; do
    if ! echo " $fired " | grep -q " $check "; then
      echo "FAIL: $d/source.md missing required check '$check' (fired: $fired)"
      must_fire_failures=$((must_fire_failures + 1))
    fi
  done
done
if [[ "$must_fire_failures" -eq 0 ]]; then
  echo "PASS: all required checks fired on source.md"
else
  failures=$((failures + 1))
fi

section "5. checks_must_not_fire_on_edited absent from edited.md findings"
must_not_failures=0
for d in "$CORPUS_DIR"/[0-9]*; do
  edited="$d/edited.md"
  brief="$d/brief.toml"
  [[ -f "$edited" && -f "$brief" ]] || continue

  must_not=$(python3 -c "
import tomllib
with open('$brief', 'rb') as f:
    d = tomllib.load(f)
print(' '.join(d['expected_findings'].get('checks_must_not_fire_on_edited', [])))
")
  [[ -z "$must_not" ]] && continue

  fired=$(python3 "$LINTER" check "$edited" --format json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(' '.join(sorted(set(f['check'] for f in d['findings']))))
")

  for check in $must_not; do
    if echo " $fired " | grep -q " $check "; then
      echo "FAIL: $d/edited.md fires forbidden check '$check'"
      must_not_failures=$((must_not_failures + 1))
    fi
  done
done
if [[ "$must_not_failures" -eq 0 ]]; then
  echo "PASS: no forbidden checks fired on edited.md"
else
  failures=$((failures + 1))
fi

echo
if [[ "$failures" -eq 0 ]]; then
  echo "── PHASE 2C ACCEPTANCE: ALL PASSED ──"
  exit 0
else
  echo "── PHASE 2C ACCEPTANCE: $failures SECTION(S) FAILED ──"
  exit 1
fi
