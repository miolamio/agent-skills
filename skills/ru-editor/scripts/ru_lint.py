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
from typing import Callable, Literal


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


# ---------------------------------------------------------------------------
# CLI — argparse + JSON output schema v1 + exit codes
# ---------------------------------------------------------------------------

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


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--format", choices=("human", "json"), default="human",
                        help="output format (default: human)")
    common.add_argument("--strict", action="store_true",
                        help="exit non-zero on WARN findings as well (default: only HARD_FAIL)")

    parser = argparse.ArgumentParser(
        prog="ru_lint",
        description="ru_lint — deterministic regex linter for Russian text edited by ru-editor.",
        parents=[common],
    )
    parser.add_argument("--version", action="version",
                        version=f"ru_lint {__version__} (schema {SCHEMA_VERSION})")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="absolute checks on edited file", parents=[common])
    p_check.add_argument("edited", help="path to edited.md")

    p_diff = sub.add_parser("diff", help="diff checks (orig vs edited)", parents=[common])
    p_diff.add_argument("source", help="path to original")
    p_diff.add_argument("edited", help="path to edited")

    p_both = sub.add_parser("both", help="absolute + diff checks (default semantics)", parents=[common])
    p_both.add_argument("source", help="path to original")
    p_both.add_argument("edited", help="path to edited")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
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


# ---------------------------------------------------------------------------
# Phase-1-locked absolute checks (Task 8)
# ---------------------------------------------------------------------------

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
            message="Прямая кавычка в русском тексте. Используйте «» для основных, „“ для вложенных.",
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


if __name__ == "__main__":
    sys.exit(main())
