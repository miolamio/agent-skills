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


# ---------------------------------------------------------------------------
# Group A — 7 plan-spec WARN checks
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Group B — 4 grounding-informed checks
# ---------------------------------------------------------------------------


class TestNoWarnMarkers(unittest.TestCase):
    def test_warn_marker_fires(self):
        # "не упустите шанс" is in TOML warn_markers.
        f = lint_check("Не упустите шанс присоединиться к нам.", "no_warn_markers")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_clean_text_no_fire(self):
        f = lint_check("Обычное предложение без шаблонов.", "no_warn_markers")
        self.assertEqual(f, [])


class TestArrowsAsBullets(unittest.TestCase):
    def test_arrow_bullet_fires(self):
        text = "Преимущества:\n→ Скорость\n→ Простота\n"
        f = lint_check(text, "arrows_as_bullets")
        self.assertEqual(len(f), 2)
        self.assertEqual(f[0].severity, "WARN")

    def test_dash_bullet_no_fire(self):
        text = "Преимущества:\n- Скорость\n- Простота\n"
        f = lint_check(text, "arrows_as_bullets")
        self.assertEqual(f, [])


class TestCheckmarkAsBullet(unittest.TestCase):
    def test_checkmark_fires(self):
        text = "Релиз:\n✅ Скорость\n✅ Простота\n"
        f = lint_check(text, "checkmark_as_bullet")
        self.assertEqual(len(f), 1)

    def test_no_checkmark_no_fire(self):
        text = "Релиз:\n- Скорость\n- Простота\n"
        f = lint_check(text, "checkmark_as_bullet")
        self.assertEqual(f, [])


class TestIntensifierBurst(unittest.TestCase):
    def test_three_intensifiers_warn(self):
        text = "Мы полностью переосмыслили интерфейс. Совершенно новый дизайн. Принципиально иной подход."
        f = lint_check(text, "intensifier_burst")
        self.assertEqual(len(f), 1)

    def test_one_intensifier_no_warn(self):
        text = "Мы полностью переосмыслили интерфейс. Хороший дизайн. Удобный подход."
        f = lint_check(text, "intensifier_burst")
        self.assertEqual(f, [])


if __name__ == "__main__":
    unittest.main()
