---
name: krrkt
description: >
  Check Russian text quality using the krrkt CLI tool — gives an objective 0-10 score
  with categorized findings. Use when: (1) user writes or edits Russian text and asks to
  check quality, (2) user says "проверь качество текста", "проверка качества", "стоп-слова",
  "krrkt", "check text quality", (3) user asks to score Russian writing style,
  (4) user opens a Russian .md/.txt file and asks for quality feedback,
  (5) user asks you to write Russian text — check it with krrkt before delivering.
  Requires krrkt CLI (pip install krrkt). NOT for English text, translation,
  or spelling/grammar (use ru-textovod for that).
license: MIT
metadata:
  author: Anthony Vdovitchenko @ Automatica (https://t.me/aiwizards)
  version: 0.1.0
  category: proofreading
---

# krrkt — Russian Text Quality Checker

CLI tool that scores Russian text 0-10 and flags stop words, stamps, bureaucratese, and other informational style issues. 1200+ pattern dictionary, Glvrd-compatible scoring.

## Quick check

```bash
krrkt check --no-llm "Text to check"
```

Always use `--no-llm` (instant, no API needed). For files: `krrkt check --no-llm /path/to/file.txt`.

JSON output: `krrkt check --no-llm --format json "Text"`

Score only: `krrkt score --no-llm "Text"`

## Score: 7.5+ green, 5-7.4 orange, below 5 red

## Workflow

**Checking existing text:** Run `krrkt check --no-llm`, show the score and key findings (weight 80+). Suggest fixes based on finding descriptions. krrkt already categorizes issues — use its output directly rather than re-analyzing from scratch.

**Writing new Russian text:** Write it, then run `krrkt check --no-llm` on your output. If score is below 7, fix the flagged issues and re-check. Deliver the final version with the score.

**Checking .md files:** Extract prose only — skip YAML frontmatter, code blocks, HTML, markdown syntax.

**Batch:** `for f in *.md; do echo "=== $f ===" && krrkt score --no-llm "$f"; done`

## Interpreting findings

krrkt output is self-explanatory: each finding has a rule name, weight, and often a description with fix advice. Focus on `■` markers (weight 80-100) — those are the real problems. `▲` (1-79) are suggestions. `○` (0) are informational.

The `description` field in JSON output often contains the specific fix (e.g., "Замените на «общение»" for pompous words). Use it.

## Install

If `krrkt` is not found: `pip install krrkt` or `uvx krrkt check --no-llm "test"`.
