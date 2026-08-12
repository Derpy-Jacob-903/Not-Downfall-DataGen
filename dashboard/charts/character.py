import pandas as pd
import plotly.graph_objects as go
from config import ORDER, COLORS
from data import fetch, load_vanilla_ascension, load_vanilla_over_time


VANILLA_CHAR_COLORS = {
    "ironclad":    "#D62000",
    "silent":      "#5EBD00",
    "defect":      "#3EB3ED",
    "necrobinder": "#CD4EED",
    "regent":      "#E36600",
}


def _fig_ascension(df, winrate_col, runs_col, van_cumulative, title, x_label):
    for c in ["min_ascension", winrate_col, runs_col]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    fig = go.Figure()
    for full in ORDER:
        s = df[df.character == full].sort_values("min_ascension")
        if s.empty:
            continue
        ch = full.split("-")[0]
        fig.add_trace(go.Scatter(
            x=s.min_ascension, y=s[winrate_col], mode="lines+markers",
            name=full, line=dict(color=COLORS[ch], width=2),
            customdata=s[[runs_col]].values,
            hovertemplate=f"{x_label} %{{x}}<br>winrate %{{y:.1%}}<br>n=%{{customdata[0]}}<extra>{full}</extra>"
        ))

    van = load_vanilla_ascension(cumulative=van_cumulative)
    for cid, color in VANILLA_CHAR_COLORS.items():
        s = van[van["character"] == cid].sort_values("ascension")
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=s["ascension"], y=s["winrate"], mode="lines",
            name=f"base: {cid}", line=dict(color=color, width=1.5, dash="dot"),
            opacity=0.7, legendgroup="vanilla",
            customdata=s[["runs"]].values,
            hovertemplate=f"{x_label} %{{x}}<br>winrate %{{y:.1%}}<br>n=%{{customdata[0]}}<extra>base: {cid}</extra>"
        ))

    fig.update_layout(
        template="plotly_white", autosize=True,
        title=title,
        xaxis=dict(title="ascension", dtick=1),
        yaxis=dict(title="winrate", tickformat=".0%"),
        legend=dict(title="Character (click to toggle)")
    )
    return fig


def fig_ascension() -> go.Figure:
    return _fig_ascension(
        fetch("character_stats"),
        winrate_col="total_winrate", runs_col="total_runs",
        van_cumulative=False,
        title="Winrate at each ascension — solid = Downfall · dotted = base game",
        x_label="asc")


def fig_ascension_cum() -> go.Figure:
    return _fig_ascension(
        fetch("character_stats"),
        winrate_col="total_min_winrate", runs_col="total_cum_runs",
        van_cumulative=True,
        title="Cumulative winrate at ascension ≥ X — solid = Downfall · dotted = base game",
        x_label="asc ≥")


def fig_daily(min_runs: int = 5) -> go.Figure:
    df = fetch("daily_winrate")
    for c in ["runs", "wins", "winrate"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["day"] = pd.to_datetime(df["day"])
    df = df[df.runs >= min_runs]

    fig = go.Figure()
    for full in ORDER:
        s = df[df.character == full].sort_values("day")
        if s.empty:
            continue
        ch = full.split("-")[0]
        fig.add_trace(go.Scatter(
            x=s.day, y=s.winrate, mode="lines+markers",
            name=full, line=dict(color=COLORS[ch], width=2),
            customdata=s[["runs"]].values,
            hovertemplate=f"%{{x|%Y-%m-%d}}<br>winrate %{{y:.1%}}<br>n=%{{customdata[0]}}<extra>{full}</extra>"
        ))
    van = load_vanilla_over_time()
    cutoff = df["day"].min() - pd.Timedelta(days=7)
    van = van[van["week"] >= cutoff]

    x_span = [df["day"].min(), df["day"].max()]  # span for drawing a lone week flat

    for cid, color in VANILLA_CHAR_COLORS.items():
        s = van[van["character"] == cid].sort_values("week")
        if s.empty:
            continue
        if len(s) == 1:
            # only one weekly point in range -> draw it as a flat reference line
            wr = s["winrate"].iloc[0]
            wk = s["week"].iloc[0]
            fig.add_trace(go.Scatter(
                x=x_span, y=[wr, wr], mode="lines",
                name=f"base: {cid}", line=dict(color=color, width=1.5, dash="dot"),
                opacity=0.7, legendgroup="vanilla",
                hovertemplate=(f"week of {wk:%Y-%m-%d}<br>winrate {wr:.1%}"
                               f"<extra>base: {cid}</extra>")
            ))
        else:
            # two or more weeks -> normal connecting line
            fig.add_trace(go.Scatter(
                x=s.week, y=s.winrate, mode="lines",
                name=f"base: {cid}", line=dict(color=color, width=1.5, dash="dot"),
                opacity=0.7, legendgroup="vanilla",
                customdata=s[["runs"]].values,
                hovertemplate=("%{x|%Y-%m-%d}<br>winrate %{y:.1%}"
                               "<br>n=%{customdata[0]}<extra>base: " + cid + "</extra>")
            ))
    fig.update_layout(
        template="plotly_white", autosize=True,
        title=f"Daily winrate per character (days with ≥{min_runs} runs)",
        xaxis=dict(title="upload date"),
        yaxis=dict(title="winrate", tickformat=".0%"),
        legend=dict(title="Character (click to toggle)")
    )
    return fig


def fig_survival() -> go.Figure:
    df = fetch("floor_survival")
    for c in ["min_floor_reached", "frac_surviving", "total_runs"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    totals = df.groupby("character")["total_runs"].first()

    fig = go.Figure()
    for full in ORDER:
        s = df[df.character == full].sort_values("min_floor_reached")
        if s.empty:
            continue
        ch = full.split("-")[0]
        fig.add_trace(go.Scatter(
            x=s.min_floor_reached, y=s.frac_surviving, mode="lines",
            name=f"{full} (n={int(totals.get(full, 0))})",
            line=dict(color=COLORS[ch], width=2),
            hovertemplate=f"floor ≥ %{{x}}<br>surviving %{{y:.1%}}<extra>{full}</extra>"
        ))
    fig.update_layout(
        template="plotly_white", autosize=True,
        title="Fraction of runs surviving to each floor",
        xaxis=dict(title="min floor reached"),
        yaxis=dict(title="fraction surviving", tickformat=".0%"),
        legend=dict(title="Character (click to toggle)")
    )
    return fig