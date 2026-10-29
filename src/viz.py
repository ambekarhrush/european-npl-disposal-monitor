"""Figures and the self-contained HTML dashboard."""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from . import config as C
from . import eba_data, ranking as ranking_mod

# Muted, print-safe palette. Country is the only categorical encoding, so four
# hues is the entire requirement.
COUNTRY_COLOR = {
    "IT": "#2E7D7B",
    "ES": "#C9663E",
    "DE": "#3D5A80",
    "FR": "#8A7A4E",
}
GRID = "#E6E3DD"
INK = "#1F2421"
MUTED = "#6B6F6D"

_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(family="Inter, Helvetica Neue, Arial, sans-serif", size=13, color=INK),
    margin=dict(l=70, r=40, t=70, b=60),
    hoverlabel=dict(bgcolor="white", font_size=12, bordercolor=GRID),
)


def _axes(fig, xtitle, ytitle):
    fig.update_xaxes(
        title_text=xtitle, gridcolor=GRID, zeroline=False,
        linecolor=GRID, ticks="outside", tickcolor=GRID,
    )
    fig.update_yaxes(
        title_text=ytitle, gridcolor=GRID, zeroline=False,
        linecolor=GRID, ticks="outside", tickcolor=GRID,
    )
    return fig


def fig_pressure_map(df):
    """Headline chart: NPL ratio vs coverage, bubble size = NPL stock.

    Upper-left is the uncomfortable corner -- a large, badly covered book.
    """
    fig = go.Figure()
    for code, name in C.TARGET_COUNTRIES.items():
        sub = df[df["country"] == code]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=sub["coverage_ratio"],
                y=sub["npl_ratio"],
                mode="markers",
                name=name,
                marker=dict(
                    size=sub["loans_npl"] ** 0.5 / 3.2 + 7,
                    color=COUNTRY_COLOR[code],
                    opacity=0.72,
                    line=dict(width=1, color="white"),
                ),
                customdata=sub[
                    ["bank", "loans_npl", "stage2_ratio", "net_npl_to_cet1", "pressure_score"]
                ].values,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "NPL ratio: %{y:.1f}%<br>"
                    "Coverage: %{x:.0f}%<br>"
                    "NPL stock: EUR %{customdata[1]:,.0f}m<br>"
                    "Stage 2: %{customdata[2]:.1f}%<br>"
                    "Unreserved NPL / CET1: %{customdata[3]:.0f}%<br>"
                    "Pressure score: %{customdata[4]:.0f}"
                    "<extra></extra>"
                ),
            )
        )

    fig.add_vline(
        x=C.READINESS_COVERAGE_FLOOR, line=dict(color=MUTED, width=1, dash="dot")
    )
    fig.add_annotation(
        x=C.READINESS_COVERAGE_FLOOR, y=df["npl_ratio"].max(),
        text="  coverage floor: below this a sale<br>  crystallises a P&L hit",
        showarrow=False, xanchor="left", font=dict(size=11, color=MUTED),
    )
    fig.update_layout(
        title="Where the European NPL stock actually sits",
        legend=dict(orientation="h", y=1.02, x=0, yanchor="bottom"),
        height=560, **_LAYOUT,
    )
    return _axes(fig, "NPL coverage ratio (%)", "NPL ratio (% of gross loans)")


def fig_country_comparison(summary):
    """Stage 2 vs NPL vs coverage by system -- the rotation argument."""
    order = summary.sort_values("stage2_ratio", ascending=False)
    bars = [
        ("stage2_ratio", "Stage 2 (% of loans)", "#3D5A80"),
        ("npl_ratio", "NPL ratio (%)", "#C9663E"),
        ("coverage_ratio", "Coverage (%)", "#2E7D7B"),
    ]
    fig = go.Figure()
    for col, label, color in bars:
        fig.add_trace(
            go.Bar(
                x=order.index, y=order[col], name=label, marker_color=color,
                hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{y:.1f}}%<extra></extra>",
            )
        )
    fig.update_layout(
        title="Germany carries the largest forward NPL pipeline and the thinnest cover",
        barmode="group",
        legend=dict(orientation="h", y=1.02, x=0, yanchor="bottom"),
        height=460, **_LAYOUT,
    )
    return _axes(fig, "", "Per cent")


