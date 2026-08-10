import pandas as pd
import requests
from config import SUPABASE_URL, KEY, char_of
import json
import os

def fetch(view: str) -> pd.DataFrame:
    """Fetch raw records from a Supabase view."""
    headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    params = {"select": "*", "limit": "100000"}
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{view}", headers=headers, params=params, timeout=90)
    r.raise_for_status()
    return pd.DataFrame(r.json())


def load_items() -> pd.DataFrame:
    """Load card metadata (name, rarity, type, cost, text) keyed by card id."""
    path = os.path.join(os.path.dirname(__file__), "items.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # items.json may be a bare list or wrapped in a key — handle both
    records = data if isinstance(data, list) else data.get("cards", data)

    items = pd.DataFrame(records)
    # keep one row per card id (base, unupgraded)
    items = items.sort_values("upgrades").drop_duplicates("id", keep="first")
    return items[["id", "name", "rarity", "type", "cost", "description"]]


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
    df["description"] = df["description"].str.replace("\n", "<br>", regex=False)
    df["label"] = df["name"].fillna(df["short"])   # real name, fall back to id
    return df