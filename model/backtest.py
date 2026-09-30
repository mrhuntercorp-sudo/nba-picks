"""Historical straight-up prediction backtest for NBA Picks."""
from __future__ import annotations
import argparse, json, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model.predict_game import predict
from model.team_features import build_team_features

def game_pairs(rows):
    grouped = defaultdict(list)
    for row in rows:
        if row.get("gameId"):
            grouped[str(row["gameId"])].append(row)
    pairs = []
    for game_rows in grouped.values():
        home = next((r for r in game_rows if r.get("homeAway") == "HOME"), None)
        away = next((r for r in game_rows if r.get("homeAway") == "AWAY"), None)
        if len(game_rows) == 2 and home and away:
            pairs.append((home, away))
    return sorted(pairs, key=lambda x: (str(x[0].get("gameDate")), str(x[0].get("gameId"))))

def run_backtest(rows, minimum_prior_games=10):
    predictions = []
    buckets = defaultdict(lambda: {"games": 0, "correct": 0})
    for home, away in game_pairs(rows):
        date = home["gameDate"]
        hf = build_team_features(
            rows,
            home["teamId"],
            date,
            "HOME",
            opponent_team_id=away["teamId"],
        )
        af = build_team_features(
            rows,
            away["teamId"],
            date,
            "AWAY",
            opponent_team_id=home["teamId"],
        )
        if min(hf["historyGamesAvailable"], af["historyGamesAvailable"]) < minimum_prior_games:
            continue
        result = predict(hf, af, home_name=home["team"], away_name=away["team"])
        actual = home["team"] if str(home.get("winLoss")).upper() == "W" else away["team"]
        correct = result["pick"] == actual
        bucket = buckets[result["confidence"]]
        bucket["games"] += 1
        bucket["correct"] += int(correct)
        predictions.append({"gameId": home["gameId"], "gameDate": date, "home": home["team"], "away": away["team"], "pick": result["pick"], "actualWinner": actual, "correct": correct, "confidence": result["confidence"], "edge": result["edge"]})
    total = len(predictions)
    correct = sum(int(p["correct"]) for p in predictions)
    by_confidence = {}
    for label in ("LOW", "MEDIUM", "HIGH"):
        b = buckets[label]
        by_confidence[label] = {"games": b["games"], "correct": b["correct"], "accuracy": round(b["correct"]/b["games"],4) if b["games"] else None}
    return {"modelVersion":"v1-h2h-candidate","minimumPriorGames":minimum_prior_games,"historicalInjuriesIncluded":False,"gamesTested":total,"correct":correct,"accuracy":round(correct/total,4) if total else None,"byConfidence":by_confidence,"predictions":predictions}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("history_file")
    parser.add_argument("--minimum-prior-games",type=int,default=10)
    args=parser.parse_args()
    source=Path(args.history_file)
    payload=json.loads(source.read_text(encoding="utf-8"))
    result=run_backtest(payload.get("games",[]),args.minimum_prior_games)
    out=ROOT/"data"/"backtests"/f"backtest-{payload.get('season',source.stem)}.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(f"Backtested {result['gamesTested']} games -> {out}")

if __name__=="__main__":
    main()
