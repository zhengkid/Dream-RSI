import json
import unittest
from pathlib import Path

from scripts.doj_nsd_repo_mapper import classify_item, repo_domains, assess

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "compliance" / "repo-risk-map.json").read_text(encoding="utf-8"))


class DOJNSDRepoMapperTests(unittest.TestCase):
    def test_export_announcement_classification(self):
        item = {"title": "Company charged with illegally exporting aerospace technology", "url": "https://www.justice.gov/example"}
        self.assertIn("export_controls", classify_item(item, CONFIG))

    def test_fara_announcement_classification(self):
        item = {"title": "Foreign Agents Registration Act FARA enforcement update", "url": "https://www.justice.gov/example"}
        self.assertIn("fara_foreign_influence", classify_item(item, CONFIG))

    def test_repo_domain_mapping(self):
        repo = {"name": "NASA-3D-ResourcesXUNIA-", "description": "space resources", "topics": ["aerospace"]}
        domains = repo_domains(repo, CONFIG)
        self.assertIn("export_controls", domains)

    def test_review_requires_overlap(self):
        repos = [{"name": "SpaceX-APIxunia", "full_name": "sonoxo/SpaceX-APIxunia", "description": "space API", "topics": [], "private": False, "archived": False}]
        items = [{"source": "export_controls", "title": "Aerospace export control prosecution", "url": "https://www.justice.gov/example"}]
        result = assess(repos, items, CONFIG)[0]
        self.assertEqual(result["decision"], "REVIEW")
        self.assertEqual(result["severity"], "high")

    def test_no_overlap_is_pass(self):
        repos = [{"name": "music-site", "full_name": "sonoxo/music-site", "description": "artist portfolio", "topics": [], "private": False, "archived": False}]
        items = [{"source": "export_controls", "title": "Aerospace export control prosecution", "url": "https://www.justice.gov/example"}]
        result = assess(repos, items, CONFIG)[0]
        self.assertEqual(result["decision"], "PASS")


if __name__ == "__main__":
    unittest.main()
