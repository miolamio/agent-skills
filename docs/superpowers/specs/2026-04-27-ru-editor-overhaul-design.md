# ru-editor Overhaul — Design Spec

**Date:** 2026-04-27
**Author:** Anthony Vdovichenko
**Status:** Approved for implementation planning
**Source:** `.development/specification.md` (wishes, not requirements) + brainstorming session

---

## 1. Goal

Превратить `ru-editor` из одного большого промпта (v2.2.0) в управляемый редакторский пайплайн с детерминированной QA, режимами редактуры, изоляцией контекста, чанкингом длинных документов и регрессионным тестированием на golden-корпусе из 100 пар.

Целевая версия: **v3.0.0**. Доставляется поэтапно — v2.3 → v2.4 → v2.5 → v2.6 → v3.0. Каждая фаза самостоятельна и шипится отдельно.

## 2. Текущее состояние (v2.2.0)

- 1 файл `SKILL.md` (204 строки) + 6 reference-файлов (1427 строк), большинство «always load».
- Один универсальный режим редактуры — нет разделения proofread / line edit / cleanup / rewrite.
- Нет детерминированной QA: модель сама себя проверяет в self-reflection.
- Нет изоляции контекста: скилл видит код, переписку, прошлые черновики.
- Нет инструментов для длинных документов: всё грузится в один контекст, что вызывает потерю фрагментов.
- Нет evals / regression-тестов.
- Внутренние противоречия: тире в `typography.md` vs `ai-markers-ru.md`; примеры в `editing-examples.md` учат выдумывать факты; «12 операций» mislabel при фактических 18.

## 3. Архитектура верхнего уровня

```
Пользователь → SKILL.md (context: fork)
                  ↓
              Brief (mode, audience, terms)
                  ↓
              Span Protect (код, URL, команды)
                  ↓
              Segmenter (если > порога)
                  ↓
              Per-chunk Task subagents ← каждый в своём контексте
                  ↓
              Merge + cross-chunk QA
                  ↓
              Span Restore
                  ↓
              ru_lint.py (HARD_FAIL gate)
                  ↓
              Output (+ optional editor notes)
```

Параллельный путь для разработки скилла:

```
.development/golden-corpus/   ← создаёт пользователь
scripts/run_evals.py          ← дёргает Anthropic API напрямую (A2)
evals/reports/                ← метрики на каждом релизе
```

## 4. Архитектурные решения

| Решение | Выбор | Альтернативы | Обоснование |
|---|---|---|---|
| Per-chunk dispatch | Task tool / subagent (A) | `context: fork` recursion (B), Python orchestrator для всего (C) | Native Claude Code, не требует API-ключей у пользователя |
| Eval runner | Python + Anthropic API напрямую (A2) | Через `claude --print` в цикле (A3); вручную через subagents (A1) | 100 документов прогоняются за один запуск; CI-friendly; не пересекается с user-facing flow |
| Корпус | `.development/golden-corpus/` | `evals/golden-corpus/` рядом со скиллом | Пользователь предпочёл `.development/`; не путается с seed corpus в `evals/seed-corpus/` |
| Изоляция | `context: fork` для всего скилла + Task subagent per chunk | Только `context: fork` без чанков; только subagents без fork | Двухуровневая изоляция: fork отрезает родительский контекст, subagent отрезает соседние чанки |
| Сегментация | Семантическая, по структурам Markdown | По символам / токенам | Не ломает code fences, таблицы, списки |
| Подход | Поэтапный (5 релизов) | Big Bang v3.0.0 | Каждая фаза приносит пользу отдельно; меньше риска |

## 5. Фазы

### Phase 1 (v2.3) — Гигиена контента

**Срок:** 1–2 дня. **Зависимости:** нет. **Можно остановиться после:** да.

**Изменения:**

| Файл | Изменение |
|---|---|
| `SKILL.md` | Добавить разделы `Factual Integrity`, `Output Discipline`, `QA Gate`. Убрать «12 operations» mislabel. |
| `references/typography.md` | Переписать раздел про тире: «по функции, не как декорация». Ссылки на Грамоту. |
| `references/editing-examples.md` | Аудит каждого примера. Удалить выдуманную конкретику. Заменить на примеры с allowed responses (удалить / ослабить / спросить / отметить). |
| Все reference-файлы | Заменить `→` в таблицах на колонки «Было / Стало». |
| `references/factual-integrity.md` | **Новый**, ~80 строк. Список запрещённых выдумок + allowed responses. |
| Always-load список | Только: `SKILL.md` + `factual-integrity.md` + `ai-markers-ru.md` (без сплита; сплит на core/extended — в Phase 5). Остальное (typography, informational-style, pretentious-words, tech-anglicisms, editing-examples) переходит в trigger-load. |

