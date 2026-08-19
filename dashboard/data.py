import pandas as pd
import requests
from config import SUPABASE_URL, KEY, char_of
import json
import os
import time


def _get_with_retry(url, headers, params, max_retries=5, base_delay=1.5):
    """GET with retry-and-backoff on transient failures (5xx, 429, network errors).

    Real client errors (4xx other than 429) are raised immediately, since
    waiting won't fix a malformed request or bad auth.
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=90)
            # treat 5xx and 429 as transient -> retry; other 4xx -> raise now
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.HTTPError(
                    f"{r.status_code} {r.reason}", response=r)
            r.raise_for_status()
            return r
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as e:
            resp = getattr(e, "response", None)
            if resp is not None and 400 <= resp.status_code < 500 and resp.status_code != 429:
                raise  # genuine client error, don't retry
            last_err = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # 1.5s, 3s, 6s, 12s ...
                print(f"  transient error ({e}); retry "
                      f"{attempt + 1}/{max_retries - 1} in {delay:.1f}s")
                time.sleep(delay)
    raise last_err


def fetch(view: str) -> pd.DataFrame:
    """Fetch all records from a Supabase view, paging past the 1000-row cap."""
    headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    page_size = 1000
    offset = 0
    frames = []
    while True:
        params = {"select": "*", "limit": str(page_size), "offset": str(offset)}
        r = _get_with_retry(f"{SUPABASE_URL}/rest/v1/{view}", headers, params)
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


def _load_relics_slice(mod_name: str) -> pd.DataFrame:
    """Load one mod's relic metadata (name, tier, description) keyed by id, from items.json.

    Note: the `pool` field is an internal pool key (e.g.
    "relic_pool:automaton-automaton_relic_pool"), not a clean character name,
    so we don't export it — the client classifies relics by the id prefix
    (AUTOMATON-..., CHAMP-...) instead.
    """
    path = os.path.join(os.path.dirname(__file__), "items.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("relics", []) if isinstance(data, dict) else []
    relics = pd.DataFrame(records)
    if relics.empty:
        return relics
    if "mod" in relics.columns:
        relics = relics[relics["mod"] == mod_name]
    # keep the latest schema version per relic id, mirroring the card loader's
    # dedup intent (cards dedup on `upgrades`; relics have no upgrades, use `v`)
    if "v" in relics.columns:
        relics = relics.sort_values("v").drop_duplicates("id", keep="last")
    else:
        relics = relics.drop_duplicates("id", keep="first")
    cols = [c for c in ["id", "name", "tier", "description"] if c in relics.columns]
    return relics[cols]


def load_relics() -> pd.DataFrame:
    """Downfall relic metadata."""
    return _load_relics_slice("Downfall")


def prep_relics() -> pd.DataFrame:
    """relic_stats view joined to relic metadata, keyed by relic id.

    Exports RAW COUNTS (*_runs_with_relic, *_wins_with_relic) so the client
    re-divides wins/runs per SP/MP/all — never averaging pre-computed rates.
    Character classification is done client-side from the id prefix.
    """
    df = fetch("relic_stats")
    count_cols = ["runs_with_relic", "wins_with_relic",
                  "sp_runs_with_relic", "sp_wins_with_relic",
                  "mp_runs_with_relic", "mp_wins_with_relic"]
    for c in count_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    meta = load_relics()
    if not meta.empty:
        df = df.merge(meta, left_on="relic", right_on="id", how="left")
        df = df.drop(columns=["id"], errors="ignore")
        df = df.loc[:, ~df.columns.duplicated()]
    # display name falls back to the raw id when metadata is missing
    if "name" in df.columns:
        df["label"] = df["name"].fillna(df["relic"])
    else:
        df["label"] = df["relic"]
    return df