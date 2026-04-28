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


class ConfigError(Exception):
    """Raised when configuration files (mode-profiles.toml, etc.) fail validation."""


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


_DOUBLE_HYPHEN_RE = re.compile(r"(?<!-)--(?!-)")


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


# ---------------------------------------------------------------------------
# Diff-mode checks (Task 9): edited vs source — Factual Integrity + structure
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# WARN checks (Task 10): heuristic patterns informed by grounding.
# Group A: 7 plan-spec checks. Group B: 4 grounding-informed additions.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Group B — 4 grounding-informed WARN checks (not in plan baseline).
# ---------------------------------------------------------------------------


@register(name="no_warn_markers", severity="WARN", mode="absolute",
          description="WARN-маркеры из banned-markers.toml [warn_markers].")
def _check_no_warn_markers(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    markers = _load_banned_markers().get("warn_markers", {}).get("phrases", [])
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
                check="no_warn_markers", severity="WARN",
                line=line, col=col, match=phrase,
                context=_context_around(text, idx),
                message=f"WARN-маркер: «{phrase}». См. banned-markers.toml [warn_markers].",
            ))
            start = idx + len(p_lower)
    return out


# Line-leading bullet patterns. Use doc.raw because doc.prose strips list-item
# prefixes that we want to inspect, and code blocks are stripped from prose
# entirely; we need the as-authored markdown for structural list checks.
_ARROW_BULLET_RE = re.compile(r"^[ \t]*[→⇒➜▶►][ \t]+", re.MULTILINE)


@register(name="arrows_as_bullets", severity="WARN", mode="absolute",
          description="Стрелка в начале строки списка — типичный AI-маркер форматирования.")
def _check_arrows_as_bullets(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    for m in _ARROW_BULLET_RE.finditer(doc.raw):
        line, col = _line_col_of(doc.raw, m.start())
        out.append(Finding(
            check="arrows_as_bullets", severity="WARN",
            line=line, col=col, match=m.group(0).strip(),
            context=_context_around(doc.raw, m.start(), 60),
            message="Стрелка как буллет в списке. Используйте «-», «*» или нумерацию.",
        ))
    return out


_CHECKMARK_BULLET_RE = re.compile(r"^[ \t]*[✅✓⭐][ \t]+", re.MULTILINE)


@register(name="checkmark_as_bullet", severity="WARN", mode="absolute",
          description="Чекмарк/звезда как маркер списка — AI-форматный шаблон.")
def _check_checkmark_as_bullet(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    out: list[Finding] = []
    matches = list(_CHECKMARK_BULLET_RE.finditer(doc.raw))
    if matches:
        m = matches[0]
        line, col = _line_col_of(doc.raw, m.start())
        out.append(Finding(
            check="checkmark_as_bullet", severity="WARN",
            line=line, col=col, match=m.group(0).strip(),
            context=f"{len(matches)} такие(их) строки в документе",
            message=f"Чекмарк/звезда как буллет ({len(matches)} строк). Используйте обычный маркер списка.",
        ))
    return out


@register(name="intensifier_burst", severity="WARN", mode="absolute",
          description="3+ интенсификатора в окне 200 символов — стилистический шум.")
def _check_intensifier_burst(doc: Document, source: Document | None, ctx: dict) -> list[Finding]:
    clusters = _load_banned_markers().get("synonym_clusters", {})
    intensifiers = list(clusters.get("intensifier_drift", [])) + list(clusters.get("emphasis_drift", []))
    if not intensifiers:
        return []
    text_lower = doc.prose.lower()
    positions: list[tuple[int, str]] = []
    for w in intensifiers:
        wl = w.lower()
        start = 0
        while True:
            idx = text_lower.find(wl, start)
            if idx < 0:
                break
            before = text_lower[idx - 1] if idx > 0 else " "
            after = text_lower[idx + len(wl)] if idx + len(wl) < len(text_lower) else " "
            if not (before.isalpha() or after.isalpha()):
                positions.append((idx, w))
            start = idx + len(wl)
    positions.sort()
    out: list[Finding] = []
    for i in range(len(positions) - 2):
        if positions[i + 2][0] - positions[i][0] <= 200:
            idx = positions[i][0]
            line, col = _line_col_of(doc.prose, idx)
            words_in_window = sorted({w for pos, w in positions[i:i + 3]})
            out.append(Finding(
                check="intensifier_burst", severity="WARN",
                line=line, col=col, match="intensifier_burst",
                context=", ".join(words_in_window),
                message=f"3+ интенсификатора в окне 200 симв.: {words_in_window}. Уменьшите эмфазу.",
            ))
            break  # one finding per document
    return out


if __name__ == "__main__":
    sys.exit(main())