**Output Discipline (новый раздел):**
- Запрет emoji
- Запрет стрелок в финальной русской прозе: `→`, `=>`, `->`, `⇒`
- Запрет прямых кавычек в русском тексте (только «»)
- Em dash только по функции, не как декоративная пауза

**Allowed responses on vague claims:** удалить / ослабить / попросить факты / добавить editor note. Запрещено: выдумывать числа, даты, клиентов, метрики, гарантии, calls to action.

**Метрики приёмки:**
- Always-load: < 600 строк (с ~1370)
- Документированных внутренних противоречий: 0
- Примеров с выдуманной конкретикой: 0

**Релиз:** v2.3.0.

---

### Phase 2 (v2.4) — Regex-линтер + seed corpus

**Срок:** 3–5 дней. **Зависимости:** Phase 1. **Можно остановиться после:** да.

**Главная цель:** детерминированная QA, реализующая принцип «пропущенные маркеры через regex».

**`scripts/ru_lint.py`** — pure Python 3.11+, без зависимостей.

CLI:
```bash
python scripts/ru_lint.py check  <edited.md>            # absolute mode
python scripts/ru_lint.py diff   <orig.md> <edited.md>  # diff mode (новое в edited)
python scripts/ru_lint.py both   <orig.md> <edited.md>  # default
```

Output: structured JSON + human-readable summary.

**Таксономия:**

| Уровень | Паттерны |
|---|---|
| `HARD_FAIL` (блокирует возврат) | Новые числа/даты/проценты/деньги в edited; изменённый код/URL; стрелки `→ => -> ⇒`; `--` вместо em dash; прямые кавычки в русском вне кода; emoji; потерянные заголовки/пункты/абзацы (count check); уцелевшие banned markers («погружаемся», «ландшафт», «гобелен», «является свидетельством», «стоит отметить»). |
| `WARN` (annotate) | >1 em dash в абзаце; 3+ предложения с одинакового слова; 3+ буллета одной формы; «X, а не Y» pile-up (3+ в proximity); «это» в 3+ определениях; повтор слова 3+ в предложении; смешанная пунктуация в списке; length ratio за пределами режима. |

**Двухрежимная архитектура линтера:**

1. **Absolute** — паттерны, которых не должно быть в финале вообще.
2. **Diff** — паттерны, которых **не было в исходнике, а в результате появились** (числа, имена, новые абзацы, новые заголовки).

Каждая проверка — отдельная функция, зарегистрированная в dict. Расширение = новая функция + строка в реестре.

**Идемпотентность как smoke-тест:** запустить редактуру на уже-отредактированном тексте; если новых правок > N — over-editing; если меньше — стабильно.

**Length-ratio guard** (по умолчанию ±20% при отсутствии режимов; per-mode значения вводятся в Phase 3).

**Интеграция в скилл:** новый раздел `## QA Gate` в `SKILL.md` — обязательный шаг перед возвратом результата. Self-reflection ссылается на findings линтера как на источник истины для типографики и фактов.

**Seed corpus:** `evals/seed-corpus/` — 20–30 пар, сделанных вручную для эмпирической грунтовки regex-паттернов. Структура пары:

```
evals/seed-corpus/001-marketing-fluff/
  source.md     # вход (AI-slop)
  expected.md   # ожидаемый выход
  brief.yaml    # mode, audience, expected linter status
```

**Метрики приёмки:**
- Линтер ловит ≥ 90% маркеров на seed corpus (manual baseline)
- 0 false-positives на reference-файлах самого скилла (после Phase 1 чистки)
- < 100 ms на документ 5k символов

**Релиз:** v2.4.0.

---

### Phase 3 (v2.5) — Режимы + изоляция

**Срок:** 2–3 дня. **Зависимости:** Phase 2 (для per-mode regex profiles). **Можно остановиться после:** да.

**Frontmatter:**
```yaml
---
name: ru-editor
description: ...
context: fork
agent: general-purpose
allowed-tools: Read Bash(python *)
argument-hint: "[mode] [text-or-file]"
---
```

**6 режимов с length-ratio guard:**

| Режим | Что делает | Length |
|---|---|---|
| Proofread | Только грамматика/пунктуация/типографика | ±5% |
| Line Edit (default) | Ясность/естественность, структура сохраняется | ±15% |
| AI Cleanup | Убрать AI-маркеры, механические фразы | ±25% |
| Infostyle | Бюрократит, пустые оценки, номинализации | ±30% |
| Technical Russian | Сохранить термины, код, команды | ±10% |
| Deep Rewrite | Только по явному запросу | без ограничений |

**Mode detection:** по запросу пользователя; если непонятно — Line Edit. Скилл явно эхоит выбранный режим в начале вывода: `Mode: Line Edit (auto-detected)` — пользователь может переопределить.

**Sticky mode:** после echo модель не дрейфует. В Phase 4 brief, разделяемый между чанками, фиксирует mode.

