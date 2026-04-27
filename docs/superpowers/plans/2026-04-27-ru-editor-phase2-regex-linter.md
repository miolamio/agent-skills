# ru-editor Phase 2 (v2.4) — Regex Linter + Seed Corpus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Доставить детерминированный regex-линтер `scripts/ru_lint.py` (pure Python 3.11+, no deps) с registry-архитектурой, seed corpus из ≥20 пар и master-регрессионным раннером, который прогоняет тесты Phase 1 + Phase 2 после каждого изменения.

**Architecture:** Линтер строится вокруг трёх абстракций: (1) `Document` с named views (`prose`, `raw`, `code_blocks`, etc.) и поддержкой ignore-директив; (2) registry-словарь `@register("name", severity, mode)` для checks; (3) три CLI-режима (`check`/`diff`/`both`) с JSON (schema_version="1.0") и human output. Banned markers лежат в TOML (`references/banned-markers.toml`). Каждая check-функция — TDD: failing test → minimal impl → passing test → commit.

**Golden rule (от пользователя):** для всего пишем тесты, складываем в tests-папку, после каждой фазы прогоняем `scripts/run_all_tests.sh`, который покрывает Phase 1 + текущую + все промежуточные. Нулевая толерантность к регрессии.

**Tech Stack:** Python 3.11+ (tomllib встроен), stdlib `unittest`, stdlib `argparse`, stdlib `re`, stdlib `json`. Bash для master-runner. Никаких внешних зависимостей.

**Source spec:** `docs/superpowers/specs/2026-04-27-ru-editor-overhaul-design.md` § 5 Phase 2.

**Lessons from Phase 1 (locked in от старта):**
1. Любая grep-проверка по «плохим строкам» обязана исключать code spans, code blocks, blockquotes-цитирования банов и meta-commentary (footnotes). Решено через `Document.prose` + директивы `<!-- ru-lint:ignore-* -->`.
2. Контентные правила, которые сами цитируют запрещённые символы (typography.md), требуют явного escape-hatch — directive comments.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `scripts/run_all_tests.sh` | **Create** | Master regression runner. Растёт по мере добавления фаз. Вызывает Phase 1 + Phase 2 acceptance + future. |
| `skills/ru-editor/scripts/ru_lint.py` | **Create** | Главный модуль линтера. CLI + framework. ~600 строк max. |
| `skills/ru-editor/scripts/tests/__init__.py` | **Create** | Делает `tests/` пакетом для `unittest discover`. |
| `skills/ru-editor/scripts/tests/test_document.py` | **Create** | Tests for Document class + directives. |
| `skills/ru-editor/scripts/tests/test_registry.py` | **Create** | Tests for check registry + Finding. |
| `skills/ru-editor/scripts/tests/test_cli.py` | **Create** | Tests for CLI argparse + JSON output schema. |
| `skills/ru-editor/scripts/tests/test_checks_absolute.py` | **Create** | Tests for all absolute (HARD_FAIL) checks. |
| `skills/ru-editor/scripts/tests/test_checks_diff.py` | **Create** | Tests for all diff checks. |
| `skills/ru-editor/scripts/tests/test_checks_warn.py` | **Create** | Tests for all WARN checks. |
| `skills/ru-editor/scripts/tests/fixtures/` | **Create** | Маленькие документы для unit-тестов. |
| `skills/ru-editor/scripts/run_phase2_acceptance.sh` | **Create** | Phase 2 acceptance: unit tests + seed corpus eval + own-files lint + perf budget. |
| `skills/ru-editor/references/banned-markers.toml` | **Create** | Машиночитаемый источник истины для banned markers. Читают и линтер, и `## QA Gate` SKILL.md. |
| `evals/seed-corpus/README.md` | **Create** | Описание формата + acceptance критерии. |
| `evals/seed-corpus/NN-<slug>/source.md` | **Create** ×20 | AI-slop вход. |
| `evals/seed-corpus/NN-<slug>/expected.md` | **Create** ×20 | Чистый ожидаемый выход. |
| `evals/seed-corpus/NN-<slug>/brief.toml` | **Create** ×20 | Метаданные + ground-truth findings. |
| `skills/ru-editor/SKILL.md` | Modify | Обновить `## QA Gate`: ссылка на `ru_lint.py` как авторитетный шаг. Bump version → 2.4.0. |
| `skills/ru-editor/CHANGELOG.md` | Modify | Запись `[2.4.0]`. |
| `.development/tests/phase2-regex-linter/grounding/` | **Create** (gitignored) | 30 source/output/tags троек для эмпирической грунтовки паттернов. Делает ПОЛЬЗОВАТЕЛЬ. |
| `.development/tests/phase2-regex-linter/01-*` | **Create** (gitignored) | Phase 2 smoke tests, аналогично Phase 1. |
| `~/.claude/skills/ru-editor/` | Sync | Финальная синхронизация перед тегом. |

**Out of scope для Phase 2:** modes (Phase 3), `context: fork` (Phase 3), per-chunk dispatcher (Phase 4), eval runner с API (Phase 5), golden corpus (Phase 5), Codex subagent (Phase 5).

---

## Setup

- [ ] **Step 0.1: Verify clean working tree on main with v2.3.0 tag**

```bash
cd /Users/codegeek/src/agent-skills
git status
git log --oneline -1
git tag -l 'ru-editor-v2.3.0'
```

Expected:
- `git status`: clean
- `git log -1`: `9bdbe65 release(ru-editor): bump to v2.3.0 + CHANGELOG`
- tag `ru-editor-v2.3.0` exists

- [ ] **Step 0.2: Verify Python toolchain**

```bash
python3 --version
python3 -c "import tomllib; print('tomllib OK')"
python3 -c "import unittest; print('unittest OK')"
```

Expected: Python ≥ 3.11, tomllib OK, unittest OK.

- [ ] **Step 0.3: Create feature branch**

```bash
git checkout -b ru-editor-v2.4-regex-linter
```

- [ ] **Step 0.4: Create directory skeleton**

```bash
mkdir -p skills/ru-editor/scripts/tests/fixtures
mkdir -p evals/seed-corpus
mkdir -p scripts
```

(Repo-root `scripts/` is for the master test runner — separate from `skills/ru-editor/scripts/` which is skill-internal.)

---

## Task 1: Master regression runner

**Files:**
- Create: `scripts/run_all_tests.sh`

This runner is the single command we run after every step to verify nothing regresses. It starts thin (only Phase 1 acceptance), then grows as we add Phase 2 capabilities.

- [ ] **Step 1.1: Write the runner with Phase 1 hooked in**

Create `scripts/run_all_tests.sh`:

```bash
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
```

- [ ] **Step 1.2: Make executable, run it (Phase 1 only)**

```bash
chmod +x scripts/run_all_tests.sh
bash scripts/run_all_tests.sh
```

Expected: `Phase 1: Content hygiene` runs `check_phase1.sh` → all 11 sections / 32 assertions PASS → final `ALL 1 PHASE(S) PASSED`. Exit code 0.

- [ ] **Step 1.3: Commit**

```bash
git add scripts/run_all_tests.sh
git commit -m "chore: add master regression runner (Phase 1 only initially)"
```

---

## Task 2: Linter scaffolding — empty module + first failing test

**Files:**
- Create: `skills/ru-editor/scripts/ru_lint.py`
- Create: `skills/ru-editor/scripts/tests/__init__.py`
- Create: `skills/ru-editor/scripts/tests/test_smoke.py`

- [ ] **Step 2.1: Create `tests/__init__.py` (empty marker)**

Create `skills/ru-editor/scripts/tests/__init__.py` with content:

```python
# Test package for ru_lint.
```

- [ ] **Step 2.2: Create empty `ru_lint.py`**

Create `skills/ru-editor/scripts/ru_lint.py` with content:

```python
"""ru_lint — deterministic regex linter for Russian text edited by the ru-editor skill.

Phase 2 (v2.4.0) of the ru-editor overhaul. Pure Python 3.11+, no third-party deps.

Public surface (built incrementally — each task adds one piece):
  - Document        : named views over a markdown source string
  - Finding         : single lint result
  - register / REGISTRY : check-function registry decorator + dict
  - main()          : CLI entry point

CLI:
  python ru_lint.py check <edited.md>
  python ru_lint.py diff  <orig.md> <edited.md>
  python ru_lint.py both  <orig.md> <edited.md>     (default semantics)

Add --format=json for machine output (schema_version "1.0"). Default is human.
Exit code: 0 if no HARD_FAIL findings; 1 otherwise. Use --strict to also fail on WARN.
"""

__version__ = "0.1.0"
SCHEMA_VERSION = "1.0"
```

- [ ] **Step 2.3: Write first failing test (smoke — module imports + version)**

Create `skills/ru-editor/scripts/tests/test_smoke.py`:

```python
"""Smoke test: module imports and exposes basic constants."""
import unittest
import sys
from pathlib import Path

# Make ru_lint importable when running tests from any cwd.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))


class TestSmoke(unittest.TestCase):
    def test_imports(self):
        import ru_lint
        self.assertEqual(ru_lint.SCHEMA_VERSION, "1.0")
        self.assertTrue(hasattr(ru_lint, "__version__"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2.4: Run tests — should pass**

```bash
cd /Users/codegeek/src/agent-skills
python3 -m unittest discover skills/ru-editor/scripts/tests/ -v
```

Expected:
```
test_imports (test_smoke.TestSmoke.test_imports) ... ok
----------------------------------------------------------------------
Ran 1 test in 0.00Xs
OK
```

- [ ] **Step 2.5: Commit**

```bash
git add skills/ru-editor/scripts/ru_lint.py \
        skills/ru-editor/scripts/tests/__init__.py \
        skills/ru-editor/scripts/tests/test_smoke.py
git commit -m "feat(ru-editor): scaffold ru_lint.py + unittest harness"
```

---

## Task 3: TOML banned markers data file

**Files:**
- Create: `skills/ru-editor/references/banned-markers.toml`
- Create: `skills/ru-editor/scripts/tests/test_banned_markers.py`

- [ ] **Step 3.1: Write failing test for TOML structure**

Create `skills/ru-editor/scripts/tests/test_banned_markers.py`:

```python
"""Validate banned-markers.toml structure and content invariants."""
import unittest
import tomllib
from pathlib import Path

REFS = Path(__file__).resolve().parents[2] / "references"
TOML_PATH = REFS / "banned-markers.toml"


class TestBannedMarkersToml(unittest.TestCase):
    def setUp(self):
        with open(TOML_PATH, "rb") as f:
            self.data = tomllib.load(f)

    def test_meta_schema_version(self):
        self.assertEqual(self.data["meta"]["schema_version"], "1.0")

    def test_hard_fail_phrases_locked(self):
        """The five Phase-1-locked HARD_FAIL markers must be present."""
        phrases = set(self.data["hard_fail_markers"]["phrases"])
        for required in [
            "погружаемся",
            "погрузимся",
            "ландшафт",
            "гобелен",
            "является свидетельством",
            "стоит отметить",
        ]:
            self.assertIn(required, phrases, f"missing locked HARD_FAIL marker: {required}")

    def test_no_duplicate_phrases_within_section(self):
        for section in ("hard_fail_markers", "warn_markers"):
            phrases = self.data.get(section, {}).get("phrases", [])
            self.assertEqual(len(phrases), len(set(phrases)),
                             f"duplicate phrases in {section}")

    def test_synonym_clusters_have_minimum_size(self):
        for name, words in self.data.get("synonym_clusters", {}).items():
            self.assertGreaterEqual(len(words), 2,
                                    f"synonym cluster {name} must have ≥2 members")

    def test_no_marker_collisions_across_sections(self):
        hard = set(self.data.get("hard_fail_markers", {}).get("phrases", []))
        warn = set(self.data.get("warn_markers", {}).get("phrases", []))
        self.assertEqual(hard & warn, set(),
                         "phrases must not appear in both hard_fail and warn")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3.2: Run test — expect FAIL (file missing)**

```bash
python3 -m unittest skills.ru-editor.scripts.tests.test_banned_markers -v
```

Wait — directory has hyphens which break Python import. Use discover instead:

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_banned_markers.py -v
```

Expected: error `FileNotFoundError: ... banned-markers.toml`.

- [ ] **Step 3.3: Create the TOML file**

Create `skills/ru-editor/references/banned-markers.toml`:

```toml
# ru-editor banned markers — machine-readable source of truth.
#
# Read by:
#   - skills/ru-editor/scripts/ru_lint.py (HARD_FAIL / WARN checks)
#   - skills/ru-editor/SKILL.md (## QA Gate cites these — keep in sync manually until v3.0)
#
# Structure:
#   [meta]                   schema_version
#   [hard_fail_markers]      phrases that must NEVER survive in final output
#   [warn_markers]           phrases that warrant a warning but do not block
#   [synonym_clusters]       groups of close synonyms — alert if 3+ from same cluster appear in proximity
#
# When adding a marker:
#   1. Add phrase to appropriate section.
#   2. Run: bash scripts/run_all_tests.sh
#   3. If false-positives surface in seed corpus, narrow the phrase or move to warn_markers.

[meta]
schema_version = "1.0"

[hard_fail_markers]
# Phase 1 locked these in. Lowercase, exact-match (case-insensitive comparison happens in linter).
phrases = [
  "погружаемся",
  "погрузимся",
  "ландшафт",
  "гобелен",
  "является свидетельством",
  "стоит отметить",
]

[warn_markers]
# To be filled empirically during grounding (Task 7). Stays empty until then.
phrases = []

[synonym_clusters]
# Detected during AI-output drift: model cycles synonyms within one document.
# 3+ members from same cluster within 500 chars → WARN.
product_drift = ["продукт", "решение", "инструмент", "платформа"]
user_drift    = ["пользователь", "клиент", "человек", "специалист"]
```

- [ ] **Step 3.4: Re-run test — expect PASS**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_banned_markers.py -v
```

Expected: 5 tests pass.

- [ ] **Step 3.5: Run full test suite (should still pass)**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -v
```

Expected: 6 tests, all OK.

- [ ] **Step 3.6: Commit**

```bash
git add skills/ru-editor/references/banned-markers.toml \
        skills/ru-editor/scripts/tests/test_banned_markers.py
