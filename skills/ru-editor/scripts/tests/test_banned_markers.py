"""Validate banned-markers.toml structure and content invariants."""
import unittest
import tomllib
from pathlib import Path

REFS = Path(__file__).resolve().parents[2] / "references"
TOML_PATH = REFS / "banned-markers.toml"


class TestBannedMarkersToml(unittest.TestCase):
    def setUp(self):
        with open(TOML_PATH, "rb") as f:
            self.data = tomllib.load(f)

    def test_meta_schema_version(self):
        self.assertEqual(self.data["meta"]["schema_version"], "1.0")

    def test_hard_fail_phrases_locked(self):
        """The five Phase-1-locked HARD_FAIL markers must be present."""
        phrases = set(self.data["hard_fail_markers"]["phrases"])
        for required in [
            "погружаемся",
            "погрузимся",
            "ландшафт",
            "гобелен",
            "является свидетельством",
            "стоит отметить",
        ]:
            self.assertIn(required, phrases, f"missing locked HARD_FAIL marker: {required}")

    def test_no_duplicate_phrases_within_section(self):
        for section in ("hard_fail_markers", "warn_markers"):
            phrases = self.data.get(section, {}).get("phrases", [])
            self.assertEqual(len(phrases), len(set(phrases)),
                             f"duplicate phrases in {section}")

    def test_synonym_clusters_have_minimum_size(self):
        for name, words in self.data.get("synonym_clusters", {}).items():
            self.assertGreaterEqual(len(words), 2,
                                    f"synonym cluster {name} must have ≥2 members")

    def test_no_marker_collisions_across_sections(self):
        hard = set(self.data.get("hard_fail_markers", {}).get("phrases", []))
        warn = set(self.data.get("warn_markers", {}).get("phrases", []))
        self.assertEqual(hard & warn, set(),
                         "phrases must not appear in both hard_fail and warn")


if __name__ == "__main__":
    unittest.main()
