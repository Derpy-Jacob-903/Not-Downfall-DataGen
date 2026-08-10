import pandas as pd
import plotly.graph_objects as go
from config import CHAR_ORDER, COLORS, char_of
from data import fetch


def fig_relics() -> go.Figure:
    df = fetch("relic_stats")
    for c in ["runs_with_relic", "relic_winrate"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["character"] = df["relic"].map(char_of)
    df["short"] = df["relic"].str.split("-", n=1).str[-1]
    df["is_vanilla"] = df["character"] == "COLORLESS"

    s = df[(df.runs_with_relic >= 20) & df.relic_winrate.notna()].copy()
    if s.empty:
        raise ValueError("No relics clear the run gate")

    fig = go.Figure()
    van = s[s.is_vanilla]
    if not van.empty:
        fig.add_trace(go.Scatter(
            x=van.runs_with_relic, y=van.relic_winrate, mode="markers",
            name=f"vanilla ({len(van)})", legendgroup="vanilla",
            marker=dict(size=7, color="#999999", opacity=0.4, line=dict(width=0)),
            customdata=van[["short", "runs_with_relic", "relic_winrate"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>winrate %{customdata[2]:.1%}<br>runs %{customdata[1]}<extra>vanilla</extra>"
        ))

    for ch in CHAR_ORDER:
        cs = s[s.character == ch]
        if cs.empty:
            continue
        fig.add_trace(go.Scatter(
            x=cs.runs_with_relic, y=cs.relic_winrate, mode="markers+text",
            name=f"{ch} ({len(cs)})", legendgroup=ch,
            marker=dict(size=10, color=COLORS[ch], opacity=0.75, line=dict(width=0)),
            text=cs.short, textposition="top center", textfont=dict(size=9, color=COLORS[ch]),
            customdata=cs[["short", "runs_with_relic", "relic_winrate"]].values,
            hovertemplate=f"<b>%{{customdata[0]}}</b><br>winrate %{{customdata[2]:.1%}}<br>runs %{{customdata[1]}}<extra>{ch}</extra>"
        ))

    fig.update_layout(
        template="plotly_white", autosize=True,
        title="Relic winrate vs sample size — vanilla (grey) vs character relics (≥20 runs)",
        xaxis=dict(title="runs with relic", type="log"),
        yaxis=dict(title="winrate", tickformat=".0%", range=[0, 1]),
        legend=dict(title="Relic set (click to toggle)")
    )
    return fig