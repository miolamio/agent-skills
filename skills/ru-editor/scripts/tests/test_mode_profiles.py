"""Phase 3: mode-profiles.toml loader and schema validation."""
import unittest
from pathlib import Path
import tempfile
import textwrap
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ru_lint


class TestModeProfilesLoader(unittest.TestCase):
    def test_loads_all_four_modes_from_canonical_file(self):
        profiles = ru_lint._load_mode_profiles()
        self.assertIn("proofread", profiles)
        self.assertIn("line_edit", profiles)
        self.assertIn("technical", profiles)
        self.assertIn("deep_rewrite", profiles)

    def test_canonical_proofread_bounds(self):
        profiles = ru_lint._load_mode_profiles()
        p = profiles["proofread"]
        self.assertAlmostEqual(p["length_ratio_min"], 0.95)
        self.assertAlmostEqual(p["length_ratio_max"], 1.05)
        self.assertAlmostEqual(p["list_items_tolerance"], 0.05)

    def test_canonical_line_edit_bounds(self):
        profiles = ru_lint._load_mode_profiles()
        p = profiles["line_edit"]
        self.assertAlmostEqual(p["length_ratio_min"], 0.70)
        self.assertAlmostEqual(p["length_ratio_max"], 1.15)
        self.assertAlmostEqual(p["list_items_tolerance"], 0.30)

    def test_canonical_deep_rewrite_disabled_bounds(self):
        profiles = ru_lint._load_mode_profiles()
        p = profiles["deep_rewrite"]
        self.assertEqual(p["length_ratio_min"], 0.0)
        self.assertGreaterEqual(p["length_ratio_max"], 99.0)
        self.assertEqual(p["list_items_tolerance"], 1.0)

    def test_missing_mode_raises_config_error(self):
        bad = textwrap.dedent("""
            schema_version = "1.0"
            [modes.proofread]
            length_ratio_min = 0.95
            length_ratio_max = 1.05
            list_items_tolerance = 0.05
        """).strip()
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(bad)
            path = f.name
        with self.assertRaises(ru_lint.ConfigError) as cm:
            ru_lint._load_mode_profiles(path=path)
        self.assertIn("missing mode", str(cm.exception))

    def test_schema_version_mismatch_raises_config_error(self):
        bad = textwrap.dedent("""
            schema_version = "2.0"
            [modes.proofread]
            length_ratio_min = 0.95
            length_ratio_max = 1.05
            list_items_tolerance = 0.05
            [modes.line_edit]
            length_ratio_min = 0.70
            length_ratio_max = 1.15
            list_items_tolerance = 0.30
            [modes.technical]
            length_ratio_min = 0.90
            length_ratio_max = 1.10
            list_items_tolerance = 0.10
            [modes.deep_rewrite]
            length_ratio_min = 0.0
            length_ratio_max = 99.0
            list_items_tolerance = 1.0
        """).strip()
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(bad)
            path = f.name
        with self.assertRaises(ru_lint.ConfigError) as cm:
            ru_lint._load_mode_profiles(path=path)
        self.assertIn("schema_version", str(cm.exception))

    def test_malformed_toml_raises_config_error(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("not = valid = toml ===")
            path = f.name
        with self.assertRaises(ru_lint.ConfigError):
            ru_lint._load_mode_profiles(path=path)


if __name__ == "__main__":
    unittest.main()