**Per-mode regex profiles** в `qa-checks.md`:
- Proofread: любая правка глубже типографики/грамматики → WARN
- Deep Rewrite: только HARD_FAIL остаётся
- Technical: правила по англицизмам ослаблены для устоявшихся dev-терминов

**Execution model** в SKILL.md — явно:
> Скилл получает только: текст или путь к файлу, режим редактуры, аудитория и регистр (если указаны), protected spans, формат вывода.
> Скилл игнорирует: код в родительском контексте, прошлые черновики, переписку, артефакты модели.

**Метрики приёмки:**
- Mode detection accuracy ≥ 85% на seed corpus
- Length-ratio violations < 5% на seed corpus при правильном режиме

**Релиз:** v2.5.0.

---

### Phase 4 (v2.6) — Per-chunk dispatcher

**Срок:** 4–6 дней. **Зависимости:** Phase 3. **Можно остановиться после:** да (это последняя архитектурная фаза).

**Главная цель:** реализовать принцип «всё в отдельных контекстах» для длинных документов. Каждый чанк редактируется в своём изолированном subagent-контексте.

**Новые скрипты:**

| Скрипт | Назначение |
|---|---|
| `scripts/build_brief.py` | Pre-pass: режим, аудитория, регистр, защищённые термины. Output: ~300 слов brief.yaml |
| `scripts/protect_spans.py` | Замена кода/URL/inline-code/команд/путей на стабильные плейсхолдеры |
| `scripts/restore_spans.py` | Обратная замена |
| `scripts/segment_markdown.py` | Семантический сегментер. Не режет code fences, таблицы, списки, абзацы. Каждый чанк знает родительский заголовок |

**Workflow в SKILL.md:**

```
Brief → Protect → Segment → Dispatch (parallel Task subagents)
                                ↓
              каждый subagent получает:
                - свой чанк
                - shared brief
                - previous_tail (~200 chars)
                - next_head (~200 chars)
                - protected spans
                                ↓
              Merge → Cross-chunk QA → Restore → ru_lint.py
```

**Адаптивный порог чанкинга:**

| Размер документа | Поведение |
|---|---|
| < 5k символов | Один контекст, без чанкинга |
| 5–30k символов | Brief + segment + chunks ~3k символов |
| > 30k символов | Aggressive segmenter, chunks ~2k |
| Высокая плотность AI-маркеров | Меньшие чанки (cheap regex pre-scan определяет density) |

**Cross-chunk QA:**
- Terminology consistency: собрать ключевые термины из всех чанков, проверить единообразие.
- Boundary check: нет дубликатов на стыках.
- Section-level diff regex (расширение линтера из Phase 2).

**Replay mode для отладки:**
Сохранять brief, чанки, выходы каждого subagent, merged result, lint output в `.ru-editor-replay/<timestamp>/`. Можно перезапустить любой чанк отдельно с тем же brief.

**Метрики приёмки:**
- Документ 30k символов проходит pipeline без потери заголовков/абзацев
- Cross-chunk terminology consistency ≥ 95%
- Replay-данные позволяют воспроизвести любую ошибку

**Релиз:** v2.6.0.

---

### Phase 5 (v3.0) — Golden corpus + evals + Codex + sync

**Срок:** 3–5 дней разработки + время пользователя на корпус. **Зависимости:** Phase 4. **Можно остановиться после:** это финал.

**Golden corpus** (создаёт пользователь):
- Локация: `.development/golden-corpus/`
- 100 пар: высококачественный исходник → AI-slop версия
- Структура пары: `original.md`, `corrupted.md`, `brief.yaml`
- Стратификация по жанру: technical / marketing / educational / blog / internal / переводной
- Стратификация по интенсивности порчи: light / medium / heavy
- Holdout split: 80 train / 20 holdout. Holdout не используется во время Phases 1–4

**`scripts/inject_ai_slop.py`** — инструмент синтетической порчи, чтобы помочь пользователю масштабировать корпус:
- Берёт чистый текст, добавляет паттерны (тире-overuse, выдуманные числа, погрузимся, X-а-не-Y, стрелки, бюрократит)
- Параметры: интенсивность (light/medium/heavy), включение/выключение конкретных паттернов
- Из 30–50 чистых исходников генерируется 100 corrupted-версий
- Пользователь вычитывает и тюнит

**`scripts/run_evals.py`** (A2 — отдельный batch-runner):
- Дёргает Anthropic API напрямую с тем же промпт-паттерном, что в скилле
- Итерирует по корпусу
- На каждом примере вычисляет метрики:
  - edit distance от output до original
  - AI-marker count delta (corrupted - output)
  - length ratio
  - HARD_FAIL count, WARN count
- Агрегация: mean / median / p95 / p99
- Отчёт в `evals/reports/YYYY-MM-DD-HHMM/`

