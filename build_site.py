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

# ================= PLOT 1: card explorer =================
def fig_cards():
    df = fetch("card_stats")
    for c in ["times_offered","offered_3c","runs_with_card","deck_winrate","pick_rate_3c"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["character"] = df["card"].map(char_of)
    df["short"] = df["card"].str.split("-", n=1).str[-1]
    s_df = df[(df.offered_3c >= 20) & (df.runs_with_card >= 20)
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
            textfont=dict(size=11, color=COLORS[ch]),
            customdata=s[["short","times_offered","runs_with_card",
                          "deck_winrate","pick_rate_3c"]].values,
            hovertemplate=("<b>%{customdata[0]}</b><br>pick 3c: %{customdata[4]:.1%}<br>"
                           "winrate: %{customdata[3]:.1%}<br>offered %{customdata[1]} · "
                           "runs %{customdata[2]}<extra>"+ch+"</extra>")))
    fig.add_vline(x=mx, line=dict(color="grey", dash="dash", width=1))
    fig.add_hline(y=my, line=dict(color="grey", dash="dash", width=1))
    fig.update_layout(template="plotly_white", autosize=True,
        title="Card draft-priority vs performance",
        xaxis=dict(title="pick rate (3-card)", tickformat=".0%", range=[0,1], constrain="domain"),
        yaxis=dict(title="deck winrate", tickformat=".0%", range=[0,1], constrain="domain"),
        legend=dict(title="Character (click to toggle)"))
    return fig

# ================= PLOT 2: winrate over min ascension =================
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

# ================= PLOT 3: daily winrate =================
def fig_daily(min_runs=5):
    df = fetch("daily_winrate")
    for c in ["runs","wins","winrate"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["day"] = pd.to_datetime(df["day"])
    df = df[df.runs >= min_runs]                 # drop thin days that are pure noise
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

# ================= stitch into a tabbed page =================
TABS = [
    ("cards",     "Card explorer",      fig_cards),
    ("ascension", "Winrate × ascension", fig_ascension),
    ("daily",     "Winrate × day",      fig_daily),
]

def build():
    updated = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    buttons, panels = [], []
    for i, (tid, label, fn) in enumerate(TABS):
        first = (i == 0)
        div = pio.to_html(fn(), include_plotlyjs=("cdn" if first else False),
                          full_html=False, div_id=f"plot-{tid}",
                          default_height="88vh",
                          config={"scrollZoom": True, "responsive": True})
        buttons.append(
            f'<button class="tab-btn{" active" if first else ""}" '
            f'onclick="showTab(\'{tid}\',this)">{label}</button>')
        panels.append(
            f'<div id="{tid}" class="tab-content"'
            f'{"" if first else " style=\"display:none\""}>{div}</div>')

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
