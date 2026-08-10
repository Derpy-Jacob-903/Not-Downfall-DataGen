import pandas as pd
import plotly.graph_objects as go
from config import CHAR_ORDER, COLORS


def _shade(hex_color: str, factor: float) -> str:
    """factor > 0 lightens toward white, < 0 darkens toward black."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if factor >= 0:
        r = r + (255 - r) * factor
        g = g + (255 - g) * factor
        b = b + (255 - b) * factor
    else:
        f = 1 + factor
        r, g, b = r * f, g * f, b * f
    return f"#{int(r):02X}{int(g):02X}{int(b):02X}"


RARITY_SHADE = {
    "Basic":    0.35,
    "Common":   0.22,
    "Uncommon": 0.0,
    "Rare":    -0.28,
    "Token":    0.22,
    "Ancient": -0.28,
}

RARITY_SYMBOL = {
    "Basic":    "circle-open",
    "Common":   "circle",
    "Uncommon": "diamond",
    "Rare":     "star",
    "Token":    "cross",
    "Ancient":  "hexagram",
}

MARKER_SIZE = 12   # <- single size knob for the card scatter


def _fig_cards(df: pd.DataFrame, winrate_col: str, runs_col: str, title_suffix: str) -> go.Figure:
    strike_rows = df[df["short"].str.startswith("STRIKE", na=False) & df["times_offered"].isna()].copy()
    strike = strike_rows.sort_values(runs_col, ascending=False).groupby("character")[winrate_col].first()

    s_df = df[(df.offered_3c >= 10) & (df[runs_col] >= 10) & df.pick_rate_3c.notna() & df[winrate_col].notna()].copy()
    if s_df.empty:
        raise ValueError(f"No cards clear the gate for {winrate_col}")

    chars = [c for c in CHAR_ORDER if c in s_df.character.unique()]
    mx, my = s_df.pick_rate_3c.median(), s_df[winrate_col].median()

    RARITIES = ["All", "Common", "Uncommon", "Rare"]

    fig = go.Figure()
    # one trace per character (legend behaves exactly as before)
    for ch in chars:
        s = s_df[s_df.character == ch]
        base = COLORS[ch]
        point_colors = [_shade(base, RARITY_SHADE.get(r, 0.0)) for r in s["rarity"]]
        symbols = s["rarity"].map(RARITY_SYMBOL).fillna("circle").tolist()
        fig.add_trace(go.Scatter(
            x=s.pick_rate_3c, y=s[winrate_col], mode="markers+text",
            name=f"{ch} ({len(s)})", legendgroup=ch,
            marker=dict(size=MARKER_SIZE, sizemode="diameter",
                        color=point_colors, opacity=0.6,
                        symbol=symbols, line=dict(width=1.5, color=point_colors)),
            text=s.label, textposition="top center",
            textfont=dict(size=11, color=base),
            customdata=s[["label", "times_offered", runs_col, winrate_col,
                          "pick_rate_3c", "rarity", "type", "cost", "description"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b> · %{customdata[5]} %{customdata[6]} · %{customdata[7]} energy<br>"
                "pick 3c: %{customdata[4]:.1%}<br>"
                "winrate: %{customdata[3]:.1%}<br>"
                "offered %{customdata[1]} · runs %{customdata[2]}<br>"
                "<i>%{customdata[8]}</i>"
                f"<extra>{ch}</extra>"
            )
        ))

    n_char_traces = len(chars)

    # build the rarity dropdown: each option restyles x/y/text/marker of the char traces
    buttons = []
    for rar in RARITIES:
        xs, ys, texts, colors, syms, cds = [], [], [], [], [], []
        for ch in chars:
            s = s_df[s_df.character == ch]
            if rar != "All":
                s = s[s["rarity"] == rar]
            base = COLORS[ch]
            xs.append(s.pick_rate_3c.tolist())
            ys.append(s[winrate_col].tolist())
            texts.append(s.label.tolist())
            colors.append([_shade(base, RARITY_SHADE.get(r, 0.0)) for r in s["rarity"]])
            syms.append(s["rarity"].map(RARITY_SYMBOL).fillna("circle").tolist())
            cds.append(s[["label", "times_offered", runs_col, winrate_col,
                          "pick_rate_3c", "rarity", "type", "cost", "description"]].values)
        buttons.append(dict(
            label=rar, method="restyle",
            args=[{"x": xs, "y": ys, "text": texts,
                   "marker.color": colors, "marker.symbol": syms,
                   "customdata": cds},
                  list(range(n_char_traces))]   # only touch the character traces
        ))

    # strike baselines (added AFTER, so the dropdown's trace-index list never touches them)
    for ch in chars:
        if ch in strike.index and pd.notna(strike[ch]):
            fig.add_trace(go.Scatter(
                x=[0, 1], y=[strike[ch], strike[ch]], mode="lines",
                line=dict(color=COLORS[ch], dash="dot", width=1.5), opacity=0.6,
                legendgroup=ch, showlegend=False,
                hovertemplate=f"{ch} Strike baseline: %{{y:.1%}}<extra></extra>"
            ))

    fig.add_vline(x=mx, line=dict(color="grey", dash="dash", width=1))
    fig.add_hline(y=my, line=dict(color="grey", dash="dash", width=1))
    fig.update_layout(
        template="plotly_white", autosize=True,
        title=f"Card draft-priority vs performance{title_suffix} — dotted line = Strike winrate · shape = rarity",
        xaxis=dict(title="pick rate (3-card)", tickformat=".0%", range=[0, 1], constrain="domain"),
        yaxis=dict(title="deck winrate", tickformat=".0%", range=[0, 1], constrain="domain"),
        legend=dict(title="Character (click to toggle)"),
        updatemenus=[dict(
            buttons=buttons, direction="down", showactive=True,
            x=1.0, xanchor="right", y=1.12, yanchor="top",
            pad=dict(l=4, r=4, t=2, b=2),
        )],
        annotations=[dict(text="Rarity:", x=0.82, xref="paper",
                          y=1.11, yref="paper", showarrow=False,
                          xanchor="right", yanchor="top")],
    )
    return fig


def fig_cards(df: pd.DataFrame) -> go.Figure:
    return _fig_cards(df, "deck_winrate", "runs_with_card", "")


def fig_cards_sp(df: pd.DataFrame) -> go.Figure:
    return _fig_cards(df, "sp_deck_winrate", "sp_runs_with_card", " · singleplayer")


def fig_cards_mp(df: pd.DataFrame) -> go.Figure:
    return _fig_cards(df, "mp_deck_winrate", "mp_runs_with_card", " · multiplayer")


def fig_cards_sp_vs_mp(df: pd.DataFrame, min_runs: int = 10) -> go.Figure:
    s = df[(df.sp_runs_with_card >= min_runs) & (df.mp_runs_with_card >= min_runs)
           & df.sp_deck_winrate.notna() & df.mp_deck_winrate.notna()].copy()
    if s.empty:
        raise ValueError("No cards clear both SP and MP run gates")
    s["gap"] = s.mp_deck_winrate - s.sp_deck_winrate

    fig = go.Figure()
    for ch in CHAR_ORDER:
        cs = s[s.character == ch]
        if cs.empty:
            continue
        fig.add_trace(go.Scatter(
            x=cs.sp_deck_winrate, y=cs.mp_deck_winrate, mode="markers+text",
            name=f"{ch} ({len(cs)})", legendgroup=ch,
            marker=dict(size=8, color=COLORS[ch], opacity=0.65, line=dict(width=0)),
            text=cs.label, textposition="top center", textfont=dict(size=9, color=COLORS[ch]),
            customdata=cs[["label", "sp_deck_winrate", "mp_deck_winrate", "sp_runs_with_card", "mp_runs_with_card", "gap"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "SP %{customdata[1]:.1%} (n=%{customdata[3]})<br>"
                "MP %{customdata[2]:.1%} (n=%{customdata[4]})<br>"
                f"gap %{{customdata[5]:+.1%}}<extra>{ch}</extra>"
            )
        ))
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1], mode="lines",
        line=dict(color="grey", dash="dash", width=1), name="equal", hoverinfo="skip", showlegend=False
    ))
    fig.update_layout(
        template="plotly_white", autosize=True,
        title=f"Card winrate: singleplayer vs multiplayer (≥{min_runs} runs each · above line = stronger in MP)",
        xaxis=dict(title="singleplayer deck winrate", tickformat=".0%", range=[0, 1], constrain="domain"),
        yaxis=dict(title="multiplayer deck winrate", tickformat=".0%", range=[0, 1], scaleanchor="x", scaleratio=1),
        legend=dict(title="Character (click to toggle)")
    )
    return fig