def fig_quadrant(df):
    """Pressure against disclosed intent.

    Banks without a verified quote are drawn on a separate band below the axis
    rather than at intent=0. Plotting them at zero would assert they said
    nothing, when the truth is that nobody has read their disclosure yet.
    """
    fig = go.Figure()
    verified = df[df["intent_verified"] == True]  # noqa: E712
    unconfirmed = df[df["intent_verified"] != True]  # noqa: E712

    if not unconfirmed.empty:
        fig.add_trace(
            go.Scatter(
                x=unconfirmed["pressure_score"],
                y=[-9] * len(unconfirmed),
                mode="markers",
                name=f"Intent unconfirmed ({len(unconfirmed)})",
                marker=dict(size=9, color="#B9B4AA", opacity=0.6,
                            symbol="line-ns-open", line=dict(width=1.6, color="#B9B4AA")),
                customdata=unconfirmed[["bank"]].values,
                hovertemplate=("<b>%{customdata[0]}</b><br>Pressure: %{x:.0f}<br>"
                               "Disclosure not yet verified<extra></extra>"),
            )
        )

    for code, name in C.TARGET_COUNTRIES.items():
        sub = verified[verified["country"] == code]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=sub["pressure_score"], y=sub["intent_score"],
                mode="markers+text", name=name,
                text=sub["bank"].str.split(",").str[0].str.title(),
                textposition="top center",
                textfont=dict(size=10, color=MUTED),
                marker=dict(size=14, color=COUNTRY_COLOR[code], opacity=0.85,
                            line=dict(width=1, color="white")),
                customdata=sub[["bank", "quadrant", "signal"]].values,
                hovertemplate=("<b>%{customdata[0]}</b><br>Pressure: %{x:.0f}<br>"
                               "Intent: %{y:.0f} (%{customdata[2]})<br>"
                               "%{customdata[1]}<extra></extra>"),
            )
        )

    fig.add_vline(x=ranking_mod.PRESSURE_CUT, line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_hline(y=ranking_mod.INTENT_CUT, line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_annotation(
        x=99, y=ranking_mod.INTENT_CUT + 5, text="Act now", showarrow=False,
        xanchor="right", font=dict(size=11, color=MUTED),
    )
    fig.add_annotation(
        x=99, y=ranking_mod.INTENT_CUT - 9, text="Watch", showarrow=False,
        xanchor="right", font=dict(size=11, color=MUTED),
    )
    fig.add_annotation(
        x=2, y=-9, text="not yet read", showarrow=False,
        xanchor="left", font=dict(size=10, color="#A09A90"),
    )
    fig.update_yaxes(range=[-18, 108])
    fig.update_layout(
        title="Pressure vs disclosed intent",
        legend=dict(orientation="h", y=1.02, x=0, yanchor="bottom"),
        height=500, **_LAYOUT,
    )
    return _axes(fig, "Pressure score (percentile-weighted)", "Disposal intent score")


def ranked_table_html(df, top=15) -> str:
    rows = []
    for _, r in df.head(top).iterrows():
        rows.append(
            f"<tr><td class='rank'>{r['rank']}</td>"
            f"<td class='bank'>{r['bank']}<span class='ctry'>{r['country']}</span></td>"
            f"<td class='num'>{r['loans_npl']:,.0f}</td>"
            f"<td class='num'>{r['npl_ratio']:.1f}</td>"
            f"<td class='num'>{r['stage2_ratio']:.1f}</td>"
            f"<td class='num'>{r['coverage_ratio']:.0f}</td>"
            f"<td class='num'>{r['pressure_score']:.0f}</td>"
            f"<td class='why'>{r['why']}</td></tr>"
        )
    return "\n".join(rows)


def build_dashboard(df, summary, out_path=None) -> str:
    """Write the self-contained HTML dashboard and return its path."""
    out_path = out_path or (C.DOCS / "dashboard.html")
    C.DOCS.mkdir(parents=True, exist_ok=True)

    period = eba_data.period_label(df["period"].iloc[0])
    opts = dict(include_plotlyjs=False, full_html=False, config={"displayModeBar": False})
    map_div = pio.to_html(fig_pressure_map(df), **opts)
    cty_div = pio.to_html(fig_country_comparison(summary), **opts)

    verified = int(df["intent_verified"].sum())
    # Plotting an axis of zeros would look like a rendering fault rather than
    # an empty input, so the chart is withheld until something real is behind it.
    quad_div = pio.to_html(fig_quadrant(df), **opts) if verified else (
        "<div class='placeholder'><div class='ph-title'>Awaiting verified disclosure text</div>"
        "<div class='ph-body'>This axis plots disposal intent extracted from bank disclosures "
        "against the pressure score. It stays empty until quotes are provenance-checked "
        "against their source documents &mdash; a chart of zeros would imply 48 banks have "
        "stated nothing, which is not what the data says. "
        f"Pipeline status: <b>0 of {len(df)} verified</b>.</div></div>"
    )

    # Partial coverage is the dangerous state: enough signal to look finished,
    # not enough to be. The banner scales with coverage rather than vanishing
    # the moment a single bank is verified.
    if verified == 0:
        intent_banner = (
            "<div class='warn'><b>Disposal-intent layer is not yet populated with verified "
            "disclosure text.</b> The extraction pipeline is live and runnable, but no quote "
            "has been provenance-checked against its source document, so every intent score "
            "is held at zero and affected banks are reported as <i>intent unconfirmed</i> "
            "rather than silent. The ranking below is therefore driven entirely by reported "
            "regulatory data.</div>"
        )
    elif verified < len(df):
        intent_banner = (
            f"<div class='warn'><b>Disposal-intent coverage is partial: {verified} of "
            f"{len(df)} banks.</b> Those {verified} carry a quote located in its source "
            "document by automated check. The remaining "
            f"{len(df) - verified} are ranked on reported regulatory data alone and are "
            "shown as <i>intent unconfirmed</i> &mdash; they are not asserted to have said "
            "nothing. Treat the vertical axis below as a worked demonstration of the "
            "method, not as full market coverage.</div>"
        )
    else:
        intent_banner = ""

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>European NPL Disposal Pipeline Monitor</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root {{ --ink:{INK}; --muted:{MUTED}; --grid:{GRID}; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:#FBFAF8; color:var(--ink);
         font-family:Inter,'Helvetica Neue',Arial,sans-serif; line-height:1.55; }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:48px 28px 72px; }}
  header {{ border-bottom:2px solid var(--ink); padding-bottom:20px; margin-bottom:34px; }}
  h1 {{ font-size:30px; margin:0 0 6px; letter-spacing:-0.02em; }}
  .sub {{ color:var(--muted); font-size:14px; }}
  h2 {{ font-size:19px; margin:42px 0 6px; letter-spacing:-0.01em; }}
  .lede {{ color:var(--muted); font-size:14px; margin:0 0 14px; max-width:78ch; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(168px,1fr));
            gap:14px; margin:26px 0 8px; }}
  .card {{ background:white; border:1px solid var(--grid); border-radius:9px; padding:15px 17px; }}
  .card .k {{ font-size:11px; letter-spacing:.07em; text-transform:uppercase; color:var(--muted); }}
  .card .v {{ font-size:25px; font-weight:600; margin-top:3px; letter-spacing:-0.02em; }}
  .card .n {{ font-size:11.5px; color:var(--muted); margin-top:2px; }}
  .panel {{ background:white; border:1px solid var(--grid); border-radius:9px;
            padding:10px 14px; margin-top:14px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; background:white; }}
  th {{ text-align:right; font-size:10.5px; letter-spacing:.06em; text-transform:uppercase;
        color:var(--muted); border-bottom:1px solid var(--ink); padding:9px 8px; font-weight:600; }}
  th:nth-child(2), th:last-child {{ text-align:left; }}
  td {{ padding:9px 8px; border-bottom:1px solid var(--grid); vertical-align:top; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  td.rank {{ text-align:right; color:var(--muted); width:34px; }}
  td.bank {{ font-weight:600; min-width:210px; }}
  .ctry {{ display:inline-block; margin-left:7px; font-size:10px; font-weight:500;
           color:var(--muted); border:1px solid var(--grid); border-radius:3px; padding:1px 5px; }}
  td.why {{ color:var(--muted); font-size:12px; max-width:380px; }}
  .warn {{ background:#FFF8E8; border:1px solid #E8D9A8; border-left:3px solid #C9A227;
           border-radius:7px; padding:13px 16px; font-size:13px; margin:22px 0; }}
  footer {{ margin-top:52px; padding-top:18px; border-top:1px solid var(--grid);
            color:var(--muted); font-size:12px; }}
  code {{ background:#F2F0EC; padding:1px 5px; border-radius:3px; font-size:12px; }}
  .placeholder {{ border:1px dashed #C9C4BA; border-radius:8px; background:#FCFBF9;
                  padding:30px 28px; text-align:center; }}
  .ph-title {{ font-size:14px; font-weight:600; color:var(--muted); letter-spacing:.01em; }}
  .ph-body {{ font-size:13px; color:var(--muted); max-width:62ch; margin:9px auto 0; }}
</style></head><body><div class="wrap">

<header>
  <h1>European NPL Disposal Pipeline Monitor</h1>
  <div class="sub">Which European banks are most likely to bring loan portfolios to market &middot;
  Italy, Spain, Germany, France &middot; EBA Transparency Exercise, {period}</div>
</header>

<div class="cards">
  <div class="card"><div class="k">Banks screened</div><div class="v">{len(df)}</div>
    <div class="n">loan book &ge; EUR {C.MIN_LOAN_BOOK_EUR_M/1000:.0f}bn</div></div>
  <div class="card"><div class="k">NPL stock in scope</div>
    <div class="v">EUR {df['loans_npl'].sum()/1000:,.0f}bn</div><div class="n">gross carrying amount</div></div>
  <div class="card"><div class="k">Weighted NPL ratio</div>
    <div class="v">{100*df['loans_npl'].sum()/df['loans_total'].sum():.2f}%</div>
    <div class="n">of gross loans</div></div>
  <div class="card"><div class="k">Priority names</div>
    <div class="v">{int((df['pressure_score']>=ranking_mod.PRESSURE_CUT).sum())}</div>
    <div class="n">pressure score &ge; {ranking_mod.PRESSURE_CUT:.0f}</div></div>
</div>

{intent_banner}

<h2>1. Where the stock sits</h2>
<p class="lede">Each bubble is a bank, sized by absolute NPL stock. The uncomfortable
corner is upper-left: a large non-performing book that has not been provisioned for.
A bank to the right of the dotted line can sell near carrying value; one to the left
takes a P&amp;L hit to transact, which is why it waits.</p>
<div class="panel">{map_div}</div>

<h2>2. The rotation</h2>
<p class="lede">Stage 2 loans are performing today but have seen a significant increase
in credit risk &mdash; they are the pipeline of tomorrow's NPLs. Germany carries the
highest Stage 2 share and the lowest coverage of the four systems, while Italy, the
market most associated with NPL supply, is now the best provisioned.</p>
<div class="panel">{cty_div}</div>

<h2>3. Pressure against stated intent</h2>
<p class="lede">Reported data measures what a balance sheet forces management to confront.
It cannot measure what management has said it will do. The vertical axis is the
language layer; where it is unpopulated, a bank is marked intent unconfirmed rather
than assumed silent.</p>
<div class="panel">{quad_div}</div>

<h2>4. Ranked pipeline</h2>
<p class="lede">Ordered by pressure score. The final column states the binding
constraint in each case, so the ranking can be argued with rather than taken on trust.</p>
<table>
  <thead><tr>
    <th>#</th><th>Bank</th><th>NPL stock<br>EUR m</th><th>NPL<br>%</th>
    <th>Stage 2<br>%</th><th>Cover<br>%</th><th>Pressure</th><th>Binding constraint</th>
  </tr></thead>
  <tbody>
{ranked_table_html(df)}
  </tbody>
</table>

<footer>
  Source: EBA EU-wide Transparency Exercise {period}, bank-level credit risk and capital
  templates. Pressure score is a percentile-weighted composite of NPL ratio, unreserved
  NPLs to CET1, Stage 2 share and absolute NPL stock; weights are set in
  <code>src/config.py</code> and are meant to be disagreed with. UK institutions are
  outside the EBA sample post-Brexit and are therefore not covered.
  Built by Hrush Ambekar.
</footer>

</div></body></html>"""

    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


def export_figures(df, summary):
    """Static PNGs for the README. Returns the paths written."""
    C.FIGURES.mkdir(parents=True, exist_ok=True)
    out = []
    for name, fig, w, h in [
        ("pressure_map", fig_pressure_map(df), 1200, 620),
        ("country_rotation", fig_country_comparison(summary), 1200, 520),
    ]:
        path = C.FIGURES / f"{name}.png"
        fig.write_image(str(path), width=w, height=h, scale=2)
        out.append(str(path))
    return out
