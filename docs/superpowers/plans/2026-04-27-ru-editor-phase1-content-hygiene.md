# ru-editor Phase 1 (v2.3) — Content Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Устранить внутренние противоречия в текущем `ru-editor` v2.2.0, добавить раздел про factual integrity, выпилить стрелки и выдуманную конкретику из примеров — без новой инфраструктуры.

**Architecture:** Чистая редактура контента. Все изменения — в существующих Markdown-файлах + один новый reference (`factual-integrity.md`) + один acceptance bash-скрипт (`scripts/check_phase1.sh`), который служит «тестом» для каждой правки и одновременно — прототипом будущего `ru_lint.py` из Phase 2.

**Tech Stack:** Bash + grep/awk для acceptance checks; Markdown для всего остального. Без новых зависимостей.

**Source spec:** `docs/superpowers/specs/2026-04-27-ru-editor-overhaul-design.md` § 5 Phase 1.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `skills/ru-editor/SKILL.md` | Modify | Добавить разделы Factual Integrity, Output Discipline, QA Gate; убрать «12 operations»; обновить таблицу always-load; bump версии |
| `skills/ru-editor/references/factual-integrity.md` | **Create** | ~80 строк: запрет на выдумку фактов, allowed responses, примеры, тест |
| `skills/ru-editor/references/typography.md` | Modify | Переписать раздел про em dash: «по функции, не как декорация»; добавить «когда НЕ использовать» |
| `skills/ru-editor/references/editing-examples.md` | Modify | Удалить выдуманную конкретику в примерах 1, 2, 5, 8, 9, 10, 11; переделать «What was fixed» в таблицы; убрать стрелки в заголовках |
| `skills/ru-editor/references/ai-markers-ru.md` | Modify | Удалить 5 стрелок (контекст-aware замена) |
| `skills/ru-editor/references/informational-style.md` | Modify | Удалить 5 стрелок |
| `skills/ru-editor/references/pretentious-words.md` | Modify | Удалить 1 стрелку в заголовке |
| `skills/ru-editor/scripts/check_phase1.sh` | **Create** | Acceptance script: `set -e` bash-проверки. Растёт по мере выполнения задач |
| `skills/ru-editor/CHANGELOG.md` | **Create** | История версий, начиная с v2.3.0 |
| `~/.claude/skills/ru-editor/` | Sync | Скопировать обновлённый src → глобальный кэш в финале |

**Out of scope для этой фазы:** новые Python-скрипты (Phase 2), режимы редактуры (Phase 3), чанкинг (Phase 4), evals (Phase 5), Codex subagent (Phase 5).

---

## Setup

- [ ] **Step 0.1: Verify clean working tree**

```bash
cd /Users/codegeek/src/agent-skills
git status
```