**Self-eval:** CI-шаг прогоняет `ru_lint.py` по reference-файлам самого скилла. Если в `editing-examples.md` появилось выдуманное число или стрелка — CI падает.

**Codex subagent:**
- `.codex/agents/ru-editor.toml` — минимальный, ссылается на скилл
- `AGENTS.md` обновление — короткое правило: «для русской редактуры использовать ru_editor subagent или $ru-editor скилл; не редактировать inline в основном контексте»
- Скилл остаётся в `skills/ru-editor/`, Codex его потребляет

**Marketplace sync:**
- `scripts/sync_marketplace.py` — перед релизом копирует `skills/ru-editor/` → marketplace mirror
- Проверка: diff чистый (отсутствие непреднамеренных расхождений)
- Тегирование релиза

**Progressive disclosure splits:**
- `informational-style.md` (447 строк) → `informational-style-core.md` (~100, always-load) + `informational-style-bureaucratese.md` (trigger) + `informational-style-syntax.md` (trigger)
- `ai-markers-ru.md` → `ai-markers-ru-core.md` (always-load) + `ai-markers-ru-extended.md` (trigger)

**Метрики приёмки на holdout (20 пар):**
- AI-marker reduction ≥ 80% (corrupted vs output)
- HARD_FAIL count = 0
- length-ratio violations = 0
- edit-distance к original меньше, чем к corrupted (проверка, что движемся в правильную сторону)

**Релиз:** v3.0.0.

---

## 6. Финальная структура репозитория

```
skills/ru-editor/
  SKILL.md                              # ~150 строк, без операций — workflow + ссылки
  references/
    factual-integrity.md                # always-load
    ai-markers-ru-core.md               # always-load
    ai-markers-ru-extended.md           # trigger
    typography.md                       # trigger
    dash-rules.md                       # trigger
    informational-style-core.md         # trigger (или always-load по итогу Phase 5)
    informational-style-bureaucratese.md
    informational-style-syntax.md
    pretentious-words.md                # trigger
    tech-anglicisms.md                  # trigger
    modes.md                            # trigger
    qa-checks.md                        # trigger
    long-document-workflow.md           # trigger
    editing-examples.md                 # trigger
  scripts/
    ru_lint.py                          # Phase 2
    build_brief.py                      # Phase 4
    protect_spans.py                    # Phase 4
    restore_spans.py                    # Phase 4
    segment_markdown.py                 # Phase 4
    inject_ai_slop.py                   # Phase 5
    run_evals.py                        # Phase 5
    sync_marketplace.py                 # Phase 5
  evals/
    seed-corpus/                        # Phase 2 (20–30 пар, в репо)
    reports/                            # Phase 5

.development/
  specification.md                      # исходные wishes пользователя
  golden-corpus/                        # Phase 5, создаёт пользователь
    train/                              # 80 пар
    holdout/                            # 20 пар

.codex/
  agents/ru-editor.toml                 # Phase 5
AGENTS.md                               # Phase 5 (правка)

docs/superpowers/specs/
  2026-04-27-ru-editor-overhaul-design.md  # этот документ
```

## 7. Метрики успеха проекта в целом

На holdout (20 пар, не использованных при разработке):

| Метрика | Цель |
|---|---|
| AI-marker reduction (corrupted → output) | ≥ 80% |
| HARD_FAIL count | 0 |
| Length-ratio violations | 0 |
| Edit-distance к original < к corrupted | 100% случаев |
| Mode detection accuracy | ≥ 85% |
| Cross-chunk terminology consistency | ≥ 95% |
| Always-load context size | < 600 строк |

## 8. Non-goals

Этот спек **не** включает:

- Перевод (остаётся в `en-ru-translator-adv`).
- Редактирование английского текста.
- Написание текста с нуля.
- Кардинальное расширение словарей AI-маркеров — только то, что эмпирически найдено через seed corpus и golden corpus.
- Замена self-reflection полностью — линтер дополняет её, а не вытесняет.

## 9. Открытые вопросы

1. **Marketplace mirror как ground truth.** В Phase 5 нужно решить, какой репозиторий — каноничный: `skills/` в src или mirror. Сейчас mirror отстаёт, что создаёт двусмысленность.
2. **API-ключи для evals.** `run_evals.py` требует `ANTHROPIC_API_KEY`. Документировать в `evals/README.md` и положить пример в `.env.example`.
3. **Кадастр banned markers.** Сейчас список banned AI-markers разбросан по reference-файлам. В Phase 2 нужно собрать единый машиночитаемый список (`references/banned-markers.yaml`?) для линтера.

## 10. План на следующий шаг

После одобрения этого спека — invoke `superpowers:writing-plans` для создания детального implementation plan по Phase 1 (v2.3 — Гигиена контента). Каждая последующая фаза получит свой план в свою очередь.
