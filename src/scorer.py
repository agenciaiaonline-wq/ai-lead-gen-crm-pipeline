"""ICP fit scoring, budget intent classification, and LLM prompt builder."""

from dataclasses import dataclass
import re
from typing import Dict, Tuple

from src.hunter import LeadSignal

DEFAULT_WEIGHTS: Dict[str, int] = {
    "saas": 15,
    "mvp": 15,
    "next.js": 12,
    "supabase": 15,
    "n8n": 18,
    "whatsapp": 16,
    "rag": 15,
    "fastapi": 12,
    "automation": 14,
    "ai agent": 18,
    "retainer": 15,
    "urgent": 10,
}

BUDGET_PATTERN = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d{4,})")


@dataclass(frozen=True)
class LeadScore:
    icp_score: int
    tier: str  # HOT | WARM | COLD
    matched_signals: Tuple[str, ...]
    recommended_pitch: str


def score_lead_heuristic(signal: LeadSignal, weights: Dict[str, int] | None = None) -> LeadScore:
    """Compute a deterministic 0-100 B2B ICP fit score from lead text and budget markers."""
    active_weights = weights or DEFAULT_WEIGHTS
    haystack = f"{signal.title} {signal.summary}".lower()

    matched: list[str] = []
    raw_score = 15  # Baseline valid feed entry

    for keyword, weight in active_weights.items():
        if keyword in haystack:
            raw_score += weight
            matched.append(keyword)

    budget_match = BUDGET_PATTERN.search(haystack)
    if budget_match:
        amount = int(budget_match.group(1).replace(",", ""))
        if amount >= 5000:
            raw_score += 25
            matched.append("budget>=5k")
        elif amount >= 2000:
            raw_score += 15
            matched.append("budget>=2k")

    bounded = min(100, raw_score)
    if bounded >= 75:
        tier = "HOT"
        pitch = "Propose 7-14 day turnkey implementation sprint with live prototype walkthrough."
    elif bounded >= 50:
        tier = "WARM"
        pitch = "Send architecture diagram + ROI calculator comparison to qualify timeline."
    else:
        tier = "COLD"
        pitch = "Archive in watchlist; low immediate alignment with core AI/SaaS retainers."

    return LeadScore(
        icp_score=bounded,
        tier=tier,
        matched_signals=tuple(matched),
        recommended_pitch=pitch,
    )


def build_llm_scoring_prompt(signal: LeadSignal) -> str:
    """Create a structured JSON extraction prompt for optional OpenAI-compatible enrichment."""
    return (
        "Classify the following inbound engineering opportunity for B2B automation / SaaS fit.\n"
        "Return strict JSON keys: icp_score (0-100), urgency (low|medium|high), recommended_package.\n\n"
        f"Source: {signal.source}\n"
        f"Title: {signal.title}\n"
        f"Summary: {signal.summary}\n"
    )
