#!/usr/bin/env python3
import os, colorsys, requests
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

KEY = os.environ["SUPABASE_SECRET_KEY"]
SUPABASE_URL = "https://wxememsxgrgrfvntulgr.supabase.co"

def fetch(view):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{view}",
                     headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"},
                     params={"select": "*", "limit": "100000"}, timeout=90)
    r.raise_for_status()
    return pd.DataFrame(r.json())

# ---- shared palette ----
S, V = 0.65, 0.80
ORDER = ["HERMIT-HERMIT","GUARDIAN-GUARDIAN","AUTOMATON-AUTOMATON","SLIMEBOSS-SLIME_BOSS",
         "SNECKO-SNECKO","AWAKENED-AWAKENED","CHAMP-CHAMP","HEXAGHOST-HEXAGHOST"]
CHAR_ORDER = [c.split("-")[0] for c in ORDER]
COLORS = {}
for i, name in enumerate(CHAR_ORDER):
    rr, gg, bb = colorsys.hsv_to_rgb(i/len(CHAR_ORDER), S, V)
    COLORS[name] = f"#{int(rr*255):02X}{int(gg*255):02X}{int(bb*255):02X}"
COLORS["COLORLESS"] = "#999999"

def char_of(card):
    p = str(card).split("-", 1)[0]
    return p if p in set(CHAR_ORDER) else "COLORLESS"

# ---- card_stats fetched ONCE, prepped once, reused by all card tabs ----
def prep_cards():
    df = fetch("card_stats")
    numeric = ["times_offered","offered_3c","runs_with_card","deck_winrate","pick_rate_3c",
               "sp_runs_with_card","sp_deck_winrate","mp_runs_with_card","mp_deck_winrate"]
    for c in numeric:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["character"] = df["card"].map(char_of)
    df["short"] = df["card"].str.split("-", n=1).str[-1]
    return df

# ================= card explorer (parameterized) =================
def _fig_cards(df, winrate_col, runs_col, title_suffix):
    strike_rows = df[df["short"].str.startswith("STRIKE", na=False)
                     & df["times_offered"].isna()].copy()
    strike = (strike_rows.sort_values(runs_col, ascending=False)
                         .groupby("character")[winrate_col].first())

    s_df = df[(df.offered_3c >= 10) & (df[runs_col] >= 10)
              & df.pick_rate_3c.notna() & df[winrate_col].notna()].copy()
    if s_df.empty:
        raise ValueError(f"no cards clear the gate for {winrate_col}")
    chars = [c for c in CHAR_ORDER if c in s_df.character.unique()]
    mx, my = s_df.pick_rate_3c.median(), s_df[winrate_col].median()

    fig = go.Figure()
    for ch in chars:
        s = s_df[s_df.character == ch]
        fig.add_trace(go.Scatter(
            x=s.pick_rate_3c, y=s[winrate_col], mode="markers+text",
            name=f"{ch} ({len(s)})", legendgroup=ch,
            marker=dict(size=(s.times_offered**0.5)*0.9, sizemin=3,
                        color=COLORS[ch], opacity=0.6, line=dict(width=0)),
            text=s.short, textposition="top center",
            textfont=dict(size=11, color=COLORS[ch]),
            customdata=s[["short","times_offered",runs_col,
                          winrate_col,"pick_rate_3c"]].values,
            hovertemplate=("<b>%{customdata[0]}</b><br>pick 3c: %{customdata[4]:.1%}<br>"
                           "winrate: %{customdata[3]:.1%}<br>offered %{customdata[1]} · "
                           "runs %{customdata[2]}<extra>"+ch+"</extra>")))

    for ch in chars:
        if ch in strike.index and pd.notna(strike[ch]):
            fig.add_trace(go.Scatter(
                x=[0, 1], y=[strike[ch], strike[ch]], mode="lines",
                line=dict(color=COLORS[ch], dash="dot", width=1.5),
                opacity=0.6, name=f"{ch} Strike",
                legendgroup=ch, showlegend=False,
                hovertemplate=f"{ch} Strike baseline: %{{y:.1%}}<extra></extra>"))

    fig.add_vline(x=mx, line=dict(color="grey", dash="dash", width=1))
    fig.add_hline(y=my, line=dict(color="grey", dash="dash", width=1))
    fig.update_layout(template="plotly_white", autosize=True,
        title=f"Card draft-priority vs performance{title_suffix} — dotted line = Strike winrate",
        xaxis=dict(title="pick rate (3-card)", tickformat=".0%", range=[0,1], constrain="domain"),
        yaxis=dict(title="deck winrate", tickformat=".0%", range=[0,1], constrain="domain"),
        legend=dict(title="Character (click to toggle)"))
    return fig

def fig_cards(df):    return _fig_cards(df, "deck_winrate",    "runs_with_card",    "")
def fig_cards_sp(df): return _fig_cards(df, "sp_deck_winrate", "sp_runs_with_card", " · singleplayer")
def fig_cards_mp(df): return _fig_cards(df, "mp_deck_winrate", "mp_runs_with_card", " · multiplayer")

