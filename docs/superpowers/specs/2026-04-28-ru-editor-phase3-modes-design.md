# ru-editor v2.5.0 — Phase 3 design — Modes + tools tightening

**Date:** 2026-04-28
**Target release:** v2.5.0
**Branch:** `ru-editor-v2.5-modes`
**Predecessor:** v2.4.0 (Phase 2 — regex linter + seed corpus)
**Successor:** v2.6.0 (Phase 4 — per-chunk dispatcher; out of scope here)
**Umbrella spec:** `docs/superpowers/specs/2026-04-27-ru-editor-overhaul-design.md` § 5 Phase 3

## 1. Goal

Convert ru-editor from a one-size-fits-all editor into a four-mode editor with per-mode constraints enforced by the linter. Tighten the skill's tool surface. Close two carry-over backlog items from Phase 2 that block correct per-mode behaviour.

## 2. Scope

1. **Four editing modes** in SKILL.md: Proofread / Line Edit (default) / Technical / Deep Rewrite. Each is instructions to the model + per-mode bounds in `ru_lint.py`.
2. **Mode detection** — hybrid: model picks the mode from request phrasing; an explicit `Mode: <name>` prefix overrides. Echoed in the first line of skill output.
3. **Per-mode profiles** in `references/mode-profiles.toml`, consumed by `ru_lint.py` via a new `--mode` flag.
4. **Frontmatter tightening:** add `allowed-tools: Read, Bash(python3:*)`. No `context: fork` (deferred to Phase 4).
5. **Backlog #4 — mode-aware `list_items_count_within_tolerance`.** Per-mode tolerance lives in profile.
6. **Backlog #5 — ignore-symmetry on diff-side checks** (`urls_preserved`, list counting). Use `doc.prose` (post-directive) for extraction so `<!-- ru-lint:ignore-* -->` blocks are respected on both sides of the diff.

## 3. Out of scope

- `context: fork` and other Claude-Code-specific isolation primitives — deferred to Phase 4 (per-chunk dispatcher provides real isolation through Task subagents in any host).
- D4 `sentence_length_p95`, D6 `cliché_density_per_100_words`, D7 `anglicism_density` — new metrics, deferred until golden corpus (Phase 5) is available for threshold calibration.
- `arrows_as_bullets` and `checkmark_as_bullet` refactor to use `raw_minus_directives` view — internal cleanup, deferred.
- Codex `ru_editor` subagent — Phase 5.
- Long-document chunking, `build_brief.py`, `protect_spans.py`, `segment_markdown.py` — Phase 4.

## 4. Architecture

### 4.1 What changes

| Layer | Change |
|---|---|
| Frontmatter | Add `allowed-tools: Read, Bash(python3:*)` |
| SKILL.md | New section `## Editing Modes` between `## QA Gate` and `## Important Rules` |
| Output format | Mandatory first line: `Mode: <name> (auto-detected\|explicit)` |
| `ru_lint.py` | New CLI flag `--mode {proofread,line_edit,technical,deep_rewrite,auto}`. Loads `mode-profiles.toml`. Two diff checks (`length_ratio_violation`, `list_items_count_within_tolerance`) consult profile bounds. Diff-side extraction switched from `doc.raw` to `doc.prose` for `urls_preserved` and list counting. |
| `references/mode-profiles.toml` | New file. Schema 1.0. Four `[modes.*]` tables. |
| `evals/seed-corpus/*/brief.toml` | Add `expected_mode = "<name>"` field to each of 20 pairs |
| `scripts/run_phase3_acceptance.sh` | New acceptance gate (unit tests + corpus eval + own-files regression + perf) |
| `scripts/run_all_tests.sh` | Add Phase 3 stage |

### 4.2 What does NOT change

- Existing 6 sections of SKILL.md (Factual Integrity, Output Discipline, QA Gate, Important Rules, Role, Reference Files, Three-Step Workflow, Context Detection, Output Format, Scope Boundaries) — touched only where mode-context must be threaded in.
- `references/banned-markers.toml` — no changes.
- The 24 existing checks in `ru_lint.py` — behaviour preserved when `--mode auto` (default).
- Phase 1 and Phase 2 acceptance scripts continue to pass without modification.

