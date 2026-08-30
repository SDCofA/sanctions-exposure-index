# -*- coding: utf-8 -*-
"""Offline contracts for the keyless pipeline and published dashboard."""
import importlib.util
import json
import os
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
        self.assertEqual(len(payload["stats"]), 4)
        self.assertIsInstance(payload["live_data"], dict)
        self.assertIsInstance(payload["events"], list)
        self.assertLessEqual(len(payload["events"]), pipeline.EVENT_LIMIT)
        for event in payload["events"]:
            self.assertTrue(event.get("title"))
            self.assertTrue(event.get("url"))

    def test_keyless_refresh_retains_last_valid_snapshot(self):
        article = {
            "title": "Validated public signal",
            "url": "https://example.org/signal",
            "domain": "example.org",
            "tone": 0,
            "seendate": "20260830T120000Z",
            "source": "PublicRSS",
        }
        previous = {"live_data": {"news_articles": [article]}}
        with tempfile.TemporaryDirectory() as directory:
            old_cwd = os.getcwd()
            try:
                os.chdir(directory)
                with (
                    mock.patch.object(pipeline, "load_previous", return_value=previous),
                    mock.patch.object(pipeline, "extract_live_data", return_value={}),
                    mock.patch.object(pipeline, "analyze_with_llm") as llm,
                    mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False),
                ):
                    pipeline.main()
                payload = json.loads(Path("data/output.json").read_text(encoding="utf-8"))
            finally:
                os.chdir(old_cwd)

        llm.assert_not_called()
        self.assertEqual(payload["meta"]["project"], PROJECT_ID)
        self.assertEqual(payload["meta"]["mode"], "partial")
        self.assertEqual(payload["events"], [article])
        self.assertEqual(payload["llm_summary"], "")
        self.assertIn("news_articles", payload["meta"]["sources"])

    def test_registered_source_is_never_required(self):
        with (
            mock.patch.dict(os.environ, {"NASA_FIRMS_API_KEY": ""}, clear=False),
            mock.patch.object(data_fetcher.requests, "get") as request,
        ):
            self.assertEqual(data_fetcher.fetch_nasa_firms(), [])
        request.assert_not_called()

    def test_dashboard_has_end_user_copy_and_complete_assets(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8").lower()
        app = (ROOT / "assets" / "app.js").read_text(encoding="utf-8").lower()
        for path in ("assets/product-logo.svg", "assets/style.css", "assets/app.js"):
            self.assertTrue((ROOT / path).is_file(), path)
        self.assertIn('data/output.json', app)
        self.assertIn("analyst brief", html)
        self.assertNotIn("need improvement", html)
        self.assertNotIn("demo mode", html)
        self.assertNotIn("latest declared source timestamp", html)
        self.assertNotIn("not ground truth", app)
        self.assertNotIn("illustrative coverage indicators", app)


if __name__ == "__main__":
    unittest.main()

