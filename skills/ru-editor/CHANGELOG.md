# Changelog

All notable changes to the `ru-editor` skill are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.7.0] — 2026-05-05

Phase 2D + 2E + 2F — closing remaining backlog after Phase 2C.

### Added (Phase 2D — linter)

- `repeated_heading_template` (WARN, absolute) — detects 2+ headings starting with marketing-template prefixes («Возможности и преимущества», «Недостатки», «Преимущества и недостатки», «Плюсы и минусы», «Ключевые особенности», «Особенности», «Применение», «Использование», «Характеристики», «Ключевые возможности», «Возможности»). Catches AI-listicle structural patterns.
- Opinion-mode whitelist for `unsourced_percentage`. The check no longer fires when an opinion marker («считаю», «думаю», «мне кажется», «по-моему», «убеждён», «честно говоря», «на мой взгляд», «лично я», «если честно») is in the ±200 char window. Removes false positives on opinion-jоurnalism.
- A/B-experiment whitelist for `unsourced_percentage`. The check skips percentages near «эксперимент», «a/b-тест», «измерени» — case-study figures from controlled experiments are not fake stats.
- `references/banned-markers.toml`: 5 new WARN phrases — «да-да,», «представляет собой», «как известно», «в наше время», «на сегодняшний день».

### Added (Phase 2E — acceptance)

- `evals/found-samples/*/brief.toml` — schema-1.0 contract for all 8 (now 13) samples: genre, intensity, expected mode, hard/warn budgets, checks_must_fire, checks_must_not_fire_on_edited, expected_clean_on_lint.
- `scripts/run_phase2c_acceptance.sh` — 5-section gate validating brief.toml schema, source-budget compliance, edited.md cleanliness (smoke-test invariant), must-fire and must-not-fire invariants.
- `scripts/run_all_tests.sh` master-runner now wires Phase 2C into the regression pipeline. All 4 phases (1, 2, 3, 2c) green.

### Added (Phase 2F — corpus expansion)

- 5 new found-samples (09–13) covering genres outside the «нейросеть-обзор» niche:
  - `09-cnews-hr-research` — corporate research summary (HR digitalization).
  - `10-vc-b2b-hr-listicle` — B2B HR-tools listicle, conversational AI tone.
  - `11-skillbox-excel-tutorial` — educational tutorial (Excel functions).
  - `12-cossa-link-report` — corporate report (link-building industry).
  - `13-sostav-rta-case-study` — marketing case study with real A/B-experiment metrics.
- Sample 08 verbatim extended from 1 model to 2 (YandexGPT + Kandinsky) so `repeated_heading_template` hits its 2+ threshold.

### Changed

- Total registered checks: 29 → 31. Total unit tests: 166 → 176.
- `evals/found-samples/README.md`: full rewrite reflecting 13-sample structure, brief.toml schema, baseline table, Phase 2G backlog (soft-AI-Slop classes).
- `SKILL.md` frontmatter: 2.6.0 → 2.7.0.

### Known gaps (Phase 2G backlog)

Samples 09, 11, 12 contain «soft-AI-Slop» that the current linter does not catch:
- Hedging openers («Вероятнее всего, это связано с…»).
- Sweeping generalizations («должны уметь все», «делает всё, что может понадобиться»).
- Evaluation without proof («значительно упрощают», «качественных площадках»).
- Corporate research stamps («ключевые данные и инсайты», «показатель зрелости рынка»).
- Bold inline-headers без двоеточия (внутри предложения).

These are documented in `evals/found-samples/README.md` and provide grounding data for Phase 2G linter additions.

---

## [2.6.0] — 2026-05-05

Phase 2C — found-samples grounding additions. Driven by 8 verbatim AI-Slop samples in `evals/found-samples/`, where Phase 2 linter caught only emoji on 7/8 files. After 2C: 7/8 files produce findings.

### Added

- `references/banned-markers.toml`: 2 new HARD_FAIL phrases («вот тут на помощь приходит/приходят») and 12 new WARN phrases («настоящий прорыв», «также отметим/отмечу», «стремительно растёт», «стремительно набирает популярность», «принципиально отличается», «первый представитель своего класса», «продвинутые пользователи», «приобретают/приобретает всё большую популярность», «оживляют пиксели», «широкий спектр задач»).
- 5 new regex-based WARN checks in `ru_lint.py`:
  - `not_only_but_also` — конструкция «не только X, но и Y» (≤120 chars, sentence-bounded).
  - `parallel_kak_tak_i` — параллель «как X, так и Y» (опционально с «среди/у/для/в»).
  - `bold_inline_header_in_list` — bullet item, открытый `**Bold**:` или `**Bold** —`.
  - `filler_paragraph_opener` — параграфы, начинающиеся на «На самом деле», «Кроме того», «Более того», «В целом», «Что касается», «В заключение», «Во-первых», «Прежде всего», «Таким образом».
  - `unsourced_percentage` — процент в прозе без URL и без citation-маркера в окне ±200 chars. Whitelist финансовых сигналов (скидка, дисконт, комиссия, НДС, ставка, тариф, пошлина) — точные цифры в pricing-контексте не флагуются.
- `evals/found-samples/` — 8 verified verbatim AI-Slop samples из открытых источников (vc.ru, habr.com, sostav.ru, lpmotor.ru, yagla.ru, skillbox.ru, it-world.ru, giga.chat). README с методологией сбора, baseline-таблицей и known gaps.
- 24 новых unit-теста в `test_checks_warn.py` (positive/negative для каждого нового чека + financial whitelist test).

### Changed

- Total registered checks: 24 → 29. Total unit tests: 142 → 166.

### Notes