## 5. Components

### 5.1 Mode taxonomy

| Mode | Purpose | Length budget | List-items tolerance | Trigger phrases (examples) |
|---|---|---|---|---|
| `proofread` | Grammar / punctuation / typography only. Do not touch meaning or structure. | 0.95–1.05 | ±5% | «вычитай», «proofread», «исправь ошибки», «исправь опечатки», «грамматика» |
| `line_edit` | Default. Clarity, naturalness, AI-marker removal, structure preserved. | 0.70–1.15 | ±30% | «отредактируй», «причеши», «улучши», «убери ИИ-шность», «инфостиль», «убери воду» |
| `technical` | Technical text. Protect terms, code, commands, paths, identifiers. Light-touch outside of those. | 0.90–1.10 | ±10% | «технически отредактируй», «technical edit», «техническая правка», document contains code blocks/CLI/API |
| `deep_rewrite` | Rewrite from scratch. No length-ratio or list guards. Absolute HARD_FAIL checks (emoji, arrows, factual integrity) still enforced. | 0.0–99.0 (disabled) | 100% (disabled) | «перепиши с нуля», «полностью переделай», «deep rewrite» |

**Length budget rationale:**

The umbrella spec proposed `±15%` for Line Edit. Phase 2 smoke test on real-world AI-Slop (8 found-samples) showed ratios 0.47–0.71 were the **correct** edits — verified at 8/8 exit 0 with WARN. Tightening Line Edit to ±15% would generate 7/8 false-positive WARN. We widen the floor to 0.70 (i.e. allow up to 30% shrinkage) while keeping the ceiling at 1.15 (no expansion beyond 15%). Empirically grounded.

**AI Cleanup / Infostyle absorption:**

The umbrella spec listed 6 modes including AI Cleanup (±25%) and Infostyle (±30%). Phase 2 evidence: a single-mode editor handled vc-listicle, gigachat, lpmotor, sostav with one length-ratio band. The distinguishing feature of those modes was budget, not editing semantics. We absorb both into Line Edit at the wider 0.70 floor. If empirical data later shows a real semantic split, we add modes back; YAGNI for now.

### 5.2 Mode detection (model-side, in SKILL.md)

Algorithm in pseudo-prose (final wording lives in SKILL.md):

```
1. If the request begins with /^Mode:\s*(\w+)/i, capture name.
   - If name is in {proofread, line_edit, technical, deep_rewrite}: explicit override, echo `(explicit)`.
   - If unknown: ignore the prefix, echo `(default; unknown mode '<name>' ignored)`, fall through.

2. Scan request for trigger phrases:
   - Deep Rewrite triggers: «перепиши с нуля», «полностью переделай», «deep rewrite».
   - Technical triggers: «технически отредактируй», «technical edit», «техническая правка»,
     OR document body contains ≥1 fenced code block / inline code span density > 5%.
   - Proofread triggers: «вычитай», «proofread», «исправь ошибки», «исправь опечатки», «грамматика».
   - Line Edit triggers: «отредактируй», «причеши», «улучши», «убери ИИ-шность», «инфостиль».

3. Priority resolution on conflict:
   - Explicit > any auto-detect.
   - Deep Rewrite > Technical > Proofread > Line Edit.
   - Tie within auto-detect: pick by primary verb (the imperative governing the request).

4. If no trigger fires: default to Line Edit. Echo `(auto-detected)` regardless of how strong the signal.

5. If signals conflict ambiguously and no clear primary verb: default to Line Edit.
   Echo `(default; ambiguous request)`. Do not block.
```

**Echo format (mandatory first line of skill output):**

```
Mode: line_edit (auto-detected)
```

```
Mode: technical (explicit)
```

```
Mode: line_edit (default; unknown mode 'aggressive' ignored)
```

```
Mode: line_edit (default; ambiguous request)
```

### 5.3 `references/mode-profiles.toml` (new file)

