"""NBA Picks V1: transparent straight-up winner prediction engine.

Consumes pregame team features plus optional injury impacts.
No betting lines, odds, spreads, or sportsbook data.

IMPORTANT:
- V1 weights are hypotheses, not validated production weights.
- Backtesting must tune/validate them.
- Inputs must contain only information available before tip-off.
"""
from __future__ import annotations

TEAM_WEIGHTS = {
    "seasonWinPct": 0.25,
    "last10WinPct": 0.20,
    "last5WinPct": 0.10,
    "sameLocationWinPct": 0.10,
    "avgPlusMinus": 0.15,
    "eFGPct": 0.10,
    "turnoverControl": 0.05,
    "rest": 0.05,
}

HOME_ADVANTAGE = 2.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _team_score(features: dict) -> tuple[float, dict]:
    season = features.get("seasonToDate", {})
    last10 = features.get("last10", {})
    last5 = features.get("last5", {})
    location = features.get("sameLocationLast10", {})
    factors = features.get("recentFourFactorInputs", {})

    # Normalize heterogeneous basketball features to approximately 0-100.
    components = {
        "seasonWinPct": 100 * float(season.get("winPct", 0)),
        "last10WinPct": 100 * float(last10.get("winPct", 0)),
        "last5WinPct": 100 * float(last5.get("winPct", 0)),
        "sameLocationWinPct": 100 * float(location.get("winPct", 0)),
        "avgPlusMinus": _clamp(50 + 2.5 * float(last10.get("avgPlusMinus", 0)), 0, 100),
        "eFGPct": _clamp(100 * float(factors.get("eFGPct", 0)), 0, 100),
        "turnoverControl": _clamp(100 - 250 * float(factors.get("turnoverRateProxy", 0)), 0, 100),
        "rest": 55 if features.get("restDays") is None else (
            40 if features.get("backToBack") else min(70, 50 + 5 * int(features.get("restDays", 0)))
        ),
    }
    score = sum(components[key] * weight for key, weight in TEAM_WEIGHTS.items())
    if str(features.get("targetLocation", "")).upper() == "HOME":
        score += HOME_ADVANTAGE
    return round(score, 2), components


def _injury_penalty(injuries: list[dict]) -> float:
    # Each item should contain an already-calculated 0-100 injuryImpact.
    # Cap prevents multiple absences from overwhelming every other signal
    # before backtesting determines a better calibration.
    total = sum(float(item.get("injuryImpact", 0)) for item in injuries)
    return round(min(25.0, total * 0.12), 2)


def _confidence(edge: float, data_quality: float) -> str:
    adjusted = edge * _clamp(data_quality, 0.0, 1.0)
    if adjusted >= 8:
        return "HIGH"
    if adjusted >= 4:
        return "MEDIUM"
    return "LOW"


def predict(
    home_features: dict,
    away_features: dict,
    home_injuries: list[dict] | None = None,
    away_injuries: list[dict] | None = None,
    home_name: str = "HOME",
    away_name: str = "AWAY",
) -> dict:
    home_injuries = home_injuries or []
    away_injuries = away_injuries or []

    home_base, home_components = _team_score(home_features)
    away_base, away_components = _team_score(away_features)
    home_penalty = _injury_penalty(home_injuries)
    away_penalty = _injury_penalty(away_injuries)

    home_final = round(home_base - home_penalty, 2)
    away_final = round(away_base - away_penalty, 2)
    edge = round(abs(home_final - away_final), 2)

    # Sparse histories should reduce confidence rather than fabricate certainty.
    min_games = min(
        int(home_features.get("historyGamesAvailable", 0)),
        int(away_features.get("historyGamesAvailable", 0)),
    )
    history_quality = min(1.0, min_games / 10.0)

    pick = home_name if home_final >= away_final else away_name
    confidence = _confidence(edge, history_quality)

    return {
        "pick": pick,
        "confidence": confidence,
        "edge": edge,
        "dataQuality": round(history_quality, 2),
        "home": {
            "team": home_name,
            "baseScore": home_base,
            "injuryPenalty": home_penalty,
            "finalScore": home_final,
            "components": home_components,
        },
        "away": {
            "team": away_name,
            "baseScore": away_base,
            "injuryPenalty": away_penalty,
            "finalScore": away_final,
            "components": away_components,
        },
        "modelVersion": "v1-unvalidated",
    }
