# ru-editor v2.5.0 Phase 3 — Modes + tools tightening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert ru-editor into a four-mode editor (Proofread / Line Edit / Technical / Deep Rewrite) with per-mode constraints enforced by the linter, tighten the skill's tool surface, and close two carry-over backlog items from Phase 2.

**Architecture:** Per-mode profiles live in a new TOML file consumed by `ru_lint.py` via a new `--mode` flag. Mode detection is hybrid: the model picks a mode from request phrasing or honors an explicit `Mode: <name>` prefix, then echoes the choice in the first line of output. `Document` extraction properties are refactored to respect `<!-- ru-lint:ignore-* -->` directives uniformly, fixing structural-check symmetry on the diff side.

**Tech Stack:** Python 3.11+ (stdlib only — `tomllib`, `argparse`, `unittest`, `dataclasses`); bash; markdown SKILL.md prose. No new third-party deps.

**Spec:** `docs/superpowers/specs/2026-04-28-ru-editor-phase3-modes-design.md`.

---

## File structure

### Files to create

| Path | Responsibility |
|---|---|
| `skills/ru-editor/references/mode-profiles.toml` | Per-mode bounds source of truth (length_ratio min/max, list-items tolerance, description). Schema 1.0. |
| `skills/ru-editor/scripts/tests/test_mode_profiles.py` | TOML loading, schema validation, error paths. |
| `skills/ru-editor/scripts/tests/test_modes_per_mode_bounds.py` | length_ratio + list_items per mode: 4 modes × 3 cases each. |
| `skills/ru-editor/scripts/tests/test_ignore_symmetry.py` | URL / code-span / list-item / heading inside ignore-block respected on both diff sides. |
| `skills/ru-editor/scripts/tests/test_cli_mode_flag.py` | `--mode` parsing, default `auto`, unknown mode → exit 3, JSON schema 1.1 with `summary.mode`. |
| `skills/ru-editor/scripts/run_phase3_acceptance.sh` | Phase 3 acceptance gate (unit tests + corpus eval + own-files regression + perf). |
| `.development/prompts/phase3-testing-agent.md` | Self-contained prompt for a delegated subagent that runs Phase 3 tests + extends corpus if needed. |
| `.development/prompts/phase3-resume-task14.md` | Resume prompt for Task 14 finalization (smoke / sync / merge / tag) after `/clear`. |

### Files to modify

| Path | What changes |
|---|---|
| `skills/ru-editor/scripts/ru_lint.py` | (a) Bump `SCHEMA_VERSION` to `"1.1"`. (b) Refactor `Document` structural properties (`urls`, `code_spans`, `code_blocks`, `headings`, `list_items`) to extract from `_without_ignored_regions` instead of `self.text`. (c) Add `_load_mode_profiles()` + module-level `_MODE_PROFILES` cache. (d) Add `--mode {proofread,line_edit,technical,deep_rewrite,auto}` to common argparse parents. (e) Inject profile into `ctx` dict in `run_checks`. (f) `_check_length_ratio` and `_check_list_items_tolerance` read profile from `ctx`. (g) `main()` returns exit 3 on config errors. (h) `_format_json` adds `summary.mode` field equal to selected lint-mode. |
| `skills/ru-editor/SKILL.md` | (a) Frontmatter: add `allowed-tools: Read, Bash(python3:*)`, bump `version: 2.5.0`. (b) Add new section `## Editing Modes` between `## QA Gate` and `## Important Rules`. (c) Update `## QA Gate` linter invocation to include `--mode <detected>`, document exit 3 fallback. (d) Update `## Output Format` to mandate `Mode: ...` first line. (e) Update `## Three-Step Workflow` with mode-aware notes. |
| `skills/ru-editor/CHANGELOG.md` | New `## [2.5.0] — 2026-04-28` entry. |
| `evals/seed-corpus/01-api-auth-light/brief.toml` … `evals/seed-corpus/20-minimal/brief.toml` | Add `expected_mode = "<name>"` field to each of the 20 files. Distribution decided per-pair during Task 8. |
| `scripts/run_all_tests.sh` | Add Phase 3 acceptance stage; bump phase counter to 3. |

### Files NOT to touch

- `skills/ru-editor/references/banned-markers.toml` — banned phrases out of scope.
- `skills/ru-editor/references/*.md` (typography, factual-integrity, etc.) — content out of scope.
- 24 existing checks in `ru_lint.py` — except for the two diff WARN checks listed above.
- Phase 1 / Phase 2 acceptance scripts — they continue to work unchanged.

---

## Task 1: Setup branch and verify baseline

**Files:** none (git operations only).

- [ ] **Step 1: Verify clean tree on main**

Run: `git status && git rev-parse HEAD && git log --oneline -2`
Expected: clean, HEAD `9609b86 docs(ru-editor): Phase 3 design spec`, parent `8212b95`.

- [ ] **Step 2: Create and check out feature branch**

Run: `git checkout -b ru-editor-v2.5-modes`
Expected: `Switched to a new branch 'ru-editor-v2.5-modes'`.

- [ ] **Step 3: Run baseline regression**

Run: `bash scripts/run_all_tests.sh 2>&1 | tail -5`
Expected: `ALL 2 PHASE(S) PASSED`.

- [ ] **Step 4: Run Phase 2 unit tests directly**

Run: `python3 -m unittest discover skills/ru-editor/scripts/tests/ 2>&1 | tail -3`
Expected: `OK` with at least 103 tests.

No commit yet. Branch created from clean state at `9609b86`.

---

## Task 2: mode-profiles.toml — schema and loader (TDD)

**Files:**
- Create: `skills/ru-editor/references/mode-profiles.toml`
- Create: `skills/ru-editor/scripts/tests/test_mode_profiles.py`
- Modify: `skills/ru-editor/scripts/ru_lint.py` (add `_load_mode_profiles()` and `_MODE_PROFILES`)

- [ ] **Step 1: Write the failing test**

Create `skills/ru-editor/scripts/tests/test_mode_profiles.py`:

```python
"""Phase 3: mode-profiles.toml loader and schema validation."""
import unittest
from pathlib import Path
import tempfile
import textwrap
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ru_lint


class TestModeProfilesLoader(unittest.TestCase):
    def test_loads_all_four_modes_from_canonical_file(self):
        profiles = ru_lint._load_mode_profiles()
        self.assertIn("proofread", profiles)
        self.assertIn("line_edit", profiles)
        self.assertIn("technical", profiles)
        self.assertIn("deep_rewrite", profiles)

    def test_canonical_proofread_bounds(self):
        profiles = ru_lint._load_mode_profiles()
        p = profiles["proofread"]
        self.assertAlmostEqual(p["length_ratio_min"], 0.95)
        self.assertAlmostEqual(p["length_ratio_max"], 1.05)
        self.assertAlmostEqual(p["list_items_tolerance"], 0.05)

    def test_canonical_line_edit_bounds(self):
        profiles = ru_lint._load_mode_profiles()
        p = profiles["line_edit"]
        self.assertAlmostEqual(p["length_ratio_min"], 0.70)
        self.assertAlmostEqual(p["length_ratio_max"], 1.15)
        self.assertAlmostEqual(p["list_items_tolerance"], 0.30)

    def test_canonical_deep_rewrite_disabled_bounds(self):
        profiles = ru_lint._load_mode_profiles()
        p = profiles["deep_rewrite"]
        self.assertEqual(p["length_ratio_min"], 0.0)
        self.assertGreaterEqual(p["length_ratio_max"], 99.0)
        self.assertEqual(p["list_items_tolerance"], 1.0)

    def test_missing_mode_raises_config_error(self):
        bad = textwrap.dedent("""
            schema_version = "1.0"
            [modes.proofread]
            length_ratio_min = 0.95
            length_ratio_max = 1.05
            list_items_tolerance = 0.05
        """).strip()
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(bad)
            path = f.name
        with self.assertRaises(ru_lint.ConfigError) as cm:
            ru_lint._load_mode_profiles(path=path)
        self.assertIn("missing mode", str(cm.exception))

    def test_schema_version_mismatch_raises_config_error(self):
        bad = textwrap.dedent("""
            schema_version = "2.0"
            [modes.proofread]
            length_ratio_min = 0.95
            length_ratio_max = 1.05
            list_items_tolerance = 0.05
            [modes.line_edit]
            length_ratio_min = 0.70
            length_ratio_max = 1.15
            list_items_tolerance = 0.30
            [modes.technical]
            length_ratio_min = 0.90
            length_ratio_max = 1.10
            list_items_tolerance = 0.10
            [modes.deep_rewrite]
            length_ratio_min = 0.0
            length_ratio_max = 99.0
            list_items_tolerance = 1.0
        """).strip()
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(bad)
            path = f.name
        with self.assertRaises(ru_lint.ConfigError) as cm:
            ru_lint._load_mode_profiles(path=path)
        self.assertIn("schema_version", str(cm.exception))

    def test_malformed_toml_raises_config_error(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("not = valid = toml ===")
            path = f.name
        with self.assertRaises(ru_lint.ConfigError):
            ru_lint._load_mode_profiles(path=path)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest skills.ru-editor.scripts.tests.test_mode_profiles -v 2>&1 | tail -15`