def fig_cards_sp_vs_mp(df, min_runs=10):
    s = df[(df.sp_runs_with_card >= min_runs) & (df.mp_runs_with_card >= min_runs)
           & df.sp_deck_winrate.notna() & df.mp_deck_winrate.notna()].copy()
    if s.empty:
        raise ValueError("no cards clear both SP and MP run gates")
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
            text=cs.short, textposition="top center", textfont=dict(size=9, color=COLORS[ch]),
            customdata=cs[["short","sp_deck_winrate","mp_deck_winrate",
                           "sp_runs_with_card","mp_runs_with_card","gap"]].values,
            hovertemplate=("<b>%{customdata[0]}</b><br>"
                           "SP %{customdata[1]:.1%} (n=%{customdata[3]})<br>"
                           "MP %{customdata[2]:.1%} (n=%{customdata[4]})<br>"
                           "gap %{customdata[5]:+.1%}<extra>"+ch+"</extra>")))
    fig.add_trace(go.Scatter(x=[0,1], y=[0,1], mode="lines",
                             line=dict(color="grey", dash="dash", width=1),
                             name="equal", hoverinfo="skip", showlegend=False))
    fig.update_layout(template="plotly_white", autosize=True,
        title=f"Card winrate: singleplayer vs multiplayer (≥{min_runs} runs each · "
              "above line = stronger in MP)",
        xaxis=dict(title="singleplayer deck winrate", tickformat=".0%",
                   range=[0,1], constrain="domain"),
        yaxis=dict(title="multiplayer deck winrate", tickformat=".0%",
                   range=[0,1], scaleanchor="x", scaleratio=1),
        legend=dict(title="Character (click to toggle)"))
    return fig

# ================= non-card tabs (unchanged) =================
def fig_ascension():
    df = fetch("character_stats")
    for c in ["min_ascension","total_min_winrate","total_cum_runs"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    fig = go.Figure()
    for full in ORDER:
        s = df[df.character == full].sort_values("min_ascension")
        if s.empty: continue
        ch = full.split("-")[0]
        fig.add_trace(go.Scatter(
            x=s.min_ascension, y=s.total_min_winrate, mode="lines+markers",
            name=full, line=dict(color=COLORS[ch], width=2),
            customdata=s[["total_cum_runs"]].values,
            hovertemplate=("asc ≥ %{x}<br>winrate %{y:.1%}<br>"
                           "n=%{customdata[0]}<extra>"+full+"</extra>")))
    fig.update_layout(template="plotly_white", autosize=True,
        title="Cumulative winrate at ascension ≥ X",
        xaxis=dict(title="ascension floor (≥)", dtick=1),
        yaxis=dict(title="winrate", tickformat=".0%"),
        legend=dict(title="Character (click to toggle)"))
    return fig

def fig_daily(min_runs=5):
    df = fetch("daily_winrate")
    for c in ["runs","wins","winrate"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["day"] = pd.to_datetime(df["day"])
    df = df[df.runs >= min_runs]
    fig = go.Figure()
    for full in ORDER:
        s = df[df.character == full].sort_values("day")
        if s.empty: continue
        ch = full.split("-")[0]
        fig.add_trace(go.Scatter(
            x=s.day, y=s.winrate, mode="lines+markers",
            name=full, line=dict(color=COLORS[ch], width=2),
            customdata=s[["runs"]].values,
            hovertemplate=("%{x|%Y-%m-%d}<br>winrate %{y:.1%}<br>"
                           "n=%{customdata[0]}<extra>"+full+"</extra>")))
    fig.update_layout(template="plotly_white", autosize=True,
        title=f"Daily winrate per character (days with ≥{min_runs} runs)",
        xaxis=dict(title="upload date"),
        yaxis=dict(title="winrate", tickformat=".0%"),
        legend=dict(title="Character (click to toggle)"))
    return fig

def fig_survival():
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
            hovertemplate=("floor ≥ %{x}<br>surviving %{y:.1%}"
                           "<extra>"+full+"</extra>")))
    fig.update_layout(template="plotly_white", autosize=True,
        title="Fraction of runs surviving to each floor",
        xaxis=dict(title="min floor reached"),
        yaxis=dict(title="fraction surviving", tickformat=".0%"),
        legend=dict(title="Character (click to toggle)"))
    return fig

