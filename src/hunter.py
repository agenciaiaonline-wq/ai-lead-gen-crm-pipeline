"""Multi-source RSS & webhook signal collector with URL deduplication."""

from dataclasses import dataclass
from typing import Iterable, List
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class LeadSignal:
    source: str
    title: str
    url: str
    summary: str
    published_at: str = ""


def parse_rss_xml(xml_text: str, source_name: str = "rss-feed") -> List[LeadSignal]:
    """Parse RSS 2.0 or Atom XML feed text into normalized LeadSignal items."""
    root = ET.fromstring(xml_text.strip())
    signals: List[LeadSignal] = []

    # RSS 2.0 <channel><item>
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        summary = (item.findtext("description") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if title and link:
            signals.append(
                LeadSignal(
                    source=source_name,
                    title=title,
                    url=link,
                    summary=summary,
                    published_at=pub_date,
                )
            )

    # Atom <entry> fallback
    atom_ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.findall(f"{atom_ns}entry"):
        title = (entry.findtext(f"{atom_ns}title") or "").strip()
        link_el = entry.find(f"{atom_ns}link")
        link = (link_el.attrib.get("href", "") if link_el is not None else "").strip()
        summary = (entry.findtext(f"{atom_ns}summary") or "").strip()
        updated = (entry.findtext(f"{atom_ns}updated") or "").strip()
        if title and link:
            signals.append(
                LeadSignal(
                    source=source_name,
                    title=title,
                    url=link,
                    summary=summary,
                    published_at=updated,
                )
            )

    return signals


def deduplicate_signals(signals: Iterable[LeadSignal]) -> List[LeadSignal]:
    """Preserve order while removing duplicate lead URLs."""
    seen: set[str] = set()
    unique: List[LeadSignal] = []
    for signal in signals:
        normalized = signal.url.strip().rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(signal)
    return unique
