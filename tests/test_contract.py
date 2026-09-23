# -*- coding: utf-8 -*-
"""Offline contract for the published news-monitor methodology."""
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = ROOT / "pipeline"
CONFIG = yaml.safe_load((PIPELINE_DIR / "config.yaml").read_text(encoding="utf-8"))
PROJECT_ID = CONFIG["project"]["id"]
PIPELINE_FILE = PIPELINE_DIR / f"{PROJECT_ID.replace('-', '_')}_pipeline.py"

sys.path.insert(0, str(PIPELINE_DIR))
spec = importlib.util.spec_from_file_location("product_pipeline", PIPELINE_FILE)
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

import data_fetcher


class ProductContractTests(unittest.TestCase):
    def test_published_snapshot_matches_product_contract(self):
        payload = json.loads((ROOT / "data" / "output.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["meta"]["project"], PROJECT_ID)
        self.assertIn(payload["meta"]["mode"], {"live", "partial", "unavailable"})
        self.assertEqual(payload["meta"]["methodology"]["scope"], "topical news sample")
        self.assertEqual(len(payload["stats"]), 2)
        self.assertNotIn("entities", payload)
        self.assertNotIn("timeseries", payload)
        self.assertLessEqual(len(payload["events"]), pipeline.EVENT_LIMIT)
        for event in payload["events"]:
            self.assertTrue(event.get("title"))
            self.assertTrue(event.get("url"))
            self.assertNotIn("tone", event)

    def test_keyless_refresh_retains_recent_snapshot_only(self):
        article = {
            "title": "Linked public article",
            "url": "https://example.org/article",
            "domain": "example.org",
            "publisher": "Example",
            "seendate": "20260923T120000Z",
        }
        previous = {
            "meta": {"generated": datetime.now(timezone.utc).isoformat()},
            "live_data": {"news_articles": [article]},
        }
        with tempfile.TemporaryDirectory() as directory:
            old_cwd = os.getcwd()
            try:
                os.chdir(directory)
                with (
                    mock.patch.object(pipeline, "load_previous", return_value=previous),
                    mock.patch.object(pipeline, "safe_fetch", return_value=[]),
                ):
                    pipeline.main()
                payload = json.loads(Path("data/output.json").read_text(encoding="utf-8"))
            finally:
                os.chdir(old_cwd)
        self.assertEqual(payload["meta"]["mode"], "partial")
        self.assertEqual(payload["events"], [article])
        self.assertEqual(payload["llm_summary"], "")

    def test_registered_source_is_never_required(self):
        with (
            mock.patch.dict(os.environ, {"NASA_FIRMS_API_KEY": ""}, clear=False),
            mock.patch.object(data_fetcher.requests, "get") as request,
        ):
            self.assertEqual(data_fetcher.fetch_nasa_firms(), [])
        request.assert_not_called()

    def test_dashboard_discloses_limits_and_has_no_generated_map_points(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8").lower()
        app = (ROOT / "assets" / "app.js").read_text(encoding="utf-8").lower()
        self.assertIn("methodology and limits", html)
        self.assertIn("data/output.json", app)
        self.assertNotIn("news tone index", app)
        self.assertNotIn("math.cos", app)
        self.assertNotIn("math.sin", app)


if __name__ == "__main__":
    unittest.main()
