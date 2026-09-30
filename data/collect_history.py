"""NBA Picks V1: zero-cost historical team-game collector.

Uses nba_api TeamGameLogs. This collector only stores raw historical evidence.
Prediction features are calculated separately so collection and modeling stay isolated.

Run:
    python data/collect_history.py --season 2025-26

Output:
    data/history/team-games-<season>.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from nba_api.stats.endpoints import teamgamelogs

OUTPUT_DIR = Path(__file__).with_name("history")


def collect_history(season: str) -> dict:
    response = teamgamelogs.TeamGameLogs(
        season_nullable=season,
        season_type_nullable="Regular Season",
    )
    rows = response.get_data_frames()[0].to_dict(orient="records")

    games = []
    for row in rows:
        matchup = str(row.get("MATCHUP", ""))
        games.append({
            "season": row.get("SEASON_YEAR"),
            "teamId": row.get("TEAM_ID"),
            "team": row.get("TEAM_NAME"),
            "abbreviation": row.get("TEAM_ABBREVIATION"),
            "gameId": row.get("GAME_ID"),
            "gameDate": row.get("GAME_DATE"),
            "matchup": matchup,
            "homeAway": "AWAY" if "@" in matchup else "HOME",
            "winLoss": row.get("WL"),
            "minutes": row.get("MIN"),
            "points": row.get("PTS"),
            "plusMinus": row.get("PLUS_MINUS"),
            "fgPct": row.get("FG_PCT"),
            "threePct": row.get("FG3_PCT"),
            "ftPct": row.get("FT_PCT"),
            "rebounds": row.get("REB"),
            "offensiveRebounds": row.get("OREB"),
            "defensiveRebounds": row.get("DREB"),
            "assists": row.get("AST"),
            "turnovers": row.get("TOV"),
            "steals": row.get("STL"),
            "blocks": row.get("BLK"),
            "fieldGoalsMade": row.get("FGM"),
            "fieldGoalsAttempted": row.get("FGA"),
            "threeMade": row.get("FG3M"),
            "threeAttempted": row.get("FG3A"),
            "freeThrowsMade": row.get("FTM"),
            "freeThrowsAttempted": row.get("FTA"),
        })

    return {
        "source": "NBA Stats TeamGameLogs via nba_api",
        "season": season,
        "seasonType": "Regular Season",
        "collectedAtUTC": datetime.now(timezone.utc).isoformat(),
        "rows": len(games),
        "games": games,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", required=True, help="NBA season, e.g. 2025-26")
    args = parser.parse_args()

    result = collect_history(args.season)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"team-games-{args.season}.json"
    output.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"Collected {result['rows']} team-game rows -> {output}")


if __name__ == "__main__":
    main()
