def render_html(buttons: list[str], panels: list[str], updated_timestamp: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8">
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
<div class="tabs">{''.join(buttons)}<span class="stamp">updated {updated_timestamp}</span></div>
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