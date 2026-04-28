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
        # Input has two straight double-quotes → two findings (opening + closing).
        self.assertGreaterEqual(len(f), 1)
        self.assertEqual(f[0].severity, "HARD_FAIL")

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

    def test_yaml_frontmatter_separator_no_fire(self):
        text = "---\nname: foo\ndescription: bar\n---\n\nТекст документа."
        f = lint_check(text, "no_double_hyphen")
        self.assertEqual(f, [])

    def test_markdown_table_separator_no_fire(self):
        text = "| Колонка | Значение |\n|---|---|\n| A | 1 |"
        f = lint_check(text, "no_double_hyphen")
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