```toml
schema_version = "1.0"

[modes.proofread]
length_ratio_min = 0.95
length_ratio_max = 1.05
list_items_tolerance = 0.05
description = "Грамматика, пунктуация, типографика. Смысл и структура — не трогать."

[modes.line_edit]
length_ratio_min = 0.70
length_ratio_max = 1.15
list_items_tolerance = 0.30
description = "Ясность и естественность. Сохранение структуры. Default."

[modes.technical]
length_ratio_min = 0.90
length_ratio_max = 1.10
list_items_tolerance = 0.10
description = "Технический текст. Защита терминов, кода, команд."

[modes.deep_rewrite]
length_ratio_min = 0.0
length_ratio_max = 99.0
list_items_tolerance = 1.0
description = "Перепиcать с нуля. Без length-ratio guard."
```

### 5.4 `ru_lint.py` changes

- New CLI flag `--mode {proofread,line_edit,technical,deep_rewrite,auto}`. Default `auto` keeps Phase 2 behaviour (global thresholds 0.80–1.20 / 30%).
- On startup: load `mode-profiles.toml`, validate `schema_version == "1.0"` and presence of all four mode tables. On failure: exit 3 (`config error`), distinct from exit 1 (HARD_FAIL) and exit 2 (WARN with `--strict`).
- `length_ratio_violation` (diff-mode WARN) reads `length_ratio_min` / `length_ratio_max` from selected profile when `--mode != auto`.
- `list_items_count_within_tolerance` (diff-mode WARN) reads `list_items_tolerance` from selected profile.
- `urls_preserved` (diff-mode HARD_FAIL): switch source-side and edited-side URL extraction from `doc.raw` to `doc.prose`. Closes Phase 2 backlog #5.
- Source-side list counting in `list_items_count_within_tolerance`: same — use `doc.prose` on both sides.
- JSON output: add `mode` field to `summary` (next to `hard_fail_count`, `warn_count`, `elapsed_ms`). Schema bumps to `1.1` (additive — clients on 1.0 ignore the new field).
- Human output: print `Mode: <name>` line near the top of the report.

### 5.5 SKILL.md changes

- Frontmatter: add `allowed-tools: Read, Bash(python3:*)`. Bump `version: 2.5.0`.
- Description: add «выбирает режим редактуры (proofread/line_edit/technical/deep_rewrite)» so the skill router knows about modes.
- New section `## Editing Modes` (~80 lines), placed between `## QA Gate` and `## Important Rules`. Contents: mode taxonomy table, detection algorithm, echo format, override syntax, examples.
- `## QA Gate` updated: linter invocation gains `--mode <detected_mode>` flag. Exit-code semantics extended (exit 3 = config error → fall through to manual checklist).
- `## Output Format`: first line is now `Mode: <name> (...)`. Document this.
- `## Three-Step Workflow`: each step gains a one-line «in <mode> mode, additionally...» note where mode-specific behaviour matters (e.g., Step 1 in `proofread` does not touch meaning; Step 1 in `deep_rewrite` ignores length budget).

## 6. Data flow

### 6.1 Standard invocation, auto-detect

```
User: «Отредактируй: <текст>»
  ↓ skill matched via description trigger
  ↓ model loads SKILL.md, reads ## Editing Modes
  ↓ no Mode: prefix; trigger «отредактируй» → Line Edit
  ↓ model executes Step 1 Edit with line_edit instructions (length 0.70–1.15)
  ↓ Step 2 Self-Reflection
  ↓ Step 3 Polish
  ↓ QA Gate: Bash python3 ru_lint.py both <source> <edited> --mode line_edit
  ↓ HARD_FAIL → fix and re-run; WARN → report
  ↓
Output:
  Mode: line_edit (auto-detected)

  <edited text>
```

### 6.2 Explicit override

```
User: «Mode: technical
       <текст с API-документацией>»
  ↓ first-line parser: matched, name 'technical' valid
  ↓ executes with technical instructions (length 0.90–1.10)
  ↓ QA Gate with --mode technical
  ↓
Output:
  Mode: technical (explicit)

  <edited text>
```

### 6.3 Conflict resolution

```
User: «Технически вычитай: <текст>»
  ↓ scan: «вычитай» → Proofread, «технически» → Technical
  ↓ Proofread > Technical (narrower wins on tie); primary verb «вычитай» confirms
  ↓
Output:
  Mode: proofread (auto-detected)
```

### 6.4 Linter pipeline with `--mode`