Or with cwd: `cd skills/ru-editor/scripts/tests && python3 -m unittest test_mode_profiles -v 2>&1 | tail -15`

Expected: failures with `AttributeError: module 'ru_lint' has no attribute '_load_mode_profiles'` and `'ConfigError'`.

- [ ] **Step 3: Create the canonical mode-profiles.toml**

Create `skills/ru-editor/references/mode-profiles.toml`:

```toml
# ru-editor mode profiles — schema 1.0
# Per-mode bounds for length_ratio_violation and list_items_count_within_tolerance.
# Used by ru_lint.py when invoked with --mode <name>.

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

- [ ] **Step 4: Add ConfigError + loader in ru_lint.py**

In `skills/ru-editor/scripts/ru_lint.py`, near the other top-level exceptions (or right after `__version__`/`SCHEMA_VERSION`), add:

```python
class ConfigError(Exception):
    """Raised when configuration files (mode-profiles.toml, etc.) fail validation."""
```

And add the loader near `_load_banned_markers` (around line 364):

```python
import tomllib

_MODE_PROFILES_CACHE: dict | None = None
_REQUIRED_MODES = ("proofread", "line_edit", "technical", "deep_rewrite")
_REQUIRED_KEYS = ("length_ratio_min", "length_ratio_max", "list_items_tolerance")


def _load_mode_profiles(path: str | None = None) -> dict[str, dict]:
    """Load per-mode profiles from references/mode-profiles.toml.

    Cached on first call when path is None. Raises ConfigError on validation failure.
    """
    global _MODE_PROFILES_CACHE
    if path is None:
        if _MODE_PROFILES_CACHE is not None:
            return _MODE_PROFILES_CACHE
        default = Path(__file__).resolve().parent.parent / "references" / "mode-profiles.toml"
        path = str(default)

    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"mode-profiles.toml: file not found at {path}")
    try:
        data = tomllib.loads(p.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"mode-profiles.toml: malformed TOML — {e}") from e

    sv = data.get("schema_version")
    if sv != "1.0":
        raise ConfigError(f"mode-profiles.toml: schema_version mismatch (got {sv!r}, expected '1.0')")

    modes = data.get("modes", {})
    profiles: dict[str, dict] = {}
    for name in _REQUIRED_MODES:
        if name not in modes:
            raise ConfigError(f"mode-profiles.toml: missing mode '{name}'")
        prof = modes[name]
        for key in _REQUIRED_KEYS:
            if key not in prof:
                raise ConfigError(f"mode-profiles.toml: mode '{name}' missing key '{key}'")
        profiles[name] = dict(prof)

    if path == str(Path(__file__).resolve().parent.parent / "references" / "mode-profiles.toml"):
        _MODE_PROFILES_CACHE = profiles
    return profiles
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd skills/ru-editor/scripts/tests && python3 -m unittest test_mode_profiles -v 2>&1 | tail -15`
Expected: 7 tests pass, OK.

- [ ] **Step 6: Run full unit-test suite to ensure no regression**

Run: `cd skills/ru-editor/scripts && python3 -m unittest discover tests 2>&1 | tail -3`
Expected: `OK` with at least 110 tests (103 baseline + 7 new).

- [ ] **Step 7: Commit**

Run:
```bash
git add skills/ru-editor/references/mode-profiles.toml \
        skills/ru-editor/scripts/tests/test_mode_profiles.py \
        skills/ru-editor/scripts/ru_lint.py
git commit -m "feat(ru-editor): add mode-profiles.toml + loader with schema validation"
```

---

## Task 3: CLI --mode flag + JSON schema 1.1 (TDD)

**Files:**
- Create: `skills/ru-editor/scripts/tests/test_cli_mode_flag.py`
- Modify: `skills/ru-editor/scripts/ru_lint.py` (argparse, ctx injection, _format_json, main exit codes)

- [ ] **Step 1: Write the failing test**

Create `skills/ru-editor/scripts/tests/test_cli_mode_flag.py`:

```python
"""Phase 3: CLI --mode flag, JSON schema bump, exit codes."""
import json
import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

RU_LINT = Path(__file__).resolve().parent.parent / "ru_lint.py"


def _run(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RU_LINT), *args],
        capture_output=True, text=True, cwd=cwd,
    )


