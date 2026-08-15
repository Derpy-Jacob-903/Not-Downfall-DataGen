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


def prep_cards() -> pd.DataFrame:
    """Fetch and prepare card stats dataframe once for reuse."""
    df = fetch("card_stats")
    numeric_cols = [
        "times_offered", "offered_3c", "runs_with_card", "deck_winrate", "pick_rate_3c",
        "sp_runs_with_card", "sp_deck_winrate", "mp_runs_with_card", "mp_deck_winrate",
        "times_upgraded", "upgrade_rate",
        "runs_acquired", "acquired_winrate",
        "sp_runs_acquired", "sp_acquired_winrate",
        "mp_runs_acquired", "mp_acquired_winrate",
        "left_deck_rate",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["character"] = df["card"].map(char_of)
    df["short"] = df["card"].str.split("-", n=1).str[-1]

    items = load_items()
    df = df.merge(items, left_on="card", right_on="id", how="left")
    df = df.reset_index(drop=True)
    df = df.drop(columns=["id"], errors="ignore")
    df = df.loc[:, ~df.columns.duplicated()]
    df["description"] = df["description"].str.replace("\n", "<br>", regex=False)
    df["label"] = df["name"].fillna(df["short"])
    return df


def prep_cards_by_version() -> pd.DataFrame:
    """card_stats_by_version + card metadata, keyed by card.

    Exports RAW COUNTS (offered_3c, picked_3c, *_runs_acquired, *_wins_acquired)
    so the client can aggregate across versions and switch SP/MP/all by
    re-dividing wins/runs — never averaging pre-computed rates.
    """
    df = fetch("card_stats_by_version")
    count_cols = ["offered_3c", "picked_3c",
                  "runs_acquired", "wins_acquired",
                  "sp_runs_acquired", "sp_wins_acquired",
                  "mp_runs_acquired", "mp_wins_acquired"]
    for c in count_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    df["character"] = df["card"].map(char_of)
    df["short"] = df["card"].str.split("-", n=1).str[-1]

    items = load_items()
    df = df.merge(items, left_on="card", right_on="id", how="left")
    df = df.drop(columns=["id"], errors="ignore")
    df = df.loc[:, ~df.columns.duplicated()]
    df["label"] = df["name"].fillna(df["short"])
    return df