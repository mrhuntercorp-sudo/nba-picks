"""Collect current-season player game logs for NBA Picks importance scoring.

Run:
    python data/collect_players.py --season 2025-26

Output:
    data/players/player-games-<season>.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from nba_api.stats.endpoints import playergamelogs

OUTPUT_DIR = Path(__file__).with_name("players")


def collect(season: str) -> dict:
    endpoint = playergamelogs.PlayerGameLogs(
        season_nullable=season,
        season_type_nullable="Regular Season",
    )
    rows = endpoint.get_data_frames()[0].to_dict(orient="records")
    return {
        "source": "NBA Stats PlayerGameLogs via nba_api",
        "season": season,
        "collectedAtUTC": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", required=True)
    args = parser.parse_args()
    result = collect(args.season)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"player-games-{args.season}.json"
    output.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"Collected {len(result['rows'])} player-game rows -> {output}")


if __name__ == "__main__":
    main()
