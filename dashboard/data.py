import pandas as pd
import requests
from config import SUPABASE_URL, KEY, char_of


def fetch(view: str) -> pd.DataFrame:
    """Fetch raw records from a Supabase view."""
    headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    params = {"select": "*", "limit": "100000"}
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{view}", headers=headers, params=params, timeout=90)
    r.raise_for_status()
    return pd.DataFrame(r.json())


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
    return df