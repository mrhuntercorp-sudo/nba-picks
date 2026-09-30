"""NBA Picks V1: zero-cost live scoreboard collector.

Uses nba_api's NBA Live scoreboard endpoint.
Run locally:
    python -m pip install nba_api
    python data/collect_today.py

Output:
    data/today-games.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from nba_api.live.nba.endpoints import scoreboard

OUTPUT = Path(__file__).with_name("today-games.json")


def collect_today() -> dict:
    board = scoreboard.ScoreBoard()
    payload = board.get_dict()
    scoreboard_data = payload.get("scoreboard", {})
    games = []

    for game in scoreboard_data.get("games", []):
        home = game.get("homeTeam", {})
        away = game.get("awayTeam", {})
        games.append(
            {
                "gameId": game.get("gameId"),
                "gameStatus": game.get("gameStatus"),
                "gameStatusText": game.get("gameStatusText"),
                "gameTimeUTC": game.get("gameTimeUTC"),
                "home": {
                    "teamId": home.get("teamId"),
                    "name": f"{home.get('teamCity', '')} {home.get('teamName', '')}".strip(),
                    "abbreviation": home.get("teamTricode"),
                    "score": home.get("score"),
                },
                "away": {
                    "teamId": away.get("teamId"),
                    "name": f"{away.get('teamCity', '')} {away.get('teamName', '')}".strip(),
                    "abbreviation": away.get("teamTricode"),
                    "score": away.get("score"),
                },
            }
        )

    return {
        "source": "NBA Live via nba_api",
        "collectedAtUTC": datetime.now(timezone.utc).isoformat(),
        "gameDate": scoreboard_data.get("gameDate"),
        "games": games,
    }


if __name__ == "__main__":
    result = collect_today()
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Collected {len(result['games'])} games -> {OUTPUT}")
