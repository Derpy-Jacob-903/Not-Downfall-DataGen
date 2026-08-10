import pandas as pd
import requests
from config import SUPABASE_URL, KEY, char_of
import json
import os


def fetch(view: str) -> pd.DataFrame:
    """Fetch all records from a Supabase view, paging past the 1000-row cap."""
    headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    page_size = 1000
    offset = 0
    frames = []
    while True:
        params = {"select": "*", "limit": str(page_size), "offset": str(offset)}
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{view}",
                         headers=headers, params=params, timeout=90)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        frames.append(pd.DataFrame(batch))
        if len(batch) < page_size:
            break
        offset += page_size
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _load_items_slice(mod_name: str) -> pd.DataFrame:
    """Load one mod's card metadata (name, rarity, type, cost, text, color) keyed by id."""
    path = os.path.join(os.path.dirname(__file__), "items.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    records = data if isinstance(data, list) else data.get("cards", data)
    items = pd.DataFrame(records)
    if "mod" in items.columns:
        items = items[items["mod"] == mod_name]
    items = items.sort_values("upgrades").drop_duplicates("id", keep="first")
    cols = ["id", "name", "rarity", "type", "cost", "description"]
    if "color" in items.columns:
        cols.append("color")
    return items[cols]


def load_items() -> pd.DataFrame:
    """Downfall card metadata."""
    return _load_items_slice("Downfall")


def load_items_base() -> pd.DataFrame:
    """Base-game card metadata."""
    return _load_items_slice("Slay the Spire 2")


def load_vanilla(min_picks: int = 5000) -> pd.DataFrame:
    """Base-game card metrics (Spire Codex) + rarity/name/text/color from items.json, as reference points."""
    try:
        data = requests.get("https://spire-codex.com/api/runs/metrics/cards", timeout=30).json()
    except Exception as e:
        print(f"vanilla reference fetch failed, skipping: {e}")
        return pd.DataFrame()
    v = pd.DataFrame(data["rows"])
    v = v[(v["upgraded"] == False) & v["pick_rate"].notna()].copy()
    v["win_rate"] = pd.to_numeric(v["win_rate"], errors="coerce") / 100.0
    v["pick_rate"] = pd.to_numeric(v["pick_rate"], errors="coerce") / 100.0
    v = v[v["picks"] >= min_picks]
    v = v[["id", "win_rate", "pick_rate", "tier", "picks"]]

    meta = load_items_base()
    v = v.merge(meta, on="id", how="left")
    v["label"] = v["name"].fillna(v["id"])
    v["description"] = v["description"].str.replace("\n", "<br>", regex=False)
    if "color" not in v.columns:
        v["color"] = "unknown"
    v["color"] = v["color"].fillna("unknown")
    return v

def load_vanilla_ascension(cumulative: bool = False) -> pd.DataFrame:
    try:
        c = requests.get("https://spire-codex.com/api/charts/winrate-by-ascension",
                         params={"split": "character"}, timeout=30).json()
    except Exception as e:
        print(f"vanilla ascension fetch failed, skipping: {e}")
        return pd.DataFrame()
    rows = []
    for series in c.get("series", []):
        cid = series.get("id", "").lower()
        pts = sorted(series.get("points", []), key=lambda p: p["x"])
        if cumulative:
            runs_cum = wins_cum = 0
            for p in reversed(pts):
                n = p["n"]; w = round(n * p["y"] / 100.0)
                runs_cum += n; wins_cum += w
                rows.append({"character": cid, "ascension": p["x"],
                             "winrate": wins_cum / runs_cum if runs_cum else None,
                             "runs": runs_cum})
        else:
            for p in pts:
                rows.append({"character": cid, "ascension": p["x"],
                             "winrate": p["y"] / 100.0, "runs": p["n"]})
    return pd.DataFrame(rows)


def prep_cards() -> pd.DataFrame:
    """Fetch and prepare card stats dataframe once for reuse."""
    df = fetch("card_stats")
    numeric_cols = [
        "times_offered", "offered_3c", "runs_with_card", "deck_winrate", "pick_rate_3c",
        "sp_runs_with_card", "sp_deck_winrate", "mp_runs_with_card", "mp_deck_winrate"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["character"] = df["card"].map(char_of)
    df["short"] = df["card"].str.split("-", n=1).str[-1]

    items = load_items()
    df = df.merge(items, left_on="card", right_on="id", how="left")
    df = df.reset_index(drop=True)          # <- add this
    df = df.drop(columns=["id"], errors="ignore")
    df = df.loc[:, ~df.columns.duplicated()]
    df["description"] = df["description"].str.replace("\n", "<br>", regex=False)
    df["label"] = df["name"].fillna(df["short"])
    return df