```
ru_lint.py both source.md edited.md --mode line_edit
  ↓ load mode-profiles.toml (validate schema)
  ↓ profile = profiles["line_edit"]
  ↓ run absolute checks on edited.prose (mode-independent)
  ↓ run diff checks (edited × source) — length_ratio and list_items use profile bounds;
    urls_preserved and list counting extract from doc.prose on both sides
  ↓ assemble JSON: summary.mode = "line_edit", schema_version = "1.1"
  ↓ exit 0 (clean) | 1 (hard_fail) | 2 (warn + --strict) | 3 (config error)
```

## 7. Error handling and edge cases

| Case | Behaviour |
|---|---|
| Linter unavailable (`Bash(python3:*)` not authorized, traceback, etc.) | Manual fallback per Phase 2 design. Add `mode: <detected>` to the warning so the manual checklist has context. |
| `mode-profiles.toml` missing or malformed | Exit 3 with explicit message (`mode-profiles.toml: missing mode 'technical'` / `schema_version mismatch`). Skill falls through to manual fallback. |
| User specifies unknown mode (`Mode: aggressive`) | Skill echoes `Mode: line_edit (default; unknown mode 'aggressive' ignored)`. Linter never sees the bad name (skill validates first). |
| Linter called with unknown `--mode` (e.g. by automation) | Exit 3, `unknown mode 'aggressive'`. |
| Explicit mode mismatched to text nature (e.g., `Mode: technical` on prose without code) | Skill applies technical bounds anyway. Not blocked — control belongs to user. |
| Length-ratio violation in `proofread` (drift > 5%) | Linter emits WARN; model in Step 2 Self-Reflection notes drift, may tighten edits or warn user: «edits exceeded proofread budget; consider Mode: line_edit». |
| `<!-- ru-lint:ignore-* -->` block contains URL only on source side (asymmetric) | Linter checks «all URLs from `source.prose` present in `edited.prose`». URL hidden by ignore-block disappears from both views; not flagged. Closes Phase 2 backlog #5. |
| Idempotency | Two consecutive linter runs on the same input produce identical JSON output (modulo `elapsed_ms`). Profile loading is deterministic. |

## 8. Acceptance metrics

| Metric | Threshold | Measured on |
|---|---|---|
| Mode detection accuracy | ≥ 85% | seed-corpus 20 pairs labelled with `expected_mode` |
| Length-ratio violations when running `--mode <expected>` | < 5% | same |
| Mode-aware list-tolerance unit tests | 100% pass | `test_modes_per_mode_bounds.py` |
| Ignore-symmetry unit tests | 100% pass | `test_ignore_symmetry.py` |
| Own-files HARD_FAIL | 0 | `skills/ru-editor/references/*.md` |
| Performance | < 100 ms per 5K char | carry-over from Phase 2 |
| Backwards compatibility | Phase 1 and Phase 2 acceptance scripts pass unchanged | `scripts/run_all_tests.sh` |

## 9. Testing strategy

### 9.1 Unit tests (new)

| File | Coverage |
|---|---|
| `test_mode_profiles.py` | TOML loading, schema validation, missing mode → exit 3, malformed → exit 3 |
| `test_modes_per_mode_bounds.py` | length_ratio + list_items per profile: 4 modes × 3 cases (within / above / below) = 12 tests |
| `test_ignore_symmetry.py` | URL / code-span / list-item inside ignore-block not lost; ignore-only-in-source path |
| `test_cli_mode_flag.py` | `--mode` parsing, `auto` default, unknown mode → exit 3, `--mode list` (introspection) |

Target: ~25 new tests on top of Phase 2's 103 → ~128 total.

### 9.2 Seed-corpus extension

Each of the 20 `evals/seed-corpus/*/brief.toml` gains:

```toml
expected_mode = "line_edit"  # or proofread / technical / deep_rewrite
```

Predicted distribution (final assignment happens during implementation by reading each brief):

- ~10 × `line_edit` (typical light/medium genre cases)
- ~4 × `technical` (`03-api-docs-heavy`, `08-dataflow-tutorial-medium`, `09-cicd-course-heavy`, `18-code-vs-prose`)
- ~3 × `proofread` (`16-idempotency-clean`, `20-minimal`, one light)
- ~3 × `deep_rewrite` (`06-marketing-landing-heavy`, `12-opinion-heavy`, `15-team-newsletter-heavy`)

