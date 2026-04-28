"""Smoke test: module imports and exposes basic constants."""
import unittest
import sys
from pathlib import Path

# Make ru_lint importable when running tests from any cwd.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))


class TestSmoke(unittest.TestCase):
    def test_imports(self):
        import ru_lint
        self.assertEqual(ru_lint.SCHEMA_VERSION, "1.1")
        self.assertTrue(hasattr(ru_lint, "__version__"))


if __name__ == "__main__":
    unittest.main()
