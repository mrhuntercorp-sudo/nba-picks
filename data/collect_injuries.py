"""NBA Picks V1: official NBA injury-report collector.

Zero paid data providers. Downloads a specific official NBA injury-report PDF
and converts its text table into structured JSON.

Usage:
  python data/collect_injuries.py \
    --url "https://ak-static.cms.nba.com/referee/injury/Injury-Report_YYYY-MM-DD_HH_MMAM.pdf"

Output:
  data/injuries/latest.json

Notes:
- The official report can contain AVAILABLE, PROBABLE, QUESTIONABLE,
  DOUBTFUL and OUT statuses.
- Teams may also appear as NOT YET SUBMITTED.
- Player-importance weighting is deliberately handled by a separate layer.
"""
from __future__ import annotations

import argparse
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from pypdf import PdfReader

OUTPUT = Path(__file__).with_name("injuries") / "latest.json"
STATUSES = {"Available", "Probable", "Questionable", "Doubtful", "Out"}


def pdf_text(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    reader = PdfReader(io.BytesIO(response.content))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def parse_report(text: str) -> dict:
    # Preserve raw normalized lines because NBA PDF layout can change.
    # Only emit a player row when a recognized participation status is present.
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    entries = []
    current_team = None
    current_matchup = None
    current_date = None

    date_re = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
    matchup_re = re.compile(r"\b[A-Z]{3}@[A-Z]{3}\b")

    for line in lines:
        date_match = date_re.search(line)
        if date_match:
            current_date = date_match.group(0)

        matchup_match = matchup_re.search(line)
        if matchup_match:
            current_matchup = matchup_match.group(0)

        if line.endswith("NOT YET SUBMITTED"):
            team = line.removesuffix("NOT YET SUBMITTED").strip()
            if team:
                current_team = team
            entries.append({
                "gameDate": current_date,
                "matchup": current_matchup,
                "team": current_team,
                "player": None,
                "status": "NOT YET SUBMITTED",
                "reason": None,
            })
            continue

        status = next((s for s in STATUSES if re.search(rf"\b{s}\b", line)), None)
        if not status:
            # Team headings in extracted PDFs are commonly standalone lines.
            if "," not in line and len(line.split()) <= 5 and not matchup_re.search(line):
                current_team = line
            continue

        before, _, after = line.partition(status)
        player = before.strip(" -")
        if not player or "," not in player:
            continue

        entries.append({
            "gameDate": current_date,
            "matchup": current_matchup,
            "team": current_team,
            "player": player,
            "status": status.upper(),
            "reason": after.strip(" -;") or None,
        })

    return {"entries": entries, "rawLineCount": len(lines)}


def collect(url: str) -> dict:
    parsed = parse_report(pdf_text(url))
    return {
        "source": "NBA Official Injury Report",
        "sourceUrl": url,
        "collectedAtUTC": datetime.now(timezone.utc).isoformat(),
        **parsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Official NBA injury-report PDF URL")
    args = parser.parse_args()

    result = collect(args.url)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Parsed {len(result['entries'])} injury/report rows -> {OUTPUT}")


if __name__ == "__main__":
    main()
