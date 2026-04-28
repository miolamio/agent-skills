# ru-editor Seed Corpus

20 hand-crafted source/expected/brief triples for empirically validating the regex linter (`scripts/ru_lint.py`) introduced in Phase 2 (v2.4).

**This is NOT the golden corpus.** Golden corpus (100 pairs, holdout split) is Phase 5 and lives in `.development/golden-corpus/`. The seed corpus is a smaller, fully-checked-in fixture for unit-style acceptance.

## Structure

```
evals/seed-corpus/
  NN-<slug>/
    source.md         # AI-slop input (corrupt with markers we want to catch)
    expected.md       # what a v2.3+ skill is expected to produce
    brief.toml        # metadata + ground-truth findings for the linter
```

## brief.toml schema

```toml
[meta]
schema_version = "1.0"
genre = "marketing"            # technical|marketing|educational|blog|internal
intensity = "heavy"            # light|medium|heavy
mode = "line_edit"             # used by Phase 3; ignored in Phase 2

[expected_findings]
# Linter, run on source.md in `check` mode, must catch this many.
hard_fail_min = 5              # at least this many HARD_FAIL
hard_fail_max = 15             # at most this many (catches false-positive proliferation)
warn_min = 0
warn_max = 20

# Specific checks the linter MUST fire on source.md:
checks_must_fire = ["no_arrows_in_prose", "no_banned_markers"]

# Specific checks the linter MUST NOT fire (when run on expected.md):
checks_must_not_fire_on_expected = ["no_emoji", "no_arrows_in_prose", "no_banned_markers"]

# Idempotency: lint(expected.md) must produce 0 HARD_FAIL.
expected_clean_on_lint = true
```

## Stratification matrix

| Genre | Light | Medium | Heavy |
|---|---|---|---|
| technical | 01 | 02 | 03 |
| marketing | 04 | 05 | 06 |
| educational | 07 | 08 | 09 |
| blog | 10 | 11 | 12 |
| internal | 13 | 14 | 15 |
| edge cases | 16-20 (idempotency, edge directives, unicode) | | |

## Acceptance metrics

`scripts/run_phase2_acceptance.sh` runs:
- For each pair: linter on `source.md` → counts within `[hard_fail_min, hard_fail_max]`
- For each pair: linter on `expected.md` → 0 HARD_FAIL
- For each pair: required checks fire / forbidden checks don't fire
- Aggregate recall ≥ 90% across the 20 pairs

## Adding a new pair

1. Pick an unused number NN.
2. Create directory `NN-<slug>/`.
3. Write `source.md`: realistic AI-slop with planted markers.
4. Write `expected.md`: clean, manually edited output.
5. Write `brief.toml` per schema above.
6. Run `bash skills/ru-editor/scripts/run_phase2_acceptance.sh` — should still pass.
