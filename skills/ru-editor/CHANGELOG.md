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
