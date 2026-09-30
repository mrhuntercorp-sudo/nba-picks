"""NBA Picks V1: transparent player-importance scoring.

Input: player game-log rows collected before the game being predicted.
Output: 0-100 importance score + role tier.

No manual star list. A player's importance is relative to teammates and is
derived from availability-independent basketball usage/production evidence.

This is V1 scoring, intentionally simple and backtestable. Weights are not
claimed optimal; backtesting must tune them before production use.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Iterable

WEIGHTS = {
    "minutes": 0.40,
    "points": 0.25,
    "assists": 0.15,
    "rebounds": 0.10,
    "plusMinus": 0.10,
}

STATUS_MULTIPLIER = {
    "OUT": 1.00,
    "DOUBTFUL": 0.75,
    "QUESTIONABLE": 0.40,
    "PROBABLE": 0.15,
    "AVAILABLE": 0.00,
}


def _safe(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _normalize(value: float, team_max: float) -> float:
    if team_max <= 0:
        return 0.0
    # Negative plus/minus should not create negative importance.
    return max(0.0, value) / team_max


def aggregate_players(rows: Iterable[dict], last_n: int = 10) -> list[dict]:
    by_player: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        key = (row.get("TEAM_ID"), row.get("PLAYER_ID"), row.get("PLAYER_NAME"))
        by_player[key].append(row)

    players = []
    for (team_id, player_id, name), games in by_player.items():
        # Expected collector order may vary; date sorting makes the window explicit.
        games = sorted(games, key=lambda x: str(x.get("GAME_DATE", "")), reverse=True)[:last_n]
        if not games:
            continue
        players.append({
            "teamId": team_id,
            "playerId": player_id,
            "player": name,
            "gamesUsed": len(games),
            "minutes": mean(_safe(g.get("MIN")) for g in games),
            "points": mean(_safe(g.get("PTS")) for g in games),
            "assists": mean(_safe(g.get("AST")) for g in games),
            "rebounds": mean(_safe(g.get("REB")) for g in games),
            "plusMinus": mean(_safe(g.get("PLUS_MINUS")) for g in games),
        })
    return players


def score_team(players: list[dict]) -> list[dict]:
    if not players:
        return []

    maxima = {
        metric: max((_safe(p.get(metric)) for p in players), default=0.0)
        for metric in WEIGHTS
    }

    scored = []
    for player in players:
        raw = sum(
            WEIGHTS[metric] * _normalize(_safe(player.get(metric)), maxima[metric])
            for metric in WEIGHTS
        )
        score = round(raw * 100, 1)
        tier = (
            "CORE" if score >= 75
            else "HIGH" if score >= 55
            else "ROTATION" if score >= 30
            else "DEPTH"
        )
        scored.append({**player, "importanceScore": score, "importanceTier": tier})

    return sorted(scored, key=lambda p: p["importanceScore"], reverse=True)


def score_all(rows: Iterable[dict], last_n: int = 10) -> list[dict]:
    aggregated = aggregate_players(rows, last_n=last_n)
    teams: dict[object, list[dict]] = defaultdict(list)
    for player in aggregated:
        teams[player["teamId"]].append(player)

    result = []
    for team_players in teams.values():
        result.extend(score_team(team_players))
    return result


def injury_impact(importance_score: float, status: str) -> float:
    """Return 0-100 absence impact before team-model calibration."""
    multiplier = STATUS_MULTIPLIER.get(str(status).upper(), 0.0)
    return round(max(0.0, min(100.0, importance_score)) * multiplier, 1)
