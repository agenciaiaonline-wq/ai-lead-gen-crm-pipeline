from pathlib import Path
import tempfile
import unittest

from src.cli import run_pipeline
from src.crm_store import LeadCRMStore
from src.exporter import export_csv
from src.hunter import deduplicate_signals, parse_rss_xml
from src.scorer import score_lead_heuristic

SAMPLE_FEED = Path(__file__).resolve().parent.parent / "examples" / "sample_feed.xml"


class LeadPipelineTests(unittest.TestCase):
    def test_parse_dedupe_and_score_sample_feed(self) -> None:
        xml_text = SAMPLE_FEED.read_text(encoding="utf-8")
        signals = parse_rss_xml(xml_text, source_name="example-board")
        self.assertEqual(len(signals), 3)

        # Duplicate detection preserves first entry
        doubled = deduplicate_signals(signals + [signals[0]])
        self.assertEqual(len(doubled), 3)

        top_score = score_lead_heuristic(signals[0])
        low_score = score_lead_heuristic(signals[2])
        self.assertEqual(top_score.tier, "HOT")
        self.assertGreaterEqual(top_score.icp_score, 75)
        self.assertEqual(low_score.tier, "COLD")

    def test_sqlite_crm_deduplication_and_digest_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "crm.db"
            digest = run_pipeline(SAMPLE_FEED, db_path, min_score=65)
            self.assertIn("Build 24/7 WhatsApp AI Agent", digest)
            self.assertNotIn("WordPress Blog Theme Tweaks", digest)

            # Re-running ingestion must not insert duplicates
            store = LeadCRMStore(db_path)
            first_count = len(store.list_leads(min_score=0))
            run_pipeline(SAMPLE_FEED, db_path, min_score=0)
            second_count = len(store.list_leads(min_score=0))
            self.assertEqual(first_count, 3)
            self.assertEqual(second_count, 3)

            csv_output = export_csv(store.list_leads(min_score=65))
            self.assertIn("icp_score,tier,status", csv_output)
            self.assertIn("HOT", csv_output)


if __name__ == "__main__":
    unittest.main()
