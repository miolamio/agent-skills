"""Phase 3: CLI --mode flag, JSON schema bump, exit codes."""
import json
import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

RU_LINT = Path(__file__).resolve().parent.parent / "ru_lint.py"


def _run(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RU_LINT), *args],
        capture_output=True, text=True, cwd=cwd,
    )


class TestCliModeFlag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = Path(self.tmp.name) / "source.md"
        self.edt = Path(self.tmp.name) / "edited.md"
        self.src.write_text("Это нейтральный исходник.\n", encoding="utf-8")
        self.edt.write_text("Это нейтральный текст.\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_mode_auto_is_default_and_matches_phase2_behaviour(self):
        r = _run(["check", str(self.edt), "--format", "json"])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["summary"].get("mode"), "auto")
        self.assertEqual(payload["schema_version"], "1.1")

    def test_mode_explicit_line_edit_exposes_in_json(self):
        r = _run(["check", str(self.edt), "--format", "json", "--mode", "line_edit"])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["summary"]["mode"], "line_edit")

    def test_mode_proofread_strict_length_in_diff(self):
        # 25-char source vs 5-char edited => ratio = 0.20, proofread bounds [0.95, 1.05]
        r = _run([
            "diff", str(self.src), str(self.edt),
            "--format", "json", "--mode", "proofread",
        ])
        payload = json.loads(r.stdout)
        names = [f["check"] for f in payload["findings"]]
        self.assertIn("length_ratio_violation", names)

    def test_unknown_mode_returns_exit_3(self):
        r = _run(["check", str(self.edt), "--mode", "aggressive"])
        self.assertEqual(r.returncode, 3)
        self.assertIn("aggressive", (r.stderr + r.stdout).lower())

    def test_malformed_profiles_file_returns_exit_3(self):
        bad = Path(self.tmp.name) / "bad-profiles.toml"
        bad.write_text("not = valid = toml ===", encoding="utf-8")
        env = os.environ.copy()
        env["RU_LINT_MODE_PROFILES"] = str(bad)
        r = subprocess.run(
            [sys.executable, str(RU_LINT), "check", str(self.edt), "--mode", "line_edit"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r.returncode, 3)


if __name__ == "__main__":
    unittest.main()
