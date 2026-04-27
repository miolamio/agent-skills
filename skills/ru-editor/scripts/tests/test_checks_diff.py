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
