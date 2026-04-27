"""Tests for the CLI: argparse + JSON output schema + exit codes."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
RU_LINT = SCRIPTS_DIR / "ru_lint.py"


def run_cli(*args, input_text: str | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(RU_LINT), *args]
    return subprocess.run(cmd, capture_output=True, text=True, input=input_text, timeout=10)


class TestCliBasic(unittest.TestCase):
    def test_help_runs(self):
        result = run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("ru_lint", result.stdout.lower() + result.stderr.lower())

    def test_version_runs(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("0.", result.stdout)

    def test_check_subcommand_help(self):
        result = run_cli("check", "--help")
        self.assertEqual(result.returncode, 0)


class TestCliCheckMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name: str, content: str) -> Path:
        p = self.tmpdir / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_check_clean_text_exits_zero(self):
        f = self._write("clean.md", "# Заголовок\n\nЧистый текст без проблем.\n")
        result = run_cli("check", str(f))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_check_json_output_has_schema_version(self):
        f = self._write("clean.md", "# H\n\nText.\n")
        result = run_cli("check", str(f), "--format", "json")
        data = json.loads(result.stdout)
        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(data["tool"], "ru_lint")
        self.assertIn("tool_version", data)
        self.assertEqual(data["mode"], "check")
        self.assertEqual(data["input_path"], str(f))
        self.assertIsNone(data["source_path"])
        self.assertIn("summary", data)
        self.assertIn("findings", data)
        self.assertEqual(data["summary"]["hard_fail_count"], 0)
        self.assertEqual(data["summary"]["warn_count"], 0)
        self.assertIn("elapsed_ms", data["summary"])


class TestCliErrors(unittest.TestCase):
    def test_diff_without_source_errors(self):
        result = run_cli("diff", "/nonexistent.md")
        self.assertNotEqual(result.returncode, 0)

    def test_check_missing_file_errors(self):
        result = run_cli("check", "/nonexistent.md")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
