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
