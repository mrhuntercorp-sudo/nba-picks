"""NBA Picks V1: derive pregame team features from historical game rows.

Critical rule: only games BEFORE the target game's tip/date may be used.
This prevents future-result leakage during backtesting.

Expected rows are produced by data/collect_history.py.
"""
from __future__ import annotations

from datetime import datetime
from statistics import mean


def _num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _date(value: str) -> datetime:
    value = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value[:10] if fmt == "%Y-%m-%d" else value, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unsupported game date: {value!r}")


def _pct(wins: int, games: int) -> float:
    return round(wins / games, 4) if games else 0.0


def _summary(rows: list[dict]) -> dict:
    if not rows:
        return {"games": 0, "wins": 0, "winPct": 0.0, "avgPoints": 0.0, "avgPlusMinus": 0.0}
    wins = sum(1 for r in rows if str(r.get("winLoss")).upper() == "W")
    return {
        "games": len(rows),
        "wins": wins,
        "winPct": _pct(wins, len(rows)),
        "avgPoints": round(mean(_num(r.get("points")) for r in rows), 2),
        "avgPlusMinus": round(mean(_num(r.get("plusMinus")) for r in rows), 2),
    }


def _four_factor_inputs(rows: list[dict]) -> dict:
    if not rows:
        return {"eFGPct": 0.0, "turnoverRateProxy": 0.0, "offReboundAvg": 0.0, "freeThrowRate": 0.0}

    fgm = sum(_num(r.get("fieldGoalsMade")) for r in rows)
    fga = sum(_num(r.get("fieldGoalsAttempted")) for r in rows)
    threes = sum(_num(r.get("threeMade")) for r in rows)
    fta = sum(_num(r.get("freeThrowsAttempted")) for r in rows)
    tov = sum(_num(r.get("turnovers")) for r in rows)
    oreb = sum(_num(r.get("offensiveRebounds")) for r in rows)

    # eFG% and FTA/FGA are standard derivations from the raw box-score fields.
    # TOV/FGA is deliberately labeled a proxy until possession data is added.
    return {
        "eFGPct": round((fgm + 0.5 * threes) / fga, 4) if fga else 0.0,
        "turnoverRateProxy": round(tov / fga, 4) if fga else 0.0,
        "offReboundAvg": round(oreb / len(rows), 2),
        "freeThrowRate": round(fta / fga, 4) if fga else 0.0,
    }


def build_team_features(
    all_rows: list[dict],
    team_id,
    target_date: str,
    target_location: str,
) -> dict:
    cutoff = _date(target_date)
    history = [
        r for r in all_rows
        if str(r.get("teamId")) == str(team_id) and _date(r.get("gameDate")) < cutoff
    ]
    history.sort(key=lambda r: _date(r.get("gameDate")), reverse=True)

    last5 = history[:5]
    last10 = history[:10]
    location = str(target_location).upper()
    same_location = [r for r in history if str(r.get("homeAway")).upper() == location][:10]

    rest_days = None
    back_to_back = False
    if history:
        delta = (cutoff.date() - _date(history[0].get("gameDate")).date()).days
        rest_days = max(0, delta - 1)
        back_to_back = delta == 1

    return {
        "teamId": team_id,
        "asOf": target_date,
        "targetLocation": location,
        "seasonToDate": _summary(history),
        "last5": _summary(last5),
        "last10": _summary(last10),
        "sameLocationLast10": _summary(same_location),
        "restDays": rest_days,
        "backToBack": back_to_back,
        "recentFourFactorInputs": _four_factor_inputs(last10),
        "historyGamesAvailable": len(history),
    }
