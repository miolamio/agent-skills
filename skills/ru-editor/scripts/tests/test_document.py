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

    def test_numeric_tokens_thousands_space(self):
        # «10 000» (Russian thousands separator) → canonical «10000».
        doc = Document(text="В таблице более 10 000 строк.")
        self.assertEqual(doc.numeric_tokens, {"10000"})

    def test_numeric_tokens_thousands_comma(self):
        # «10,000» (English thousands) → canonical «10000».
        doc = Document(text="The table has more than 10,000 rows.")
        self.assertEqual(doc.numeric_tokens, {"10000"})

    def test_numeric_tokens_decimal_comma(self):
        # «3,14» (Russian decimal) → canonical «3.14».
        doc = Document(text="Число пи примерно равно 3,14.")
        self.assertEqual(doc.numeric_tokens, {"3.14"})

    def test_numeric_tokens_thousands_and_decimal(self):
        # «1 234,56» → «1234.56»; «1,000,000» → «1000000».
        doc = Document(text="Сумма 1 234,56 рублей; население 1,000,000.")
        self.assertEqual(doc.numeric_tokens, {"1234.56", "1000000"})

    def test_numeric_tokens_thousands_typography_diff_normalized(self):
        # Source uses «10,000»; edited uses «10 000» — same token after canon.
        src = Document(text="Более 10,000 строк.")
        edt = Document(text="Более 10 000 строк.")
        self.assertEqual(src.numeric_tokens, edt.numeric_tokens)

    def test_numeric_tokens_short_decimal_not_grouped(self):
        # «10,5» — Russian decimal (only 1-2 digits after comma) → «10.5», not stripped.
        doc = Document(text="Размер 10,5 МБ.")
        self.assertEqual(doc.numeric_tokens, {"10.5"})


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
