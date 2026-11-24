"""WAL-enabled SQLite CRM storage for deduplicated, scored B2B leads."""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Iterator, List, Optional

from src.hunter import LeadSignal
from src.scorer import LeadScore


@dataclass(frozen=True)
class StoredLead:
    id: int
    source: str
    title: str
    url: str
    icp_score: int
    tier: str
    status: str
    recommended_pitch: str


class LeadCRMStore:
    """Persistent lightweight CRM backed by SQLite WAL mode."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._session() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    summary TEXT NOT NULL,
                    icp_score INTEGER NOT NULL,
                    tier TEXT NOT NULL,
                    matched_signals TEXT NOT NULL,
                    recommended_pitch TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def upsert_lead(self, signal: LeadSignal, score: LeadScore) -> bool:
        """Insert a new lead by unique URL. Returns True if inserted, False if already tracked."""
        with self._session() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO leads (
                    source, title, url, summary, icp_score, tier, matched_signals, recommended_pitch
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    signal.source,
                    signal.title,
                    signal.url.strip().rstrip("/"),
                    signal.summary,
                    score.icp_score,
                    score.tier,
                    ", ".join(score.matched_signals),
                    score.recommended_pitch,
                ),
            )
            return cursor.rowcount > 0

    def list_leads(self, min_score: int = 0, limit: Optional[int] = None) -> List[StoredLead]:
        query = (
            "SELECT id, source, title, url, icp_score, tier, status, recommended_pitch "
            "FROM leads WHERE icp_score >= ? ORDER BY icp_score DESC, id DESC"
        )
        params: list[object] = [min_score]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._session() as conn:
            rows = conn.execute(query, params).fetchall()

        return [StoredLead(*row) for row in rows]

    def update_status(self, lead_id: int, status: str) -> None:
        allowed = {"new", "contacted", "qualified", "won", "archived"}
        if status not in allowed:
            raise ValueError(f"Unsupported CRM status: {status}")
        with self._session() as conn:
            conn.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