def fig_relics():
    df = fetch("relic_stats")
    for c in ["runs_with_relic","relic_winrate"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["character"] = df["relic"].map(char_of)   # vanilla -> "COLORLESS"
    df["short"] = df["relic"].str.split("-", n=1).str[-1]
    df["is_vanilla"] = df["character"] == "COLORLESS"

    s = df[(df.runs_with_relic >= 20) & df.relic_winrate.notna()].copy()
    if s.empty:
        raise ValueError("no relics clear the run gate")

    fig = go.Figure()
    # vanilla relics as one grey series (drawn first, so char relics sit on top)
    van = s[s.is_vanilla]
    if not van.empty:
        fig.add_trace(go.Scatter(
            x=van.runs_with_relic, y=van.relic_winrate, mode="markers",
            name=f"vanilla ({len(van)})", legendgroup="vanilla",
            marker=dict(size=7, color="#999999", opacity=0.4, line=dict(width=0)),
            customdata=van[["short","runs_with_relic","relic_winrate"]].values,
            hovertemplate=("<b>%{customdata[0]}</b><br>winrate %{customdata[2]:.1%}<br>"
                           "runs %{customdata[1]}<extra>vanilla</extra>")))
    # character relics, colored + labeled
    for ch in CHAR_ORDER:
        cs = s[s.character == ch]
        if cs.empty:
            continue
        fig.add_trace(go.Scatter(
            x=cs.runs_with_relic, y=cs.relic_winrate, mode="markers+text",
            name=f"{ch} ({len(cs)})", legendgroup=ch,
            marker=dict(size=10, color=COLORS[ch], opacity=0.75, line=dict(width=0)),
            text=cs.short, textposition="top center", textfont=dict(size=9, color=COLORS[ch]),
            customdata=cs[["short","runs_with_relic","relic_winrate"]].values,
            hovertemplate=("<b>%{customdata[0]}</b><br>winrate %{customdata[2]:.1%}<br>"
                           "runs %{customdata[1]}<extra>"+ch+"</extra>")))

    fig.update_layout(template="plotly_white", autosize=True,
        title="Relic winrate vs sample size — vanilla (grey) vs character relics (≥20 runs)",
        xaxis=dict(title="runs with relic", type="log"),
        yaxis=dict(title="winrate", tickformat=".0%", range=[0,1]),
        legend=dict(title="Relic set (click to toggle)"))
    return fig
    
# ================= build =================
def build():
    updated = pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M UTC")

    # fetch the heavy view ONCE, share it across all card tabs
    try:
        cards_df = prep_cards()
    except Exception as e:
        print(f"card_stats fetch failed, all card tabs skipped: {e}")
        cards_df = None

    TABS = []
    if cards_df is not None:
        TABS += [
            ("cards",    "Card explorer",        lambda: fig_cards(cards_df)),
            ("cards_sp", "Cards · singleplayer", lambda: fig_cards_sp(cards_df)),
            ("cards_mp", "Cards · multiplayer",  lambda: fig_cards_mp(cards_df)),
            ("cards_gap","Cards · SP vs MP",     lambda: fig_cards_sp_vs_mp(cards_df)),
        ]
    TABS += [
        ("ascension", "Winrate × ascension", fig_ascension),
        ("daily",     "Winrate × day",       fig_daily),
        ("survival",  "Floor survival",      fig_survival),
        ("relics", "Relic winrate", fig_relics),
    ]

    buttons, panels, first_ok = [], [], True
    for tid, label, fn in TABS:
        try:
            figure = fn()
        except Exception as e:
            print(f"skipping tab '{tid}': {e}")
            continue
        div = pio.to_html(figure,
                          include_plotlyjs=("cdn" if first_ok else False),
                          full_html=False, div_id=f"plot-{tid}",
                          default_height="88vh",
                          config={"scrollZoom": True, "responsive": True})
        buttons.append(
            f'<button class="tab-btn{" active" if first_ok else ""}" '
            f'onclick="showTab(\'{tid}\',this)">{label}</button>')
        panels.append(
            f'<div id="{tid}" class="tab-content"'
            f'{"" if first_ok else " style=\"display:none\""}>{div}</div>')
        first_ok = False

    if not panels:
        raise SystemExit("no tabs built — every view failed to fetch")

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Downfall data</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 0; }}
  .tabs {{ display:flex; gap:4px; padding:8px 12px; background:#f4f4f4;
           border-bottom:1px solid #ddd; align-items:center; flex-wrap:wrap; }}
  .tab-btn {{ padding:8px 16px; border:none; background:#e2e2e2; border-radius:6px;
              cursor:pointer; font-size:14px; }}
  .tab-btn.active {{ background:#333; color:#fff; }}
  .stamp {{ margin-left:auto; color:#888; font-size:12px; }}
  .tab-content {{ padding:0 8px; }}
</style></head><body>
<div class="tabs">{''.join(buttons)}<span class="stamp">updated {updated}</span></div>
{''.join(panels)}
<script>
function showTab(id, btn) {{
  document.querySelectorAll('.tab-content').forEach(e => e.style.display='none');
  document.querySelectorAll('.tab-btn').forEach(e => e.classList.remove('active'));
  document.getElementById(id).style.display='block';
  btn.classList.add('active');
  document.querySelectorAll('#'+id+' .plotly-graph-div')
          .forEach(gd => window.Plotly && Plotly.Plots.resize(gd));
}}
</script></body></html>"""

    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w") as f:
        f.write(html)
    print("wrote public/index.html")

if __name__ == "__main__":
    build()
