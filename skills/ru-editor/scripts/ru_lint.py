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

import re
from dataclasses import dataclass
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

_URL_TRAILING_PUNCT = ".,;:!?"


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
        # Trailing sentence punctuation is stripped so "URL." doesn't capture the period.
        return [m.group(0).rstrip(_URL_TRAILING_PUNCT) for m in _URL_RE.finditer(self.text)]

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
