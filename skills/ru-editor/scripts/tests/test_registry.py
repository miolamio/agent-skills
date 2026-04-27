"""Tests for the check registry and Finding dataclass."""
import unittest
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import ru_lint  # noqa: E402
from ru_lint import Document, Finding, register, REGISTRY  # noqa: E402


class TestFinding(unittest.TestCase):
    def test_finding_construction(self):
        f = Finding(
            check="x",
            severity="HARD_FAIL",
            line=12,
            col=3,
            match="→",
            context="foo → bar",
            message="arrow not allowed",
        )
        self.assertEqual(f.check, "x")
        self.assertEqual(f.severity, "HARD_FAIL")
        self.assertEqual(f.line, 12)

    def test_finding_to_dict(self):
        f = Finding(check="x", severity="WARN", line=1, col=0,
                    match="!", context="!", message="m")
        d = f.to_dict()
        self.assertEqual(d["check"], "x")
        self.assertEqual(d["severity"], "WARN")
        self.assertEqual(d["line"], 1)


class TestRegistry(unittest.TestCase):
    def setUp(self):
        # Snapshot the registry; restore after each test.
        self._snapshot = dict(REGISTRY)

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._snapshot)

    def test_register_decorator_adds_to_registry(self):
        REGISTRY.clear()

        @register(name="sample", severity="HARD_FAIL", mode="absolute",
                  description="sample check")
        def sample_check(doc: Document, source: Document | None, ctx: dict):
            return []

        self.assertIn("sample", REGISTRY)
        self.assertEqual(REGISTRY["sample"].severity, "HARD_FAIL")
        self.assertEqual(REGISTRY["sample"].mode, "absolute")

    def test_register_invalid_severity_rejected(self):
        REGISTRY.clear()
        with self.assertRaises(ValueError):
            @register(name="bad", severity="CRITICAL", mode="absolute", description="x")
            def bad(doc, source, ctx):
                return []

    def test_register_invalid_mode_rejected(self):
        REGISTRY.clear()
        with self.assertRaises(ValueError):
            @register(name="bad", severity="WARN", mode="weird", description="x")
            def bad(doc, source, ctx):
                return []

    def test_register_duplicate_name_rejected(self):
        REGISTRY.clear()

        @register(name="dup", severity="WARN", mode="absolute", description="x")
        def first(doc, source, ctx):
            return []

        with self.assertRaises(ValueError):
            @register(name="dup", severity="WARN", mode="absolute", description="x")
            def second(doc, source, ctx):
                return []


class TestRunChecks(unittest.TestCase):
    def setUp(self):
        self._snapshot = dict(REGISTRY)
        REGISTRY.clear()

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._snapshot)

    def test_run_checks_invokes_absolute_in_check_mode(self):
        @register(name="abs1", severity="HARD_FAIL", mode="absolute", description="x")
        def abs1(doc, source, ctx):
            return [Finding(check="abs1", severity="HARD_FAIL",
                            line=1, col=0, match="!", context="!", message="abs1 fired")]

        doc = Document(text="hello")
        findings = ru_lint.run_checks(doc, source=None, mode="check")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].check, "abs1")

    def test_run_checks_skips_diff_in_check_mode(self):
        @register(name="diff1", severity="HARD_FAIL", mode="diff", description="x")
        def diff1(doc, source, ctx):
            return [Finding(check="diff1", severity="HARD_FAIL",
                            line=1, col=0, match="!", context="!", message="diff1 fired")]

        doc = Document(text="hello")
        findings = ru_lint.run_checks(doc, source=None, mode="check")
        self.assertEqual(findings, [])

    def test_run_checks_diff_mode_requires_source(self):
        with self.assertRaises(ValueError):
            ru_lint.run_checks(Document(text="x"), source=None, mode="diff")

    def test_run_checks_both_mode_runs_all(self):
        @register(name="abs1", severity="HARD_FAIL", mode="absolute", description="x")
        def abs1(doc, source, ctx):
            return [Finding(check="abs1", severity="HARD_FAIL",
                            line=1, col=0, match="!", context="!", message="m")]

        @register(name="diff1", severity="HARD_FAIL", mode="diff", description="x")
        def diff1(doc, source, ctx):
            return [Finding(check="diff1", severity="HARD_FAIL",
                            line=1, col=0, match="!", context="!", message="m")]

        doc = Document(text="a")
        src = Document(text="b")
        findings = ru_lint.run_checks(doc, source=src, mode="both")
        names = sorted(f.check for f in findings)
        self.assertEqual(names, ["abs1", "diff1"])


if __name__ == "__main__":
    unittest.main()