git commit -m "feat(ru-editor): add banned-markers.toml as machine-readable source of truth"
```

---

## Task 4: Document class with named views + ignore directives

**Files:**
- Modify: `skills/ru-editor/scripts/ru_lint.py`
- Create: `skills/ru-editor/scripts/tests/test_document.py`
- Create: `skills/ru-editor/scripts/tests/fixtures/doc_with_code.md`
- Create: `skills/ru-editor/scripts/tests/fixtures/doc_with_directives.md`

`Document` is the central abstraction. Each check operates on one *named view*:
- `raw` — the entire input string, unmodified
- `prose` — fenced code blocks AND inline code spans removed; ignored regions removed
- `code_blocks` — list of fenced code block bodies (preserved verbatim)
- `code_spans` — list of inline `code` span contents
- `urls` — list of URLs (http/https)
- `headings` — list of `(level, text)` tuples
- `list_items` — list of bullet/numbered list item bodies
- `numeric_tokens` — set of numeric strings (digits + optional decimal)

Ignore directives (HTML comments) suppress all checks within their scope:
- `<!-- ru-lint:ignore-line -->` — applies to the next non-empty line
- `<!-- ru-lint:ignore-start -->` ... `<!-- ru-lint:ignore-end -->` — applies to lines in between

- [ ] **Step 4.1: Create fixture files**

Create `skills/ru-editor/scripts/tests/fixtures/doc_with_code.md`:

```markdown
# Заголовок

Это абзац с инлайн-кодом `const x = 1;` и стрелкой → внутри текста.

```python
def hello():
    return "→ this arrow is in code, ignore"
```

Ссылка: https://example.com/path?q=1.

- Первый пункт списка.
- Второй пункт.
```

Create `skills/ru-editor/scripts/tests/fixtures/doc_with_directives.md`:

```markdown
# Документ с директивами

Этот текст проверяется обычно.

<!-- ru-lint:ignore-line -->
Эта строка содержит → и не должна вызывать findings.

<!-- ru-lint:ignore-start -->
Здесь живёт несколько строк со стрелками → и `--`,
которые показываются как примеры запрещённого.
<!-- ru-lint:ignore-end -->

Эта строка снова проверяется.
```

- [ ] **Step 4.2: Write failing tests for Document**

Create `skills/ru-editor/scripts/tests/test_document.py`:

```python
"""Tests for the Document class — named views over markdown."""
import unittest
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from ru_lint import Document  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestDocumentBasic(unittest.TestCase):
    def setUp(self):
        self.doc = Document(text=(FIXTURES / "doc_with_code.md").read_text(encoding="utf-8"))

    def test_raw_unchanged(self):
        self.assertIn("→", self.doc.raw)
        self.assertIn("```python", self.doc.raw)

    def test_prose_strips_code_blocks(self):
        self.assertNotIn("def hello", self.doc.prose)
        self.assertNotIn("```", self.doc.prose)

    def test_prose_strips_inline_code_spans(self):
        self.assertNotIn("const x = 1", self.doc.prose)
        self.assertNotIn("`", self.doc.prose)

    def test_prose_keeps_arrow_in_real_text(self):
        # The arrow inside actual prose ("стрелкой → внутри текста") must remain in prose.
        self.assertIn("→", self.doc.prose)

    def test_prose_does_not_keep_arrow_from_code(self):
        # Arrow from inside ```python``` block must NOT appear in prose.
        # (Verified by counting: input has 2 arrows, prose should have 1.)
        self.assertEqual(self.doc.raw.count("→"), 2)
        self.assertEqual(self.doc.prose.count("→"), 1)

    def test_code_blocks_extracted(self):
        self.assertEqual(len(self.doc.code_blocks), 1)
        self.assertIn("def hello", self.doc.code_blocks[0])

    def test_code_spans_extracted(self):
        self.assertIn("const x = 1;", self.doc.code_spans)

    def test_urls_extracted(self):
        self.assertEqual(self.doc.urls, ["https://example.com/path?q=1"])

    def test_headings_extracted(self):
        self.assertEqual(self.doc.headings, [(1, "Заголовок")])

    def test_list_items_extracted(self):
        self.assertEqual(self.doc.list_items, ["Первый пункт списка.", "Второй пункт."])


class TestDocumentNumeric(unittest.TestCase):
    def test_numeric_tokens_basic(self):
        doc = Document(text="В 2024 году выросло на 47% за 3.5 года.")
        self.assertEqual(doc.numeric_tokens, {"2024", "47", "3.5"})

    def test_numeric_tokens_skip_code(self):
        # Numbers inside code spans don't count as content numeric tokens.
        doc = Document(text="Параметр `--port=8080` это про настройку.")
        self.assertEqual(doc.numeric_tokens, set())


class TestDocumentDirectives(unittest.TestCase):
    def setUp(self):
        self.doc = Document(text=(FIXTURES / "doc_with_directives.md").read_text(encoding="utf-8"))

    def test_prose_excludes_ignore_line(self):
        self.assertNotIn("Эта строка содержит →", self.doc.prose)

    def test_prose_excludes_ignore_block(self):
        self.assertNotIn("Здесь живёт несколько строк", self.doc.prose)
        self.assertNotIn("которые показываются", self.doc.prose)

    def test_prose_keeps_normal_lines(self):
        self.assertIn("Этот текст проверяется обычно.", self.doc.prose)
        self.assertIn("Эта строка снова проверяется.", self.doc.prose)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4.3: Run tests — expect FAIL (Document not defined)**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_document.py -v
```

Expected: ImportError `cannot import name 'Document'`.

- [ ] **Step 4.4: Implement Document in `ru_lint.py`**

Append to `skills/ru-editor/scripts/ru_lint.py`:

```python
import re
from dataclasses import dataclass, field
from functools import cached_property


_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
_CODE_SPAN_RE = re.compile(r"`[^`\n]+`")
_URL_RE = re.compile(r"https?://[^\s)\]]+")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.+?)\s*$", re.MULTILINE)
_NUMERIC_RE = re.compile(r"\d+(?:[.,]\d+)?")
_DIRECTIVE_LINE = re.compile(r"<!--\s*ru-lint:ignore-line\s*-->")
_DIRECTIVE_START = re.compile(r"<!--\s*ru-lint:ignore-start\s*-->")
_DIRECTIVE_END = re.compile(r"<!--\s*ru-lint:ignore-end\s*-->")


@dataclass(frozen=True)
class Document:
    text: str
    path: str | None = None

    @cached_property
    def raw(self) -> str:
        return self.text

    @cached_property
    def _without_ignored_regions(self) -> str:
        """Strip lines covered by ignore-line / ignore-start..ignore-end directives."""
        lines = self.text.splitlines(keepends=True)
        out: list[str] = []
        in_block = False
        skip_next_nonempty = False
        for line in lines:
            if _DIRECTIVE_START.search(line):
                in_block = True
                continue
            if _DIRECTIVE_END.search(line):
                in_block = False
                continue
            if _DIRECTIVE_LINE.search(line):
                skip_next_nonempty = True
                continue
            if in_block:
                continue
            if skip_next_nonempty and line.strip():
                skip_next_nonempty = False
                continue
            out.append(line)
        return "".join(out)

    @cached_property
    def prose(self) -> str:
        """Text with code blocks, inline code spans, and ignored regions removed."""
        t = self._without_ignored_regions
        t = _CODE_BLOCK_RE.sub("", t)
        t = _CODE_SPAN_RE.sub("", t)
        return t

    @cached_property
    def code_blocks(self) -> list[str]:
        return [m.group(0) for m in _CODE_BLOCK_RE.finditer(self.text)]

    @cached_property
    def code_spans(self) -> list[str]:
        # Strip surrounding backticks.
        return [m.group(0)[1:-1] for m in _CODE_SPAN_RE.finditer(self.text)]

    @cached_property
    def urls(self) -> list[str]:
        # URLs in raw text (including inside code) — for diff comparison they're the same set.
        return [m.group(0) for m in _URL_RE.finditer(self.text)]

    @cached_property
    def headings(self) -> list[tuple[int, str]]:
        return [(len(m.group(1)), m.group(2)) for m in _HEADING_RE.finditer(self.text)]

    @cached_property
    def list_items(self) -> list[str]:
        return [m.group(1) for m in _LIST_ITEM_RE.finditer(self.text)]

    @cached_property
    def numeric_tokens(self) -> set[str]:
        # Numbers from prose only (not code).
        return set(_NUMERIC_RE.findall(self.prose))
```

- [ ] **Step 4.5: Re-run document tests — expect PASS**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_document.py -v
```

Expected: all tests pass.

- [ ] **Step 4.6: Run full suite**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -v
```

Expected: smoke + banned_markers + document tests all OK.

- [ ] **Step 4.7: Run master regression**

```bash
bash scripts/run_all_tests.sh
```

Expected: Phase 1 still PASS (Python tests are not yet hooked into Phase 2 runner — that comes in Task 12).

- [ ] **Step 4.8: Commit**

```bash
git add skills/ru-editor/scripts/ru_lint.py \
        skills/ru-editor/scripts/tests/test_document.py \
        skills/ru-editor/scripts/tests/fixtures/
git commit -m "feat(ru-editor): Document class with named views + ignore directives"
```

---

## Task 5: Finding dataclass + check registry

**Files:**
- Modify: `skills/ru-editor/scripts/ru_lint.py`
- Create: `skills/ru-editor/scripts/tests/test_registry.py`

- [ ] **Step 5.1: Write failing tests for registry**

Create `skills/ru-editor/scripts/tests/test_registry.py`:

```python
"""Tests for the check registry and Finding dataclass."""
import unittest
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import ru_lint  # noqa: E402
from ru_lint import Document, Finding, register, REGISTRY  # noqa: E402


class TestFinding(unittest.TestCase):
    def test_finding_construction(self):
        f = Finding(
            check="x",
            severity="HARD_FAIL",
            line=12,
            col=3,
            match="→",
            context="foo → bar",
            message="arrow not allowed",
        )
        self.assertEqual(f.check, "x")
        self.assertEqual(f.severity, "HARD_FAIL")
        self.assertEqual(f.line, 12)

    def test_finding_to_dict(self):
        f = Finding(check="x", severity="WARN", line=1, col=0,
                    match="!", context="!", message="m")
        d = f.to_dict()
        self.assertEqual(d["check"], "x")
        self.assertEqual(d["severity"], "WARN")
        self.assertEqual(d["line"], 1)


class TestRegistry(unittest.TestCase):
    def setUp(self):
        # Snapshot the registry; restore after each test.
        self._snapshot = dict(REGISTRY)

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._snapshot)

    def test_register_decorator_adds_to_registry(self):
        REGISTRY.clear()

        @register(name="sample", severity="HARD_FAIL", mode="absolute",
                  description="sample check")
        def sample_check(doc: Document, source: Document | None, ctx: dict):
            return []

        self.assertIn("sample", REGISTRY)
        self.assertEqual(REGISTRY["sample"].severity, "HARD_FAIL")
        self.assertEqual(REGISTRY["sample"].mode, "absolute")

    def test_register_invalid_severity_rejected(self):
        REGISTRY.clear()
        with self.assertRaises(ValueError):
            @register(name="bad", severity="CRITICAL", mode="absolute", description="x")
            def bad(doc, source, ctx):
                return []

    def test_register_invalid_mode_rejected(self):
        REGISTRY.clear()
        with self.assertRaises(ValueError):
            @register(name="bad", severity="WARN", mode="weird", description="x")
            def bad(doc, source, ctx):
                return []

    def test_register_duplicate_name_rejected(self):
        REGISTRY.clear()

        @register(name="dup", severity="WARN", mode="absolute", description="x")
        def first(doc, source, ctx):
            return []

        with self.assertRaises(ValueError):
            @register(name="dup", severity="WARN", mode="absolute", description="x")
            def second(doc, source, ctx):
                return []


