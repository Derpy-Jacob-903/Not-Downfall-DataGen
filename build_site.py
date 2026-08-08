#!/usr/bin/env python3
import os
import colorsys
import requests
import pandas as pd
import plotly.graph_objects as go

KEY = os.environ["SUPABASE_SECRET_KEY"]          # from GitHub Secrets at build time
SUPABASE_URL = "https://wxememsxgrgrfvntulgr.supabase.co"

# ---- fetch ----
r = requests.get(
    f"{SUPABASE_URL}/rest/v1/card_stats",
    headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"},
    params={"select": "*", "limit": "10000"},
    timeout=60,
)
r.raise_for_status()
df = pd.DataFrame(r.json())

num = ["times_offered","times_picked","times_skipped","pick_rate","offered_3c",
       "picked_3c","pick_rate_3c","runs_with_card","wins_with_card",
       "deck_winrate","times_upgraded","upgrade_rate"]
for c in num:
    df[c] = pd.to_numeric(df[c], errors="coerce")

KNOWN = {"HERMIT","GUARDIAN","AUTOMATON","AWAKENED","SNECKO","CHAMP","HEXAGHOST","SLIMEBOSS"}
df["character"] = df["card"].str.split("-", n=1).str[0].where(
    lambda s: s.isin(KNOWN), "COLORLESS")
df["short"] = df["card"].str.split("-", n=1).str[-1]

# ---- palette ----
S, V = 0.65, 0.80
ORDER = ["HERMIT-HERMIT","GUARDIAN-GUARDIAN","AUTOMATON-AUTOMATON","SLIMEBOSS-SLIME_BOSS",
         "SNECKO-SNECKO","AWAKENED-AWAKENED","CHAMP-CHAMP","HEXAGHOST-HEXAGHOST"]
CHAR_ORDER = [c.split("-")[0] for c in ORDER]
COLORS = {}
for i, name in enumerate(CHAR_ORDER):
    rr, gg, bb = colorsys.hsv_to_rgb(i/len(CHAR_ORDER), S, V)
    COLORS[name] = f"#{int(rr*255):02X}{int(gg*255):02X}{int(bb*255):02X}"
COLORS["COLORLESS"] = "#999999"

# ---- build figure ----
MIN_OFFER, MIN_RUNS = 20, 20
LABEL_SIZE = 13
s_df = df[(df.offered_3c >= MIN_OFFER) & (df.runs_with_card >= MIN_RUNS)
          & df.pick_rate_3c.notna() & df.deck_winrate.notna()].copy()
chars = [c for c in CHAR_ORDER if c in s_df.character.unique()]
mx, my = s_df.pick_rate_3c.median(), s_df.deck_winrate.median()

fig = go.Figure()
for ch in chars:
    s = s_df[s_df.character == ch]
    fig.add_trace(go.Scatter(
        x=s.pick_rate_3c, y=s.deck_winrate, mode="markers+text",
        name=f"{ch} ({len(s)})",
        marker=dict(size=(s.times_offered**0.5)*0.9, sizemin=3,
                    color=COLORS[ch], opacity=0.6, line=dict(width=0)),
        text=s.short, textposition="top center",
        textfont=dict(size=LABEL_SIZE, color=COLORS[ch]),
        customdata=s[["short","times_offered","offered_3c","runs_with_card",
                      "deck_winrate","pick_rate_3c"]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "pick rate (3c): %{customdata[5]:.1%}<br>"
            "deck winrate: %{customdata[4]:.1%}<br>"
            "offered: %{customdata[1]}  ·  runs: %{customdata[3]}"
            "<extra>"+ch+"</extra>"),
    ))

fig.add_vline(x=mx, line=dict(color="grey", dash="dash", width=1))
fig.add_hline(y=my, line=dict(color="grey", dash="dash", width=1))

updated = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC")
fig.update_layout(
    title=f"Card draft-priority vs performance — click a character to toggle · updated {updated}",
    xaxis_title="pick rate (3-card)", yaxis_title="deck winrate",
    xaxis=dict(tickformat=".0%", range=[0, 1], constrain="domain"),
    yaxis=dict(tickformat=".0%", range=[0, 1], constrain="domain"),
    legend=dict(title="Character (click to hide/show)"),
    template="plotly_white", autosize=True,
)

os.makedirs("public", exist_ok=True)
fig.write_html("public/index.html", include_plotlyjs="cdn",
               full_html=True, default_width="100%", default_height="95vh",
               config={"scrollZoom": True, "responsive": True})
print("wrote public/index.html")
