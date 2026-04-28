# Changelog

All notable changes to the `ru-editor` skill are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