class TestRunChecks(unittest.TestCase):
    def setUp(self):
        self._snapshot = dict(REGISTRY)
        REGISTRY.clear()

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._snapshot)

    def test_run_checks_invokes_absolute_in_check_mode(self):
        @register(name="abs1", severity="HARD_FAIL", mode="absolute", description="x")
        def abs1(doc, source, ctx):
            return [Finding(check="abs1", severity="HARD_FAIL",
                            line=1, col=0, match="!", context="!", message="abs1 fired")]

        doc = Document(text="hello")
        findings = ru_lint.run_checks(doc, source=None, mode="check")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].check, "abs1")

    def test_run_checks_skips_diff_in_check_mode(self):
        @register(name="diff1", severity="HARD_FAIL", mode="diff", description="x")
        def diff1(doc, source, ctx):
            return [Finding(check="diff1", severity="HARD_FAIL",
                            line=1, col=0, match="!", context="!", message="diff1 fired")]

        doc = Document(text="hello")
        findings = ru_lint.run_checks(doc, source=None, mode="check")
        self.assertEqual(findings, [])

    def test_run_checks_diff_mode_requires_source(self):
        with self.assertRaises(ValueError):
            ru_lint.run_checks(Document(text="x"), source=None, mode="diff")

    def test_run_checks_both_mode_runs_all(self):
        @register(name="abs1", severity="HARD_FAIL", mode="absolute", description="x")
        def abs1(doc, source, ctx):
            return [Finding(check="abs1", severity="HARD_FAIL",
                            line=1, col=0, match="!", context="!", message="m")]

        @register(name="diff1", severity="HARD_FAIL", mode="diff", description="x")
        def diff1(doc, source, ctx):
            return [Finding(check="diff1", severity="HARD_FAIL",
                            line=1, col=0, match="!", context="!", message="m")]

        doc = Document(text="a")
        src = Document(text="b")
        findings = ru_lint.run_checks(doc, source=src, mode="both")
        names = sorted(f.check for f in findings)
        self.assertEqual(names, ["abs1", "diff1"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5.2: Run tests — expect FAIL (Finding/register/run_checks not defined)**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_registry.py -v
```

Expected: ImportError.

- [ ] **Step 5.3: Implement Finding + Check + register + run_checks**

Append to `skills/ru-editor/scripts/ru_lint.py`:

```python
from typing import Callable, Literal


Severity = Literal["HARD_FAIL", "WARN"]
Mode = Literal["absolute", "diff"]
RunMode = Literal["check", "diff", "both"]

_VALID_SEVERITIES = ("HARD_FAIL", "WARN")
_VALID_MODES = ("absolute", "diff")


@dataclass(frozen=True)
class Finding:
    check: str
    severity: Severity
    line: int
    col: int
    match: str
    context: str
    message: str

    def to_dict(self) -> dict:
        return {
            "check": self.check,
            "severity": self.severity,
            "line": self.line,
            "col": self.col,
            "match": self.match,
            "context": self.context,
            "message": self.message,
        }


CheckFn = Callable[[Document, "Document | None", dict], list[Finding]]


@dataclass(frozen=True)
class Check:
    name: str
    severity: Severity
    mode: Mode
    description: str
    fn: CheckFn


REGISTRY: dict[str, Check] = {}


def register(*, name: str, severity: str, mode: str, description: str):
    """Decorator: register a check function under `name`.

    Raises ValueError on invalid severity, mode, or duplicate name.
    """
    if severity not in _VALID_SEVERITIES:
        raise ValueError(f"invalid severity: {severity!r}; expected one of {_VALID_SEVERITIES}")
    if mode not in _VALID_MODES:
        raise ValueError(f"invalid mode: {mode!r}; expected one of {_VALID_MODES}")
    if name in REGISTRY:
        raise ValueError(f"duplicate check name: {name!r}")

    def deco(fn: CheckFn) -> CheckFn:
        REGISTRY[name] = Check(name=name, severity=severity, mode=mode,
                               description=description, fn=fn)
        return fn

    return deco


def run_checks(
    doc: Document,
    source: Document | None,
    mode: RunMode,
    ctx: dict | None = None,
) -> list[Finding]:
    """Run checks selected by mode. Returns flat list of findings."""
    if mode == "diff" and source is None:
        raise ValueError("diff mode requires source document")
    if mode == "both" and source is None:
        raise ValueError("both mode requires source document")

    ctx = ctx or {}
    findings: list[Finding] = []
    for check in REGISTRY.values():
        run_this = (
            (mode == "check" and check.mode == "absolute")
            or (mode == "diff" and check.mode == "diff")
            or (mode == "both")
        )
        if not run_this:
            continue
        try:
            result = check.fn(doc, source, ctx)
        except Exception as exc:  # noqa: BLE001
            findings.append(Finding(
                check=check.name,
                severity="HARD_FAIL",
                line=0, col=0, match="",
                context="",
                message=f"check raised {type(exc).__name__}: {exc}",
            ))
            continue
        findings.extend(result)
    return findings
```

- [ ] **Step 5.4: Re-run registry tests — expect PASS**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_registry.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 5.5: Run full suite**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -v
```

Expected: all tests pass (smoke + banned_markers + document + registry).

- [ ] **Step 5.6: Commit**

```bash
git add skills/ru-editor/scripts/ru_lint.py \
        skills/ru-editor/scripts/tests/test_registry.py
git commit -m "feat(ru-editor): Finding + check registry + run_checks"
```

---

## Task 6: CLI argparse + JSON schema v1

**Files:**
- Modify: `skills/ru-editor/scripts/ru_lint.py`
- Create: `skills/ru-editor/scripts/tests/test_cli.py`

- [ ] **Step 6.1: Write failing tests for CLI**

Create `skills/ru-editor/scripts/tests/test_cli.py`:

```python
"""Tests for the CLI: argparse + JSON output schema + exit codes."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
RU_LINT = SCRIPTS_DIR / "ru_lint.py"


def run_cli(*args, input_text: str | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(RU_LINT), *args]
    return subprocess.run(cmd, capture_output=True, text=True, input=input_text, timeout=10)


class TestCliBasic(unittest.TestCase):
    def test_help_runs(self):
        result = run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("ru_lint", result.stdout.lower() + result.stderr.lower())

    def test_version_runs(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("0.", result.stdout)

    def test_check_subcommand_help(self):
        result = run_cli("check", "--help")
        self.assertEqual(result.returncode, 0)


class TestCliCheckMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name: str, content: str) -> Path:
        p = self.tmpdir / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_check_clean_text_exits_zero(self):
        f = self._write("clean.md", "# Заголовок\n\nЧистый текст без проблем.\n")
        result = run_cli("check", str(f))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_check_json_output_has_schema_version(self):
        f = self._write("clean.md", "# H\n\nText.\n")
        result = run_cli("check", str(f), "--format", "json")
        data = json.loads(result.stdout)
        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(data["tool"], "ru_lint")
        self.assertIn("tool_version", data)
        self.assertEqual(data["mode"], "check")
        self.assertEqual(data["input_path"], str(f))
        self.assertIsNone(data["source_path"])
        self.assertIn("summary", data)
        self.assertIn("findings", data)
        self.assertEqual(data["summary"]["hard_fail_count"], 0)
        self.assertEqual(data["summary"]["warn_count"], 0)
        self.assertIn("elapsed_ms", data["summary"])


class TestCliErrors(unittest.TestCase):
    def test_diff_without_source_errors(self):
        result = run_cli("diff", "/nonexistent.md")
        self.assertNotEqual(result.returncode, 0)

    def test_check_missing_file_errors(self):
        result = run_cli("check", "/nonexistent.md")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6.2: Run tests — expect FAIL (CLI not implemented)**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_cli.py -v
```

Expected: failures (script has no CLI yet).

- [ ] **Step 6.3: Implement CLI in `ru_lint.py`**

Append to `skills/ru-editor/scripts/ru_lint.py`:

```python
import argparse
import json
import sys
import time
from pathlib import Path


def _load_doc(path_str: str) -> Document:
    p = Path(path_str)
    if not p.is_file():
        raise FileNotFoundError(f"file not found: {path_str}")
    return Document(text=p.read_text(encoding="utf-8"), path=str(p))


def _format_human(findings: list[Finding], mode: str, hard: int, warn: int, elapsed_ms: int) -> str:
    lines: list[str] = []
    if not findings:
        lines.append(f"── ru_lint {mode}: no findings ({elapsed_ms} ms) ──")
        return "\n".join(lines) + "\n"

    by_sev: dict[str, list[Finding]] = {"HARD_FAIL": [], "WARN": []}
    for f in findings:
        by_sev.setdefault(f.severity, []).append(f)

    for sev in ("HARD_FAIL", "WARN"):
        if by_sev[sev]:
            lines.append(f"── {sev} ({len(by_sev[sev])}) ──")
            for f in by_sev[sev]:
                where = f"L{f.line}:C{f.col}" if f.line else ""
                lines.append(f"  [{f.check}] {where} {f.message}")
                if f.match:
                    lines.append(f"      match: {f.match!r}  context: {f.context!r}")

    lines.append(f"── summary: {hard} hard_fail, {warn} warn  ({elapsed_ms} ms) ──")
    return "\n".join(lines) + "\n"


def _format_json(findings: list[Finding], mode: str, input_path: str,
                 source_path: str | None, hard: int, warn: int, elapsed_ms: int) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "tool": "ru_lint",
        "tool_version": __version__,
        "mode": mode,
        "input_path": input_path,
        "source_path": source_path,
        "summary": {
            "hard_fail_count": hard,
            "warn_count": warn,
            "elapsed_ms": elapsed_ms,
        },
        "findings": [f.to_dict() for f in findings],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ru_lint",
        description="ru_lint — deterministic regex linter for Russian text edited by ru-editor.",
    )
    parser.add_argument("--version", action="version",
                        version=f"ru_lint {__version__} (schema {SCHEMA_VERSION})")
    parser.add_argument("--format", choices=("human", "json"), default="human",
                        help="output format (default: human)")
    parser.add_argument("--strict", action="store_true",
                        help="exit non-zero on WARN findings as well (default: only HARD_FAIL)")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="absolute checks on edited file")
    p_check.add_argument("edited", help="path to edited.md")

    p_diff = sub.add_parser("diff", help="diff checks (orig vs edited)")
    p_diff.add_argument("source", help="path to original")
    p_diff.add_argument("edited", help="path to edited")

    p_both = sub.add_parser("both", help="absolute + diff checks (default semantics)")
    p_both.add_argument("source", help="path to original")
    p_both.add_argument("edited", help="path to edited")

    args = parser.parse_args(argv)

    try:
        if args.cmd == "check":
            edited = _load_doc(args.edited)
            source = None
            run_mode = "check"
            input_path = args.edited
            source_path = None
        elif args.cmd == "diff":
            source = _load_doc(args.source)
            edited = _load_doc(args.edited)
            run_mode = "diff"
            input_path = args.edited
            source_path = args.source
        elif args.cmd == "both":
            source = _load_doc(args.source)
            edited = _load_doc(args.edited)
            run_mode = "both"
            input_path = args.edited
            source_path = args.source
        else:
            parser.error(f"unknown command: {args.cmd}")
            return 2  # unreachable
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    t0 = time.monotonic()
    findings = run_checks(edited, source=source, mode=run_mode)
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    hard = sum(1 for f in findings if f.severity == "HARD_FAIL")
    warn = sum(1 for f in findings if f.severity == "WARN")

    if args.format == "json":
        out = _format_json(findings, run_mode, input_path, source_path, hard, warn, elapsed_ms)
    else:
        out = _format_human(findings, run_mode, hard, warn, elapsed_ms)
    sys.stdout.write(out)

    if hard > 0:
        return 1
    if args.strict and warn > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6.4: Re-run CLI tests — expect PASS**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_cli.py -v
```

Expected: all tests pass.

- [ ] **Step 6.5: Manual sanity check**

```bash
python3 skills/ru-editor/scripts/ru_lint.py --version
python3 skills/ru-editor/scripts/ru_lint.py check skills/ru-editor/SKILL.md --format json | head -30
```

Expected: version printed; JSON with `schema_version: "1.0"`, `mode: "check"`, empty findings (no checks registered yet).

- [ ] **Step 6.6: Run full suite**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6.7: Commit**

```bash
git add skills/ru-editor/scripts/ru_lint.py \
        skills/ru-editor/scripts/tests/test_cli.py
git commit -m "feat(ru-editor): CLI with check/diff/both subcommands and JSON schema v1"
```

---

## Task 7: Empirical grounding (USER step) — 30 source/output/tags triples

**Files:**
- Create (gitignored): `.development/tests/phase2-regex-linter/grounding/NN-<slug>/{source.md, output.md, tags.md}`
- Create (gitignored): `.development/tests/phase2-regex-linter/grounding/README.md`

This is the slowest part of Phase 2 — done by the user. The plan blocks here for the empirical signal that informs which WARN patterns to add and which markers to extend. WARN checks (Task 10) require this data; they cannot be authored by intuition.

**Stratification target (15 of 30 minimum, rest is opportunistic):**

| Genre | Light slop | Medium slop | Heavy slop |
|---|---|---|---|
| technical | 1 | 1 | 1 |
| marketing | 1 | 1 | 1 |
| educational | 1 | 1 | 1 |
| blog | 1 | 1 | 1 |
| internal/email | 1 | 1 | 1 |

- [ ] **Step 7.1: Create grounding workflow README**

Create `.development/tests/phase2-regex-linter/grounding/README.md`:

```markdown
# Phase 2 Empirical Grounding

Назначение: накопить 30+ троек (source, output, tags) для эмпирической грунтовки regex-паттернов линтера. Без этой грунтовки WARN-проверки писать запрещено (требование спеки §5 Phase 2 + золотое правило).

Локация **gitignored** (как и весь `.development/tests/`). Это локальные dev-артефакты пользователя.

## Workflow на одну тройку

1. Возьми реальный AI-сгенерированный или AI-причёсанный русский текст. Источники: ChatGPT-вывод, маркетинговые блоги, корпоративные новости, переводной AI-ассистированный контент. Длина 500–3000 символов.
2. Сохрани в `NN-<slug>/source.md`, где NN — двузначный номер, slug — короткий идентификатор (`12-marketing-saas-pitch`).
3. В свежей CC-сессии вызови скилл `ru-editor` v2.3 на этом тексте.
4. Сохрани результат в `NN-<slug>/output.md`.
5. Прочитай `output.md` ВНИМАТЕЛЬНО как читатель, не как автор. Запиши в `NN-<slug>/tags.md` все маркеры, которые скилл пропустил или испортил.

## Формат `tags.md`

```markdown
# Tags for case NN-slug

**Genre:** marketing|technical|educational|blog|internal
**Slop intensity (input):** light|medium|heavy
**Output verdict:** clean|some-issues|broken

## Missed markers (что должен был поймать линтер, но v2.3 скилл не убрал)

- L12: «погружаемся в мир» — banned marker survived
- L18: 4 предложения подряд начинаются с «Мы» — repeated-opening pattern
- L23: «X, а не Y» три раза в одном абзаце — pile-up
- L31: em dash 3 раза в одном предложении — em-dash density

## Invented specifics (Factual Integrity violations)

- L8: «47% клиентов» — числа не было в источнике
- L15: «McKinsey» — выдуманный источник

## False corrections (правильное удалено или испорчено)

- L21: исходник содержал реальное число «12» в legitimate контексте, скилл удалил → потеря факта

## Other observations

(свободный текст)
```

## Stratification target

Минимум 15 троек по матрице 5 жанров × 3 интенсивности (см. план Task 7). Остальные 15+ — usual suspects: повторяющиеся паттерны, найденные за время грунтовки.

## Acceptance gate

Грунтовка считается завершённой, когда:
- ≥30 троек в каталоге
- Каждая имеет source.md, output.md, tags.md
- В сумме tags.md упоминают ≥10 различных pattern types (не одно и то же 30 раз)

## Что делать с результатами

После завершения грунтовки:
1. Открой все `tags.md` рядом, выпиши частоту каждого pattern type.
2. Top-5 most-missed → добавляются как новые HARD_FAIL или WARN в `banned-markers.toml` (Task 9 в плане).
3. Top-5 ложных корректировок → закладываются в acceptance критерии: линтер не должен флагать эти случаи.
```

- [ ] **Step 7.2: User collects grounding data (manual, time-boxed ≤4 часа)**

Шаги, которые делает пользователь (не агент):

1. Прочитать `grounding/README.md`.
2. Собрать 15 source-текстов по матрице 5×3.
3. Прогнать `ru-editor` на каждом, сохранить output.md.
4. Аннотировать tags.md.
5. Дополнить ≥15 ad-hoc случаями.

Минимум, чтобы разблокировать Task 8: 15 троек по стратификации. Остальные 15+ можно довести параллельно с Task 8–9.

- [ ] **Step 7.3: Verify count and structure**

```bash
ls .development/tests/phase2-regex-linter/grounding/ | grep -E '^[0-9]{2}-' | wc -l
```

Expected: ≥15 для разблокировки Task 8; ≥30 для финального acceptance.

```bash
for d in .development/tests/phase2-regex-linter/grounding/[0-9]*; do
  for f in source.md output.md tags.md; do
    [[ -f "$d/$f" ]] || echo "MISSING: $d/$f"
  done
done
```

Expected: пусто (все файлы на месте).

- [ ] **Step 7.4: Commit grounding README (data is gitignored)**

```bash
git add .development/tests/phase2-regex-linter/grounding/README.md 2>/dev/null || true
# .development/ is gitignored — README probably won't be added either.
# This task does NOT produce committed artefacts; it produces local data.
echo "Grounding data is gitignored; nothing to commit for this task."
```

(No commit step; the data is local-only.)

---

## Task 8: Absolute (HARD_FAIL) checks — Phase-1-locked patterns

**Files:**
- Modify: `skills/ru-editor/scripts/ru_lint.py`
- Create: `skills/ru-editor/scripts/tests/test_checks_absolute.py`

These checks are NOT empirical — they enforce Phase 1 rules already locked into SKILL.md. So they can be authored before grounding completes.

Six absolute checks:

| Check name | Severity | View | What it flags |
|---|---|---|---|
| `no_emoji` | HARD_FAIL | raw | any emoji unicode point |
| `no_arrows_in_prose` | HARD_FAIL | prose | `→`, `=>`, `->`, `⇒` |
| `no_straight_quotes` | HARD_FAIL | prose | `"` or `'` |
| `no_double_hyphen` | HARD_FAIL | prose | `--` |
| `em_dash_budget` | WARN | prose | >1 em dash per block (paragraph or list-item) |
| `no_banned_markers` | HARD_FAIL | prose | any phrase from `banned-markers.toml [hard_fail_markers]` (case-insensitive) |

`em_dash_budget` is WARN per spec §5 Phase 2 (note: SKILL.md text says "Hard limit: at most one" — this is the human-facing rule; the linter expresses it as WARN to allow style judgment). This is intentional.

- [ ] **Step 8.1: Write failing tests for all six checks**

Create `skills/ru-editor/scripts/tests/test_checks_absolute.py`:

```python
"""Tests for Phase-1-locked absolute checks."""
import unittest
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import ru_lint  # noqa: E402
from ru_lint import Document, run_checks  # noqa: E402


def lint_check(text: str, check_name: str | None = None):
    """Helper: run all absolute checks on a doc, optionally filter to one check."""
    findings = run_checks(Document(text=text), source=None, mode="check")
    if check_name:
        findings = [f for f in findings if f.check == check_name]
    return findings


class TestNoEmoji(unittest.TestCase):
    def test_emoji_in_prose_fires(self):
        f = lint_check("Привет 🚀 мир.", "no_emoji")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "HARD_FAIL")

    def test_emoji_in_code_block_does_not_fire(self):
        # Emoji inside a code block is intentional code, not prose. Skip.
        f = lint_check("```\necho 🚀\n```\n", "no_emoji")
        self.assertEqual(f, [])

    def test_clean_text_no_finding(self):
        f = lint_check("Чистый текст.", "no_emoji")
        self.assertEqual(f, [])


class TestNoArrowsInProse(unittest.TestCase):
    def test_arrow_in_prose_fires(self):
        f = lint_check("До → После", "no_arrows_in_prose")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "HARD_FAIL")

    def test_arrow_in_code_span_does_not_fire(self):
        f = lint_check("Используйте `a -> b` вот так.", "no_arrows_in_prose")
        self.assertEqual(f, [])

    def test_double_arrow_caught(self):
        f = lint_check("a => b", "no_arrows_in_prose")
        self.assertEqual(len(f), 1)

    def test_dash_arrow_caught(self):
        f = lint_check("a -> b", "no_arrows_in_prose")
        self.assertEqual(len(f), 1)

    def test_unicode_double_arrow_caught(self):
        f = lint_check("a ⇒ b", "no_arrows_in_prose")
        self.assertEqual(len(f), 1)


class TestNoStraightQuotes(unittest.TestCase):
    def test_straight_quotes_in_prose_fire(self):
        f = lint_check('Он сказал "привет".', "no_straight_quotes")
        self.assertEqual(len(f), 1)

    def test_straight_quotes_in_code_do_not_fire(self):
        f = lint_check('Запусти `print("hi")`.', "no_straight_quotes")
        self.assertEqual(f, [])

    def test_guillemets_clean(self):
        f = lint_check("Он сказал «привет».", "no_straight_quotes")
        self.assertEqual(f, [])


class TestNoDoubleHyphen(unittest.TestCase):
    def test_double_hyphen_in_prose_fires(self):
        f = lint_check("Это -- длинная пауза.", "no_double_hyphen")
        self.assertEqual(len(f), 1)

    def test_double_hyphen_in_flag_does_not_fire(self):
        f = lint_check("Используй флаг `--fast`.", "no_double_hyphen")
        self.assertEqual(f, [])

    def test_em_dash_clean(self):
        f = lint_check("Это — длинная пауза.", "no_double_hyphen")
        self.assertEqual(f, [])


class TestEmDashBudget(unittest.TestCase):
    def test_one_em_dash_per_paragraph_ok(self):
        f = lint_check("Москва — столица.\n\nСанкт-Петербург — город.", "em_dash_budget")
        self.assertEqual(f, [])

    def test_two_em_dashes_in_one_paragraph_warn(self):
        f = lint_check("Москва — столица — крупный город.", "em_dash_budget")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_em_dashes_in_separate_list_items_ok(self):
        text = "- Первый — описание.\n- Второй — описание.\n"
        f = lint_check(text, "em_dash_budget")
        self.assertEqual(f, [])


class TestNoBannedMarkers(unittest.TestCase):
    def test_pogruzhaemsya_fires(self):
        f = lint_check("Сегодня погружаемся в детали.", "no_banned_markers")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "HARD_FAIL")

    def test_landshaft_fires(self):
        f = lint_check("В современном ландшафте ИИ.", "no_banned_markers")
        self.assertEqual(len(f), 1)

    def test_stoit_otmetit_fires(self):
        f = lint_check("Стоит отметить, что система работает.", "no_banned_markers")
        self.assertEqual(len(f), 1)

    def test_marker_inside_code_does_not_fire(self):
        f = lint_check("В шаблоне есть переменная `landshaft_var`.", "no_banned_markers")
        # 'landshaft_var' is in a code span — should not fire.
        # Also test phrase boundary: 'ландшафт' as substring should still fire only in prose.
        self.assertEqual(f, [])

    def test_clean_text_no_finding(self):
        f = lint_check("Чистый русский текст без маркеров.", "no_banned_markers")
        self.assertEqual(f, [])


class TestDirectiveSuppression(unittest.TestCase):
    """Verify ignore directives suppress HARD_FAIL findings on covered lines."""
    def test_ignore_line_suppresses_finding(self):
        text = "Норм текст.\n<!-- ru-lint:ignore-line -->\nЗдесь стрелка → допустима.\nДальше норма.\n"
        f = lint_check(text, "no_arrows_in_prose")
        self.assertEqual(f, [])

    def test_ignore_block_suppresses_findings(self):
        text = (
            "Норма.\n"
            "<!-- ru-lint:ignore-start -->\n"
            "Стрелка → и `--` живут здесь как примеры.\n"
            "Ещё одна → стрелка.\n"
            "<!-- ru-lint:ignore-end -->\n"
            "Снова норма.\n"
        )
        f = lint_check(text, "no_arrows_in_prose")
        self.assertEqual(f, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 8.2: Run tests — expect FAIL (checks not registered)**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_checks_absolute.py -v
```

Expected: failures (no checks registered yet).

- [ ] **Step 8.3: Implement the six absolute checks**

Append to `skills/ru-editor/scripts/ru_lint.py`:

```python
import tomllib

_REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"
_BANNED_MARKERS_PATH = _REFERENCES_DIR / "banned-markers.toml"


def _load_banned_markers() -> dict:
    with open(_BANNED_MARKERS_PATH, "rb") as fp:
        return tomllib.load(fp)


def _line_col_of(text: str, idx: int) -> tuple[int, int]:
    """Translate string index to (1-based line, 0-based column)."""
    line = text.count("\n", 0, idx) + 1
    last_nl = text.rfind("\n", 0, idx)
    col = idx - (last_nl + 1) if last_nl >= 0 else idx
    return line, col


def _context_around(text: str, idx: int, span: int = 30) -> str:
    start = max(0, idx - span)
    end = min(len(text), idx + span)
    s = text[start:end].replace("\n", " ")
    return s.strip()


_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF"
    "☀-➿"
    "\U0001F900-\U0001F9FF"
    "]"
)


@register(name="no_emoji", severity="HARD_FAIL", mode="absolute",
          description="Финальный текст не должен содержать emoji.")
def _check_no_emoji(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    text = doc.prose
    for m in _EMOJI_RE.finditer(text):
        line, col = _line_col_of(text, m.start())
        out.append(Finding(
            check="no_emoji", severity="HARD_FAIL",
            line=line, col=col, match=m.group(0),
            context=_context_around(text, m.start()),
            message="Emoji в финальной русской прозе запрещены (Output Discipline).",
        ))
    return out


_ARROW_RE = re.compile(r"→|⇒|=>|->")


@register(name="no_arrows_in_prose", severity="HARD_FAIL", mode="absolute",
          description="Стрелки → => -> ⇒ запрещены в русской прозе вне кода.")
def _check_no_arrows(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    text = doc.prose
    for m in _ARROW_RE.finditer(text):
        line, col = _line_col_of(text, m.start())
        out.append(Finding(
            check="no_arrows_in_prose", severity="HARD_FAIL",
            line=line, col=col, match=m.group(0),
            context=_context_around(text, m.start()),
            message="Стрелка в русской прозе. Используйте «заменить на», «состоит из», «после этого».",
        ))
    return out


_STRAIGHT_QUOTE_RE = re.compile(r'["\']')


@register(name="no_straight_quotes", severity="HARD_FAIL", mode="absolute",
          description="Прямые кавычки запрещены в русском тексте вне кода.")
def _check_no_straight_quotes(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    text = doc.prose
    for m in _STRAIGHT_QUOTE_RE.finditer(text):
        line, col = _line_col_of(text, m.start())
        out.append(Finding(
            check="no_straight_quotes", severity="HARD_FAIL",
            line=line, col=col, match=m.group(0),
            context=_context_around(text, m.start()),
            message="Прямая кавычка в русском тексте. Используйте «» для основных, „" для вложенных.",
        ))
    return out


_DOUBLE_HYPHEN_RE = re.compile(r"--")


@register(name="no_double_hyphen", severity="HARD_FAIL", mode="absolute",
          description="Двойной дефис -- запрещён вне кода.")
def _check_no_double_hyphen(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    text = doc.prose
    for m in _DOUBLE_HYPHEN_RE.finditer(text):
        line, col = _line_col_of(text, m.start())
        out.append(Finding(
            check="no_double_hyphen", severity="HARD_FAIL",
            line=line, col=col, match=m.group(0),
            context=_context_around(text, m.start()),
            message="Двойной дефис вне кода. Используйте em dash (—).",
        ))
    return out


_BLOCK_BOUNDARY_RE = re.compile(r"\n(\s*(?:[-*+]|\d+\.)\s)")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


def _split_into_blocks(text: str) -> list[str]:
    """Split prose into blocks: each paragraph + each list-item is a block."""
    # Promote list-item lines to paragraph boundaries by inserting blank lines.
    promoted = _BLOCK_BOUNDARY_RE.sub(r"\n\n\1", text)
    return [b for b in _PARAGRAPH_SPLIT_RE.split(promoted) if b.strip()]


@register(name="em_dash_budget", severity="WARN", mode="absolute",
          description=">1 em dash в одном блоке (абзаце или list-item).")
def _check_em_dash_budget(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    for block in _split_into_blocks(doc.prose):
        count = block.count("—")
        if count > 1:
            # Find first em dash in block to anchor the finding.
            idx = doc.prose.find(block)
            offset = block.find("—")
            line, col = _line_col_of(doc.prose, idx + offset) if idx >= 0 else (0, 0)
            out.append(Finding(
                check="em_dash_budget", severity="WARN",
                line=line, col=col, match="—",
                context=block.strip()[:80].replace("\n", " "),
                message=f"В блоке {count} em dash. Hard limit — 1. Перепишите через точку или двоеточие.",
            ))
    return out


@register(name="no_banned_markers", severity="HARD_FAIL", mode="absolute",
          description="Запрещённые AI-маркеры из banned-markers.toml [hard_fail_markers].")
def _check_no_banned_markers(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    markers = _load_banned_markers().get("hard_fail_markers", {}).get("phrases", [])
    text = doc.prose
    text_lower = text.lower()
    for phrase in markers:
        p_lower = phrase.lower()
        start = 0
        while True:
            idx = text_lower.find(p_lower, start)
            if idx < 0:
                break
            line, col = _line_col_of(text, idx)
            out.append(Finding(
                check="no_banned_markers", severity="HARD_FAIL",
                line=line, col=col, match=phrase,
                context=_context_around(text, idx),
                message=f"Запрещённый AI-маркер: «{phrase}». См. banned-markers.toml.",
            ))
            start = idx + len(p_lower)
    return out
```

- [ ] **Step 8.4: Re-run absolute checks tests — expect PASS**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_checks_absolute.py -v
```

Expected: all tests pass.

- [ ] **Step 8.5: Run full suite + master regression**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -v
bash scripts/run_all_tests.sh
```

Expected: all unit tests OK; Phase 1 still PASS.

- [ ] **Step 8.6: Sanity test on Phase 1 smoke fixture**

```bash
python3 skills/ru-editor/scripts/ru_lint.py check \
  .development/tests/phase1-content-hygiene/01-basic-ai-slop/output.md
```

Expected: exit 0 (Phase 1 output already passes Phase 2 absolute checks).

```bash
python3 skills/ru-editor/scripts/ru_lint.py check \
  .development/tests/phase1-content-hygiene/01-basic-ai-slop/input.md
```

Expected: exit 1 (input contains 🚀, →, "...", banned markers — should be flagged).

- [ ] **Step 8.7: Commit**

```bash
git add skills/ru-editor/scripts/ru_lint.py \
        skills/ru-editor/scripts/tests/test_checks_absolute.py
git commit -m "feat(ru-editor): six Phase-1-locked absolute checks (emoji, arrows, quotes, double-hyphen, em-dash-budget, banned-markers)"
```

---

## Task 9: Diff checks (Document × Document)

**Files:**
- Modify: `skills/ru-editor/scripts/ru_lint.py`
- Create: `skills/ru-editor/scripts/tests/test_checks_diff.py`

Diff checks compare edited against source. They flag content that **was not in the source but appeared in the edited version** — the Factual Integrity enforcement.

| Check name | Severity | Flags |
|---|---|---|
| `no_new_numeric_tokens` | HARD_FAIL | Number in `edited.numeric_tokens` not in `source.numeric_tokens` |
| `no_new_percentages` | HARD_FAIL | Percentage tokens (`\d+%`) new in edited |
| `no_new_money_tokens` | HARD_FAIL | Money expressions new in edited (руб/USD/EUR/$/€/тыс/млн/млрд) |
| `code_spans_preserved` | HARD_FAIL | Code spans in source but not (verbatim) in edited |
| `urls_preserved` | HARD_FAIL | URLs in source but not in edited |
| `headings_preserved` | HARD_FAIL | Heading count in edited < source (silent loss) |
| `list_items_count_within_tolerance` | WARN | List item count drift > 30% |

- [ ] **Step 9.1: Write failing tests**

Create `skills/ru-editor/scripts/tests/test_checks_diff.py`:

```python
"""Tests for diff-mode checks (orig vs edited)."""
import unittest
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from ru_lint import Document, run_checks  # noqa: E402


def lint_diff(orig: str, edited: str, check_name: str | None = None):
    findings = run_checks(Document(text=edited), source=Document(text=orig), mode="diff")
    if check_name:
        findings = [f for f in findings if f.check == check_name]
    return findings


class TestNoNewNumericTokens(unittest.TestCase):
    def test_new_number_fires(self):
        f = lint_diff("Текст без чисел.", "За 47 дней мы выросли.", "no_new_numeric_tokens")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "HARD_FAIL")
        self.assertIn("47", f[0].match)

    def test_existing_number_preserved_does_not_fire(self):
        f = lint_diff("В 2024 году было 5 проектов.", "В 2024 году — 5 проектов.", "no_new_numeric_tokens")
        self.assertEqual(f, [])

    def test_number_in_code_does_not_count_as_new(self):
        # Code spans don't contribute to numeric_tokens.
        f = lint_diff("Текст.", "Используй `--port=8080`.", "no_new_numeric_tokens")
        self.assertEqual(f, [])


class TestNoNewPercentages(unittest.TestCase):
    def test_new_percentage_fires(self):
        f = lint_diff("Растём.", "Выросли на 47%.", "no_new_percentages")
        self.assertEqual(len(f), 1)

    def test_existing_percentage_preserved_does_not_fire(self):
        f = lint_diff("Доля 47%.", "Доля 47%.", "no_new_percentages")
        self.assertEqual(f, [])


class TestNoNewMoneyTokens(unittest.TestCase):
    def test_new_money_token_rub_fires(self):
        f = lint_diff("Стоит дёшево.", "Стоит 500 руб.", "no_new_money_tokens")
        self.assertEqual(len(f), 1)

    def test_new_money_token_usd_fires(self):
        f = lint_diff("Дорого.", "100 USD за месяц.", "no_new_money_tokens")
        self.assertEqual(len(f), 1)

    def test_existing_money_preserved(self):
        f = lint_diff("Стоит 500 руб.", "Стоит 500 руб.", "no_new_money_tokens")
        self.assertEqual(f, [])


class TestCodeSpansPreserved(unittest.TestCase):
    def test_modified_code_span_fires(self):
        f = lint_diff("Используй `--fast`.", "Используй `--quick`.", "code_spans_preserved")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "HARD_FAIL")

    def test_unchanged_code_span_passes(self):
        f = lint_diff("Используй `--fast`.", "Запусти `--fast` сейчас.", "code_spans_preserved")
        self.assertEqual(f, [])


class TestUrlsPreserved(unittest.TestCase):
    def test_lost_url_fires(self):
        f = lint_diff(
            "Документация на https://example.com/v1.",
            "Документация есть.",
            "urls_preserved",
        )
        self.assertEqual(len(f), 1)

    def test_modified_url_fires(self):
        f = lint_diff(
            "https://example.com/v1",
            "https://example.com/v2",
            "urls_preserved",
        )
        self.assertEqual(len(f), 1)


class TestHeadingsPreserved(unittest.TestCase):
    def test_lost_heading_fires(self):
        orig = "# H1\n\nПара.\n\n## H2\n\nПара.\n"
        edited = "# H1\n\nПара.\n"  # H2 lost
        f = lint_diff(orig, edited, "headings_preserved")
        self.assertEqual(len(f), 1)

    def test_added_heading_does_not_fire_here(self):
        # Adding heading is a different concern (expansion); this check only catches loss.
        orig = "# H1\n"
        edited = "# H1\n\n## New H2\n"
        f = lint_diff(orig, edited, "headings_preserved")
        self.assertEqual(f, [])


class TestListItemsTolerance(unittest.TestCase):
    def test_within_tolerance_no_warn(self):
        orig = "- a\n- b\n- c\n- d\n"
        edited = "- a\n- b\n- c\n"  # 4→3, drift 25% — within 30% tolerance
        f = lint_diff(orig, edited, "list_items_count_within_tolerance")
        self.assertEqual(f, [])

    def test_over_tolerance_warns(self):
        orig = "- a\n- b\n- c\n- d\n- e\n"
        edited = "- a\n- b\n"  # 5→2, drift 60%
        f = lint_diff(orig, edited, "list_items_count_within_tolerance")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 9.2: Run tests — expect FAIL**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_checks_diff.py -v
```

Expected: failures.

- [ ] **Step 9.3: Implement diff checks**

Append to `skills/ru-editor/scripts/ru_lint.py`:

```python
_PERCENTAGE_RE = re.compile(r"\d+(?:[.,]\d+)?\s*%")
_MONEY_RE = re.compile(
    r"\d+(?:[.,]\d+)?\s*"
    r"(?:руб(?:\.|лей|ля)?|USD|EUR|долл(?:ара|аров)?|евро|тыс\.?|млн\.?|млрд\.?|₽|\$|€)"
)


def _diff_set(edited_set: set, source_set: set) -> set:
    """Return items in edited but not in source."""
    return edited_set - source_set


@register(name="no_new_numeric_tokens", severity="HARD_FAIL", mode="diff",
          description="Числовые токены, которых не было в исходнике (Factual Integrity).")
def _check_no_new_numbers(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    assert source is not None
    new = _diff_set(doc.numeric_tokens, source.numeric_tokens)
    out: list[Finding] = []
    for tok in sorted(new):
        idx = doc.prose.find(tok)
        line, col = _line_col_of(doc.prose, idx) if idx >= 0 else (0, 0)
        out.append(Finding(
            check="no_new_numeric_tokens", severity="HARD_FAIL",
            line=line, col=col, match=tok,
            context=_context_around(doc.prose, idx) if idx >= 0 else "",
            message=f"Число «{tok}» появилось в правке, но отсутствовало в исходнике. Запрещено выдумывать конкретику.",
        ))
    return out


@register(name="no_new_percentages", severity="HARD_FAIL", mode="diff",
          description="Проценты, которых не было в исходнике.")
def _check_no_new_percentages(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    assert source is not None
    src = set(_PERCENTAGE_RE.findall(source.prose))
    edt = set(_PERCENTAGE_RE.findall(doc.prose))
    new = edt - src
    out: list[Finding] = []
    for tok in sorted(new):
        idx = doc.prose.find(tok)
        line, col = _line_col_of(doc.prose, idx) if idx >= 0 else (0, 0)
        out.append(Finding(
            check="no_new_percentages", severity="HARD_FAIL",
            line=line, col=col, match=tok,
            context=_context_around(doc.prose, idx) if idx >= 0 else "",
            message=f"Процент «{tok}» отсутствовал в исходнике.",
        ))
    return out


@register(name="no_new_money_tokens", severity="HARD_FAIL", mode="diff",
          description="Денежные выражения, которых не было в исходнике.")
def _check_no_new_money(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    assert source is not None
    src = set(_MONEY_RE.findall(source.prose))
    edt = set(_MONEY_RE.findall(doc.prose))
    new = edt - src
    out: list[Finding] = []
    for tok in sorted(new):
        idx = doc.prose.find(tok)
        line, col = _line_col_of(doc.prose, idx) if idx >= 0 else (0, 0)
        out.append(Finding(
            check="no_new_money_tokens", severity="HARD_FAIL",
            line=line, col=col, match=tok,
            context=_context_around(doc.prose, idx) if idx >= 0 else "",
            message=f"Денежная сумма «{tok}» отсутствовала в исходнике.",
        ))
    return out


@register(name="code_spans_preserved", severity="HARD_FAIL", mode="diff",
          description="Inline code spans должны быть сохранены посимвольно.")
def _check_code_spans_preserved(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    assert source is not None
    src = set(source.code_spans)
    edt = set(doc.code_spans)
    lost = src - edt
    out: list[Finding] = []
    for span in sorted(lost):
        out.append(Finding(
            check="code_spans_preserved", severity="HARD_FAIL",
            line=0, col=0, match=span,
            context=span,
            message=f"Code span «`{span}`» был в исходнике, но изменён или удалён.",
        ))
    return out


@register(name="urls_preserved", severity="HARD_FAIL", mode="diff",
          description="URLs из исходника должны быть сохранены.")
def _check_urls_preserved(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    assert source is not None
    src = set(source.urls)
    edt = set(doc.urls)
    lost = src - edt
    out: list[Finding] = []
    for url in sorted(lost):
        out.append(Finding(
            check="urls_preserved", severity="HARD_FAIL",
            line=0, col=0, match=url,
            context=url,
            message=f"URL «{url}» был в исходнике, но изменён или удалён.",
        ))
    return out


@register(name="headings_preserved", severity="HARD_FAIL", mode="diff",
          description="Количество заголовков не должно уменьшаться.")
def _check_headings_preserved(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    assert source is not None
    src_count = len(source.headings)
    edt_count = len(doc.headings)
    if edt_count < src_count:
        return [Finding(
            check="headings_preserved", severity="HARD_FAIL",
            line=0, col=0, match=str(src_count - edt_count),
            context=f"source: {src_count}, edited: {edt_count}",
            message=f"Потеряно {src_count - edt_count} заголов(ка/ков). Silent structural loss запрещён.",
        )]
    return []


@register(name="list_items_count_within_tolerance", severity="WARN", mode="diff",
          description="Количество list-items не должно отличаться больше чем на 30%.")
def _check_list_items_tolerance(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    assert source is not None
    src_n = len(source.list_items)
    edt_n = len(doc.list_items)
    if src_n == 0:
        return []
    drift = abs(edt_n - src_n) / src_n
    if drift > 0.30:
        return [Finding(
            check="list_items_count_within_tolerance", severity="WARN",
            line=0, col=0, match=f"{int(drift*100)}%",
            context=f"source: {src_n} items, edited: {edt_n} items",
            message=f"Дрейф числа list-items {int(drift*100)}% превышает порог 30%.",
        )]
    return []
```

- [ ] **Step 9.4: Re-run diff tests — expect PASS**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_checks_diff.py -v
```

Expected: all tests pass.

- [ ] **Step 9.5: Run full suite + master regression**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -v
bash scripts/run_all_tests.sh
```

Expected: all OK, Phase 1 still passes.

- [ ] **Step 9.6: Sanity test on Phase 1 smoke fixture (diff mode)**

```bash
python3 skills/ru-editor/scripts/ru_lint.py both \
  .development/tests/phase1-content-hygiene/01-basic-ai-slop/input.md \
  .development/tests/phase1-content-hygiene/01-basic-ai-slop/output.md
```

Expected: 0 HARD_FAIL findings (input had emoji/arrows/etc; output is clean and didn't invent anything new).

- [ ] **Step 9.7: Commit**

```bash
git add skills/ru-editor/scripts/ru_lint.py \
        skills/ru-editor/scripts/tests/test_checks_diff.py
git commit -m "feat(ru-editor): seven diff-mode checks (numbers, percentages, money, code, URLs, headings, list-tolerance)"
```

---

## Task 10: WARN checks informed by grounding

**Files:**
- Modify: `skills/ru-editor/scripts/ru_lint.py`
- Create: `skills/ru-editor/scripts/tests/test_checks_warn.py`

Prerequisite: Task 7 grounding ≥15 троек complete. Tag frequency analysis informs which WARN patterns to ship and how strict to make them.

| Check name | Severity | Flags |
|---|---|---|
| `repeated_sentence_openers` | WARN | 3+ consecutive sentences start with same first word |
| `x_a_ne_y_pileup` | WARN | 3+ «..., а не ...» constructions within 500 chars |
| `eto_in_definitions` | WARN | 3+ sentences in proximity using «X — это Y» pattern |
| `word_repetition_in_sentence` | WARN | A non-stopword appears 3+ times in one sentence |
| `synonym_cluster_drift` | WARN | 3+ members of one cluster from `banned-markers.toml [synonym_clusters]` within 500 chars |
| `mixed_list_punctuation` | WARN | Items in one list end with mixed terminal punctuation |
| `length_ratio_violation` | WARN | edited length is < 80% or > 120% of source length |

- [ ] **Step 10.1: Decide on grounding-informed adjustments (manual)**

Before coding, review tags.md across all grounding cases. Note:
- Which patterns appear ≥5 times across cases? Implement them as below.
- Which patterns appear in fewer than 3 cases? Defer them to v2.5+.
- Note any new patterns missing from this list. Add as additional checks.

Document decisions in `.development/tests/phase2-regex-linter/grounding-summary.md` (gitignored). One section per pattern: pattern name, count, decision (implement / defer / extend marker list).

- [ ] **Step 10.2: Write failing tests**

Create `skills/ru-editor/scripts/tests/test_checks_warn.py`:

```python
"""Tests for WARN checks (Task 10) — heuristic patterns informed by grounding."""
import unittest
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from ru_lint import Document, run_checks  # noqa: E402


def lint_check(text: str, check_name: str | None = None):
    findings = run_checks(Document(text=text), source=None, mode="check")
    if check_name:
        findings = [f for f in findings if f.check == check_name]
    return findings


def lint_diff(orig: str, edited: str, check_name: str | None = None):
    findings = run_checks(Document(text=edited), source=Document(text=orig), mode="diff")
    if check_name:
        findings = [f for f in findings if f.check == check_name]
    return findings


class TestRepeatedSentenceOpeners(unittest.TestCase):
    def test_three_in_a_row_same_opener_warns(self):
        text = "Мы запустили продукт. Мы наняли команду. Мы выросли."
        f = lint_check(text, "repeated_sentence_openers")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_two_in_a_row_no_warn(self):
        text = "Мы запустили продукт. Мы наняли команду. Команда сильная."
        f = lint_check(text, "repeated_sentence_openers")
        self.assertEqual(f, [])


class TestXANeYPileup(unittest.TestCase):
    def test_three_in_proximity_warns(self):
        text = (
            "Скорость, а не громоздкость. Простота, а не сложность. Гибкость, а не жёсткость."
        )
        f = lint_check(text, "x_a_ne_y_pileup")
        self.assertEqual(len(f), 1)

    def test_two_in_proximity_no_warn(self):
        text = "Скорость, а не громоздкость. Простота, а не сложность."
        f = lint_check(text, "x_a_ne_y_pileup")
        self.assertEqual(f, [])


class TestEtoInDefinitions(unittest.TestCase):
    def test_three_definitions_with_eto_warn(self):
        text = (
            "Проект — это план. Команда — это люди. Успех — это результат."
        )
        f = lint_check(text, "eto_in_definitions")
        self.assertEqual(len(f), 1)

    def test_two_definitions_no_warn(self):
        text = "Проект — это план. Команда — это люди."
        f = lint_check(text, "eto_in_definitions")
        self.assertEqual(f, [])


class TestWordRepetitionInSentence(unittest.TestCase):
    def test_three_in_one_sentence_warns(self):
        text = "Система обрабатывает данные системы из системы."
        f = lint_check(text, "word_repetition_in_sentence")
        self.assertEqual(len(f), 1)

    def test_stopword_repetition_does_not_fire(self):
        # Stopwords like «и», «в», «не» — common, do not trigger.
        text = "В системе и в коде и в данных всё работает."
        f = lint_check(text, "word_repetition_in_sentence")
        self.assertEqual(f, [])


class TestSynonymClusterDrift(unittest.TestCase):
    def test_three_synonyms_from_one_cluster_warn(self):
        text = (
            "Наш продукт быстрый. Это решение надёжное. Платформа удобна для всех."
        )
        # product_drift cluster: продукт, решение, платформа — 3 members in proximity.
        f = lint_check(text, "synonym_cluster_drift")
        self.assertEqual(len(f), 1)

    def test_two_synonyms_no_warn(self):
        text = "Наш продукт быстрый. Решение надёжное."
        f = lint_check(text, "synonym_cluster_drift")
        self.assertEqual(f, [])


class TestMixedListPunctuation(unittest.TestCase):
    def test_mixed_terminal_punctuation_warns(self):
        text = "- Первый.\n- Второй;\n- Третий\n"
        f = lint_check(text, "mixed_list_punctuation")
        self.assertEqual(len(f), 1)

    def test_consistent_list_no_warn(self):
        text = "- Первый.\n- Второй.\n- Третий.\n"
        f = lint_check(text, "mixed_list_punctuation")
        self.assertEqual(f, [])


class TestLengthRatioViolation(unittest.TestCase):
    def test_within_tolerance_ok(self):
        f = lint_diff("a" * 1000, "a" * 1100, "length_ratio_violation")
        self.assertEqual(f, [])

    def test_too_short_warns(self):
        f = lint_diff("a" * 1000, "a" * 700, "length_ratio_violation")
        self.assertEqual(len(f), 1)

    def test_too_long_warns(self):
        f = lint_diff("a" * 1000, "a" * 1300, "length_ratio_violation")
        self.assertEqual(len(f), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 10.3: Run tests — expect FAIL**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_checks_warn.py -v
```

Expected: failures.

- [ ] **Step 10.4: Implement WARN checks**

Append to `skills/ru-editor/scripts/ru_lint.py`:

```python
# Russian stopwords (extended). Repetition of these doesn't count for word_repetition check.
_RU_STOPWORDS = frozenset({
    "и", "в", "не", "на", "с", "по", "для", "что", "это", "к", "а", "но", "или",
    "о", "от", "до", "из", "за", "у", "при", "об", "со", "под", "над", "без",
    "же", "ли", "то", "так", "уже", "ещё", "ещё", "как", "когда", "где", "куда",
    "всё", "все", "вся", "весь", "тот", "та", "те", "этот", "эта", "эти",
    "мы", "вы", "они", "он", "она", "я", "ты",
    "быть", "есть", "был", "была", "было", "были", "будет", "будут",
    "наш", "ваш", "его", "её", "их", "свой", "сам", "сама",
    "если", "чтобы", "потому", "поэтому", "также", "только", "лишь",
    "the", "a", "an", "of", "to", "is", "in", "for", "and", "or", "but",
})


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _first_word(sentence: str) -> str:
    m = re.match(r"\s*([\w-]+)", sentence, flags=re.UNICODE)
    return m.group(1).lower() if m else ""


@register(name="repeated_sentence_openers", severity="WARN", mode="absolute",
          description="3+ предложения подряд начинаются с одного слова.")
def _check_repeated_openers(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    sentences = _split_sentences(doc.prose)
    if len(sentences) < 3:
        return []
    streak_word = ""
    streak_len = 0
    for s in sentences:
        w = _first_word(s)
        if w and w == streak_word:
            streak_len += 1
        else:
            streak_word = w
            streak_len = 1
        if streak_len == 3:
            idx = doc.prose.find(s)
            line, col = _line_col_of(doc.prose, idx) if idx >= 0 else (0, 0)
            out.append(Finding(
                check="repeated_sentence_openers", severity="WARN",
                line=line, col=col, match=streak_word,
                context=s[:80].replace("\n", " "),
                message=f"3+ предложения подряд начинаются с «{streak_word}». Варьируйте начала.",
            ))
    return out


_X_A_NE_Y_RE = re.compile(r"[^,.;!?]+,\s*а\s+не\s+[^,.;!?]+", re.UNICODE)


@register(name="x_a_ne_y_pileup", severity="WARN", mode="absolute",
          description="3+ конструкции «X, а не Y» в окне 500 символов.")
def _check_x_a_ne_y_pileup(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    matches = list(_X_A_NE_Y_RE.finditer(doc.prose))
    for i in range(len(matches) - 2):
        if matches[i + 2].start() - matches[i].start() <= 500:
            idx = matches[i].start()
            line, col = _line_col_of(doc.prose, idx)
            out.append(Finding(
                check="x_a_ne_y_pileup", severity="WARN",
                line=line, col=col, match="X, а не Y",
                context=_context_around(doc.prose, idx, 60),
                message="3+ конструкции «X, а не Y» подряд. Свернуть в простой список или варьировать.",
            ))
            break  # one finding is enough
    return out


_DEFINITION_ETO_RE = re.compile(r"\b\w+\s+—\s+это\s+", re.UNICODE)


@register(name="eto_in_definitions", severity="WARN", mode="absolute",
          description="3+ предложения в проксимити используют «X — это Y».")
def _check_eto_definitions(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    matches = list(_DEFINITION_ETO_RE.finditer(doc.prose))
    out: list[Finding] = []
    for i in range(len(matches) - 2):
        if matches[i + 2].start() - matches[i].start() <= 500:
            idx = matches[i].start()
            line, col = _line_col_of(doc.prose, idx)
            out.append(Finding(
                check="eto_in_definitions", severity="WARN",
                line=line, col=col, match="X — это Y",
                context=_context_around(doc.prose, idx, 60),
                message="3+ определения через «это» в проксимити. Варьируйте структуру.",
            ))
            break
    return out


def _normalize_word(w: str) -> str:
    """Lowercase + strip Russian/Latin grammatical endings (crude stem)."""
    w = w.lower()
    # Crude: trim 1–3 trailing chars to fold case/number variants.
    # Better: would need pymorphy2, but no deps allowed.
    return w[:max(4, len(w) - 2)]


@register(name="word_repetition_in_sentence", severity="WARN", mode="absolute",
          description="Не-стоп-слово повторяется 3+ раз в одном предложении.")
def _check_word_repetition(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    for s in _split_sentences(doc.prose):
        words = re.findall(r"[\w-]+", s, flags=re.UNICODE)
        counts: dict[str, int] = {}
        for w in words:
            wl = w.lower()
            if wl in _RU_STOPWORDS or len(wl) < 4:
                continue
            stem = _normalize_word(w)
            counts[stem] = counts.get(stem, 0) + 1
        flagged = [(stem, c) for stem, c in counts.items() if c >= 3]
        if flagged:
            stem, c = flagged[0]
            idx = doc.prose.find(s)
            line, col = _line_col_of(doc.prose, idx) if idx >= 0 else (0, 0)
            out.append(Finding(
                check="word_repetition_in_sentence", severity="WARN",
                line=line, col=col, match=stem,
                context=s[:80].replace("\n", " "),
                message=f"«{stem}*» встречается {c} раз в одном предложении. Варьируйте.",
            ))
    return out


@register(name="synonym_cluster_drift", severity="WARN", mode="absolute",
          description="3+ члена одного синонимического кластера в окне 500 символов.")
def _check_synonym_cluster_drift(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    text_lower = doc.prose.lower()
    clusters = _load_banned_markers().get("synonym_clusters", {})
    for name, words in clusters.items():
        # Find all positions of all words in the cluster (case-insensitive).
        positions: list[tuple[int, str]] = []
        for w in words:
            wl = w.lower()
            start = 0
            while True:
                idx = text_lower.find(wl, start)
                if idx < 0:
                    break
                # Word boundary check: surrounding chars not letters.
                before = text_lower[idx - 1] if idx > 0 else " "
                after = text_lower[idx + len(wl)] if idx + len(wl) < len(text_lower) else " "
                if not (before.isalpha() or after.isalpha()):
                    positions.append((idx, w))
                start = idx + len(wl)
        positions.sort()
        # Sliding window of 500 chars: if 3+ DIFFERENT cluster members appear, flag once.
        for i in range(len(positions) - 2):
            window = positions[i:]
            seen_words = set()
            for pos, word in window:
                if pos - positions[i][0] > 500:
                    break
                seen_words.add(word.lower())
            if len(seen_words) >= 3:
                idx, word = positions[i]
                line, col = _line_col_of(doc.prose, idx)
                out.append(Finding(
                    check="synonym_cluster_drift", severity="WARN",
                    line=line, col=col, match=name,
                    context=", ".join(sorted(seen_words)),
                    message=f"Кластер «{name}»: {len(seen_words)} синонимов в проксимити. Не циклируйте близкие слова.",
                ))
                break  # one finding per cluster
    return out


_LIST_BLOCK_RE = re.compile(
    r"(?:^[ \t]*(?:[-*+]|\d+\.)[ \t]+.+(?:\n|$))+",
    re.MULTILINE,
)


@register(name="mixed_list_punctuation", severity="WARN", mode="absolute",
          description="Элементы одного списка имеют разную терминальную пунктуацию.")
def _check_mixed_list_punctuation(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    for block_match in _LIST_BLOCK_RE.finditer(doc.prose):
        block = block_match.group(0)
        items = [line for line in block.splitlines() if line.strip()]
        if len(items) < 2:
            continue
        endings: set[str] = set()
        for item in items:
            stripped = item.rstrip()
            if not stripped:
                continue
            last = stripped[-1]
            if last in ".;,:":
                endings.add(last)
            else:
                endings.add("none")
        if len(endings) > 1:
            idx = block_match.start()
            line, col = _line_col_of(doc.prose, idx)
            out.append(Finding(
                check="mixed_list_punctuation", severity="WARN",
                line=line, col=col, match="list",
                context=", ".join(sorted(endings)),
                message=f"Список имеет смешанные окончания строк: {sorted(endings)}.",
            ))
    return out


@register(name="length_ratio_violation", severity="WARN", mode="diff",
          description="Длина edited вне диапазона ±20% от source.")
def _check_length_ratio(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    assert source is not None
    src_len = len(source.prose)
    if src_len == 0:
        return []
    ratio = len(doc.prose) / src_len
    if 0.80 <= ratio <= 1.20:
        return []
    return [Finding(
        check="length_ratio_violation", severity="WARN",
        line=0, col=0,
        match=f"{ratio:.2f}",
        context=f"source: {src_len} chars, edited: {len(doc.prose)} chars",
        message=f"Length ratio {ratio:.2f} вне диапазона [0.80, 1.20] (Phase 2 default ±20%).",
    )]
```

- [ ] **Step 10.5: Re-run WARN tests — expect PASS**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -p test_checks_warn.py -v
```

Expected: all tests pass.

- [ ] **Step 10.6: Run full suite**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -v
```

Expected: all tests OK.

- [ ] **Step 10.7: Commit**

```bash
git add skills/ru-editor/scripts/ru_lint.py \
        skills/ru-editor/scripts/tests/test_checks_warn.py
git commit -m "feat(ru-editor): seven WARN checks (openers, X-a-ne-Y, eto, word-rep, synonym-drift, list-punct, length-ratio)"
```

---

## Task 11: Refine TOML markers from grounding

**Files:**
- Modify: `skills/ru-editor/references/banned-markers.toml`

After Task 7 grounding produces tag frequency analysis, candidate new markers are added here.

- [ ] **Step 11.1: Review grounding-summary.md**

```bash
cat .development/tests/phase2-regex-linter/grounding-summary.md
```

Identify:
- Phrases appearing as missed markers in ≥5 grounding cases → candidate for `[hard_fail_markers]`
- Phrases appearing in 2–4 cases → candidate for `[warn_markers]`
- New synonym clusters observed → candidate for `[synonym_clusters]`

- [ ] **Step 11.2: Update TOML**

Edit `skills/ru-editor/references/banned-markers.toml`. Add entries based on grounding findings. Example additions (placeholder — actual content depends on grounding):

```toml
[hard_fail_markers]
phrases = [
  # Existing locked-in:
  "погружаемся",
  "погрузимся",
  "ландшафт",
  "гобелен",
  "является свидетельством",
  "стоит отметить",
  # NEW from grounding (Task 7 output):
  # "фактор цифровой трансформации",   # found 7× in grounding
  # "ключевой момент",                  # found 5×
]

[warn_markers]
phrases = [
  # NEW from grounding:
  # "целая парадигма",                  # found 3× — strong but not 5+
]

[synonym_clusters]
product_drift = ["продукт", "решение", "инструмент", "платформа"]
user_drift    = ["пользователь", "клиент", "человек", "специалист"]
# value_drift = ["качество", "ценность", "польза", "эффект"]   # added if observed
```

(Specific phrases TBD by grounding output. The plan mandates the **process**, not the **content**.)

- [ ] **Step 11.3: Re-run all tests — `test_banned_markers.py` must still pass**

```bash
python3 -m unittest discover skills/ru-editor/scripts/tests/ -v
```

Expected: existing tests still pass. Specifically `test_hard_fail_phrases_locked` must continue to pass — never remove the six Phase-1 markers.

- [ ] **Step 11.4: Lint reference files for false positives**

```bash
for f in skills/ru-editor/SKILL.md skills/ru-editor/references/*.md; do
  echo "── $f ──"
  python3 skills/ru-editor/scripts/ru_lint.py check "$f" --format json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"  hard_fail: {d['summary']['hard_fail_count']}, warn: {d['summary']['warn_count']}\")
for f in d['findings']:
  if f['severity'] == 'HARD_FAIL':
    print(f\"  HARD_FAIL [{f['check']}] L{f['line']}: {f['match']}\")
"
done
```

Expected: 0 HARD_FAIL on every file. If any fire, either:
- The marker is too aggressive — narrow it.
- The reference file legitimately documents the marker — wrap with `<!-- ru-lint:ignore-start --> ... <!-- ru-lint:ignore-end -->` directives.

- [ ] **Step 11.5: Commit**

```bash
git add skills/ru-editor/references/banned-markers.toml
git commit -m "feat(ru-editor): refine banned markers from empirical grounding (N additions)"
```

(Replace N with actual count.)

---

## Task 12: Seed corpus — 20 hand-crafted pairs

**Files:**
- Create: `evals/seed-corpus/README.md`
- Create: `evals/seed-corpus/NN-<slug>/source.md` × 20
- Create: `evals/seed-corpus/NN-<slug>/expected.md` × 20
- Create: `evals/seed-corpus/NN-<slug>/brief.toml` × 20

The seed corpus is committed to the repo. It serves three purposes:
1. **Acceptance gate:** linter must achieve ≥90% recall on `source.md` (catch what's marked in `brief.toml`).
2. **Idempotency invariant:** linter on `expected.md` produces 0 HARD_FAIL.
3. **Reproducible regression** for Phase 3+ work.

Stratification: 5 genres × 3 intensities = 15 cases, plus 5 ad-hoc edge cases.

- [ ] **Step 12.1: Create README**

Create `evals/seed-corpus/README.md`:

```markdown
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
```

- [ ] **Step 12.2: Create the 15 stratified pairs**

For each cell in the 5×3 matrix, craft:
- `source.md` with realistic AI-slop (200–800 chars typically) showing genre-typical issues
- `expected.md` showing the v2.3 skill's expected clean output
- `brief.toml` with ground-truth findings

This is content work — ~30–60 min per pair. Use these prompts as a template per genre:

| Genre | Source paradigm | Typical markers |
|---|---|---|
| technical | API docs, runbook | bureaucratese, anglicism overuse, vague specs |
| marketing | landing copy, pitch | invented numbers, emojis, arrows, banned markers |
| educational | tutorial, course | пafosnост, «погружаемся», parallel-construction overuse |
| blog | opinion piece | rule-of-three, X-a-ne-Y, em dash decoration |
| internal | email, status update | euphemisms, hedging, soft language |

- [ ] **Step 12.3: Create the 5 edge-case pairs**

Edge cases stress-test specific linter behaviours:
- 16: Idempotency check — `source.md` IS already clean; `expected.md` is identical; linter should produce 0 findings on both.
- 17: Directive-heavy — uses `<!-- ru-lint:ignore-* -->` directives. Verifies suppression works.
- 18: Code-spans-vs-prose — content where banned strings appear ONLY in code (must not fire) and ONLY in prose (must fire), in same doc.
- 19: Unicode — non-ASCII letters in tokens, multi-byte emoji, mixed scripts.
- 20: Empty / minimal — single sentence, single heading, very short doc.

For each, write source / expected / brief that exercises the targeted behavior precisely.

- [ ] **Step 12.4: Verify all pairs are well-formed (no checks yet)**

```bash
for d in evals/seed-corpus/[0-9]*; do
  for f in source.md expected.md brief.toml; do
    [[ -f "$d/$f" ]] || echo "MISSING: $d/$f"
  done
done
echo "---"
ls evals/seed-corpus/ | grep -E '^[0-9]{2}-' | wc -l
```

Expected: no MISSING lines; count is 20.

- [ ] **Step 12.5: Sanity-lint each expected.md (idempotency invariant)**

```bash
for d in evals/seed-corpus/[0-9]*; do
  out=$(python3 skills/ru-editor/scripts/ru_lint.py check "$d/expected.md" --format json)
  hard=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['hard_fail_count'])")
  if [[ "$hard" -ne 0 ]]; then
    echo "FAIL: $d/expected.md has $hard HARD_FAIL — fix expected or use ignore directive."
  fi
done
```

Expected: no FAIL lines.

- [ ] **Step 12.6: Commit corpus**

```bash
git add evals/seed-corpus/
git commit -m "feat(ru-editor): seed corpus with 20 stratified pairs (5 genres × 3 intensities + 5 edge cases)"
```

---

## Task 13: Phase 2 acceptance script

**Files:**
- Create: `skills/ru-editor/scripts/run_phase2_acceptance.sh`

This is the script `run_all_tests.sh` calls to verify Phase 2.

- [ ] **Step 13.1: Write the acceptance script**

Create `skills/ru-editor/scripts/run_phase2_acceptance.sh`:

```bash
#!/usr/bin/env bash
# Phase 2 (v2.4.0) acceptance:
#   1. unittest suite under tests/
#   2. seed-corpus: source.md fires within [hard_fail_min, hard_fail_max]
#   3. seed-corpus: expected.md has 0 HARD_FAIL
#   4. own reference files: 0 HARD_FAIL
#   5. perf budget: <100 ms per 5K-char doc
#
# Exits 0 on full pass, 1 on any failure.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

failures=0
section() { echo; echo "── $1 ──"; }

section "1. Unit tests (unittest discover)"
if python3 -m unittest discover skills/ru-editor/scripts/tests/ -v 2>&1 | tail -5; then
  echo "PASS: unit tests"
else
  echo "FAIL: unit tests"
  failures=$((failures + 1))
fi

section "2. Seed corpus — sources fire within budget"
corpus_failures=0
for d in evals/seed-corpus/[0-9]*; do
  src="$d/source.md"
  brief="$d/brief.toml"
  [[ -f "$src" && -f "$brief" ]] || continue

  result=$(python3 skills/ru-editor/scripts/ru_lint.py check "$src" --format json 2>/dev/null)
  hard=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['hard_fail_count'])")

  expected_min=$(python3 -c "
import tomllib
with open('$brief', 'rb') as f:
    d = tomllib.load(f)
print(d.get('expected_findings', {}).get('hard_fail_min', 0))
")
  expected_max=$(python3 -c "
import tomllib
with open('$brief', 'rb') as f:
    d = tomllib.load(f)
print(d.get('expected_findings', {}).get('hard_fail_max', 999))
")

  if [[ "$hard" -lt "$expected_min" ]] || [[ "$hard" -gt "$expected_max" ]]; then
    echo "FAIL: $d source has $hard HARD_FAIL (expected [$expected_min, $expected_max])"
    corpus_failures=$((corpus_failures + 1))
  fi
done
if [[ "$corpus_failures" -eq 0 ]]; then
  echo "PASS: all seed-corpus sources within budget"
else
  echo "FAIL: $corpus_failures seed-corpus source(s) outside budget"
  failures=$((failures + 1))
fi

section "3. Seed corpus — expected.md has 0 HARD_FAIL (idempotency invariant)"
expected_failures=0
for d in evals/seed-corpus/[0-9]*; do
  exp="$d/expected.md"
  [[ -f "$exp" ]] || continue
  result=$(python3 skills/ru-editor/scripts/ru_lint.py check "$exp" --format json 2>/dev/null)
  hard=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['hard_fail_count'])")
  if [[ "$hard" -ne 0 ]]; then
    echo "FAIL: $d/expected.md has $hard HARD_FAIL"
    expected_failures=$((expected_failures + 1))
  fi
done
if [[ "$expected_failures" -eq 0 ]]; then
  echo "PASS: all seed-corpus expected.md are linter-clean"
else
  echo "FAIL: $expected_failures expected.md violate idempotency"
  failures=$((failures + 1))
fi

section "4. Own reference files — 0 HARD_FAIL (use directives where needed)"
own_failures=0
for f in skills/ru-editor/SKILL.md skills/ru-editor/references/*.md; do
  result=$(python3 skills/ru-editor/scripts/ru_lint.py check "$f" --format json 2>/dev/null)
  hard=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['hard_fail_count'])")
  if [[ "$hard" -ne 0 ]]; then
    echo "FAIL: $f has $hard HARD_FAIL"
    own_failures=$((own_failures + 1))
  fi
done
if [[ "$own_failures" -eq 0 ]]; then
  echo "PASS: 0 HARD_FAIL on own reference files"
else
  echo "FAIL: $own_failures own reference file(s) flagged"
  failures=$((failures + 1))
fi

section "5. Perf budget — <100 ms per 5K-char doc"
# Use one of the larger reference files as a 5K-char sample.
sample=$(ls -S skills/ru-editor/references/*.md | head -1)
sample_size=$(wc -c < "$sample")

elapsed=$(python3 -c "
import json, subprocess, time
t0 = time.monotonic()
r = subprocess.run(['python3', 'skills/ru-editor/scripts/ru_lint.py', 'check', '$sample', '--format', 'json'], capture_output=True, text=True)
elapsed_ms = int((time.monotonic() - t0) * 1000)
print(elapsed_ms)
")

# Normalize: elapsed_ms per 5K chars
normalized=$(python3 -c "print(int($elapsed * 5000 / $sample_size))")
echo "  sample: $sample ($sample_size chars), elapsed: ${elapsed}ms, normalized to 5K: ${normalized}ms"
if [[ "$normalized" -lt 100 ]]; then
  echo "PASS: perf within 100 ms / 5K chars"
else
  echo "FAIL: perf ${normalized} ms / 5K chars exceeds 100 ms budget"
  failures=$((failures + 1))
fi

echo
if [[ "$failures" -eq 0 ]]; then
  echo "── PHASE 2 ACCEPTANCE: ALL PASSED ──"
  exit 0
else
  echo "── PHASE 2 ACCEPTANCE: $failures SECTION(S) FAILED ──"
  exit 1
fi
```

- [ ] **Step 13.2: Make executable**

```bash
chmod +x skills/ru-editor/scripts/run_phase2_acceptance.sh
```

- [ ] **Step 13.3: Run acceptance**

```bash
bash skills/ru-editor/scripts/run_phase2_acceptance.sh
```

Expected: ALL PASSED. If any section fails, fix before continuing.

- [ ] **Step 13.4: Run master regression — Phase 1 + Phase 2 both green**

```bash
bash scripts/run_all_tests.sh
```

Expected: `ALL 2 PHASE(S) PASSED`.

- [ ] **Step 13.5: Commit**

```bash
git add skills/ru-editor/scripts/run_phase2_acceptance.sh
git commit -m "chore(ru-editor): Phase 2 acceptance script + master-runner integration"
```

---

## Task 14: SKILL.md QA Gate update

**Files:**
- Modify: `skills/ru-editor/SKILL.md` (`## QA Gate` section)

Replace the placeholder language with explicit script invocation as the authoritative step.

- [ ] **Step 14.1: Read current `## QA Gate` section**

```bash
sed -n '/^## QA Gate$/,/^## /p' skills/ru-editor/SKILL.md
```

- [ ] **Step 14.2: Replace it**

Find the existing `## QA Gate` section (created in Phase 1, ends before `## Important Rules`):

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

Replace with:

```markdown
## QA Gate

Before returning edited text, run the deterministic linter:

```bash
python3 skills/ru-editor/scripts/ru_lint.py both <source-file> <edited-file>
```

If `Bash(python *)` is not authorized in the current session, fall back to the manual checklist below — but flag this in the output (`Editor note: linter not available; manual self-check applied`).

The linter enforces:

| Check | Severity | What it catches |
|---|---|---|
| Output Discipline | HARD_FAIL | emoji, arrows in prose, straight quotes, double hyphens |
| Banned AI markers | HARD_FAIL | «погружаемся», «ландшафт», «является свидетельством», «стоит отметить», «гобелен» (full list in `references/banned-markers.toml`) |
| Em dash budget | WARN | >1 em dash per block (paragraph or list-item) |
| Factual Integrity (diff mode) | HARD_FAIL | numbers, percentages, money tokens new in edited but absent from source |
| Structural preservation (diff mode) | HARD_FAIL | code spans modified, URLs lost, headings deleted |
| Style WARNs | WARN | repeated openers, X-a-ne-Y pile-up, «это» in 3+ definitions, word repetition, synonym cluster drift, mixed list punctuation, length-ratio violation |

**Exit code 0** means the edit is clean to return. **Exit code 1** means at least one HARD_FAIL — do NOT return the edit; either fix the issue or include findings as `Editor notes`.

### Manual fallback checklist (if linter unavailable)

1. **No invented facts.** Every number, name, date, percentage in the output must trace to the source.
2. **No protected spans changed.** Code, URLs, commands, file paths, API names, product names — unchanged.
3. **No banned outputs.** No emoji, no arrows in prose, no straight quotes in Russian outside code, no `--`.
4. **No surviving banned AI markers** in final text. See `references/banned-markers.toml [hard_fail_markers]` for the authoritative list.
5. **Structure preserved.** Headings, list items, paragraphs counted in vs out — no silent loss.

### Suppressing false positives

If a passage legitimately contains a banned string (e.g., reference documentation showing what's banned), wrap it with HTML directive comments:

```markdown
<!-- ru-lint:ignore-line -->
This single line is ignored.

<!-- ru-lint:ignore-start -->
Multiple lines
ignored here.
<!-- ru-lint:ignore-end -->
```

These directives suppress all checks on the covered lines.
```

- [ ] **Step 14.3: Run linter on the updated SKILL.md (own-files check)**

```bash
python3 skills/ru-editor/scripts/ru_lint.py check skills/ru-editor/SKILL.md
```

Expected: 0 HARD_FAIL. (The «погружаемся / ландшафт / etc.» listed in the table are inside markdown code spans and ignore-blocks if needed.)

If it fires on those — wrap the marker list with `<!-- ru-lint:ignore-* -->` directives.

- [ ] **Step 14.4: Commit**

```bash
git add skills/ru-editor/SKILL.md
git commit -m "feat(ru-editor): point QA Gate at ru_lint.py with manual fallback"
```

---

## Task 15: Bump version to v2.4.0 + CHANGELOG

**Files:**
- Modify: `skills/ru-editor/SKILL.md` (frontmatter)
- Modify: `skills/ru-editor/CHANGELOG.md`

- [ ] **Step 15.1: Bump frontmatter version**

In `skills/ru-editor/SKILL.md`, replace:

```yaml
  version: 2.3.0
```

with:

```yaml
  version: 2.4.0
```

- [ ] **Step 15.2: Add CHANGELOG entry**

In `skills/ru-editor/CHANGELOG.md`, after the line `# Changelog` and its preamble, before the existing `## [2.3.0]` section, insert:

```markdown
## [2.4.0] — 2026-04-27

Phase 2 of v3.0.0 overhaul: deterministic regex linter + seed corpus. SKILL.md `## QA Gate` now references the linter as authoritative.

### Added

- `scripts/ru_lint.py` — pure Python 3.11+ regex linter, no third-party deps. Three CLI modes: `check`, `diff`, `both`. JSON output (`schema_version: "1.0"`) and human-readable output. `--strict` flag fails on WARN.
- 13 registered checks (6 absolute HARD_FAIL, 7 diff-mode, 7 WARN).
- `references/banned-markers.toml` — machine-readable source of truth for banned phrases and synonym clusters.
- HTML ignore directives: `<!-- ru-lint:ignore-line -->`, `<!-- ru-lint:ignore-start --> ... <!-- ru-lint:ignore-end -->`. Suppress checks on legitimate documentation of banned content.
- `evals/seed-corpus/` — 20 stratified hand-crafted pairs (5 genres × 3 intensities + 5 edge cases) for empirical acceptance.
- `scripts/run_all_tests.sh` — master regression runner orchestrating all phase acceptance scripts.
- `skills/ru-editor/scripts/run_phase2_acceptance.sh` — Phase 2 acceptance gate (unit tests + seed corpus + own files + perf budget).
- `skills/ru-editor/scripts/tests/` — unittest suite covering Document, registry, CLI, all 20 checks.

### Changed

- `SKILL.md` `## QA Gate`: now invokes `python3 scripts/ru_lint.py` as authoritative step. Manual checklist remains as fallback when `Bash(python *)` is not authorized.
- Version bumped: 2.3.0 → 2.4.0.

### Notes

- No frontmatter `allowed-tools` change yet; that comes with Phase 3 (`context: fork` + isolation).
- Acceptance metrics on seed corpus: ≥90% recall, 0 false-positives on own reference files, perf <100 ms per 5K-char document.
- Empirical grounding (30 source/output/tags triples) lives at `.development/tests/phase2-regex-linter/grounding/` — gitignored.

---
```

- [ ] **Step 15.3: Run linter on updated SKILL.md**

```bash
python3 skills/ru-editor/scripts/ru_lint.py check skills/ru-editor/SKILL.md
```

Expected: 0 HARD_FAIL.

- [ ] **Step 15.4: Run check_phase1.sh — verify version check still passes**

```bash
# check_phase1.sh asserts version: 2.3.0. We bumped to 2.4.0, so it will fail.
# Update check_phase1.sh to accept ≥ 2.3.0, OR add a check_phase2.sh that asserts 2.4.0.
# Decision: keep check_phase1.sh asserting 2.3.0 as the *Phase 1* gate (it's a frozen
# acceptance), and add a Phase 2 gate inside run_phase2_acceptance.sh.
```

Add to `skills/ru-editor/scripts/run_phase2_acceptance.sh` (insert before `section "1."`):

```bash
section "0. Version is 2.4.0"
if grep -q "version: 2.4.0" skills/ru-editor/SKILL.md; then
  echo "PASS: version bumped to 2.4.0"
else
  echo "FAIL: version is not 2.4.0"
  failures=$((failures + 1))
fi
```

And update `check_phase1.sh` section 10 to accept any 2.x.x ≥ 2.3.0:

In `skills/ru-editor/scripts/check_phase1.sh`, find:
```bash
if grep -q "version: 2.3.0" SKILL.md; then
  pass "SKILL.md frontmatter version is 2.3.0"
else
  fail "SKILL.md frontmatter version is not 2.3.0"
fi
```

Replace with:
```bash
ver=$(grep -E "^\s+version: [0-9]+\.[0-9]+\.[0-9]+" SKILL.md | head -1 | awk '{print $2}')
if [ -n "$ver" ]; then
  major=$(echo "$ver" | cut -d. -f1)
  minor=$(echo "$ver" | cut -d. -f2)
  if [ "$major" -ge 2 ] && { [ "$major" -gt 2 ] || [ "$minor" -ge 3 ]; }; then
    pass "SKILL.md frontmatter version is $ver (≥ 2.3.0)"
  else
    fail "SKILL.md frontmatter version $ver is below Phase 1 minimum 2.3.0"
  fi
else
  fail "SKILL.md frontmatter version not parseable"
fi
```

- [ ] **Step 15.5: Run master regression**

```bash
bash scripts/run_all_tests.sh
```

Expected: both phases PASS.

- [ ] **Step 15.6: Commit**

```bash
git add skills/ru-editor/SKILL.md \
        skills/ru-editor/CHANGELOG.md \
        skills/ru-editor/scripts/check_phase1.sh \
        skills/ru-editor/scripts/run_phase2_acceptance.sh
git commit -m "release(ru-editor): bump to v2.4.0 + CHANGELOG; relax Phase 1 version check"
```

---

## Task 16: Final master regression + sync + tag

**Files:**
- Sync: `skills/ru-editor/` → `~/.claude/skills/ru-editor/`

- [ ] **Step 16.1: Final regression run**

```bash
bash scripts/run_all_tests.sh
```

Expected: `ALL 2 PHASE(S) PASSED`.

- [ ] **Step 16.2: Verify branch state**

```bash
git status
git log main..HEAD --oneline
```

Expected: clean tree, ~12–15 commits ahead of main.

- [ ] **Step 16.3: Dry-run sync to global cache**

```bash
rsync -av --dry-run --delete \
  /Users/codegeek/src/agent-skills/skills/ru-editor/ \
  /Users/codegeek/.claude/skills/ru-editor/
```

Review output. Expected: new files (ru_lint.py, banned-markers.toml, scripts/tests/, run_phase2_acceptance.sh), modified SKILL.md and CHANGELOG.

- [ ] **Step 16.4: Confirm with user before destructive sync**

The `--delete` flag will remove anything in global not in source. Smoke-check what would be deleted.

```bash
rsync -av --dry-run --delete \
  /Users/codegeek/src/agent-skills/skills/ru-editor/ \
  /Users/codegeek/.claude/skills/ru-editor/ \
  | grep "^deleting"
```

Expected: empty or only `.DS_Store`.

- [ ] **Step 16.5: Run actual sync**

```bash
rsync -av --delete \
  /Users/codegeek/src/agent-skills/skills/ru-editor/ \
  /Users/codegeek/.claude/skills/ru-editor/
```

- [ ] **Step 16.6: Verify global is in sync**

```bash
diff -rq /Users/codegeek/src/agent-skills/skills/ru-editor/ \
         /Users/codegeek/.claude/skills/ru-editor/
```

Expected: empty output.

- [ ] **Step 16.7: Verify global SKILL.md version**

```bash
grep "version:" /Users/codegeek/.claude/skills/ru-editor/SKILL.md
```

Expected: `version: 2.4.0`.

- [ ] **Step 16.8: Smoke test in fresh CC session (manual, USER step)**

In a new CC session, invoke ru-editor on a short test text. Verify:
- Skill loads cleanly
- `## QA Gate` references the linter
- Output discipline observed
- Linter (if `Bash(python *)` permitted) runs cleanly on the output

If smoke test fails, fix on the same branch and re-run regression.

- [ ] **Step 16.9: Merge to main (after user confirms smoke test)**

```bash
git checkout main
git merge --ff-only ru-editor-v2.4-regex-linter
```

- [ ] **Step 16.10: Tag the release**

```bash
git tag -a ru-editor-v2.4.0 -m "ru-editor v2.4.0 — Phase 2 Regex Linter + Seed Corpus"
```

Don't push tag without user consent.

- [ ] **Step 16.11: Delete merged branch**

```bash
git branch -d ru-editor-v2.4-regex-linter
```

- [ ] **Step 16.12: Final regression on main**

```bash
bash scripts/run_all_tests.sh
```

Expected: `ALL 2 PHASE(S) PASSED`.

---

## Self-Review Notes

**Spec coverage check (against spec § 5 Phase 2):**

| Spec requirement | Plan task |
|---|---|
| `scripts/ru_lint.py` pure Python 3.11+, no deps | Tasks 2, 4–10 |
| 3 CLI modes (check/diff/both) | Task 6 |
| JSON output + schema versioning | Task 6 |
| Registry-based check architecture | Task 5 |
| HARD_FAIL / WARN taxonomy from spec | Tasks 8, 9, 10 |
| Two-mode (absolute + diff) architecture | Tasks 5, 8, 9 |
| Empirical grounding (30+ outputs, tagged) | Task 7 |
| `evals/seed-corpus/` (20–30 pairs) | Task 12 |
| Idempotency check | Task 12.5 + acceptance script section 3 |
| Length-ratio guard ±20% | Task 10 (`length_ratio_violation`) |
| QA Gate in SKILL.md → script | Task 14 |
| Acceptance: ≥90% recall on seed corpus | Task 13 (acceptance script) |
| 0 false-positives on own reference files | Task 13 (section 4) |
| <100 ms per 5K-char doc | Task 13 (section 5) |
| Code-span / meta-commentary exemption | Task 4 (Document.prose) + ignore directives |
| Banned markers single source of truth | Task 3 (TOML) |

All requirements covered.

**Placeholder scan:** No "TBD/TODO/implement later" in concrete code. Task 11 mentions «specific phrases TBD by grounding output» — this is intentional: the *process* is locked, the *content* is empirical. Task 7.2 is a USER step explicitly marked as such. Task 12.2 / 12.3 specify the **shape** of corpus content and a per-genre paradigm, but the actual prose is content work — analogous to Phase 1 Task 4 which gave exact replacements.

**Type consistency:** Severity is `Literal["HARD_FAIL", "WARN"]` everywhere; mode is `Literal["absolute", "diff"]`; run mode is `Literal["check", "diff", "both"]`. Document, Finding, Check, REGISTRY signatures defined in Tasks 4–5 and used consistently in Tasks 8–10. CLI argparse subcommands match `RunMode`.

**Open risks:**
- WARN heuristic checks (Task 10) are inherently fuzzy. Tuning will surface mismatches. Plan handles this via grounding feedback (Task 11) and explicit `WARN` severity (not blocking).
- Word-repetition stem (`_normalize_word`) is crude (drops 2 trailing chars). Without `pymorphy2` we can't do proper stemming. Acceptance for this check is "catches obvious cases, allows false positives <5% on seed corpus". If too noisy in seed corpus testing, demote check to opt-in.
- Synonym cluster drift requires word-boundary checks; Cyrillic word boundaries via `\b` work in Python `re` if we don't mix scripts. Tested in Task 10.
- Em dash budget treats list-items as own paragraphs. Already validated via Phase 1 smoke (`.development/tests/phase1-content-hygiene/01-basic-ai-slop/checks.sh`).

---

## Done Criteria

Phase 2 (v2.4.0) is complete when:

- [ ] `bash scripts/run_all_tests.sh` exits 0 with `ALL 2 PHASE(S) PASSED`.
- [ ] `python3 -m unittest discover skills/ru-editor/scripts/tests/ -v` shows all tests OK.
- [ ] `bash skills/ru-editor/scripts/run_phase2_acceptance.sh` exits 0 with all 5 (or 6, with version section) sections PASS.
- [ ] All 20 seed corpus pairs satisfy: source produces findings within `[hard_fail_min, hard_fail_max]`; expected.md produces 0 HARD_FAIL.
- [ ] All 7 reference files (`SKILL.md` + 6 `references/*.md`) lint clean (0 HARD_FAIL).
- [ ] Perf <100 ms per 5K-char document.
- [ ] `~/.claude/skills/ru-editor/` synced; `version: 2.4.0`.
- [ ] Manual smoke test in fresh CC session passes.
- [ ] Branch merged to main fast-forward.
- [ ] Tag `ru-editor-v2.4.0` created locally (not pushed).
- [ ] Phase 1 acceptance still passes (`bash skills/ru-editor/scripts/check_phase1.sh` exits 0).

After Phase 2 lands, proceed to Phase 3 (v2.5 — Modes + isolation). A new plan will be written for that phase, and `scripts/run_all_tests.sh` will gain a Phase 3 section.
