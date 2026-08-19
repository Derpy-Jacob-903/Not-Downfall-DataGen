import os
import json
import pandas as pd
import traceback

from data import prep_cards_by_version, fetch, prep_relics


def export_data_files():
    """Write public/cards.json, activity.json, characters.json, relics.json for the static explorer."""
    os.makedirs("public", exist_ok=True)

    # ---- cards.json : one row per (card, version_group), RAW COUNTS ----
    dfv = prep_cards_by_version()
    dfv = dfv[dfv["character"] != "COLORLESS"]
    keep = ["card", "version_group", "label", "character", "rarity", "type", "cost",
            "description",
            "offered_3c", "picked_3c",
            "runs_acquired", "wins_acquired",
            "sp_runs_acquired", "sp_wins_acquired",
            "mp_runs_acquired", "mp_wins_acquired"]
    dfv[[c for c in keep if c in dfv.columns]].to_json(
        "public/cards.json", orient="records")
    print(f"Wrote public/cards.json ({len(dfv)} rows)")

    # ---- relics.json : one row per (relic, version_group), RAW COUNTS + metadata ----
    rel = prep_relics()
    keep_rel = ["relic", "version_group", "label", "name", "tier", "description",
                "runs_with_relic", "wins_with_relic",
                "sp_runs_with_relic", "sp_wins_with_relic",
                "mp_runs_with_relic", "mp_wins_with_relic"]
    rel[[c for c in keep_rel if c in rel.columns]].to_json(
        "public/relics.json", orient="records")
    print(f"Wrote public/relics.json ({len(rel)} rows)")

    # ---- activity.json : {day, hour} runs over time ----
    day = fetch("runs_per_day")
    hour = fetch("runs_per_hour")
    with open("public/activity.json", "w", encoding="utf-8") as f:
        json.dump({"day": day.to_dict(orient="records"),
                   "hour": hour.to_dict(orient="records")}, f, default=str)
    print(f"Wrote public/activity.json (day={len(day)}, hour={len(hour)})")

    # ---- characters.json : per-character winrate raw counts, by version ----
    asc = fetch("char_ascension_by_version")
    daily = fetch("char_daily_by_version")
    with open("public/characters.json", "w", encoding="utf-8") as f:
        json.dump({"ascension": asc.to_dict(orient="records"),
                   "daily": daily.to_dict(orient="records")}, f, default=str)
    print(f"Wrote public/characters.json (asc={len(asc)}, daily={len(daily)})")


def build():
    updated = pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M UTC")

    # ---- 1. the client-side dashboard data ----
    try:
        export_data_files()
    except Exception as e:
        print(f"export_data_files failed: {e}")
        traceback.print_exc()

    # ---- 2. copy the dashboard page into public/ ----
    try:
        import shutil
        shutil.copy(os.path.join(os.path.dirname(__file__), "index.html"),
                    "public/index.html")
        print("Copied index.html")
    except Exception as e:
        print(f"index.html copy failed: {e}")


if __name__ == "__main__":
    build()