- Phase 2C делал на основании 8 страниц одного жанрового кластера (обзоры русскоязычных нейросетей 2026). Расширение на другие жанры — в Phase 2D.
- Sample 08 (giga.chat) намеренно остался без находок — его AI-Slop структурный (повторяющиеся блоки «Возможности/Недостатки» под каждой моделью), а не лексический. Кандидат на structural-checker в будущих фазах.

---

## [2.5.0] — 2026-04-29

Phase 3 of v3.0.0 overhaul: editing modes + tools tightening.

### Added

- `references/mode-profiles.toml` — schema 1.0, four modes (`proofread`, `line_edit`, `technical`, `deep_rewrite`) with per-mode `length_ratio_min`/`length_ratio_max`/`list_items_tolerance`.
- `--mode {auto,proofread,line_edit,technical,deep_rewrite}` flag in `ru_lint.py`. Default `auto` reproduces Phase 2 globals (0.80–1.20 / ±30%). When a named mode is specified, `length_ratio_violation` and `list_items_count_within_tolerance` consult the profile.
- `## Editing Modes` section in `SKILL.md` with mode taxonomy, hybrid detection algorithm (auto + explicit `Mode: <name>` prefix), echo format, and examples.
- Mandatory first-line echo in skill output: `Mode: <name> (<auto-detected|explicit|default; ...>)`.
- New unit tests: `test_mode_profiles.py`, `test_modes_per_mode_bounds.py`, `test_ignore_symmetry.py`, `test_cli_mode_flag.py` (~25 new tests).
- `scripts/run_phase3_acceptance.sh` — Phase 3 acceptance gate (unit tests + seed-corpus mode-aware eval + own-files regression + perf budget).
- `expected_mode` field in all 20 `evals/seed-corpus/*/brief.toml` files.

### Changed

- `Document` structural extraction (`urls`, `code_spans`, `code_blocks`, `headings`, `list_items`) now reads from `_without_ignored_regions`, making `<!-- ru-lint:ignore-* -->` directives uniformly respected on both sides of diff-mode checks. Closes Phase 2 backlog #5.
- `SKILL.md` frontmatter: `allowed-tools: Read, Bash(python3:*)` added (skill is restricted to file reads and Python invocations). `version: 2.4.0 → 2.5.0`. Description mentions mode selection.
- `SKILL.md` `## QA Gate`: linter invocation now passes `--mode <detected>`. Documented exit code 3 (config error → manual fallback).
- `SKILL.md` `## Output Format`: first line is `Mode: <name> (...)`.
- `SKILL.md` `## Three-Step Workflow`: per-mode aggressiveness preamble.
- JSON output schema bumped from `1.0` to `1.1` (additive: new `summary.mode` field with selected lint mode).

### Notes

- `context: fork` and other Claude-Code-specific isolation primitives remain deferred to Phase 4.
- D4 `sentence_length_p95`, D6 `cliché_density_per_100_words`, D7 `anglicism_density` — still deferred to Phase 5 (need golden corpus for threshold calibration).
- Acceptance metrics: detection accuracy ≥ 85%, length/list violations < 5%, 0 HARD_FAIL on own files, < 100ms per 5K char.

---

## [2.4.0] — 2026-04-28

Phase 2 of v3.0.0 overhaul: deterministic regex linter + seed corpus. SKILL.md `## QA Gate` now references the linter as authoritative.

### Added

- `scripts/ru_lint.py` — pure Python 3.11+ regex linter, no third-party deps. Three CLI modes: `check`, `diff`, `both`. JSON output (`schema_version: "1.0"`) and human-readable output. `--strict` flag fails on WARN.
- 24 registered checks: 5 absolute HARD_FAIL, 6 diff-mode HARD_FAIL, 11 absolute WARN, 2 diff-mode WARN.
- `references/banned-markers.toml` — machine-readable source of truth for banned phrases (14 hard-fail markers, 35 warn markers, 6 synonym clusters).
- HTML ignore directives: `<!-- ru-lint:ignore-line -->`, `<!-- ru-lint:ignore-start --> ... <!-- ru-lint:ignore-end -->`. Suppress checks on legitimate documentation of banned content.
- `evals/seed-corpus/` — 20 stratified hand-crafted pairs (5 genres × 3 intensities + 5 edge cases) for empirical acceptance.
- `scripts/run_all_tests.sh` — master regression runner orchestrating all phase acceptance scripts.
- `skills/ru-editor/scripts/run_phase2_acceptance.sh` — Phase 2 acceptance gate (unit tests + seed corpus + own files + perf budget).
- `skills/ru-editor/scripts/tests/` — unittest suite covering Document, registry, CLI, all checks (103 tests).

### Changed

- `SKILL.md` `## QA Gate`: now invokes `python3 scripts/ru_lint.py` as authoritative step. Manual checklist remains as fallback when `Bash(python *)` is not authorized.
- Version bumped: 2.3.0 → 2.4.0.
- Phase 1 always-load line budget bumped 600 → 700 to accommodate the expanded QA Gate.
- Phase 1 version check relaxed from `== 2.3.0` to `≥ 2.3.0`.

### Notes

- No frontmatter `allowed-tools` change yet; that comes with Phase 3 (`context: fork` + isolation).
- Acceptance metrics: 0 HARD_FAIL on own reference files, perf <100 ms per 5K-char document (measured: ~10 ms).
- Empirical grounding (15 source/output/tags triples across 5 genres) lives at `.development/tests/phase2-regex-linter/grounding/` — gitignored.

---

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
- `references/editing-examples.md`: removed all invented specifics from examples 1, 2, 5, 8, 9, 10, 11. Replaced bullet «What was fixed» lists with «Было / Стало / Почему» tables. Section headings changed from arrows to colons.
- All reference files: arrows `→` replaced with section colons, tables, or natural-language phrases. Zero prose arrows now appear in skill content.
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
