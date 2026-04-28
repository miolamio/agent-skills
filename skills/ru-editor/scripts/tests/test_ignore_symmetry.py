"""Phase 3: backlog #5 — ignore-directives respected on both diff sides."""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ru_lint
from ru_lint import Document, run_checks


CTX_AUTO = {"lint_mode": "auto", "profile": None}


class TestIgnoreSymmetry(unittest.TestCase):
    def test_url_inside_ignore_block_not_extracted(self):
        text = (
            "before\n"
            "<!-- ru-lint:ignore-start -->\n"
            "see https://example.com/secret for details\n"
            "<!-- ru-lint:ignore-end -->\n"
            "after\n"
        )
        doc = Document(text=text)
        self.assertEqual(doc.urls, [])

    def test_url_outside_ignore_block_extracted(self):
        text = (
            "see https://public.example.com here\n"
        )
        doc = Document(text=text)
        self.assertEqual(doc.urls, ["https://public.example.com"])

    def test_urls_preserved_does_not_flag_ignored_url_loss(self):
        # URL only in source's ignored region; edited drops the entire frontmatter
        src_text = (
            "<!-- ru-lint:ignore-start -->\n"
            "url: https://internal.example.com\n"
            "<!-- ru-lint:ignore-end -->\n"
            "Body text.\n"
        )
        edt_text = "Body text.\n"
        src = Document(text=src_text)
        edt = Document(text=edt_text)
        findings = run_checks(edt, src, "diff", CTX_AUTO)
        for f in findings:
            self.assertNotEqual(
                f.check, "urls_preserved",
                msg=f"unexpected urls_preserved finding: {f}",
            )

    def test_code_span_inside_ignore_block_not_extracted(self):
        text = (
            "<!-- ru-lint:ignore-line -->\n"
            "do not lint `secret_token`\n"
            "and `public_token` is fine\n"
        )
        doc = Document(text=text)
        # ignore-line covers the next non-empty line
        self.assertNotIn("secret_token", doc.code_spans)
        self.assertIn("public_token", doc.code_spans)

    def test_heading_inside_ignore_block_not_counted(self):
        text = (
            "<!-- ru-lint:ignore-start -->\n"
            "## Hidden Heading\n"
            "<!-- ru-lint:ignore-end -->\n"
            "## Real Heading\n"
        )
        doc = Document(text=text)
        self.assertEqual(len(doc.headings), 1)
        self.assertEqual(doc.headings[0][1], "Real Heading")

    def test_list_items_inside_ignore_block_not_counted(self):
        text = (
            "<!-- ru-lint:ignore-start -->\n"
            "- hidden 1\n"
            "- hidden 2\n"
            "<!-- ru-lint:ignore-end -->\n"
            "- real 1\n"
            "- real 2\n"
            "- real 3\n"
        )
        doc = Document(text=text)
        self.assertEqual(len(doc.list_items), 3)

    def test_list_items_count_does_not_flag_ignored_drop(self):
        # source has 3 items inside ignore + 4 real; edited preserves only the 4 real
        src_text = (
            "<!-- ru-lint:ignore-start -->\n"
            "- a\n- b\n- c\n"
            "<!-- ru-lint:ignore-end -->\n"
            "- one\n- two\n- three\n- four\n"
        )
        edt_text = "- one\n- two\n- three\n- four\n"
        src = Document(text=src_text)
        edt = Document(text=edt_text)
        findings = run_checks(edt, src, "diff", CTX_AUTO)
        for f in findings:
            self.assertNotEqual(f.check, "list_items_count_within_tolerance")


if __name__ == "__main__":
    unittest.main()