### 9.3 Acceptance script (`scripts/run_phase3_acceptance.sh`)

```
1. python3 -m unittest discover skills/ru-editor/scripts/tests/
2. python3 ru_lint.py --version (smoke)
3. for each pair in evals/seed-corpus/:
     read brief.toml expected_mode
     run linter --mode auto on (source, edited) → record detected_mode
     run linter --mode <expected_mode> → count length/list violations
   detection_accuracy = correct_detections / 20
   violation_rate = violations / 20
   assert detection_accuracy >= 0.85
   assert violation_rate < 0.05
4. linter on skills/ru-editor/references/*.md → 0 HARD_FAIL
5. perf: <100ms per 5K char
```

### 9.4 Master regression

`scripts/run_all_tests.sh` extended:

```
PHASE 1: bash skills/ru-editor/scripts/check_phase1.sh
PHASE 2: bash skills/ru-editor/scripts/run_phase2_acceptance.sh
PHASE 3: bash skills/ru-editor/scripts/run_phase3_acceptance.sh
─────────────────
ALL 3 PHASE(S) PASSED
```

### 9.5 Smoke test (post-merge, pre-tag)

ru-editor v2.5.0 on 8 found-samples + 3 controlled-mode requests. Verify:

1. Echo appears in first line.
2. `--mode line_edit` does not produce false-positive length WARN on AI-slop (the regression case from Phase 2 smoke).
3. Explicit `Mode: technical` correctly tightens behaviour.
4. `Mode: proofread` correctly refuses to touch meaning.

## 10. Backwards compatibility

- `ru_lint.py` invoked without `--mode` (or with `--mode auto`) reproduces Phase 2 behaviour bit-for-bit. Phase 2 unit tests and acceptance scripts pass without modification.
- Existing skill invocations without explicit mode signals are routed to `line_edit` (default). Echo line is the only visible new output. Not breaking — Phase 2 outputs already had varied formatting in the first line.
- JSON consumers on schema 1.0 ignore the new `summary.mode` field (additive change).
- `evals/seed-corpus/*/brief.toml` without `expected_mode` field: Phase 3 acceptance script treats it as `line_edit` for backward compatibility, but Phase 3 implementation labels all 20 pairs explicitly — so this fallback is for safety, not active use.

## 11. Release artifacts

- Branch `ru-editor-v2.5-modes` (created off current `main` HEAD).
- Local annotated tag `ru-editor-v2.5.0` after smoke-test approval.
- `skills/ru-editor/CHANGELOG.md` entry for `[2.5.0]`.
- No push (per local-only operating mode).
- Sync to `~/.claude/skills/ru-editor/` after merge to main.

## 12. Open questions

None blocking. Items listed under § 3 Out of scope are tracked for future phases.

## 13. Risks

| Risk | Mitigation |
|---|---|
| Mode detection accuracy < 85% on labelled corpus | Trigger phrase taxonomy is explicit and tunable. If a few corpus pairs are misclassified, refine triggers and re-measure. Acceptance is a numeric gate, not a vote. |
| `expected_mode` labels are subjective for a few seed-corpus pairs | Ambiguous pairs default to `line_edit`. Acceptance threshold (85%) tolerates 3 mislabels without failing. |
| Backlog #5 fix breaks a hidden Phase 2 test | All Phase 2 unit tests and acceptance scripts run unchanged in Phase 3 master regression. Any breakage surfaces immediately. |
| `--mode auto` semantics divergence from Phase 2 globals | Hard-coded backstop: when `mode == 'auto'`, the linter uses the literal Phase 2 thresholds (0.80–1.20 / 0.30). No profile loaded for `auto`. |

## 14. Success criteria (single line)

`bash scripts/run_all_tests.sh` reports `ALL 3 PHASE(S) PASSED`, smoke test on found-samples shows zero false-positive length WARN at `--mode line_edit`, and explicit `Mode: <name>` overrides observably change linter exit codes on intentional mismatches.
