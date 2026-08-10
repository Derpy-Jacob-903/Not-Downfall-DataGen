import os
import pandas as pd
import plotly.io as pio

from charts import get_tabs
from template import render_html


def build():
    updated = pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M UTC")
    tabs = get_tabs()

    buttons, panels, first_ok = [], [], True
    for tab in tabs:
        try:
            figure = tab.builder()
        except Exception as e:
            print(f"Skipping tab '{tab.id}': {e}")
            continue

        div = pio.to_html(
            figure,
            include_plotlyjs=("cdn" if first_ok else False),
            full_html=False,
            div_id=f"plot-{tab.id}",
            default_height="88vh",
            config={"scrollZoom": True, "responsive": True}
        )
        buttons.append(
            f'<button class="tab-btn{" active" if first_ok else ""}" '
            f'onclick="showTab(\'{tab.id}\',this)">{tab.label}</button>'
        )
        panels.append(
            f'<div id="{tab.id}" class="tab-content"'
            f'{"" if first_ok else " style=\"display:none\""}>{div}</div>'
        )
        first_ok = False

    if not panels:
        raise SystemExit("No tabs built — every view failed to fetch or render.")

    html = render_html(buttons, panels, updated)

    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w") as f:
        f.write(html)
    print("Successfully generated public/index.html")


if __name__ == "__main__":
    build()