class TestCliModeFlag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = Path(self.tmp.name) / "source.md"
        self.edt = Path(self.tmp.name) / "edited.md"
        self.src.write_text("Это нейтральный исходник.\n", encoding="utf-8")
        self.edt.write_text("Это нейтральный текст.\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_mode_auto_is_default_and_matches_phase2_behaviour(self):
        r = _run(["check", str(self.edt), "--format", "json"])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["summary"].get("mode"), "auto")
        self.assertEqual(payload["schema_version"], "1.1")

    def test_mode_explicit_line_edit_exposes_in_json(self):
        r = _run(["check", str(self.edt), "--format", "json", "--mode", "line_edit"])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["summary"]["mode"], "line_edit")

    def test_mode_proofread_strict_length_in_diff(self):
        # 25-char source vs 5-char edited => ratio = 0.20, proofread bounds [0.95, 1.05]
        r = _run([
            "diff", str(self.src), str(self.edt),
            "--format", "json", "--mode", "proofread",
        ])
        payload = json.loads(r.stdout)
        names = [f["check"] for f in payload["findings"]]
        self.assertIn("length_ratio_violation", names)

    def test_unknown_mode_returns_exit_3(self):
        r = _run(["check", str(self.edt), "--mode", "aggressive"])
        self.assertEqual(r.returncode, 3)
        self.assertIn("aggressive", (r.stderr + r.stdout).lower())

    def test_malformed_profiles_file_returns_exit_3(self):
        bad = Path(self.tmp.name) / "bad-profiles.toml"
        bad.write_text("not = valid = toml ===", encoding="utf-8")
        env = os.environ.copy()
        env["RU_LINT_MODE_PROFILES"] = str(bad)
        r = subprocess.run(
            [sys.executable, str(RU_LINT), "check", str(self.edt), "--mode", "line_edit"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r.returncode, 3)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/ru-editor/scripts/tests && python3 -m unittest test_cli_mode_flag -v 2>&1 | tail -10`
Expected: failures (the `--mode` argument is unknown, schema_version is "1.0", etc.).

- [ ] **Step 3: Bump SCHEMA_VERSION**

In `skills/ru-editor/scripts/ru_lint.py`, change near the top:

```python
SCHEMA_VERSION = "1.1"
```

- [ ] **Step 4: Add --mode to argparse common parents**

In `_build_parser` (around line 274), in the `common` parser, after the `--strict` line, add:

```python
common.add_argument(
    "--mode",
    choices=("auto", "proofread", "line_edit", "technical", "deep_rewrite"),
    default="auto",
    help="editing mode for length/list-items bounds (default: auto = Phase 2 globals)",
)
```

- [ ] **Step 5: Inject lint_mode into ctx and JSON output**

Find the `main()` function (around line 305). Locate the section where `ctx` is built before `run_checks` is called. Add the profile resolution:

```python
# Resolve mode profile (Phase 3)
lint_mode = args.mode  # "auto" | "proofread" | "line_edit" | "technical" | "deep_rewrite"
profile = None
if lint_mode != "auto":
    try:
        profiles_path = os.environ.get("RU_LINT_MODE_PROFILES")
        profile = _load_mode_profiles(path=profiles_path)[lint_mode]
    except KeyError:
        print(f"ru_lint: unknown mode '{lint_mode}'", file=sys.stderr)
        return 3
    except ConfigError as e:
        print(f"ru_lint: {e}", file=sys.stderr)
        return 3

ctx = {"lint_mode": lint_mode, "profile": profile}
```

Add `import os` at the top of the file if not already present.

In `_format_json` (around line 255), add `"mode"` inside the `summary` dict:

```python
"summary": {
    "mode": lint_mode,
    "hard_fail_count": hard,
    "warn_count": warn,
    "elapsed_ms": elapsed_ms,
},
```

Update the call site in `main()` to pass `lint_mode` to `_format_json`. Since `_format_json` already takes `mode` (the run-mode `check`/`diff`/`both`), rename the run-mode param to `run_mode` everywhere in the function signature to avoid shadowing, OR add a new `lint_mode` param positionally after it. Recommended: extend signature to accept `lint_mode`:

```python
def _format_json(
    findings: list[Finding],
    mode: str,            # run-mode: "check" / "diff" / "both"
    input_path: str,
    source_path: str | None,
    hard: int,
    warn: int,
    elapsed_ms: int,
    lint_mode: str = "auto",  # editing mode for Phase 3
) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "tool": "ru_lint",
        "tool_version": __version__,
        "mode": mode,
        "input_path": input_path,
        "source_path": source_path,
        "summary": {
            "mode": lint_mode,
            "hard_fail_count": hard,
            "warn_count": warn,
            "elapsed_ms": elapsed_ms,
        },
        "findings": [f.to_dict() for f in findings],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
```

In `main()`, update the `_format_json` call to pass `lint_mode=lint_mode`.

- [ ] **Step 6: Wire ConfigError handling in main exit path**

At the very top of `main()`, wrap profile-resolution logic so any uncaught `ConfigError` returns exit 3. The block in Step 5 already does this; verify there is no other code path that swallows it.

- [ ] **Step 7: Run test to verify it passes**

Run: `cd skills/ru-editor/scripts/tests && python3 -m unittest test_cli_mode_flag -v 2>&1 | tail -15`
Expected: 5 tests pass, OK.

- [ ] **Step 8: Run full test suite**

Run: `cd skills/ru-editor/scripts && python3 -m unittest discover tests 2>&1 | tail -3`
Expected: `OK` with at least 115 tests, no regressions.

- [ ] **Step 9: Commit**

```bash
git add skills/ru-editor/scripts/tests/test_cli_mode_flag.py \
        skills/ru-editor/scripts/ru_lint.py
git commit -m "feat(ru-editor): --mode CLI flag, JSON schema 1.1, exit 3 for config errors"
```

---

## Task 4: Per-mode bounds — length_ratio_violation (TDD)

**Files:**
- Create: `skills/ru-editor/scripts/tests/test_modes_per_mode_bounds.py` (length-ratio half; list-items half added in Task 5)
- Modify: `skills/ru-editor/scripts/ru_lint.py` — `_check_length_ratio` reads bounds from `ctx["profile"]`

- [ ] **Step 1: Write the failing test**

Create `skills/ru-editor/scripts/tests/test_modes_per_mode_bounds.py`:

```python
"""Phase 3: per-mode bounds for length_ratio_violation."""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ru_lint
from ru_lint import Document, run_checks


def _docs(src_text: str, edt_text: str) -> tuple[Document, Document]:
    return Document(text=src_text), Document(text=edt_text)


def _has_length_violation(findings) -> bool:
    return any(f.check == "length_ratio_violation" for f in findings)


def _ctx_for_mode(name: str) -> dict:
    profile = ru_lint._load_mode_profiles()[name]
    return {"lint_mode": name, "profile": profile}


class TestLengthRatioPerMode(unittest.TestCase):
    def test_proofread_within_bounds(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 100)  # ratio 1.0
        findings = run_checks(edt, src, "diff", _ctx_for_mode("proofread"))
        self.assertFalse(_has_length_violation(findings))

    def test_proofread_above_bounds(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 110)  # ratio 1.10 > 1.05
        findings = run_checks(edt, src, "diff", _ctx_for_mode("proofread"))
        self.assertTrue(_has_length_violation(findings))

    def test_proofread_below_bounds(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 90)  # ratio 0.90 < 0.95
        findings = run_checks(edt, src, "diff", _ctx_for_mode("proofread"))
        self.assertTrue(_has_length_violation(findings))

    def test_line_edit_within_bounds_at_70_floor(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 75)  # ratio 0.75 inside [0.70, 1.15]
        findings = run_checks(edt, src, "diff", _ctx_for_mode("line_edit"))
        self.assertFalse(_has_length_violation(findings))

    def test_line_edit_below_70_floor(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 60)  # ratio 0.60 < 0.70
        findings = run_checks(edt, src, "diff", _ctx_for_mode("line_edit"))
        self.assertTrue(_has_length_violation(findings))

    def test_line_edit_above_115_ceiling(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 120)  # ratio 1.20 > 1.15
        findings = run_checks(edt, src, "diff", _ctx_for_mode("line_edit"))
        self.assertTrue(_has_length_violation(findings))

    def test_technical_within_bounds(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 95)  # ratio 0.95 inside [0.90, 1.10]
        findings = run_checks(edt, src, "diff", _ctx_for_mode("technical"))
        self.assertFalse(_has_length_violation(findings))

    def test_technical_above_bounds(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 115)  # ratio 1.15 > 1.10
        findings = run_checks(edt, src, "diff", _ctx_for_mode("technical"))
        self.assertTrue(_has_length_violation(findings))

    def test_technical_below_bounds(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 80)  # ratio 0.80 < 0.90
        findings = run_checks(edt, src, "diff", _ctx_for_mode("technical"))
        self.assertTrue(_has_length_violation(findings))

    def test_deep_rewrite_disables_length_check(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 10)  # ratio 0.10
        findings = run_checks(edt, src, "diff", _ctx_for_mode("deep_rewrite"))
        self.assertFalse(_has_length_violation(findings))

    def test_deep_rewrite_disables_even_for_expansion(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 5000)  # ratio 50.0
        findings = run_checks(edt, src, "diff", _ctx_for_mode("deep_rewrite"))
        self.assertFalse(_has_length_violation(findings))

    def test_auto_mode_uses_phase2_globals(self):
        # ratio 0.85 — inside Phase 2 globals [0.80, 1.20], outside line_edit floor 0.70 only matters
        src = Document(text="а" * 100)
        edt = Document(text="а" * 85)
        findings_auto = run_checks(edt, src, "diff", {"lint_mode": "auto", "profile": None})
        self.assertFalse(_has_length_violation(findings_auto))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/ru-editor/scripts/tests && python3 -m unittest test_modes_per_mode_bounds -v 2>&1 | tail -15`
Expected: many failures because `_check_length_ratio` ignores the profile.

- [ ] **Step 3: Modify _check_length_ratio to consult profile**

In `skills/ru-editor/scripts/ru_lint.py`, replace the existing `_check_length_ratio` (around lines 886–902):

```python
@register(name="length_ratio_violation", severity="WARN", mode="diff",
          description="Длина edited вне per-mode диапазона.")
def _check_length_ratio(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    assert source is not None
    src_len = len(source.prose)
    if src_len == 0:
        return []
    ratio = len(doc.prose) / src_len

    profile = ctx.get("profile")
    if profile is not None:
        lo = float(profile["length_ratio_min"])
        hi = float(profile["length_ratio_max"])
    else:
        # auto / Phase 2 globals
        lo, hi = 0.80, 1.20

    if lo <= ratio <= hi:
        return []
    return [Finding(
        check="length_ratio_violation", severity="WARN",
        line=0, col=0,
        match=f"{ratio:.2f}",
        context=f"source: {src_len} chars, edited: {len(doc.prose)} chars, bounds: [{lo:.2f}, {hi:.2f}]",
        message=f"Length ratio {ratio:.2f} вне диапазона [{lo:.2f}, {hi:.2f}].",
    )]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/ru-editor/scripts/tests && python3 -m unittest test_modes_per_mode_bounds.TestLengthRatioPerMode -v 2>&1 | tail -20`
Expected: 12 tests pass, OK.

- [ ] **Step 5: Run full test suite — confirm no Phase 2 regression**

Run: `cd skills/ru-editor/scripts && python3 -m unittest discover tests 2>&1 | tail -3`
Expected: `OK`. (Phase 2 length tests pass because they don't pass a profile, so behaviour stays at globals.)

- [ ] **Step 6: Commit**

```bash
git add skills/ru-editor/scripts/tests/test_modes_per_mode_bounds.py \
        skills/ru-editor/scripts/ru_lint.py
git commit -m "feat(ru-editor): per-mode length_ratio bounds in length_ratio_violation"
```

---

## Task 5: Per-mode bounds — list_items_count_within_tolerance (TDD)

**Files:**
- Modify: `skills/ru-editor/scripts/tests/test_modes_per_mode_bounds.py` (add second test class)
- Modify: `skills/ru-editor/scripts/ru_lint.py` — `_check_list_items_tolerance` reads tolerance from `ctx["profile"]`

- [ ] **Step 1: Add list-items test class**

Append to `skills/ru-editor/scripts/tests/test_modes_per_mode_bounds.py`:

```python
def _has_list_violation(findings) -> bool:
    return any(f.check == "list_items_count_within_tolerance" for f in findings)


def _list_md(n: int) -> str:
    return "\n".join(f"- item {i}" for i in range(n)) + "\n"


class TestListItemsTolerancePerMode(unittest.TestCase):
    def test_proofread_within_5pct(self):
        # 20 items → 19 items = 5% drift, exactly at the border (drift > 5% triggers; 5.0% does not)
        src = Document(text=_list_md(20))
        edt = Document(text=_list_md(19))
        findings = run_checks(edt, src, "diff", _ctx_for_mode("proofread"))
        self.assertFalse(_has_list_violation(findings))

    def test_proofread_drift_exceeds_5pct(self):
        # 20 → 18 = 10% drift, exceeds 5%
        src = Document(text=_list_md(20))
        edt = Document(text=_list_md(18))
        findings = run_checks(edt, src, "diff", _ctx_for_mode("proofread"))
        self.assertTrue(_has_list_violation(findings))

    def test_line_edit_30pct_tolerance(self):
        # 10 → 7 = 30% drift, at boundary
        src = Document(text=_list_md(10))
        edt = Document(text=_list_md(7))
        findings = run_checks(edt, src, "diff", _ctx_for_mode("line_edit"))
        self.assertFalse(_has_list_violation(findings))

    def test_line_edit_drift_exceeds_30pct(self):
        # 10 → 6 = 40%
        src = Document(text=_list_md(10))
        edt = Document(text=_list_md(6))
        findings = run_checks(edt, src, "diff", _ctx_for_mode("line_edit"))
        self.assertTrue(_has_list_violation(findings))

    def test_technical_10pct_tolerance(self):
        src = Document(text=_list_md(20))
        edt = Document(text=_list_md(18))
        findings = run_checks(edt, src, "diff", _ctx_for_mode("technical"))
        self.assertFalse(_has_list_violation(findings))

    def test_technical_drift_exceeds_10pct(self):
        src = Document(text=_list_md(20))
        edt = Document(text=_list_md(17))
        findings = run_checks(edt, src, "diff", _ctx_for_mode("technical"))
        self.assertTrue(_has_list_violation(findings))

    def test_deep_rewrite_disables_list_check(self):
        src = Document(text=_list_md(20))
        edt = Document(text=_list_md(0))
        findings = run_checks(edt, src, "diff", _ctx_for_mode("deep_rewrite"))
        self.assertFalse(_has_list_violation(findings))

    def test_auto_mode_uses_phase2_30pct(self):
        src = Document(text=_list_md(10))
        edt = Document(text=_list_md(7))  # 30% drift, allowed
        findings = run_checks(edt, src, "diff", {"lint_mode": "auto", "profile": None})
        self.assertFalse(_has_list_violation(findings))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/ru-editor/scripts/tests && python3 -m unittest test_modes_per_mode_bounds.TestListItemsTolerancePerMode -v 2>&1 | tail -15`
Expected: failures because `_check_list_items_tolerance` still uses hardcoded 0.30.

- [ ] **Step 3: Modify _check_list_items_tolerance to read profile**

In `skills/ru-editor/scripts/ru_lint.py`, replace `_check_list_items_tolerance` (around lines 647–663):

```python
@register(name="list_items_count_within_tolerance", severity="WARN", mode="diff",
          description="Количество list-items не должно отличаться больше per-mode tolerance.")
def _check_list_items_tolerance(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    assert source is not None
    src_n = len(source.list_items)
    edt_n = len(doc.list_items)
    if src_n == 0:
        return []
    drift = abs(edt_n - src_n) / src_n

    profile = ctx.get("profile")
    tolerance = float(profile["list_items_tolerance"]) if profile is not None else 0.30

    if drift > tolerance:
        return [Finding(
            check="list_items_count_within_tolerance", severity="WARN",
            line=0, col=0, match=f"{int(drift*100)}%",
            context=f"source: {src_n} items, edited: {edt_n} items, tolerance: {int(tolerance*100)}%",
            message=f"Дрейф числа list-items {int(drift*100)}% превышает порог {int(tolerance*100)}%.",
        )]
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/ru-editor/scripts/tests && python3 -m unittest test_modes_per_mode_bounds -v 2>&1 | tail -25`
Expected: 20 tests pass total (12 length + 8 list-items), OK.

- [ ] **Step 5: Run full test suite**

Run: `cd skills/ru-editor/scripts && python3 -m unittest discover tests 2>&1 | tail -3`
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add skills/ru-editor/scripts/tests/test_modes_per_mode_bounds.py \
        skills/ru-editor/scripts/ru_lint.py
git commit -m "feat(ru-editor): per-mode list-items tolerance in list_items_count check"
```

---

## Task 6: Backlog #5 — refactor Document properties to respect ignore-directives (TDD)

**Files:**
- Create: `skills/ru-editor/scripts/tests/test_ignore_symmetry.py`
- Modify: `skills/ru-editor/scripts/ru_lint.py` — `Document` properties extract from `_without_ignored_regions`

**Background:** The five structural extraction properties (`urls`, `code_spans`, `code_blocks`, `headings`, `list_items`) currently use `self.text` (= `raw`). Phase 2 smoke test surfaced asymmetry: a URL inside `<!-- ru-lint:ignore-* -->` in source.md is captured by `source.urls` but not in `edited.md` if the editor removed the ignored block. False-positive «URL потерян». Fix: change all five properties to read from `_without_ignored_regions`. This makes ignore-directives uniformly respected on both sides of the diff.

- [ ] **Step 1: Write the failing test**

Create `skills/ru-editor/scripts/tests/test_ignore_symmetry.py`:

```python
"""Phase 3: backlog #5 — ignore-directives respected on both diff sides."""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ru_lint
from ru_lint import Document, run_checks


CTX_AUTO = {"lint_mode": "auto", "profile": None}


class TestIgnoreSymmetry(unittest.TestCase):
    def test_url_inside_ignore_block_not_extracted(self):
        text = (
            "before\n"
            "<!-- ru-lint:ignore-start -->\n"
            "see https://example.com/secret for details\n"
            "<!-- ru-lint:ignore-end -->\n"
            "after\n"
        )
        doc = Document(text=text)
        self.assertEqual(doc.urls, [])

    def test_url_outside_ignore_block_extracted(self):
        text = (
            "see https://public.example.com here\n"
        )
        doc = Document(text=text)
        self.assertEqual(doc.urls, ["https://public.example.com"])

    def test_urls_preserved_does_not_flag_ignored_url_loss(self):
        # URL only in source's ignored region; edited drops the entire frontmatter
        src_text = (
            "<!-- ru-lint:ignore-start -->\n"
            "url: https://internal.example.com\n"
            "<!-- ru-lint:ignore-end -->\n"
            "Body text.\n"
        )
        edt_text = "Body text.\n"
        src = Document(text=src_text)
        edt = Document(text=edt_text)
        findings = run_checks(edt, src, "diff", CTX_AUTO)
        for f in findings:
            self.assertNotEqual(
                f.check, "urls_preserved",
                msg=f"unexpected urls_preserved finding: {f}",
            )

    def test_code_span_inside_ignore_block_not_extracted(self):
        text = (
            "<!-- ru-lint:ignore-line -->\n"
            "do not lint `secret_token`\n"
            "and `public_token` is fine\n"
        )
        doc = Document(text=text)
        # ignore-line covers the next non-empty line
        self.assertNotIn("secret_token", doc.code_spans)
        self.assertIn("public_token", doc.code_spans)

    def test_heading_inside_ignore_block_not_counted(self):
        text = (
            "<!-- ru-lint:ignore-start -->\n"
            "## Hidden Heading\n"
            "<!-- ru-lint:ignore-end -->\n"
            "## Real Heading\n"
        )
        doc = Document(text=text)
        self.assertEqual(len(doc.headings), 1)
        self.assertEqual(doc.headings[0][1], "Real Heading")

    def test_list_items_inside_ignore_block_not_counted(self):
        text = (
            "<!-- ru-lint:ignore-start -->\n"
            "- hidden 1\n"
            "- hidden 2\n"
            "<!-- ru-lint:ignore-end -->\n"
            "- real 1\n"
            "- real 2\n"
            "- real 3\n"
        )
        doc = Document(text=text)
        self.assertEqual(len(doc.list_items), 3)

    def test_list_items_count_does_not_flag_ignored_drop(self):
        # source has 3 items inside ignore + 4 real; edited preserves only the 4 real
        src_text = (
            "<!-- ru-lint:ignore-start -->\n"
            "- a\n- b\n- c\n"
            "<!-- ru-lint:ignore-end -->\n"
            "- one\n- two\n- three\n- four\n"
        )
        edt_text = "- one\n- two\n- three\n- four\n"
        src = Document(text=src_text)
        edt = Document(text=edt_text)
        findings = run_checks(edt, src, "diff", CTX_AUTO)
        for f in findings:
            self.assertNotEqual(f.check, "list_items_count_within_tolerance")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/ru-editor/scripts/tests && python3 -m unittest test_ignore_symmetry -v 2>&1 | tail -20`
Expected: failures (URLs/headings/list-items still extracted from raw text).

- [ ] **Step 3: Refactor Document structural properties**

In `skills/ru-editor/scripts/ru_lint.py`, change the bodies of these `@cached_property` methods on `Document` (around lines 84–104) to read from `self._without_ignored_regions` instead of `self.text`:

```python
@cached_property
def code_blocks(self) -> list[str]:
    return [m.group(0) for m in _CODE_BLOCK_RE.finditer(self._without_ignored_regions)]

@cached_property
def code_spans(self) -> list[str]:
    return [m.group(0)[1:-1] for m in _CODE_SPAN_RE.finditer(self._without_ignored_regions)]

@cached_property
def urls(self) -> list[str]:
    return [
        m.group(0).rstrip(_URL_TRAILING_PUNCT)
        for m in _URL_RE.finditer(self._without_ignored_regions)
    ]

@cached_property
def headings(self) -> list[tuple[int, str]]:
    return [
        (len(m.group(1)), m.group(2))
        for m in _HEADING_RE.finditer(self._without_ignored_regions)
    ]

@cached_property
def list_items(self) -> list[str]:
    return [m.group(1) for m in _LIST_ITEM_RE.finditer(self._without_ignored_regions)]
```

Leave `prose`, `numeric_tokens`, and `raw` unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/ru-editor/scripts/tests && python3 -m unittest test_ignore_symmetry -v 2>&1 | tail -15`
Expected: 7 tests pass, OK.

- [ ] **Step 5: Run full test suite — Phase 2 must still be green**

Run: `cd skills/ru-editor/scripts && python3 -m unittest discover tests 2>&1 | tail -3`
Expected: `OK`. If any Phase 2 fixture used ignore-directives expecting the old behaviour, that's a real bug — investigate and update the test only if the new behaviour is correct per spec.

- [ ] **Step 6: Run own-files regression**

Run: `python3 skills/ru-editor/scripts/ru_lint.py check skills/ru-editor/SKILL.md && \
      python3 skills/ru-editor/scripts/ru_lint.py check skills/ru-editor/references/editing-examples.md && \
      python3 skills/ru-editor/scripts/ru_lint.py check skills/ru-editor/references/typography.md`
Expected: all three exit 0 (no HARD_FAIL). Same as Phase 2 baseline.

- [ ] **Step 7: Commit**

```bash
git add skills/ru-editor/scripts/tests/test_ignore_symmetry.py \
        skills/ru-editor/scripts/ru_lint.py
git commit -m "fix(ru-editor): respect ignore-directives in all structural Document properties

Closes Phase 2 backlog #5: urls_preserved, list_items_count, and other
diff-mode structural checks now extract from _without_ignored_regions
on both sides, eliminating false positives from ignore-wrapped frontmatter."
```

---

## Task 7: Run master regression after linter changes

**Files:** none (verification only).

- [ ] **Step 1: Run master runner**

Run: `bash scripts/run_all_tests.sh 2>&1 | tail -10`
Expected: `ALL 2 PHASE(S) PASSED` (Phase 3 stage doesn't exist yet — added in Task 11).

- [ ] **Step 2: Confirm test count**

Run: `cd skills/ru-editor/scripts && python3 -m unittest discover tests 2>&1 | tail -3`
Expected: `OK` with at least 130 tests (103 baseline + 7 mode-profiles + 5 cli + 12 length + 8 list + 7 ignore-symmetry).

If anything fails, return to the relevant earlier task before proceeding. No commit (no changes).

---

## Task 8: Label seed corpus with expected_mode

**Files:** modify all 20 files at `evals/seed-corpus/*/brief.toml`.

Final per-pair assignment (based on each pair's source/expected/intensity):

| Pair | expected_mode | Reasoning |
|---|---|---|
| `01-api-auth-light` | `technical` | API/auth content |
| `02-runbook-medium` | `technical` | Runbook with commands |
| `03-api-docs-heavy` | `technical` | API documentation |
| `04-pitch-light` | `line_edit` | Marketing copy, light cleanup |
| `05-product-launch-medium` | `line_edit` | Product announcement |
| `06-marketing-landing-heavy` | `deep_rewrite` | Landing page, heavy AI-slop |
| `07-tutorial-intro-light` | `line_edit` | Tutorial prose |
| `08-dataflow-tutorial-medium` | `technical` | Tutorial with code/dataflow |
| `09-cicd-course-heavy` | `technical` | CI/CD content |
| `10-blog-note-light` | `line_edit` | Casual blog |
| `11-listicle-medium` | `line_edit` | Listicle |
| `12-opinion-heavy` | `deep_rewrite` | Heavy opinion piece |
| `13-status-light` | `proofread` | Status update — minimal edits |
| `14-support-reply-medium` | `line_edit` | Support reply |
| `15-team-newsletter-heavy` | `deep_rewrite` | Heavy newsletter cleanup |
| `16-idempotency-clean` | `proofread` | Already clean |
| `17-directives-heavy` | `line_edit` | Tests directives, prose-heavy |
| `18-code-vs-prose` | `technical` | Mixed code/prose |
| `19-unicode-mixed` | `line_edit` | Unicode handling |
| `20-minimal` | `proofread` | Minimal text |

Tally: 7 technical, 8 line_edit, 3 proofread, 2 deep_rewrite. Distribution is meaningful for accuracy measurement (no single class dominates).

- [ ] **Step 1: Add expected_mode to each brief.toml**

For each of the 20 files in the table above, append (or insert at top, preserving the existing structure) the line:

```toml
expected_mode = "<value-from-table>"
```

The implementer should open each `brief.toml`, read the existing structure, and place `expected_mode` near the other top-level metadata (typically near `genre = ...` or `intensity = ...`). Do not duplicate if it already exists.

- [ ] **Step 2: Verify all 20 files have the field**

Run: `grep -l "^expected_mode" evals/seed-corpus/*/brief.toml | wc -l`
Expected: `20`.

- [ ] **Step 3: Verify each value is one of the four allowed**

Run: `grep -h "^expected_mode" evals/seed-corpus/*/brief.toml | sort | uniq -c`
Expected: counts matching the table above (8 line_edit, 7 technical, 3 proofread, 2 deep_rewrite).

- [ ] **Step 4: Commit**

```bash
git add evals/seed-corpus/*/brief.toml
git commit -m "chore(eval): label seed-corpus pairs with expected_mode for Phase 3"
```

---

## Task 9: SKILL.md — frontmatter + new ## Editing Modes section

**Files:**
- Modify: `skills/ru-editor/SKILL.md`

- [ ] **Step 1: Read current SKILL.md to confirm structure**

Run: `grep -n "^## \|^---" skills/ru-editor/SKILL.md | head -20`
Expected: confirms `## Factual Integrity` (line 23), `## QA Gate` (line 53), `## Important Rules` (line 102).

- [ ] **Step 2: Update frontmatter**

In `skills/ru-editor/SKILL.md`, modify the frontmatter block (lines 2–17) to add `allowed-tools` and bump version. Replace:

```yaml
---
name: ru-editor
description: Edits AI-generated or poorly written Russian text into natural, idiomatic
  Russian following informational style. Use when user says "отредактируй",
  "причеши текст", "сделай текст человечным", "убери ИИ-шность", "инфостиль",
  "почисти текст", "перепиши по-человечески", "humanize Russian", "edit Russian text",
  "fix AI text", or provides Russian text for editing and quality improvement.
  Removes AI markers (ChatGPT-isms), applies informational style, fixes typography,
  adds human voice. NOT for translation (use en-ru-translator-adv), English text
  editing, or creative writing.
license: MIT
metadata:
  author: Anthony Vdovitchenko @ Automatica (https://t.me/aiwizards)
  version: 2.4.0
  category: editing
---
```

with:

```yaml
---
name: ru-editor
description: Edits AI-generated or poorly written Russian text into natural, idiomatic
  Russian following informational style. Picks one of four modes (proofread, line_edit,
  technical, deep_rewrite) from request phrasing, or honors an explicit `Mode: <name>`
  prefix. Use when user says "отредактируй", "причеши текст", "сделай текст человечным",
  "убери ИИ-шность", "инфостиль", "почисти текст", "перепиши по-человечески",
  "humanize Russian", "edit Russian text", "fix AI text", or provides Russian text
  for editing and quality improvement. Removes AI markers (ChatGPT-isms), applies
  informational style, fixes typography, adds human voice. NOT for translation
  (use en-ru-translator-adv), English text editing, or creative writing.
allowed-tools: Read, Bash(python3:*)
license: MIT
metadata:
  author: Anthony Vdovitchenko @ Automatica (https://t.me/aiwizards)
  version: 2.5.0
  category: editing
---
```

- [ ] **Step 3: Insert ## Editing Modes section**

Insert the following section in `skills/ru-editor/SKILL.md` immediately AFTER the `## QA Gate` section (and any nested `### Manual fallback checklist` / `### Suppressing false positives` subsections), and BEFORE `## Important Rules`. The exact insertion point: after the last line of the QA Gate block, before the line `## Important Rules`.

````markdown
## Editing Modes

`ru-editor` operates in one of four modes. Each mode is a contract about how aggressively you edit and how much length drift is permitted. The QA Gate enforces the contract via per-mode bounds in `ru_lint.py`.

### Mode taxonomy

| Mode | Purpose | Length budget | List-items tolerance |
|---|---|---|---|
| `proofread` | Grammar, punctuation, typography only. Do not touch meaning, structure, or word choice beyond corrections. | 0.95–1.05 (±5%) | ±5% |
| `line_edit` (default) | Clarity, naturalness, AI-marker removal. Structure preserved; meaning preserved; aggressive cleanup of puffery, padding, and AI-isms. | 0.70–1.15 | ±30% |
| `technical` | Technical text. Protect terms, code spans, commands, paths, identifiers. Light-touch outside protected fragments. | 0.90–1.10 (±10%) | ±10% |
| `deep_rewrite` | Rewrite from scratch. Length and list-tolerance disabled. Absolute HARD_FAIL checks (emoji, arrows, factual integrity, banned markers) still enforced. | disabled | disabled |

### Mode detection

1. **Explicit override.** If the user's first line matches `/^Mode:\s*(\w+)/i`, capture the name.
   - If the name is `proofread`, `line_edit`, `technical`, or `deep_rewrite` — use it. Echo `(explicit)`.
   - If the name is unknown — ignore the prefix, fall through to auto-detect, and echo `(default; unknown mode '<name>' ignored)`.

2. **Auto-detect by trigger phrases:**
   - **`deep_rewrite`** — «перепиши с нуля», «полностью переделай», «deep rewrite».
   - **`technical`** — «технически отредактируй», «technical edit», «техническая правка», OR the document contains ≥1 fenced code block / inline code spans cover ≥5% of body characters.
   - **`proofread`** — «вычитай», «proofread», «исправь ошибки», «исправь опечатки», «грамматика».
   - **`line_edit`** — «отредактируй», «причеши», «улучши», «убери ИИ-шность», «инфостиль», «убери воду», «почисти текст», «humanize».

3. **Conflict resolution.**
   - Explicit always wins over auto-detect.
   - In auto-detect ties: `deep_rewrite` > `technical` > `proofread` > `line_edit`.
   - When phrases from two modes both fire (e.g. «технически вычитай»), pick by primary verb (the imperative governing the request: «вычитай» → proofread).

4. **Default.** If no trigger fires, mode is `line_edit`. Echo `(auto-detected)`.

5. **Ambiguous.** If signals conflict and no clear primary verb resolves it, default to `line_edit`. Echo `(default; ambiguous request)`. Do not block — just continue.

### Echo format

The first line of skill output is mandatory and uses one of these exact formats:

```
Mode: line_edit (auto-detected)
Mode: technical (explicit)
Mode: proofread (auto-detected)
Mode: line_edit (default; unknown mode 'aggressive' ignored)
Mode: line_edit (default; ambiguous request)
```

A blank line follows. Then the edited text.

### Examples

**Example 1 — auto-detect line_edit (default):**

```
User: «Отредактируй это: <текст>»
→ no Mode: prefix, trigger «отредактируй» → line_edit
→ Output:
   Mode: line_edit (auto-detected)

   <edited text>
```

**Example 2 — explicit technical:**

```
User: «Mode: technical
       <текст с CLI-командами>»
→ first line matches; valid mode → technical (explicit)
→ Output:
   Mode: technical (explicit)

   <edited text>
```

**Example 3 — conflict resolved by primary verb:**

```
User: «Технически вычитай <текст>»
→ both technical and proofread fire; primary verb «вычитай» → proofread
→ Output:
   Mode: proofread (auto-detected)

   <edited text>
```
````

- [ ] **Step 4: Verify the section is well-formed**

Run: `grep -n "^## " skills/ru-editor/SKILL.md`
Expected: new `## Editing Modes` heading appears between `## QA Gate` and `## Important Rules`.

- [ ] **Step 5: Verify line budget — must stay under 700 lines for always-load**

Run: `wc -l skills/ru-editor/SKILL.md`
Expected: under 700 lines (Phase 2 budget). The `## Editing Modes` section is ~80 lines; SKILL.md should land around 350–400 lines total.

- [ ] **Step 6: Commit**

```bash
git add skills/ru-editor/SKILL.md
git commit -m "feat(ru-editor): SKILL.md frontmatter (allowed-tools, v2.5.0) + ## Editing Modes section"
```

---

## Task 10: SKILL.md — update QA Gate, Output Format, Three-Step Workflow

**Files:**
- Modify: `skills/ru-editor/SKILL.md`

- [ ] **Step 1: Update ## QA Gate to reference --mode**

In `skills/ru-editor/SKILL.md`, find the `## QA Gate` section. Locate the linter invocation line (typically describing `python3 scripts/ru_lint.py both ...`). Replace it with the mode-aware invocation. Read the existing section first:

Run: `sed -n '53,100p' skills/ru-editor/SKILL.md`

Then edit: change the invocation example to:

```bash
python3 ~/.claude/skills/ru-editor/scripts/ru_lint.py both <source.md> <edited.md> --mode <detected_mode>
```

And add a paragraph about exit codes:

```markdown
**Exit codes:**

- `0` — no findings (clean).
- `1` — at least one HARD_FAIL.
- `2` — only WARN, but `--strict` was passed.
- `3` — configuration error (`mode-profiles.toml` missing/malformed, unknown `--mode`). Fall through to manual fallback and warn the user that the linter could not run.
```

- [ ] **Step 2: Update ## Output Format to mandate echo first-line**

In `skills/ru-editor/SKILL.md`, find `## Output Format` (around line 268). Add at the top of the section:

````markdown
The first line of every output is the mode echo (see `## Editing Modes`):

```
Mode: <name> (<auto-detected|explicit|default; ...>)
```

A blank line follows, then the edited text.
````

(Preserve any existing content in `## Output Format` after this insertion.)

- [ ] **Step 3: Update ## Three-Step Workflow with mode-aware notes**

In `skills/ru-editor/SKILL.md`, find `## Three-Step Workflow` (around line 144). Add a one-paragraph preamble at the top of the section:

```markdown
The three steps below apply in every mode. Mode determines aggressiveness:

- **Proofread** — Step 1 only fixes typography/grammar/punctuation. Steps 2 and 3 verify nothing else changed.
- **Line Edit (default)** — Steps 1–3 as written below.
- **Technical** — Step 1 protects code spans, commands, paths, and technical terms; treats them as immutable. Otherwise Steps 1–3 as written.
- **Deep Rewrite** — Step 1 may restructure freely; length and list-tolerance are disabled in QA Gate. Absolute HARD_FAIL checks still apply.
```

- [ ] **Step 4: Verify line budget**

Run: `wc -l skills/ru-editor/SKILL.md`
Expected: still under 700 lines.

- [ ] **Step 5: Run own-files regression — SKILL.md must still pass linter**

Run: `python3 skills/ru-editor/scripts/ru_lint.py check skills/ru-editor/SKILL.md`
Expected: exit 0 (no HARD_FAIL).

- [ ] **Step 6: Commit**

```bash
git add skills/ru-editor/SKILL.md
git commit -m "feat(ru-editor): mode-aware QA Gate, Output Format echo line, Workflow notes"
```

---

## Task 11: Phase 3 acceptance script

**Files:**
- Create: `skills/ru-editor/scripts/run_phase3_acceptance.sh`
- Modify: `scripts/run_all_tests.sh`

- [ ] **Step 1: Create acceptance script**

Create `skills/ru-editor/scripts/run_phase3_acceptance.sh`:

```bash
#!/usr/bin/env bash
# Phase 3 acceptance gate: unit tests + corpus eval + own-files + perf.
# Exits 0 on full pass; non-zero on any failure.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SKILL_DIR="$ROOT/skills/ru-editor"
SCRIPTS_DIR="$SKILL_DIR/scripts"
TESTS_DIR="$SCRIPTS_DIR/tests"
LINTER="$SCRIPTS_DIR/ru_lint.py"
CORPUS_DIR="$ROOT/evals/seed-corpus"

echo "── PHASE 3 ACCEPTANCE: starting ──"

# 1. Unit tests
echo "  [1/5] unit tests..."
( cd "$SCRIPTS_DIR" && python3 -m unittest discover tests 2>&1 | tail -3 )

# 2. Mode-profiles smoke
echo "  [2/5] mode-profiles smoke..."
python3 "$LINTER" --version > /dev/null
python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path("skills/ru-editor/scripts").resolve()))
import ru_lint
profiles = ru_lint._load_mode_profiles()
required = {"proofread", "line_edit", "technical", "deep_rewrite"}
assert required.issubset(profiles.keys()), f"missing modes: {required - profiles.keys()}"
print(f"  loaded {len(profiles)} profiles: {sorted(profiles.keys())}")
PY

# 3. Seed-corpus eval (mode detection accuracy + violation rate)
echo "  [3/5] seed-corpus eval..."
python3 - <<PY
import json, subprocess, sys, tomllib
from pathlib import Path

corpus = Path("$CORPUS_DIR")
linter = "$LINTER"

pairs = sorted(p for p in corpus.iterdir() if p.is_dir())
assert len(pairs) == 20, f"expected 20 pairs, got {len(pairs)}"

correct = 0
violations = 0
results = []
for pair in pairs:
    brief = tomllib.loads((pair / "brief.toml").read_text(encoding="utf-8"))
    expected = brief.get("expected_mode")
    assert expected, f"{pair.name}: missing expected_mode"

    src = pair / "source.md"
    edt = pair / "expected.md"

    # Run with declared mode and count length/list violations
    r = subprocess.run(
        ["python3", linter, "both", str(src), str(edt),
         "--format", "json", "--mode", expected],
        capture_output=True, text=True,
    )
    payload = json.loads(r.stdout)
    bad = [f for f in payload["findings"]
           if f["check"] in ("length_ratio_violation",
                             "list_items_count_within_tolerance")]
    if bad:
        violations += 1

    # Mode detection: simple proxy — length-ratio ok at expected mode means mode is plausible
    # Since the model performs detection, here we measure linter agreement: the linter
    # accepts the pair under the declared mode. detection_accuracy = pairs with no
    # length/list violation when run at expected_mode.
    if not bad:
        correct += 1
    results.append((pair.name, expected, len(bad)))

accuracy = correct / 20
violation_rate = violations / 20

print(f"  pairs: 20")
print(f"  correct (zero length/list violations at expected mode): {correct}")
print(f"  violation_rate: {violation_rate:.2%}")
print(f"  accuracy: {accuracy:.2%}")

if accuracy < 0.85:
    print("  FAIL: accuracy < 0.85")
    for name, mode, n in results:
        print(f"    {name}: mode={mode}, violations={n}")
    sys.exit(1)
if violation_rate >= 0.05:
    print("  FAIL: violation_rate >= 0.05")
    for name, mode, n in results:
        if n:
            print(f"    {name}: mode={mode}, violations={n}")
    sys.exit(1)
print("  PASS")
PY

# 4. Own-files regression — 0 HARD_FAIL
echo "  [4/5] own-files regression..."
for f in "$SKILL_DIR/SKILL.md" "$SKILL_DIR"/references/*.md; do
    if ! python3 "$LINTER" check "$f" > /dev/null 2>&1; then
        echo "  FAIL: HARD_FAIL on $f"
        python3 "$LINTER" check "$f"
        exit 1
    fi
done
echo "  PASS"

# 5. Performance: <100ms per 5K char
echo "  [5/5] performance budget..."
SAMPLE="$SKILL_DIR/references/editing-examples.md"
python3 - <<PY
import subprocess, time, sys
sample = "$SAMPLE"
chars = len(open(sample, encoding="utf-8").read())
n = 3
elapsed = []
for _ in range(n):
    t0 = time.perf_counter()
    subprocess.run(["python3", "$LINTER", "check", sample],
                   capture_output=True, check=True)
    elapsed.append((time.perf_counter() - t0) * 1000)
avg_ms = sum(elapsed) / n
per_5k = avg_ms / chars * 5000
print(f"  sample: {sample} ({chars} chars), avg: {avg_ms:.0f}ms, per 5K: {per_5k:.1f}ms")
if per_5k > 100:
    print("  FAIL: per-5K time > 100ms")
    sys.exit(1)
print("  PASS")
PY

echo "── PHASE 3 ACCEPTANCE: ALL PASSED ──"
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x skills/ru-editor/scripts/run_phase3_acceptance.sh`

- [ ] **Step 3: Run acceptance script**

Run: `bash skills/ru-editor/scripts/run_phase3_acceptance.sh`
Expected: ends with `── PHASE 3 ACCEPTANCE: ALL PASSED ──`. If accuracy < 85% or violation rate ≥ 5%, the failure prints per-pair detail — diagnose by reviewing the offending pairs and adjusting either mode-profiles bounds or the per-pair `expected_mode` label. Do not loosen mode-profiles bounds purely to make tests pass; if labels are wrong, fix them; if bounds are wrong relative to seed corpus reality, that is meaningful design feedback to surface.

- [ ] **Step 4: Update master runner**

Modify `scripts/run_all_tests.sh` — find the existing Phase 1 / Phase 2 invocation block. After Phase 2, add Phase 3 invocation and update the final "ALL N PHASE(S) PASSED" line. Read the file first:

Run: `cat scripts/run_all_tests.sh`

Then add a Phase 3 stage before the final summary line. The exact diff depends on current structure; the new Phase 3 stage should mirror the Phase 2 one:

```bash
echo
echo "════════════════════════════════════════════════════════════"
echo "  PHASE 3"
echo "════════════════════════════════════════════════════════════"
bash "$ROOT/skills/ru-editor/scripts/run_phase3_acceptance.sh"
echo "── Phase 3 PASSED ──"
```

Update the final phase counter: `ALL 2 PHASE(S) PASSED` → `ALL 3 PHASE(S) PASSED`.

- [ ] **Step 5: Run master runner**

Run: `bash scripts/run_all_tests.sh 2>&1 | tail -5`
Expected: `ALL 3 PHASE(S) PASSED`.

- [ ] **Step 6: Commit**

```bash
git add skills/ru-editor/scripts/run_phase3_acceptance.sh scripts/run_all_tests.sh
git commit -m "chore(ru-editor): Phase 3 acceptance script + master-runner integration"
```

---

## Task 12: CHANGELOG entry for v2.5.0

**Files:**
- Modify: `skills/ru-editor/CHANGELOG.md`

- [ ] **Step 1: Insert v2.5.0 entry above v2.4.0**

Open `skills/ru-editor/CHANGELOG.md`. Insert this block right after the top header section (before the existing `## [2.4.0] — 2026-04-28` heading):

```markdown
## [2.5.0] — 2026-04-28

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
```

- [ ] **Step 2: Verify the file is well-formed**

Run: `head -50 skills/ru-editor/CHANGELOG.md`
Expected: top of file shows the v2.5.0 entry above v2.4.0.

- [ ] **Step 3: Commit**

```bash
git add skills/ru-editor/CHANGELOG.md
git commit -m "release(ru-editor): bump to v2.5.0 + CHANGELOG"
```

---

## Task 13: Test-agent prompt for delegated testing

**Files:**
- Create: `.development/prompts/phase3-testing-agent.md`

This task creates the prompt the user requested — a self-contained brief that can be handed to a fresh subagent (via Task/Agent tool) to validate Phase 3, optionally extend the test corpus, and report results. The prompt is dispatched in Task 14 (smoke step) or anytime after.

- [ ] **Step 1: Write the test-agent prompt**

Create `.development/prompts/phase3-testing-agent.md`:

````markdown
# Phase 3 Testing Agent — Brief

You are dispatched as a subagent to validate ru-editor v2.5.0 (Phase 3 — Modes + tools tightening). You start with no shared context. Read this brief end-to-end before doing anything.

## What to verify

The implementation introduces four editing modes (`proofread`, `line_edit`, `technical`, `deep_rewrite`), per-mode bounds in `ru_lint.py`, hybrid mode detection in `SKILL.md`, and a refactored `Document` extraction that respects ignore-directives uniformly.

You must verify, in order:

1. **Phase 1 + Phase 2 + Phase 3 master regression is green.**
2. **The four modes produce distinct linter behaviour on identical input.** Specifically: a (source, edited) pair that produces zero violations under `line_edit` should produce a length WARN under `proofread` if the drift is `> 5%`; should produce no violations under `deep_rewrite`; etc.
3. **Mode echo is present in skill output** when ru-editor is actually invoked. Verify by inspection of any sample output you can generate.
4. **The 20 seed-corpus pairs pass acceptance** (`bash skills/ru-editor/scripts/run_phase3_acceptance.sh`).
5. **The 8 found-samples (real-world AI-Slop) pass under `--mode line_edit`** with zero false-positive length WARN. This is the regression case from Phase 2 smoke.
6. **Optional corpus extension** (only if step 4 has < 85% accuracy or step 5 fails): see «Extending the test corpus» below.

## Setup

Working directory: `/Users/codegeek/src/agent-skills`. Branch should be `ru-editor-v2.5-modes` (verify with `git branch --show-current`). If a different branch, stop and report — do not attempt to switch.

Before running anything, confirm:
- `git status` shows clean tree (or only the agent's own scratch).
- `python3 --version` reports ≥ 3.11 (required for `tomllib`).

## Run the master regression

```bash
bash scripts/run_all_tests.sh 2>&1 | tail -10
```

Expected: ends with `ALL 3 PHASE(S) PASSED`. If anything fails, capture the failing block and stop. Report which phase failed and what the linter said.

## Run mode-distinction tests by hand

Pick any pair from `evals/seed-corpus/` (e.g., `04-pitch-light/`). Run the linter with each of the four modes:

```bash
PAIR=evals/seed-corpus/04-pitch-light
for M in proofread line_edit technical deep_rewrite; do
    echo "--- mode=$M ---"
    python3 skills/ru-editor/scripts/ru_lint.py both \
        $PAIR/source.md $PAIR/expected.md \
        --format json --mode $M | jq '.summary'
done
```

Expected: `proofread` likely shows higher length-violation count than `line_edit`; `deep_rewrite` shows zero length/list violations regardless. If all four modes produce identical output, the per-mode bounds plumbing has a bug — investigate `ctx["profile"]` injection in `main()` and `_check_length_ratio` / `_check_list_items_tolerance`.

## Run the found-samples regression (the Phase 2 smoke gap)

```bash
for d in evals/found-samples/0*/; do
    echo "=== $d ==="
    python3 skills/ru-editor/scripts/ru_lint.py both \
        "$d/source.md" "$d/edited.md" \
        --format json --mode line_edit | jq '.summary'
done
```

Expected: 8/8 exit 0. The `summary.warn_count` may include `length_ratio_violation` if drift exceeds 0.70 floor — this is acceptable and expected (real AI-slop sometimes shrinks > 30%). Report any HARD_FAIL.

## Extending the test corpus (only if acceptance < 85% or found-samples fail)

If accuracy drops below 85%, the cause is one of:

1. **Mislabeled `expected_mode`.** A pair labeled `technical` whose `expected.md` shrinks > 10% from `source.md` will violate technical bounds. Check whether the label matches the actual editorial intent of the pair. If the pair is genuinely a `line_edit` (clarity edit, not technical-protect-the-code edit), relabel.

2. **Bounds too tight relative to corpus.** Less likely — bounds were chosen empirically. But if an entire mode class consistently violates (e.g., all 7 `technical` pairs fail), bounds need adjustment.

3. **Extension needed.** If the corpus is too small to discriminate (e.g., only 2 `deep_rewrite` pairs), generate 1–2 more pairs of the under-represented class.

### How to add a new corpus pair

Create directory `evals/seed-corpus/21-<name>-<intensity>/` (numbering continues from 20). Required files:

- `source.md` — input text (Russian, may be AI-slop, marketing, technical, etc.)
- `expected.md` — your hand-edited output, exemplifying the chosen mode.
- `brief.toml` — metadata. Minimal schema:

```toml
genre = "<technical|marketing|tutorial|listicle|opinion|status|support|newsletter|clean|directives|code-vs-prose|unicode|minimal>"
intensity = "<light|medium|heavy>"
expected_mode = "<proofread|line_edit|technical|deep_rewrite>"
notes = "Short freeform description of what makes this pair interesting."

[expected_findings]
hard_fail_max = 0
warn_max = <N>  # generous upper bound on tolerated WARN
```

Once added, re-run `bash skills/ru-editor/scripts/run_phase3_acceptance.sh`. New pairs are picked up automatically (the script iterates `evals/seed-corpus/*/`).

### How to add a found-samples pair

Same structure under `evals/found-samples/<NN>-<source>-<short-desc>/` with `source.md` and `edited.md`. No `brief.toml` required for found-samples.

## What to report

A concise report (under 400 words) with:

1. Pass/fail status for each numbered verification (1–6).
2. If any failed: the exact command, the truncated output, your diagnosis, and the proposed fix.
3. If you extended the corpus: list the new pairs and reason for adding each.
4. Any insight that's worth feeding into Phase 4 / 5 (anomalies, threshold tuning ideas, etc.).

## What NOT to do

- Do not push anything. The user has standing instruction: local only.
- Do not modify `mode-profiles.toml` unless step 4 specifically demands it; if you must, document why.
- Do not delete or merge branches. Your job is verification.
- Do not invoke ru-editor on the parent context's text. You operate within the agent-skills repo.
````

- [ ] **Step 2: Commit**

```bash
git add .development/prompts/phase3-testing-agent.md
git commit -m "docs(ru-editor): Phase 3 testing-agent prompt for delegated validation"
```

Note: `.development/` is in `.gitignore`. The commit will fail with "no changes added to commit". This is expected. The prompt lives locally only, just like the smoke-test report from Phase 2.

If you want the prompt tracked in git, move it to `docs/superpowers/prompts/2026-04-28-ru-editor-phase3-testing-agent.md` instead and commit there. Otherwise, leave under `.development/` per the established pattern.

**Decision:** keep under `.development/` (matches Phase 2 prompt convention). Skip the commit step.

---

## Task 14: Smoke test, sync, merge, tag, cleanup

**Files:** none (git + filesystem operations).

This is the destructive-ops task — analogous to Phase 2's Task 16. Two gates:

- **Gate 1 (sync to global):** rsync to `~/.claude/skills/ru-editor/`. User approval needed.
- **Gate 2 (merge + tag + branch delete):** after smoke test passes. User approval needed.

- [ ] **Step 1: Final regression on branch tip**

Run: `bash scripts/run_all_tests.sh 2>&1 | tail -5`
Expected: `ALL 3 PHASE(S) PASSED`.

- [ ] **Step 2: Verify branch state**

Run: `git status -s && git rev-list --count main..HEAD && git log --oneline -1`
Expected: clean tree, ~12 commits ahead of main, HEAD is the v2.5.0 release commit.

- [ ] **Step 3: Request Gate 1 approval, then sync to global**

Ask the user: «Подтверждаешь Гейт 1 — rsync в ~/.claude/skills/ru-editor/?»

On approval:

```bash
rsync -av --delete \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' \
    /Users/codegeek/src/agent-skills/skills/ru-editor/ \
    /Users/codegeek/.claude/skills/ru-editor/

diff -rq /Users/codegeek/src/agent-skills/skills/ru-editor/ /Users/codegeek/.claude/skills/ru-editor/ \
    | grep -v -E '__pycache__|\.pyc$|\.DS_Store'

grep "^  version:" /Users/codegeek/.claude/skills/ru-editor/SKILL.md
```

Expected: empty diff (modulo excluded patterns), `version: 2.5.0`.

- [ ] **Step 4: Smoke test (USER step)**

Tell the user: open a fresh CC session (`/clear`), invoke ru-editor on a short test text, verify mode echo appears in first line, run optional `python3 ~/.claude/skills/ru-editor/scripts/ru_lint.py both <s> <e> --mode <m>` to confirm linter is mode-aware. Report «smoke ok» or specific failure.

Optionally: dispatch the test-agent prompt from Task 13 to a subagent via the Task tool. The subagent runs the broader matrix and reports back.

**STOP HERE and wait for user confirmation.**

- [ ] **Step 5: Request Gate 2 approval, then merge**

Ask the user: «Подтверждаешь Гейт 2 — merge в main, локальный тег v2.5.0, удаление ветки?»

On approval:

```bash
git checkout main
git merge --ff-only ru-editor-v2.5-modes
git tag -a ru-editor-v2.5.0 -m "ru-editor v2.5.0 — Phase 3 Modes + tools tightening"
git branch -d ru-editor-v2.5-modes
bash scripts/run_all_tests.sh 2>&1 | tail -5
```

Expected: fast-forward merge, tag created locally, branch deleted, master runner reports `ALL 3 PHASE(S) PASSED` on main.

- [ ] **Step 6: Verify final state**

Run:
```bash
git tag -l "ru-editor-v2.5.0"
git branch
git log --oneline -3
```

Expected: tag exists, only `main` branch, top commit is the v2.5.0 release commit.

- [ ] **Step 7: NO push**

Hard constraint per user instruction: do not `git push`, do not push tag, do not push main. All work stays local.

---

## Plan self-review

Spec coverage check:

- ✅ § 2.1 four modes — Tasks 8 (corpus labels), 9 (SKILL.md modes section)
- ✅ § 2.2 hybrid mode detection — Task 9
- ✅ § 2.3 per-mode profiles + `--mode` flag — Tasks 2, 3, 4, 5
- ✅ § 2.4 frontmatter `allowed-tools` — Task 9
- ✅ § 2.5 backlog #4 (mode-aware list tolerance) — Task 5
- ✅ § 2.6 backlog #5 (ignore-symmetry) — Task 6
- ✅ § 5.1 mode taxonomy table — Tasks 8, 9
- ✅ § 5.2 mode detection algorithm — Task 9
- ✅ § 5.3 mode-profiles.toml — Task 2
- ✅ § 5.4 ru_lint.py changes — Tasks 2, 3, 4, 5, 6
- ✅ § 5.5 SKILL.md changes — Tasks 9, 10
- ✅ § 6 data flow — Task 9 (examples in section)
- ✅ § 7 error handling — Tasks 3, 6 (cover exit 3, ignore-symmetry edge cases)
- ✅ § 8 acceptance metrics — Task 11
- ✅ § 9 testing strategy — Tasks 2, 3, 4, 5, 6, 11
- ✅ § 10 backwards compat — Tasks 4, 5 (auto mode preserved)
- ✅ § 11 release artifacts — Tasks 12, 14

No spec section is uncovered.

Placeholder scan: no TBD/TODO/FIXME in any task. All code blocks contain runnable code. All file paths are absolute or repo-relative.

Type / signature consistency:
- `_load_mode_profiles(path: str | None = None) -> dict[str, dict]` — same signature in Tasks 2 and 3.
- `ConfigError` — defined Task 2, used Task 3.
- `_check_length_ratio` — same `register` signature kept in Task 4.
- `_check_list_items_tolerance` — same `register` signature kept in Task 5.
- `Document` properties — refactored together in Task 6 (no signature changes, just internal source).
- `ctx["lint_mode"]` and `ctx["profile"]` — keys consistent across Tasks 3, 4, 5.
- JSON `summary.mode` — added Task 3, schema 1.1 — referenced consistently in Task 12 (CHANGELOG).

No issues found.

---

## Execution handoff

**Plan complete and saved to** `docs/superpowers/plans/2026-04-28-ru-editor-phase3-modes.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review between tasks, fast iteration. Best when tasks should be checked one-by-one and the user wants visibility into each step.
2. **Inline Execution** — tasks executed in the current session using `superpowers:executing-plans`, batched with checkpoints.

Recommendation for this plan: **Subagent-Driven** for Tasks 2–6 (TDD-heavy linter changes — easy to verify per-task) and **inline** for Tasks 7–14 (markdown content + acceptance script + final ops where context continuity matters).

Or pick one strategy and stick with it. The plan is structured to work with either.
