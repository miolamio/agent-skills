#!/usr/bin/env bash
# Phase 1 (v2.3) acceptance checks for ru-editor.
# Each check exits non-zero on failure with a clear message.
# Run from repo root: bash skills/ru-editor/scripts/check_phase1.sh

set -u
cd "$(dirname "$0")/.."   # → skills/ru-editor

failures=0
section() { echo; echo "── $1 ──"; }
fail()    { echo "FAIL: $1"; failures=$((failures+1)); }
pass()    { echo "PASS: $1"; }

section "1. Arrow check (no →, =>, ⇒ in prose; code spans are exempt)"
arrow_count=0
arrow_locations=""
for f in SKILL.md references/*.md; do
  [ -f "$f" ] || continue
  # Strip inline code spans (`...`) before checking — characters listed inside
  # backticks are documentation about banned characters, not prose use.
  hits=$(sed 's/`[^`]*`//g' "$f" | grep -cE '→|⇒|=>' || true)
  arrow_count=$((arrow_count + hits))
  if [ "$hits" -gt 0 ]; then
    arrow_locations="$arrow_locations\n$f: $hits prose-arrow line(s)"
  fi
done
if [ "$arrow_count" -eq 0 ]; then
  pass "no prose arrows in references or SKILL.md"
else
  echo -e "$arrow_locations"
  sed 's/`[^`]*`//g' SKILL.md references/*.md 2>/dev/null | grep -nE '→|⇒|=>' | head -20
  fail "found $arrow_count prose arrow occurrences (expected 0)"
fi

section "2. Emoji check (no emoji anywhere)"
emoji_count=$(grep -rcP '[\x{1F300}-\x{1FAFF}]|[\x{2600}-\x{27BF}]' SKILL.md references/ 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
if [ "$emoji_count" -eq 0 ]; then
  pass "no emoji in references"
else
  fail "found $emoji_count emoji occurrences (expected 0)"
fi

section "3. '12 operations' mislabel"
if grep -q "12 operations" SKILL.md; then
  fail "SKILL.md still says '12 operations'"
else
  pass "no '12 operations' mislabel"
fi

section "4. Required new sections in SKILL.md"
for section_name in "## Factual Integrity" "## Output Discipline" "## QA Gate"; do
  if grep -q "^$section_name$" SKILL.md; then
    pass "SKILL.md contains '$section_name'"
  else
    fail "SKILL.md missing '$section_name'"
  fi
done

section "5. factual-integrity.md exists with required sections"
file=references/factual-integrity.md
if [ ! -f "$file" ]; then
  fail "$file does not exist"
else
  pass "$file exists"
  for h in "## Allowed Responses to Vague Claims" "## Forbidden" "## Examples"; do
    if grep -q "^$h$" "$file"; then
      pass "$file contains '$h'"
    else
      fail "$file missing '$h'"
    fi
  done
fi

section "6. Invented specifics removed from editing-examples.md"
for forbidden in \
  "Работаем с 2018 года" \
  "сделали 80+ проектов" \
  "в 4 раза" \
  "200 компаний" \
  "ручную работу на 60%" \
  "бесплатно 14 дней" \
  "По данным McKinsey" \
  "72% крупных компаний" \
  "за 3 минуты вместо 20" \
  "за два дня" \
  "Работы займут 3–4 часа" \
  "Согласовывали документ два месяца" \
  "захлопнул ноутбук" \
  "сайт никуда не годится" \
  "Второй день не отвечает"
do
  if grep -qF "$forbidden" references/editing-examples.md; then
    fail "editing-examples.md still contains invented specific: \"$forbidden\""
  else
    pass "no \"$forbidden\""
  fi
done

section "7. Typography.md dash section reform"
if grep -q "Em dash (—, длинное тире):\*\* everything else" references/typography.md; then
  fail "typography.md still claims em dash for 'everything else'"
else
  pass "typography.md no longer claims em dash for 'everything else'"
fi
if grep -q "by grammatical or semantic function" references/typography.md; then
  pass "typography.md has 'by function' rule"
else
  fail "typography.md missing 'by function' rule"
fi

section "8. Always-load list trimmed (new structure)"
old_format=$(grep -c "Always load before editing" SKILL.md || true)
if [ "$old_format" -eq 0 ]; then
  pass "no old-style 'Always load before editing' rows"
else
  fail "found $old_format old-style 'Always load before editing' rows (Task 10 not done?)"
fi
if grep -q '^\*\*Always load\*\* (before any editing)' SKILL.md; then
  pass "new always-load section header present"
else
  fail "new always-load section header missing"
fi

section "9. Always-load total line count under 600"
total=0
for f in SKILL.md references/factual-integrity.md references/ai-markers-ru.md; do
  if [ -f "$f" ]; then
    n=$(wc -l < "$f")
    total=$((total + n))
  fi
done
if [ "$total" -lt 600 ]; then
  pass "always-load total: $total lines (< 600)"
else
  fail "always-load total: $total lines (expected < 600)"
fi

section "10. Version bumped to 2.3.0"
if grep -q "version: 2.3.0" SKILL.md; then
  pass "SKILL.md frontmatter version is 2.3.0"
else
  fail "SKILL.md frontmatter version is not 2.3.0"
fi

section "11. CHANGELOG exists with v2.3.0 entry"
if [ -f CHANGELOG.md ] && grep -q "## \[2.3.0\]" CHANGELOG.md; then
  pass "CHANGELOG.md has [2.3.0] entry"
else
  fail "CHANGELOG.md missing or no [2.3.0] entry"
fi

echo
if [ "$failures" -eq 0 ]; then
  echo "── ALL CHECKS PASSED ──"
  exit 0
else
  echo "── $failures CHECKS FAILED ──"
  exit 1
fi
