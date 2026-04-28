"""Phase 3: per-mode bounds for length_ratio_violation."""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ru_lint
from ru_lint import Document, run_checks


def _docs(src_text: str, edt_text: str) -> tuple[Document, Document]:
    return Document(text=src_text), Document(text=edt_text)


def _has_length_violation(findings) -> bool:
    return any(f.check == "length_ratio_violation" for f in findings)


def _ctx_for_mode(name: str) -> dict:
    profile = ru_lint._load_mode_profiles()[name]
    return {"lint_mode": name, "profile": profile}


class TestLengthRatioPerMode(unittest.TestCase):
    def test_proofread_within_bounds(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 100)  # ratio 1.0
        findings = run_checks(edt, src, "diff", _ctx_for_mode("proofread"))
        self.assertFalse(_has_length_violation(findings))

    def test_proofread_above_bounds(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 110)  # ratio 1.10 > 1.05
        findings = run_checks(edt, src, "diff", _ctx_for_mode("proofread"))
        self.assertTrue(_has_length_violation(findings))

    def test_proofread_below_bounds(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 90)  # ratio 0.90 < 0.95
        findings = run_checks(edt, src, "diff", _ctx_for_mode("proofread"))
        self.assertTrue(_has_length_violation(findings))

    def test_line_edit_within_bounds_at_70_floor(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 75)  # ratio 0.75 inside [0.70, 1.15]
        findings = run_checks(edt, src, "diff", _ctx_for_mode("line_edit"))
        self.assertFalse(_has_length_violation(findings))

    def test_line_edit_below_70_floor(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 60)  # ratio 0.60 < 0.70
        findings = run_checks(edt, src, "diff", _ctx_for_mode("line_edit"))
        self.assertTrue(_has_length_violation(findings))

    def test_line_edit_above_115_ceiling(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 120)  # ratio 1.20 > 1.15
        findings = run_checks(edt, src, "diff", _ctx_for_mode("line_edit"))
        self.assertTrue(_has_length_violation(findings))

    def test_technical_within_bounds(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 95)  # ratio 0.95 inside [0.90, 1.10]
        findings = run_checks(edt, src, "diff", _ctx_for_mode("technical"))
        self.assertFalse(_has_length_violation(findings))

    def test_technical_above_bounds(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 115)  # ratio 1.15 > 1.10
        findings = run_checks(edt, src, "diff", _ctx_for_mode("technical"))
        self.assertTrue(_has_length_violation(findings))

    def test_technical_below_bounds(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 80)  # ratio 0.80 < 0.90
        findings = run_checks(edt, src, "diff", _ctx_for_mode("technical"))
        self.assertTrue(_has_length_violation(findings))

    def test_deep_rewrite_disables_length_check(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 10)  # ratio 0.10
        findings = run_checks(edt, src, "diff", _ctx_for_mode("deep_rewrite"))
        self.assertFalse(_has_length_violation(findings))

    def test_deep_rewrite_disables_even_for_expansion(self):
        src = Document(text="а" * 100)
        edt = Document(text="а" * 5000)  # ratio 50.0
        findings = run_checks(edt, src, "diff", _ctx_for_mode("deep_rewrite"))
        self.assertFalse(_has_length_violation(findings))

    def test_auto_mode_uses_phase2_globals(self):
        # ratio 0.85 — inside Phase 2 globals [0.80, 1.20], outside line_edit floor 0.70 only matters
        src = Document(text="а" * 100)
        edt = Document(text="а" * 85)
        findings_auto = run_checks(edt, src, "diff", {"lint_mode": "auto", "profile": None})
        self.assertFalse(_has_length_violation(findings_auto))


if __name__ == "__main__":
    unittest.main()
