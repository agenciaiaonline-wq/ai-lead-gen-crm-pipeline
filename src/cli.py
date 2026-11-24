"""CLI entrypoint for ingesting RSS lead signals, scoring ICP fit, and exporting digests."""

import argparse
from pathlib import Path
import sys

from src.crm_store import LeadCRMStore
from src.exporter import export_markdown
from src.hunter import deduplicate_signals, parse_rss_xml
from src.scorer import score_lead_heuristic


def run_pipeline(feed_file: Path, db_path: Path, min_score: int, source_name: str = "sample-feed") -> str:
    xml_text = feed_file.read_text(encoding="utf-8")
    signals = deduplicate_signals(parse_rss_xml(xml_text, source_name=source_name))
    store = LeadCRMStore(db_path)

    for signal in signals:
        score = score_lead_heuristic(signal)
        store.upsert_lead(signal, score)

    qualified = store.list_leads(min_score=min_score)
    return export_markdown(qualified)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest, score, and export B2B AI automation leads.")
    parser.add_argument("--feed-file", type=Path, required=True, help="Path to RSS/Atom XML feed file")
    parser.add_argument("--db-path", type=Path, default=Path("./data/leads.db"), help="SQLite CRM database path")
    parser.add_argument("--min-score", type=int, default=50, help="Minimum ICP score (0-100) for digest export")
    args = parser.parse_args(argv)

    if not args.feed_file.exists():
        print(f"Feed file not found: {args.feed_file}", file=sys.stderr)
        return 2

    digest = run_pipeline(args.feed_file, args.db_path, args.min_score)
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
