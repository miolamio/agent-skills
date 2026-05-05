#!/usr/bin/env bash
# ru-editor master regression runner.
# Runs all phase acceptance tests in order. Exits non-zero on any failure.
#
# Usage:
#   bash scripts/run_all_tests.sh              # all phases
#   bash scripts/run_all_tests.sh --phase 1    # only Phase 1
#   bash scripts/run_all_tests.sh --phase 2    # only Phase 2
#
# Each phase's acceptance is owned by its own script. This runner only
# orchestrates and aggregates pass/fail.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

PHASE_FILTER=""
if [[ "${1:-}" == "--phase" ]]; then
  PHASE_FILTER="${2:-}"
fi

failures=0
ran=0

run_phase() {
  local phase_num="$1"
  local label="$2"
  local cmd="$3"

  if [[ -n "$PHASE_FILTER" && "$PHASE_FILTER" != "$phase_num" ]]; then
    return 0
  fi

  echo
  echo "════════════════════════════════════════════════════════════"
  echo "  Phase $phase_num: $label"
  echo "════════════════════════════════════════════════════════════"
  ran=$((ran + 1))

  if eval "$cmd"; then
    echo "── Phase $phase_num PASSED ──"
  else
    echo "── Phase $phase_num FAILED ──"
    failures=$((failures + 1))
  fi
}

# Phase 1 — content hygiene
run_phase 1 "Content hygiene (v2.3.0)" \
  "bash skills/ru-editor/scripts/check_phase1.sh"

# Phase 2 — regex linter (added incrementally)
if [[ -f skills/ru-editor/scripts/run_phase2_acceptance.sh ]]; then
  run_phase 2 "Regex linter + seed corpus (v2.4.0)" \
    "bash skills/ru-editor/scripts/run_phase2_acceptance.sh"
fi

# Phase 3 — modes + tools tightening (added incrementally)
if [[ -f skills/ru-editor/scripts/run_phase3_acceptance.sh ]]; then
  run_phase 3 "Modes + tools tightening (v2.5.0)" \
    "bash skills/ru-editor/scripts/run_phase3_acceptance.sh"
fi

# Phase 2C — found-samples grounding additions (real-world AI-Slop corpus)
if [[ -f skills/ru-editor/scripts/run_phase2c_acceptance.sh ]]; then
  run_phase 2c "Found-samples corpus + Phase 2D linter additions (v2.7.0)" \
    "bash skills/ru-editor/scripts/run_phase2c_acceptance.sh"
fi

# Future phases — append run_phase calls here.

echo
echo "════════════════════════════════════════════════════════════"
if [[ "$ran" -eq 0 ]]; then
  echo "  No phases ran (filter '$PHASE_FILTER' matched nothing)"
  exit 2
elif [[ "$failures" -eq 0 ]]; then
  echo "  ALL $ran PHASE(S) PASSED"
  exit 0
else
  echo "  $failures of $ran PHASE(S) FAILED"
  exit 1
fi
