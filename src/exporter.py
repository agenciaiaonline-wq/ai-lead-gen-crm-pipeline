"""Export qualified CRM leads into Markdown digests or CSV spreadsheets."""

import csv
import io
from typing import Iterable

from src.crm_store import StoredLead


def export_markdown(leads: Iterable[StoredLead]) -> str:
    rows = list(leads)
    if not rows:
        return "# Daily Lead Digest\n\n_No qualified leads matched the active threshold._\n"

    lines = [
        "# Daily Qualified Lead Digest",
        "",
        "| Score | Tier | Source | Opportunity | Recommended Pitch |",
        "| :---: | :---: | :--- | :--- | :--- |",
    ]
    for lead in rows:
        safe_title = lead.title.replace("|", "/")
        lines.append(
            f"| {lead.icp_score} | **{lead.tier}** | `{lead.source}` | [{safe_title}]({lead.url}) | {lead.recommended_pitch} |"
        )
    return "\n".join(lines) + "\n"


def export_csv(leads: Iterable[StoredLead]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "icp_score", "tier", "status", "source", "title", "url", "recommended_pitch"])
    for lead in leads:
        writer.writerow([
            lead.id,
            lead.icp_score,
            lead.tier,
            lead.status,
            lead.source,
            lead.title,
            lead.url,
            lead.recommended_pitch,
        ])
    return buf.getvalue()