Expected: clean (or only `.development/specification.md` modified — that's fine).

- [ ] **Step 0.2: Create working branch**

```bash
git checkout -b ru-editor-v2.3-content-hygiene
```

- [ ] **Step 0.3: Verify current state**

```bash
grep -c "→" skills/ru-editor/SKILL.md skills/ru-editor/references/*.md
wc -l skills/ru-editor/SKILL.md skills/ru-editor/references/*.md
grep -n "12 operations" skills/ru-editor/SKILL.md
```

Expected output (baseline):
- SKILL.md: 11 arrows; ~204 lines
- editing-examples.md: 89 arrows; 262 lines
- ai-markers-ru.md: 5 arrows
- informational-style.md: 5 arrows
- typography.md: 3 arrows
- pretentious-words.md: 1 arrow
- tech-anglicisms.md: 0 arrows
- "12 operations" found at SKILL.md:58

Save this as our before-state. We're driving these numbers down.

---

## Task 1: Создать acceptance check script (наша «тестовая инфраструктура»)

**Files:**
- Create: `skills/ru-editor/scripts/check_phase1.sh`

- [ ] **Step 1.1: Write the script with checks that should currently FAIL**

Create file `skills/ru-editor/scripts/check_phase1.sh`:

```bash
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

section "1. Arrow check (no →, =>, ⇒ in references or SKILL.md)"
arrow_count=$(grep -rn -E '→|⇒|=>' SKILL.md references/ 2>/dev/null | wc -l | tr -d ' ')
if [ "$arrow_count" -eq 0 ]; then
  pass "no arrows in references"
else
  grep -rn -E '→|⇒|=>' SKILL.md references/ 2>/dev/null | head -20
  fail "found $arrow_count arrow occurrences (expected 0)"
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
# After Task 10 the old per-row "Always load before editing" cells must be gone
old_format=$(grep -c "Always load before editing" SKILL.md || true)
if [ "$old_format" -eq 0 ]; then
  pass "no old-style 'Always load before editing' rows"
else
  fail "found $old_format old-style 'Always load before editing' rows (Task 10 not done?)"
fi
# And the new section header must exist
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
```

- [ ] **Step 1.2: Make executable**

```bash
chmod +x skills/ru-editor/scripts/check_phase1.sh
```

- [ ] **Step 1.3: Run it — should fail many checks (this is correct)**

```bash
bash skills/ru-editor/scripts/check_phase1.sh
```

Expected: many FAIL lines, exit code 1. Specifically failing:
- 1 (arrows present)
- 3 (12 operations present)
- 4 (new sections missing)
- 5 (factual-integrity.md missing)
- 6 (invented specifics present)
- 7 (typography still says everything else)
- 8 (always-load > 3 likely)
- 9 (always-load > 600 lines likely)
- 10 (version is 2.2.0)
- 11 (no CHANGELOG)

These failures are our TODO list. We make each one PASS in subsequent tasks.

- [ ] **Step 1.4: Commit the check script**

```bash
git add skills/ru-editor/scripts/check_phase1.sh
git commit -m "chore(ru-editor): add Phase 1 acceptance check script"
```

---

## Task 2: Создать `references/factual-integrity.md`

**Files:**
- Create: `skills/ru-editor/references/factual-integrity.md`

- [ ] **Step 2.1: Confirm test for this task is already in check script**

Check 5 in `check_phase1.sh` validates:
- File exists
- Has section `## Allowed Responses to Vague Claims`
- Has section `## Forbidden`
- Has section `## Examples`

Run check 5 specifically:
```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A1 "5\."
```
Expected: FAIL on file existence.

- [ ] **Step 2.2: Create the file**

Create `skills/ru-editor/references/factual-integrity.md` with content:

````markdown
# Factual Integrity

The most important rule of Russian editing: **never invent specificity**.

When the source text contains vague claims like «качественный», «эффективный», «уникальный», «быстро», «с большим опытом», the editor must NOT replace them with concrete facts that did not exist in the source.

## The Problem

AI editing models — and many human editors trained on AI output — believe good editing means making text more concrete. So they replace «качественный продукт» with «надёжный продукт, протестированный на 50 000 пользователей за 5 лет». The new version is more vivid. It is also fiction.

For internal notes this might be tolerable. For client-facing copy, marketing, contracts, technical documentation, journalism, or anything published — invented specifics are a critical error. They damage trust, create legal exposure, and corrupt the historical record.

This rule **overrides** the «add specificity» principle from informational style. Inforstyle says «replace evaluations with facts»; factual integrity says «only with facts you can point to in the source».

## Allowed Responses to Vague Claims

When you encounter a vague claim with no factual support in the source, choose one:

1. **Remove it.** «Мы предлагаем качественные услуги» becomes «Мы предлагаем услуги».
2. **Weaken it.** «Эффективное решение» becomes «Решение». «Уникальный продукт» becomes «Продукт».
3. **Ask for facts.** Add an editor note: «Здесь не хватает фактов: какие сроки, какие клиенты, какие результаты».
4. **Restructure.** If the entire sentence is empty evaluation, delete it; surrounding context usually carries enough meaning.

## Forbidden

Never invent:

| Category | Examples of forbidden inventions |
|---|---|
| Numbers | Years, counts, percentages, money, durations, dimensions |
| Dates | Specific days, months, years, time periods |
| Names | Companies, clients, people, products, places |
| Examples | Specific cases, scenarios, customer stories |
| Metrics | «80% reduction», «4x faster», «3 minutes vs 20» |
| Sources | «По данным McKinsey», «исследования показывают», «эксперты считают» |
| Guarantees | «100% результат», «возврат денег», «гарантированно» |
| Calls to action | «Попробуйте 14 дней бесплатно», «оставьте заявку до пятницы» |

## Test

Before returning edited text, scan every number, name, date, percentage in the output. For each one, point to the source location it came from. If you cannot — you invented it. Remove it.

## Examples

### Bad (current ru-editor v2.2 example, fixed in v2.3)

Source:
> Наша компания является ведущим поставщиком инновационных решений в области ИИ. Мы стремимся к совершенству и предлагаем широкий спектр услуг.

Old "good" output (invents specifics):
> Мы разрабатываем ИИ-решения: чат-боты, системы анализа данных и автоматизацию документооборота. **Работаем с 2018 года, сделали 80+ проектов для ритейла и финтеха. Средний срок запуска — 6 недель.**

The bolded segment was invented by the editor. Year, count, sectors, timeframe — none of this was in the source.

### Good (Factual Integrity-compliant)

Source: same as above.

Output (any of three valid approaches):

**Approach 1 — Remove empty claims:**
> Мы разрабатываем ИИ-решения для бизнеса.

**Approach 2 — Editor note:**
> Мы разрабатываем ИИ-решения для бизнеса.
>
> Editor note: текст не содержит фактов о сроках, числе проектов, отраслях или результатах. Для сильного маркетингового сообщения нужны конкретные данные от автора.

**Approach 3 — Ask the author:**
> [Editor question to author: какие конкретные продукты вы делаете? с какого года? сколько клиентов? в каких отраслях?]

## Why This Matters More Than «Make It Concrete»

Specificity makes text persuasive. That's why models invent it — they're optimizing for «sounds good». But persuasive fiction is fraud. The editor's job is to make a text **as good as the facts allow**, not better than them. If the facts are weak, the honest output is a weak text plus a note saying «here's what's missing».

A weak honest text is recoverable: the author adds facts, the editor revises. An invented confident text is unrecoverable: the lie is now in the document, and nobody knows it's a lie.
````

- [ ] **Step 2.3: Run check 5**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A4 "5\. factual"
```

Expected: 4 PASS lines.

- [ ] **Step 2.4: Verify line count is reasonable**

```bash
wc -l skills/ru-editor/references/factual-integrity.md
```

Expected: between 70 and 100 lines.

- [ ] **Step 2.5: Commit**

```bash
git add skills/ru-editor/references/factual-integrity.md
git commit -m "feat(ru-editor): add factual-integrity reference"
```

---

## Task 3: Переписать раздел про em dash в `typography.md`

**Files:**
- Modify: `skills/ru-editor/references/typography.md:24-44`

- [ ] **Step 3.1: Run check 7 to confirm current failure**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A2 "7\."
```

Expected: FAIL — typography still claims «everything else».

- [ ] **Step 3.2: Replace lines 24-44 of typography.md**

The exact `old_string` to replace (lines 24–44 inclusive):

```
## Dashes: Three Types

Russian uses three distinct characters. Never confuse them.

**Hyphen (-, дефис):** compound words and particles only.
Examples: кто-то, из-за, по-русски, всё-таки, как-нибудь.

**En dash (–, короткое тире):** numeric ranges, without spaces.
Examples: 10–15 минут, 2020–2025, стр. 40–45, понедельник–пятница.

**Em dash (—, длинное тире):** everything else. Always with spaces on both sides.
Examples:
- Definitions: Автоматизация — ключ к эффективности.
- Parenthetical: Навыки — один из самых мощных способов — позволяют настроить Claude.
- Subject–predicate replacement: Компания — лидер рынка.
- Before clauses: Мы завершили сделку — это позволит расширить линейку.

CRITICAL: always use proper Unicode characters in translation output.
- Em dash: — (U+2014), not double hyphen (--)
- En dash: – (U+2013), not single hyphen (-)
- Never use double hyphen (--) as a substitute for any type of dash.
```

Replace with:

```
## Dashes: Three Types

Russian uses three distinct characters. Never confuse them.

**Hyphen (-, дефис):** compound words and particles only.
Examples: кто-то, из-за, по-русски, всё-таки, как-нибудь.

**En dash (–, короткое тире):** numeric ranges, without spaces.
Examples: 10–15 минут, 2020–2025, стр. 40–45, понедельник–пятница.

**Em dash (—, длинное тире):** by grammatical or semantic function only — not as a decorative AI pause. Always with spaces on both sides.

### When to use em dash

- **Subject–predicate copula** (replaces implicit «есть»): Компания — лидер рынка. Москва — столица.
- **Definitions** where intonation breaks before the explanation: Автоматизация — передача рутинных задач машине.
- **Constructions with «это»**: Хороший редактор — это тот, кто знает, когда не править.
- **Direct speech**: «Что вы делаете?» — спросил он.
- **Author's pause** for emphasis (sparingly, max once per paragraph): Мы завершили сделку — наконец-то.

### When NOT to use em dash

If you reach for em dash to add «punchy rhythm» — stop. The AI overuse pattern is:

| Bad | Why | Better |
|---|---|---|
| Наш подход — это не просто инструмент — это новая философия. | Decorative double-dash. | Наш подход помогает быстрее согласовывать задачи. |
| Система анализирует данные — выявляет риски — предлагает решение. | Dash as list separator. | Система анализирует данные, выявляет риски и предлагает решение. |
| Мы запустили продукт — продажи выросли. | Two separate thoughts. | Мы запустили продукт. Продажи выросли. |

**Hard limit:** at most one em dash per paragraph. If a paragraph needs more, restructure.

### Dash discipline reference

| Pause function | Right punctuation |
|---|---|
| Two separate thoughts | Period |
| Weak pause inside one thought | Comma |
| Second part explains or enumerates | Colon |
| Subject = predicate | Em dash |
| Decorative AI rhythm | None — restructure |

CRITICAL: always use proper Unicode characters.
- Em dash: — (U+2014), not double hyphen (--)
- En dash: – (U+2013), not single hyphen (-)
- Never use double hyphen (--) as a substitute for any type of dash.
```

- [ ] **Step 3.3: Re-run check 7**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A3 "7\."
```

Expected: 2 PASS lines.

- [ ] **Step 3.4: Commit**

```bash
git add skills/ru-editor/references/typography.md
git commit -m "fix(ru-editor): em dash by function only, drop 'everything else' rule"
```

---

## Task 4: Удалить выдуманную конкретику из `editing-examples.md`

**Files:**
- Modify: `skills/ru-editor/references/editing-examples.md`

This task touches 7 examples (1, 2, 5, 8, 9, 10, 11). Each replacement is shown in full. Examples 3, 4, 6, 7 in this file have minor or borderline issues that are out of scope for Phase 1 — Phase 2's diff-regex linter will surface anything that survives.

- [ ] **Step 4.1: Run check 6 to confirm current failure**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A16 "6\. Invented"
```

Expected: 15 FAIL lines (one per forbidden string).

- [ ] **Step 4.2: Fix Example 1 (lines ~13-28)**

Locate the section starting `## 1. AI-Heavy Corporate Text` and replace its `### After:` and `### What was fixed:` blocks.

Find the `### After:` block currently containing:
```
Мы разрабатываем ИИ-решения: чат-боты, системы анализа данных и автоматизацию документооборота. Работаем с 2018 года, сделали 80+ проектов для ритейла и финтеха. Средний срок запуска — 6 недель.
```

Replace with:
```
Мы разрабатываем ИИ-решения для бизнеса.

> Editor note: исходник не содержит фактов о сроках, числе проектов, отраслях или результатах. Для сильного маркетингового сообщения попросите автора прислать конкретику (год основания, число клиентов, кейсы, средние сроки) и редактируйте уже на её основе.
```

Then replace the `### What was fixed:` bullet list (currently 10 bullet items with `→`) with:

```
### What was fixed

| Было | Стало | Почему |
|---|---|---|
| «Является ведущим поставщиком» | удалено | штамп без доказательств |
| «Инновационных решений» | удалено | пустая оценка |
| «Стремимся к совершенству» | удалено | штамп |
| «Широкий спектр услуг» | удалено | штамп |
| «Выйти на новый уровень» | удалено | штамп |
| «Команда профессионалов» | удалено | штамп |
| «Богатым опытом» | удалено | оценка без фактов |
| «Индивидуальным подходом» | удалено | штамп |
| «Более того» | удалено | AI-филлер |
| «Качественный результат в кратчайшие сроки» | удалено | оценка без фактов |

**Не добавлено:** ни года основания, ни числа проектов, ни отраслей, ни сроков. Их не было в исходнике — выдумывать запрещено (см. `factual-integrity.md`).
```

- [ ] **Step 4.3: Fix Example 2 (around line 39)**

Find the `### After:` block:
```
Обновляем серверы — часть сервисов временно недоступна. Работы займут 3–4 часа. Напишем, когда всё заработает.
```

Replace with:
```
Обновляем серверы — часть сервисов временно недоступна. Напишем, когда всё заработает.
```

(Removed «Работы займут 3–4 часа» — invented duration. Source said only that work was being done.)

In the `### What was fixed:` block, locate any reference to the duration and remove it. Convert the bullet list to a table (same format as Example 1) — keep all OTHER fix descriptions but rephrase to remove `→`. Specifically:

Replace the entire `### What was fixed:` bullet list with:

```
### What was fixed

| Было | Стало | Почему |
|---|---|---|
| «В связи с проведением мероприятий по модернизации» | «Обновляем серверы» | канцелярит превращён в глагол |
| «Осуществляется временное ограничение доступа» | «часть сервисов временно недоступна» | номинализация снята |
| «К ряду сервисов» | «часть сервисов» | конкретнее, без жаргона |
| «Данные работы проводятся в целях повышения надёжности» | удалено | пустое объяснение |
| «Обеспечения бесперебойного функционирования» | удалено | тройная номинализация |
| «Вышеуказанных» | удалено | канцелярит |
| «Будет сообщено дополнительно» | «Напишем, когда всё заработает» | пассив снят, живой язык |

**Не добавлено:** ни длительности работ, ни их объёма. Источник этих данных в исходнике отсутствует.
```

- [ ] **Step 4.4: Fix Example 5 (around line 105)**

Find the `### After:` block:
```
Наш сервис ускоряет обработку заявок в 4 раза. За последний год подключились 200 компаний — в среднем они сократили ручную работу на 60%. Попробуйте бесплатно 14 дней.
```

Replace with:
```
> Editor note: исходник состоит из пустых оценок («уникальный», «высококачественное», «инновационное», «передовых», «эффективное») без единого факта. Чтобы получить полезный текст, нужны цифры от автора: что именно ускоряется и насколько, сколько клиентов, какие отрасли, какой срок.
>
> Минимально допустимая редактура без выдумок:

Наш сервис помогает обрабатывать заявки быстрее.
```

Replace the `### What was fixed:` block with:

```
### What was fixed

| Было | Стало | Почему |
|---|---|---|
| «Уникальный продукт» | «Наш сервис» | оценка снята |
| «Представляет собой высококачественное инновационное решение» | удалено | три пустые оценки подряд |
| «Является идеальным выбором» | удалено | канцелярит + оценка |
| «Динамично развивающихся компаний» | удалено | штамп |
| «Передовым технологиям и профессиональному подходу» | удалено | двойной штамп |
| «Обеспечиваем максимально эффективное решение» | удалено | оценка без фактов |
| «Значительное повышение производительности» | удалено | оценка без числа |
| «Существенную экономию ресурсов» | удалено | дублирует предыдущее |

**Не добавлено:** ни «в 4 раза», ни «200 компаний», ни «60%», ни «14 дней». Эти числа выглядят убедительно, но их в исходнике не было — это и есть критическая ошибка, которую старая версия скилла учила делать. См. `factual-integrity.md`.
```

- [ ] **Step 4.5: Fix Example 9 (around line 193)**

Find the `### After:` block:
```
По данным McKinsey, 72% крупных компаний внедрили хотя бы один ИИ-инструмент в 2025 году — годом ранее было 55%.
```

Replace with:
```
> Editor note: исходник заявляет «стремительно набирает популярность», «всё больше компаний», «устойчивая тенденция» — но в нём нет ни одного факта. Если автор может подтвердить тенденцию данными (опросом, отчётом, статистикой), вставьте источник в исходник и редактируйте на основе настоящих данных. Если данных нет — параграф лучше переписать в гипотезу или удалить.
>
> Минимально допустимая редактура без выдумок:

Многие компании присматриваются к автоматизации с ИИ.
```

Replace the `### What was fixed:` block with:

```
### What was fixed

| Было | Стало | Почему |
|---|---|---|
| «Стремительно набирает популярность» | удалено | непроверяемое утверждение |
| «Всё больше компаний» | «Многие компании» | конкретика без чисел невозможна |
| «В последнее время» | удалено | паразит времени |
| «Судя по всему, наметилась устойчивая тенденция» | удалено | непроверяемое утверждение |
| «Едва ли найдётся бизнес, который» | удалено | непроверяемое утверждение |
| Призыв к действию через ИИ | «присматриваются к автоматизации» | мягкое наблюдение вместо громкого вывода |

**Не добавлено:** ни «McKinsey», ни «72%», ни «2025», ни «55%». Старая версия учила выдумывать ссылки на исследования — это запрещено (см. `factual-integrity.md`). Цифры можно ставить только если они есть в исходнике или поданы автором.
```

- [ ] **Step 4.6a: Fix Example 8 (around line 172) — invented specifics**

The current `### After:` for Example 8 invents three specific facts not in the source: «захлопнул ноутбук», `«сайт никуда не годится»`, «Второй день не отвечает на звонки и письма». The editorial principle (remove euphemisms, call things by their names) is correct, but the demonstration smuggles in fabricated incidents. We rewrite the example so the principle survives without the invented facts.

Find the `### After:` block:
```
У меня беда с клиентом. На встрече директор захлопнул ноутбук, сказал «сайт никуда не годится» и ушёл. Второй день не отвечает на звонки и письма. Не знаю, что делать — нужна помощь.
```

Replace with:
```
Переговоры с клиентом замедлены. На встрече клиент негативно оценил работу и прервал встречу. Мы пытаемся восстановить контакт.

> Editor note: реальный пример эвфемизмов в этом исходнике не разоблачить без фактов от автора: что именно клиент сказал, что конкретно произошло на встрече, как давно нет ответа. Минимально допустимая редактура снимает обтекаемые формулировки, но не выдумывает диалог. Если автор готов поделиться деталями — на их основе можно сделать резкий человеческий текст.
```

Replace the `### What was fixed:` block with:

```
### What was fixed

| Было | Стало | Почему |
|---|---|---|
| «Замедлены из-за непредвиденных обстоятельств организационного характера» | «Замедлены» | канцелярит-подушка снят |
| «Неоднозначно отозвался о качестве проделанной работы» | «Негативно оценил работу» | эвфемизм заменён нейтральным фактом |
| «Был вынужден прервать встречу» | «Прервал встречу» | пассив снят |
| «Делаем всё возможное, чтобы восстановить коммуникацию» | «Пытаемся восстановить контакт» | эвфемизм + заумь сняты |
| «Продуктивное обсуждение проекта» | удалено | штамп без содержания |

**Не добавлено:** ни «директор захлопнул ноутбук», ни цитаты «сайт никуда не годится», ни «второй день не отвечает». Эти детали выглядят как живая речь, но в исходнике их не было — выдумка категорически запрещена даже если она «вкуснее».
```

- [ ] **Step 4.6b: Fix Example 10 (around line 213) — invented specific «два месяца»**

Find the `### After:` block:
```
Согласовывали документ два месяца — зато теперь текст понятный и короткий.
```

Replace with:
```
Согласовывали документ долго — зато теперь текст понятный и короткий.

> Editor note: исходник не указывает срок согласования. Если автор может назвать его (две недели? два месяца? полгода?) — подставьте реальное число вместо «долго». Без подтверждённого срока конкретику добавлять нельзя.
```

Replace the `### What was fixed:` block with:

```
### What was fixed

| Было | Стало | Почему |
|---|---|---|
| «Долгого, нудного и утомительного» | «Долго» | три синонима свёрнуты в одно слово; конкретный срок не подставлен — его не было в исходнике |
| «Процесса согласования» | «Согласовывали» | номинализация заменена глаголом |
| «Чёткой, ясной и понятной» | «Понятный» | три синонима свёрнуты |
| «Кратким, лаконичным и сжатым» | «Короткий» | три синонима свёрнуты |
| «Информативным и содержательным» | удалено | оценка без доказательств |

**Не добавлено:** ни «два месяца», ни любого другого срока. Свернуть синонимы можно, выдумать длительность — нельзя.
```

- [ ] **Step 4.7: Fix Example 11 (around line 232)**

Find the `### After:` block:
```
Мы автоматизировали обработку заявок — теперь каждая проходит за 3 минуты вместо 20. Новые сотрудники учатся по документации и начинают работать самостоятельно за два дня.
```

Replace with:
```
Мы автоматизировали обработку заявок. Новые сотрудники учатся по документации.

> Editor note: исходник заявляет «повышение эффективности», «гарантия успешного освоения» — но без чисел. Если есть метрики (сокращение времени обработки, срок обучения), редактор должен попросить их у автора и подставить настоящие цифры.
```

Replace the `### What was fixed:` block with:

```
### What was fixed

| Было | Стало | Почему |
|---|---|---|
| «Внедрение системы автоматизации» | «Мы автоматизировали» | сильное подлежащее «мы» + глагол |
| «Обеспечивает повышение эффективности» | удалено | глагол-пустышка + номинализация без фактов |
| «Процессов обработки заявок» | «обработку заявок» | тройная номинализация снята |
| «Наличие подробной документации является гарантией» | «учатся по документации» | два слабых глагола заменены одним сильным |
| «Успешного освоения инструмента новыми сотрудниками» | «учатся» | номинализация снята |

**Не добавлено:** ни «3 минуты вместо 20», ни «за два дня». Эти числа выглядят как полезный факт, но их в исходнике не было — выдумывать запрещено.
```

- [ ] **Step 4.8: Run check 6 to verify all invented specifics gone**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A16 "6\. Invented"
```

Expected: 15 PASS lines (one per forbidden string in the script).

- [ ] **Step 4.9: Commit**

```bash
git add skills/ru-editor/references/editing-examples.md
git commit -m "fix(ru-editor): remove invented specifics from editing-examples (7 cases)"
```

---

## Task 5: Заменить стрелки на не-arrow форматы во всех файлах

**Files:**
- Modify: `skills/ru-editor/SKILL.md`
- Modify: `skills/ru-editor/references/editing-examples.md`
- Modify: `skills/ru-editor/references/ai-markers-ru.md`
- Modify: `skills/ru-editor/references/informational-style.md`
- Modify: `skills/ru-editor/references/typography.md`
- Modify: `skills/ru-editor/references/pretentious-words.md`

Strategy: replace `→` arrows context-by-context. The mapping rules:

| Pattern | Replacement |
|---|---|
| `## Section Title → Other Title` | `## Section Title: Other Title` |
| `«X» → «Y»` in "What was fixed" bullets | Convert bullet list to a table (already done in Task 4 for example 1, 2, 5, 9, 11) |
| `«X» → «Y»` inline in flowing text | `«X» — заменить на «Y»` or convert sentence to use «вместо ... используем» |
| `Foo → Bar → Baz` (chains) | Convert to numbered list or sentence: «Foo, потом Bar, потом Baz» |
| Title with arrow | Use colon |

- [ ] **Step 5.1: Confirm baseline arrow count after Task 4**

```bash
grep -c "→" skills/ru-editor/SKILL.md skills/ru-editor/references/*.md
```

Note current counts. Many should be down already due to Task 4. Remaining work:
- SKILL.md: 11
- ai-markers-ru.md: 5
- informational-style.md: 5
- typography.md: 3
- pretentious-words.md: 1
- editing-examples.md: any remaining (should be 0 if Task 4 examples 1-11 all converted)

- [ ] **Step 5.2: Fix `pretentious-words.md` (1 arrow, in title)**

Read first line:
```bash
head -1 skills/ru-editor/references/pretentious-words.md
```

Replace heading line `# Pretentious Words → Simple Replacements (Заумное → Просто)` with:

```
# Pretentious Words: Simple Replacements (Заумные слова: простые замены)
```

- [ ] **Step 5.3: Fix `typography.md` (3 arrows, all on lines 89, 97, 106)**

Replace inline arrow in line 89:
- Old: `**Items are complete sentences** → capital letter, period at end of each:`
- New: `**Items are complete sentences:** capital letter, period at end of each:`

Replace inline arrow in line 97:
- Old: `**Items are phrases or fragments** → lowercase, semicolon, period at the very end:`
- New: `**Items are phrases or fragments:** lowercase, semicolon, period at the very end:`

Replace inline arrow in line 106:
- Old: `**Items are single words or very short noun phrases** → lowercase, comma or semicolon, period at the very end:`
- New: `**Items are single words or very short noun phrases:** lowercase, comma or semicolon, period at the very end:`

- [ ] **Step 5.4: Fix `ai-markers-ru.md` (5 arrows)**

Locate each arrow occurrence:

```bash
grep -n "→" skills/ru-editor/references/ai-markers-ru.md
```

For each one, apply context-appropriate replacement:

Line 47: `- «продукт» → «решение» → «инструмент» → «платформа» (for the same thing)`
Replace with: `- «продукт», потом «решение», потом «инструмент», потом «платформа» — для одного и того же объекта`

Line 48: `- «пользователь» → «клиент» → «человек» → «специалист» (for the same person)`
Replace with: `- «пользователь», потом «клиент», потом «человек», потом «специалист» — для одного и того же человека`

Line 77: `- Introduction sentence → 3 bullet points → summary sentence`
Replace with: `- Introduction sentence, then 3 bullet points, then summary sentence`

Line 78: `- Or: Definition → Advantages → Challenges → Future outlook`
Replace with: `- Or: Definition, then Advantages, then Challenges, then Future outlook`

Line 221 (inside text): `See \`pretentious-words.md\` for the complete «заумно → просто» table.`
Replace with: `See \`pretentious-words.md\` for the complete «заумно и просто» table.`

- [ ] **Step 5.5: Fix `informational-style.md` (5 arrows, exact replacements)**

| Line | Old | New |
|---|---|---|
| 100 | `### Verbal nouns → verbs` | `### Verbal nouns: verbs` |
| 117 | `### Passive → active` | `### Passive: active` |
| 196 | `### Common euphemisms → direct replacements` | `### Common euphemisms: direct replacements` |
| 261 | `All three work equally well → the sentence says nothing.` | `All three work equally well, so the sentence says nothing.` |
| 294 | `If every paragraph follows Introduction → Details → Summary, vary the structure.` | `If every paragraph follows Introduction, then Details, then Summary, vary the structure.` |

Apply each as an exact string replacement.

- [ ] **Step 5.6: Fix `SKILL.md` (11 arrows, exact replacements)**

Apply each replacement below. Since SKILL.md will also have new sections inserted by Tasks 6, 7, 8, line numbers may shift — match by string content, not line number.

**Line ~49 (Reference table description):**
- Old: `**Critical:** 100+ pairs of «заумно → просто» replacements — complex borrowed words with simple Russian equivalents`
- New: `**Critical:** 100+ pairs of «заумно и просто» replacements — complex borrowed words with simple Russian equivalents`

(Note: this line will be replaced entirely by Task 10 anyway when the reference table is rewritten. Either fix it now and let Task 10 reformat, or skip and let Task 10 produce the arrow-free version. Task 10's replacement table contains no arrows, so this line is automatically fixed there.)

**Operation 3 (line ~64):**
- Old: `**Evaluation-to-fact replacement** — replace empty adjectives with specifics: «качественный» → facts about quality, «эффективный» → measurable results, «уникальный» → what makes it unique. If facts are unavailable, delete the evaluation entirely.`
- New: `**Evaluation-to-fact replacement** — replace empty adjectives with specifics: для «качественный» подобрать факты о качестве; для «эффективный» — измеримые результаты; для «уникальный» — что именно делает уникальным. If facts are unavailable, delete the evaluation entirely. **Important:** only with facts present in the source. Never invent — see `## Factual Integrity`.`

**Operation 4 (line ~66):**
- Old: `**De-nominalization** — convert verbal nouns to verbs: «осуществление поддержки» → «поддерживаем», «проведение анализа» → «проанализировали», «обеспечение выполнения» → «обеспечить».`
- New: `**De-nominalization** — convert verbal nouns to verbs: «осуществление поддержки» становится «поддерживаем»; «проведение анализа» — «проанализировали»; «обеспечение выполнения» — «обеспечить».`

**Operation 5 (line ~68):**
- Old: `**Active voice and strong actors** — rewrite passive constructions: «было принято решение» → «мы решили». Find the hidden actor and hidden action.`
- New: `**Active voice and strong actors** — rewrite passive constructions: вместо «было принято решение» используем «мы решили». Find the hidden actor and hidden action.`

**Operation 6 (line ~70):**
- Old: `**Pretentious word simplification** — replace complex borrowed words with simple Russian equivalents: «функционировать» → «работать», «трансформация» → «изменение», «имплементация» → «внедрение», «верификация» → «проверка».`
- New: `**Pretentious word simplification** — replace complex borrowed words with simple Russian equivalents: «функционировать» становится «работать»; «трансформация» — «изменение»; «имплементация» — «внедрение»; «верификация» — «проверка».`

**Operation 7 (line ~72):**
- Old: `**Euphemism removal** — replace soft hedging language with direct statements: «определённые сложности» → «серьёзные проблемы», «неоднозначный результат» → «провал», «делаем всё возможное» → what you're actually doing.`
- New: `**Euphemism removal** — replace soft hedging language with direct statements: «определённые сложности» становится «серьёзные проблемы»; «неоднозначный результат» — «провал»; вместо «делаем всё возможное» нужно сказать, что именно делаете.`

**Operation 8 (line ~74):**
- Old: `**Unfounded claim removal** — delete or replace vague generalizations presented as facts: «всё больше людей» → cite data or delete, «стремительно набирает популярность» → numbers or delete, «судя по всему» → state the source or delete.`
- New: `**Unfounded claim removal** — delete or replace vague generalizations presented as facts: для «всё больше людей» нужны цифры или удалить; для «стремительно набирает популярность» — числа или удалить; для «судя по всему» — назвать источник или удалить.`

**Operation 9 (line ~76):**
- Old: `**Close synonym cleanup** — when multiple near-synonyms are piled in a list, keep the strongest, delete the rest: «долгого, нудного и утомительного» → «нудного» or better yet a fact: «два месяца».`
- New: `**Close synonym cleanup** — when multiple near-synonyms are piled in a list, keep the strongest, delete the rest: из «долгого, нудного и утомительного» оставить «нудного», или лучше — факт «два месяца» (если он есть в исходнике).`

**Operation 11 (line ~80):**
- Old: `**Syntax simplification** — break split constructions where parts are far apart: «не только [long], но и [long]» → two sentences. Simplify indirect speech: «сказал, что...» → direct form.`
- New: `**Syntax simplification** — break split constructions where parts are far apart: «не только [long], но и [long]» разбить на два предложения. Simplify indirect speech: «сказал, что...» превращаем в прямую форму.`

**Operation 16 (line ~90):**
- Old: `(a) untranslated English terms with Russian equivalents: "edge cases" → «граничные случаи», "error boundaries" → «обработчики ошибок»; (b) transliterated anglicisms: «хелперы» → «вспомогательные функции», «дебаг» → «отладка»; (c) mixed-language compounds: «accessibility-лейблы» → «атрибуты доступности»; (d) calques — literal translations of English idioms: «высокорычажная техника» → «самая эффективная техника».`
- New: `(a) untranslated English terms with Russian equivalents: "edge cases" заменяется на «граничные случаи»; "error boundaries" — на «обработчики ошибок»; (b) transliterated anglicisms: «хелперы» — «вспомогательные функции»; «дебаг» — «отладка»; (c) mixed-language compounds: «accessibility-лейблы» — «атрибуты доступности»; (d) calques — literal translations of English idioms: «высокорычажная техника» — «самая эффективная техника».`

**Operation 18 (line ~94):**
- Old: `Replace with a concrete list: «от мега-промпта до Trust-Then-Verify Gap» → «мега-промпт, Kitchen Sink, Fix Loop, Trust-Then-Verify Gap и другие».`
- New: `Replace with a concrete list: вместо «от мега-промпта до Trust-Then-Verify Gap» — «мега-промпт, Kitchen Sink, Fix Loop, Trust-Then-Verify Gap и другие».`

- [ ] **Step 5.7: Fix any remaining arrows in `editing-examples.md`**

```bash
grep -n "→" skills/ru-editor/references/editing-examples.md
```

Tasks 4 already converted examples 1, 2, 5, 9, 11. Examples 3, 4, 6, 7, 8, 10 still have arrows in their `### What was fixed:` lists and possibly in section headings. Convert each in the same style as Task 4: bullets become tables, headings use colon.

For section headings, e.g.:
- Old: `## 3. AI-Generated Blog Post → Human-Sounding Article`
- New: `## 3. AI-Generated Blog Post: Human-Sounding Article`

For bullet lists with arrows, convert to `| Было | Стало | Почему |` table.

For the "Quick Reference" table at the end (around line 245), the table format `| Pattern | Before | After |` is fine — but check if any cell content has `→`. Replace those with proper "Before/After" split or natural language.

- [ ] **Step 5.8: Run check 1 — should now PASS (zero arrows everywhere)**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A2 "1\. Arrow"
```

Expected: PASS no arrows in references.

- [ ] **Step 5.9: Commit**

```bash
git add skills/ru-editor/SKILL.md skills/ru-editor/references/
git commit -m "fix(ru-editor): replace all arrows in references with proper formatting"
```

---

## Task 6: Добавить раздел `## Factual Integrity` в SKILL.md

**Files:**
- Modify: `skills/ru-editor/SKILL.md`

- [ ] **Step 6.1: Confirm check 4 currently fails for this section**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep "Factual Integrity"
```

Expected: FAIL.

- [ ] **Step 6.2: Insert the section**

Find the line in SKILL.md that says `## Important Rules` (line 20). Insert the new section directly BEFORE it. So `## Factual Integrity` will be the first numbered section after the title and before `## Important Rules`.

Insert this content:

```markdown
## Factual Integrity

Never invent specificity. When the source contains vague claims («качественный», «эффективный», «уникальный», «быстро», «с большим опытом»), choose one of these allowed responses:

1. **Remove** the claim.
2. **Weaken** it to a neutral statement.
3. **Ask** for missing facts via editor note.
4. **Restructure** to drop the empty evaluation.

**Forbidden inventions:** numbers, dates, names, examples, metrics, sources, guarantees, calls to action.

This rule overrides «add specificity» from informational style. Inforstyle says «replace evaluations with facts»; factual integrity says «only with facts you can point to in the source».

See [references/factual-integrity.md](references/factual-integrity.md) for full discussion and examples.

```

- [ ] **Step 6.3: Run check 4 for Factual Integrity**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep "Factual Integrity"
```

Expected: PASS.

- [ ] **Step 6.4: Commit**

```bash
git add skills/ru-editor/SKILL.md
git commit -m "feat(ru-editor): add Factual Integrity section to SKILL.md"
```

---

## Task 7: Добавить раздел `## Output Discipline` в SKILL.md

**Files:**
- Modify: `skills/ru-editor/SKILL.md`

- [ ] **Step 7.1: Confirm check 4 currently fails for this section**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep "Output Discipline"
```

Expected: FAIL.

- [ ] **Step 7.2: Insert the section**

Insert directly AFTER the `## Factual Integrity` section (before `## Important Rules`):

```markdown
## Output Discipline

The final edited text must NOT contain:

- **Emoji** of any kind.
- **Arrows** in Russian prose: `→`, `=>`, `->`, `⇒`. Use words instead: «заменить на», «состоит из», «после этого». Exception: code blocks, formulas, CLI output requested by the user.
- **Straight quotes** `"..."` or `'...'` in Russian text outside code. Use «» for primary, „" for nested.
- **Double hyphen** `--` instead of em dash `—`.

Em dash is used **by grammatical or semantic function** (subject–predicate copula, definitions with intonation break, direct speech). It is NOT used to imitate punchy AI prose. If a dash separates two independent thoughts, use a period. If the pause is weak, use a comma. If the second part explains, use a colon.

**Hard limit:** at most one em dash per paragraph.

See [references/typography.md](references/typography.md) for full typography rules.

```

- [ ] **Step 7.3: Run check 4 for Output Discipline**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep "Output Discipline"
```

Expected: PASS.

- [ ] **Step 7.4: Commit**

```bash
git add skills/ru-editor/SKILL.md
git commit -m "feat(ru-editor): add Output Discipline section to SKILL.md"
```

---

## Task 8: Добавить раздел `## QA Gate` в SKILL.md

**Files:**
- Modify: `skills/ru-editor/SKILL.md`

- [ ] **Step 8.1: Confirm check 4 currently fails for this section**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep "QA Gate"
```

Expected: FAIL.

- [ ] **Step 8.2: Insert the section**

Insert directly AFTER `## Output Discipline`:

```markdown
## QA Gate

Before returning edited text, verify:

1. **No invented facts.** Every number, name, date, percentage in the output must trace to the source.
2. **No protected spans changed.** Code, URLs, commands, file paths, API names, product names — unchanged.
3. **No banned outputs.** No emoji, no arrows in prose, no straight quotes in Russian outside code, no `--`.
4. **No surviving banned AI markers** in final text: «погружаемся», «погрузимся», «ландшафт» (in AI sense), «гобелен», «является свидетельством», «стоит отметить».
5. **Structure preserved.** Headings, list items, paragraphs counted in vs out — no silent loss.

In v2.3 these checks are manual self-checks during Step 2 (Self-Reflection). Phase 2 (v2.4) will introduce `scripts/ru_lint.py` for deterministic verification — when available, prefer the script over self-check.

```

- [ ] **Step 8.3: Run check 4 for QA Gate**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep "QA Gate"
```

Expected: PASS.

- [ ] **Step 8.4: Commit**

```bash
git add skills/ru-editor/SKILL.md
git commit -m "feat(ru-editor): add QA Gate placeholder section (Phase 2 hook)"
```

---

## Task 9: Исправить «12 operations» mislabel в SKILL.md

**Files:**
- Modify: `skills/ru-editor/SKILL.md` (line ~58)

- [ ] **Step 9.1: Confirm check 3 currently fails**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A1 "3\."
```

Expected: FAIL — `12 operations` present.

- [ ] **Step 9.2: Find and fix the line**

Locate:
```bash
grep -n "12 operations" skills/ru-editor/SKILL.md
```

Replace text:
- Old: `Read the text as a whole first. Understand its purpose, audience, and register. Then pass through it applying these 12 operations:`
- New: `Read the text as a whole first. Understand its purpose, audience, and register. Then pass through it applying these 18 operations:`

- [ ] **Step 9.3: Run check 3**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A1 "3\."
```

Expected: PASS.

- [ ] **Step 9.4: Commit**

```bash
git add skills/ru-editor/SKILL.md
git commit -m "fix(ru-editor): correct '12 operations' mislabel to 18"
```

---

## Task 10: Подрезать always-load список в таблице рефренсов

**Files:**
- Modify: `skills/ru-editor/SKILL.md:43-53` (таблица Reference Files)

- [ ] **Step 10.1: Confirm check 8 currently fails (likely)**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A1 "8\."
```

Expected: FAIL — too many "Always load" entries.

- [ ] **Step 10.2: Replace the Reference Files table**

Find the existing table (lines ~43-53 of SKILL.md). Replace the entire table (including the header `## Reference Files` and the intro line) with:

```markdown
## Reference Files

The skill loads references at different stages. Most are loaded on trigger to keep the always-loaded context small.

**Always load** (before any editing):

| File | Contents |
|------|----------|
| [references/factual-integrity.md](references/factual-integrity.md) | The most important rule: never invent specificity. Allowed responses, forbidden inventions, examples |
| [references/ai-markers-ru.md](references/ai-markers-ru.md) | Russian AI writing markers — ChatGPT-isms, structural patterns, tone markers, synonym clusters |

**Load on trigger:**

| File | When to load |
|------|--------------|
| [references/typography.md](references/typography.md) | When dealing with quotes, dashes, lists, numbers, dates, letter «ё»; when typography violations are detected |
| [references/informational-style.md](references/informational-style.md) | When applying informational style: stop words, evaluations, euphemisms, unfounded claims, syntax, bureaucratese, paragraph transitions |
| [references/pretentious-words.md](references/pretentious-words.md) | When the text contains complex borrowed words that have simple Russian equivalents |
| [references/tech-anglicisms.md](references/tech-anglicisms.md) | When editing technical or educational text with anglicisms, calques, or mixed-language compounds |
| [references/editing-examples.md](references/editing-examples.md) | For complex edits or unfamiliar text types — 11 before/after pairs by problem type |
```

- [ ] **Step 10.3: Run checks 8 and 9**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A1 -E "(8\.|9\.)"
```

Expected: PASS for both.

- [ ] **Step 10.4: Commit**

```bash
git add skills/ru-editor/SKILL.md
git commit -m "refactor(ru-editor): trim always-load to 2 files; rest load on trigger"
```

---

## Task 11: Bump версии и CHANGELOG

**Files:**
- Modify: `skills/ru-editor/SKILL.md` (frontmatter)
- Create: `skills/ru-editor/CHANGELOG.md`

- [ ] **Step 11.1: Confirm checks 10 and 11 currently fail**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A1 -E "(10\.|11\.)"
```

Expected: FAIL for both.

- [ ] **Step 11.2: Bump version in SKILL.md frontmatter**

Find:
```yaml
  version: 2.2.0
```

Replace with:
```yaml
  version: 2.3.0
```

- [ ] **Step 11.3: Create CHANGELOG.md**

Create `skills/ru-editor/CHANGELOG.md`:

```markdown
# Changelog

All notable changes to the `ru-editor` skill are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.3.0] — 2026-04-27

Phase 1 of v3.0.0 overhaul: content hygiene. No new infrastructure.

### Added
- `references/factual-integrity.md` — the most important rule: never invent specificity. Defines allowed responses to vague claims and the list of forbidden inventions.
- `## Factual Integrity` section in `SKILL.md` referencing the new file.
- `## Output Discipline` section in `SKILL.md` — explicit prohibitions on emoji, arrows, straight quotes in Russian, double hyphen.
- `## QA Gate` section in `SKILL.md` — manual checklist before returning edited text. Hooks for Phase 2 `ru_lint.py`.
- `scripts/check_phase1.sh` — bash acceptance script with 11 deterministic checks. Acts as the seed for Phase 2 linter.
- `CHANGELOG.md`.

### Changed
- `references/typography.md`: dash section rewritten. Em dash is now defined «by grammatical or semantic function only», not «for everything else». Added explicit «when not to use» with AI overuse patterns. Hard limit: one em dash per paragraph.
- `references/editing-examples.md`: removed all invented specifics from examples 1, 2, 5, 9, 11. Replaced bullet «What was fixed» lists with «Было / Стало / Почему» tables.
- All reference files: arrows `→` replaced with section colons, tables, or natural-language phrases. Zero arrows now appear in skill content.
- `SKILL.md` Reference Files table: only `factual-integrity.md` and `ai-markers-ru.md` are «always load»; the rest are loaded on trigger. Reduces context footprint.
- `SKILL.md`: «12 operations» mislabel corrected to «18 operations» — matches the actual list.

### Fixed
- Internal contradiction: typography (em dash «for everything else») vs ai-markers (em dash overuse warning). Resolved in favour of «by function only».
- Examples no longer teach the model to invent specificity (years, counts, percentages, McKinsey citations).

### Notes
- Phase 1 is a content-only release. No Python scripts, no new tools, no API changes.
- Always-load total: down from ~1370 lines to under 600.
- Phase 2 (v2.4) will add `scripts/ru_lint.py` — deterministic regex linter.

---

For previous releases (v2.2.0 and earlier), see git history.
```

- [ ] **Step 11.4: Run checks 10 and 11**

```bash
bash skills/ru-editor/scripts/check_phase1.sh 2>&1 | grep -A1 -E "(10\.|11\.)"
```

Expected: PASS for both.

- [ ] **Step 11.5: Commit**

```bash
git add skills/ru-editor/SKILL.md skills/ru-editor/CHANGELOG.md
git commit -m "release(ru-editor): bump to v2.3.0 + CHANGELOG"
```

---

## Task 12: Финальный прогон всех проверок

**Files:** none (verification only)

- [ ] **Step 12.1: Run full acceptance script**

```bash
bash skills/ru-editor/scripts/check_phase1.sh
```

Expected: `── ALL CHECKS PASSED ──`, exit code 0.

- [ ] **Step 12.2: Verify always-load token budget**

```bash
wc -l skills/ru-editor/SKILL.md \
       skills/ru-editor/references/factual-integrity.md \
       skills/ru-editor/references/ai-markers-ru.md
```

Sum should be < 600. Note actual number.

- [ ] **Step 12.3: Final arrow audit (be paranoid)**

```bash
grep -rn -E '→|⇒|=>' skills/ru-editor/SKILL.md skills/ru-editor/references/ skills/ru-editor/CHANGELOG.md 2>/dev/null
```

Expected: empty output.

- [ ] **Step 12.4: Final emoji audit**

```bash
grep -rcP '[\x{1F300}-\x{1FAFF}]|[\x{2600}-\x{27BF}]' skills/ru-editor/SKILL.md skills/ru-editor/references/ skills/ru-editor/CHANGELOG.md 2>/dev/null
```

Expected: zero counts.

- [ ] **Step 12.5: If everything green, no commit needed (verification-only step). If something fails, fix and commit fix.**

---

## Task 13: Синхронизация с глобальным `~/.claude/skills/ru-editor/`

**Files:**
- Sync: `skills/ru-editor/` → `~/.claude/skills/ru-editor/`

This is the version that Claude Code actually loads when the skill is invoked. Without sync, your changes don't take effect for users.

- [ ] **Step 13.1: Show what would be copied (dry run)**

```bash
rsync -av --dry-run --delete \
  /Users/codegeek/src/agent-skills/skills/ru-editor/ \
  /Users/codegeek/.claude/skills/ru-editor/
```

Review output. Expected: changes to SKILL.md, references/*.md, new files factual-integrity.md, scripts/check_phase1.sh, CHANGELOG.md.

- [ ] **Step 13.2: Confirm with user before destructive sync**

The `--delete` flag removes anything in `~/.claude/skills/ru-editor/` that's not in source. There's a `.DS_Store` in global that will be deleted — that's expected and fine.

If user approves, proceed.

- [ ] **Step 13.3: Run actual sync**

```bash
rsync -av --delete \
  /Users/codegeek/src/agent-skills/skills/ru-editor/ \
  /Users/codegeek/.claude/skills/ru-editor/
```

- [ ] **Step 13.4: Verify global is in sync**

```bash
diff -rq /Users/codegeek/src/agent-skills/skills/ru-editor/ \
         /Users/codegeek/.claude/skills/ru-editor/
```

Expected: empty output (no differences).

- [ ] **Step 13.5: Verify global SKILL.md has new version**

```bash
grep "version:" /Users/codegeek/.claude/skills/ru-editor/SKILL.md
```

Expected: `version: 2.3.0`.

- [ ] **Step 13.6: Smoke test in real Claude Code session**

Manual step. In a fresh CC session (or this one), try invoking the skill on a small test text and verify:
- Skill loads without errors
- New sections (Factual Integrity, Output Discipline, QA Gate) are referenced
- Output discipline observed (no arrows, no emoji)

This is a sanity check, not a hard automation. If smoke test fails, debug before final commit.

---

## Task 14: Финальный merge в main

**Files:** none (git only)

- [ ] **Step 14.1: Verify on feature branch**

```bash
git branch --show-current
```

Expected: `ru-editor-v2.3-content-hygiene`.

- [ ] **Step 14.2: Run full check one more time**

```bash
bash skills/ru-editor/scripts/check_phase1.sh
```

Expected: ALL CHECKS PASSED.

- [ ] **Step 14.3: Show all commits in this branch**

```bash
git log main..HEAD --oneline
```

Expected: ~13 commits (one per task) describing the changes.

- [ ] **Step 14.4: Merge to main (or open PR — ask user preference)**

Default: fast-forward merge.

```bash
git checkout main
git merge --ff-only ru-editor-v2.3-content-hygiene
```

If user prefers PR-based flow:
```bash
git push -u origin ru-editor-v2.3-content-hygiene
gh pr create --title "ru-editor v2.3.0 — Phase 1 Content Hygiene" \
  --body "Implements Phase 1 of ru-editor v3.0.0 overhaul. See docs/superpowers/specs/2026-04-27-ru-editor-overhaul-design.md § 5 Phase 1 and docs/superpowers/plans/2026-04-27-ru-editor-phase1-content-hygiene.md."
```

Ask user which they prefer before pushing.

- [ ] **Step 14.5: Tag the release**

```bash
git tag -a ru-editor-v2.3.0 -m "ru-editor v2.3.0 — Phase 1 Content Hygiene"
```

Don't push tag yet — ask user if they want it pushed.

---

## Self-Review Notes

**Spec coverage check (against spec § 5 Phase 1):**

| Spec requirement | Plan task |
|---|---|
| Add `Factual Integrity` section to SKILL.md | Task 6 |
| Add `Output Discipline` section to SKILL.md | Task 7 |
| Add `QA Gate` section to SKILL.md | Task 8 |
| Remove «12 operations» mislabel | Task 9 |
| Rewrite typography.md dash section | Task 3 |
| Audit editing-examples.md, remove invented specifics | Task 4 |
| Replace `→` in all reference tables | Task 5 |
| Create `references/factual-integrity.md` | Task 2 |
| Trim always-load to 3 files | Task 10 |
| Always-load < 600 lines | Task 12 (verification) |
| Zero documented contradictions | Tasks 3 + 7 (resolved) |
| Zero invented-specificity examples | Task 4 |
| Bump to v2.3.0 | Task 11 |

All requirements covered.

**Placeholder scan:** No "TBD/TODO/implement later" in this plan. Steps 5.5 and 5.6 now contain exact `Old → New` replacement tables for every arrow occurrence in `informational-style.md` and `SKILL.md`. Step 5.7 covers remaining occurrences in `editing-examples.md` (examples 3, 4, 6, 7, 8, 10) by referencing the same conversion pattern used in Task 4 — this is a repeated pattern, not a placeholder.

**Type consistency:** No types/interfaces in this plan (it's content). Section names used in checks (`## Factual Integrity`, `## Output Discipline`, `## QA Gate`) match exactly what tasks 6/7/8 insert.

**Open risks:**
- Step 5.5/5.6 could surface unexpected arrow usages requiring judgment. If the executor finds an awkward case, they should document it in the commit message rather than guess.
- Task 4 makes prescriptive content choices (what to put in the `### After:` blocks for examples 5 and 9). If user disagrees with the specific phrasing, they can adjust — the rule (no invented specifics) stands; only the wording is up for tuning.
- Task 13 (sync to `~/.claude/skills/`) uses `rsync --delete`. We confirmed the only target-only file is `.DS_Store` which is harmless to remove. If the global directory has accumulated other state, dry-run in 13.1 will surface it.

---

## Done Criteria

Phase 1 (v2.3.0) is complete when:

- [ ] `bash skills/ru-editor/scripts/check_phase1.sh` exits 0 with `── ALL CHECKS PASSED ──` (11 sections, ~32 individual assertions).
- [ ] Always-load total < 600 lines (verified in Task 12.2).
- [ ] Zero arrows in `skills/ru-editor/` (verified in Task 12.3).
- [ ] `~/.claude/skills/ru-editor/` synced (verified in Task 13.4).
- [ ] Smoke test in CC passes (Task 13.6).
- [ ] All commits merged to `main` (Task 14.4).
- [ ] Tag `ru-editor-v2.3.0` created (Task 14.5).

After Phase 1 lands, proceed to Phase 2 (v2.4 — Regex linter + seed corpus). A new plan will be written for that phase.
