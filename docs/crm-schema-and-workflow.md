# SQLite WAL CRM Schema & Scoring Guide

## 1. `leads` Table
- `url TEXT UNIQUE NOT NULL` enforces idempotent ingestion via `INSERT OR IGNORE`, preventing duplicate alerts on repeated feed runs.
- `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=5000;` keep concurrent dashboard reads and scheduled hunter writes safe.

## 2. ICP Scoring Tiers (`src/scorer.py`)
- **HOT (`75–100`):** Strong stack alignment (`n8n`, `whatsapp`, `supabase`, `saas`, `ai agent`) plus explicit budget signals (`>= $5,000`).
- **WARM (`50–74`):** Partial stack fit or medium urgency; queue architecture diagram + ROI benchmark outreach.
- **COLD (`< 50`):** Low-budget or unrelated projects automatically filtered out of daily digests (`--min-score 65`).
