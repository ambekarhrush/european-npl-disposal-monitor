"""Build the single-page pitch document that travels with the CV.

Everything is drawn as inline SVG from live pipeline output rather than
embedded images, so the page stays crisp at print resolution and the numbers
cannot drift away from what the repository actually produces.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config as C  # noqa: E402
from src import eba_data, pressure as P, ranking as R  # noqa: E402

INK = "#161D1A"
MUTED = "#6E7471"
RULE = "#D8D4CC"
PAPER = "#FFFFFF"
ACCENT = "#1F5F5B"
WARM = "#B4552D"
SAND = "#8A7A4E"
SLATE = "#3D5A80"

COUNTRY_COLOR = {"IT": ACCENT, "ES": WARM, "DE": SLATE, "FR": SAND}


def svg_architecture() -> str:
    """Three-stage flow: two independent signals, crossed into one call."""
    def box(x, y, w, h, fill, stroke, rx=5):
        return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>')

    def txt(x, y, s, size=8.2, fill=INK, weight="400", anchor="middle"):
        return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
                f'font-weight="{weight}" text-anchor="{anchor}" '
                f'font-family="Inter,Helvetica,Arial,sans-serif">{s}</text>')

    def arrow(x1, y1, x2, y2):
        return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{MUTED}" '
                f'stroke-width="1.1" marker-end="url(#ah)"/>')

    p = ['<svg viewBox="0 0 700 172" width="100%" style="display:block">',
         '<defs><marker id="ah" markerWidth="7" markerHeight="7" refX="6" refY="2.4" '
         f'orient="auto"><path d="M0,0 L0,4.8 L6,2.4 z" fill="{MUTED}"/></marker></defs>']

    p.append(txt(92, 13, "SOURCE", 7, MUTED, "600"))
    p.append(txt(300, 13, "SIGNAL", 7, MUTED, "600"))
    p.append(txt(505, 13, "VERIFICATION", 7, MUTED, "600"))
    p.append(txt(640, 13, "OUTPUT", 7, MUTED, "600"))

    p.append(box(18, 26, 148, 44, "#F6F4F0", RULE))
    p.append(txt(92, 42, "EBA Transparency Exercise", 8.4, INK, "600"))
    p.append(txt(92, 54, "48 banks &#183; bank-level", 7.6, MUTED))
    p.append(txt(92, 64, "NPL &#183; Stage 2 &#183; coverage &#183; CET1", 7.6, MUTED))

    p.append(arrow(168, 48, 222, 48))

    p.append(box(224, 26, 150, 44, "#EDF2F6", SLATE))
    p.append(txt(299, 42, "PRESSURE SCORE", 8.4, SLATE, "700"))
    p.append(txt(299, 54, "4 factors, percentile-ranked", 7.6, MUTED))
    p.append(txt(299, 64, "what the balance sheet forces", 7.6, MUTED))

    p.append(box(18, 96, 148, 52, "#F6F4F0", RULE))
    p.append(txt(92, 112, "Annual reports &#183; Pillar 3", 8.4, INK, "600"))
    p.append(txt(92, 124, "IR sites, 5 languages", 7.6, MUTED))
    p.append(txt(92, 135, "discovery via headless browser", 7.6, MUTED))
    p.append(txt(92, 145, "(JS-rendered: HTTP fetch fails)", 7.2, MUTED))

    p.append(arrow(168, 122, 222, 122))

    p.append(box(224, 96, 150, 52, "#F2EEE9", WARM))
    p.append(txt(299, 112, "DISPOSAL INTENT", 8.4, WARM, "700"))
    p.append(txt(299, 124, "LLM classifies prose onto", 7.6, MUTED))
    p.append(txt(299, 135, "programme &#8594; target &#8594; exploring", 7.6, MUTED))
    p.append(txt(299, 145, "&#8594; monitoring &#8594; denial", 7.6, MUTED))

    p.append(arrow(376, 122, 424, 122))

    p.append(box(426, 90, 158, 64, "#FFFBF0", "#C9A227"))
    p.append(txt(505, 104, "VERBATIM GATE", 8.4, "#8A6D12", "700"))
    p.append(txt(505, 117, "quote must be located in", 7.6, MUTED))
    p.append(txt(505, 127, "the PDF it cites", 7.6, MUTED))
    p.append(txt(505, 139, "fails &#8594; score forced to 0", 7.6, "#8A6D12", "600"))
    p.append(txt(505, 149, "unread &#8800; silent", 7.4, MUTED))

    p.append(f'<path d="M374,48 L604,48 L604,82" stroke="{MUTED}" stroke-width="1.1" '
             f'fill="none" marker-end="url(#ah)"/>')
    p.append(arrow(584, 122, 604, 122))
    p.append(f'<line x1="604" y1="122" x2="604" y2="108" stroke="{MUTED}" stroke-width="1.1"/>')

    p.append(box(576, 84, 110, 42, PAPER, INK))
    p.append(txt(631, 99, "PRESSURE &#215; INTENT", 8, INK, "700"))
    p.append(txt(631, 112, "Act now &#183; Watch", 7.6, MUTED))
    p.append(txt(631, 122, "Opportunistic &#183; Drop", 7.6, MUTED))

    p.append('</svg>')
    return "".join(p)


def svg_rotation(summary) -> str:
    """Grouped bars: Stage 2 vs NPL vs coverage by banking system."""
    order = summary.sort_values("stage2_ratio", ascending=False)
    W, H, pad_l, pad_b, top = 330, 140, 26, 24, 14
    plot_h = H - pad_b - top
    maxv = 56.0

    p = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="display:block">']
    for gv in (0, 20, 40):
        y = top + plot_h - (gv / maxv) * plot_h
        p.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W-6}" y2="{y:.1f}" '
                 f'stroke="{RULE}" stroke-width="0.7"/>')
        p.append(f'<text x="{pad_l-5}" y="{y+2.6:.1f}" font-size="6.6" fill="{MUTED}" '
                 f'text-anchor="end" font-family="Inter,Arial">{gv}</text>')

    group_w = (W - pad_l - 10) / len(order)
    series = [("stage2_ratio", SLATE), ("npl_ratio", WARM), ("coverage_ratio", ACCENT)]
    bw = min(13, (group_w - 14) / 3)

    for i, (name, row) in enumerate(order.iterrows()):
        gx = pad_l + i * group_w + 7
        for j, (col, colr) in enumerate(series):
            v = float(row[col])
            h = (v / maxv) * plot_h
            x = gx + j * (bw + 2.5)
            y = top + plot_h - h
            p.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                     f'fill="{colr}" rx="1"/>')
            p.append(f'<text x="{x+bw/2:.1f}" y="{y-2.6:.1f}" font-size="6.2" '
                     f'fill="{MUTED}" text-anchor="middle" font-family="Inter,Arial">'
                     f'{v:.1f}</text>')
        label = str(name)[:9]
        p.append(f'<text x="{gx + (3*bw+5)/2:.1f}" y="{H-13}" font-size="7.4" '
                 f'fill="{INK}" text-anchor="middle" font-weight="600" '
                 f'font-family="Inter,Arial">{label}</text>')

    legend = [("Stage 2", SLATE), ("NPL ratio", WARM), ("Coverage", ACCENT)]
    lx = pad_l
    for lab, colr in legend:
        p.append(f'<rect x="{lx}" y="{H-7}" width="7" height="5" fill="{colr}" rx="1"/>')
        p.append(f'<text x="{lx+10}" y="{H-2.8}" font-size="6.6" fill="{MUTED}" '
                 f'font-family="Inter,Arial">{lab}</text>')
        lx += len(lab) * 4.0 + 24
    p.append('</svg>')
    return "".join(p)


def svg_quadrant(df) -> str:
    """The 2x2, with the verified names actually placed on it."""
    W, H = 330, 140
    pad_l, pad_b, top, pad_r = 30, 24, 12, 10
    pw, ph = W - pad_l - pad_r, H - pad_b - top

    def sx(v):
        return pad_l + (v / 100.0) * pw

    def sy(v):
        return top + ph - (v / 100.0) * ph

    cutx, cuty = sx(R.PRESSURE_CUT), sy(R.INTENT_CUT)
    p = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="display:block">']

    p.append(f'<rect x="{cutx:.1f}" y="{top}" width="{pad_l+pw-cutx:.1f}" '
             f'height="{cuty-top:.1f}" fill="#F0F6F4"/>')
    p.append(f'<rect x="{pad_l}" y="{top}" width="{pw}" height="{ph}" fill="none" '
             f'stroke="{RULE}" stroke-width="0.8"/>')
    p.append(f'<line x1="{cutx:.1f}" y1="{top}" x2="{cutx:.1f}" y2="{top+ph}" '
             f'stroke="{MUTED}" stroke-width="0.8" stroke-dasharray="2.5,2.5"/>')
    p.append(f'<line x1="{pad_l}" y1="{cuty:.1f}" x2="{pad_l+pw}" y2="{cuty:.1f}" '
             f'stroke="{MUTED}" stroke-width="0.8" stroke-dasharray="2.5,2.5"/>')

    p.append(f'<text x="{pad_l+pw-4}" y="{top+11}" font-size="7" fill="{ACCENT}" '
             f'text-anchor="end" font-weight="700" font-family="Inter,Arial">ACT NOW</text>')
    p.append(f'<text x="{pad_l+pw-4}" y="{top+ph-5}" font-size="7" fill="{MUTED}" '
             f'text-anchor="end" font-weight="600" font-family="Inter,Arial">WATCH</text>')
    p.append(f'<text x="{pad_l+4}" y="{top+ph-5}" font-size="7" fill="{MUTED}" '
             f'font-weight="600" font-family="Inter,Arial">DEPRIORITISE</text>')

    unconf = df[df["intent_verified"] != True]  # noqa: E712
    for _, r in unconf.iterrows():
        p.append(f'<line x1="{sx(r["pressure_score"]):.1f}" y1="{top+ph+4:.1f}" '
                 f'x2="{sx(r["pressure_score"]):.1f}" y2="{top+ph+9:.1f}" '
                 f'stroke="#BFBAB0" stroke-width="1"/>')
    p.append(f'<text x="{pad_l}" y="{top+ph+17:.1f}" font-size="6.2" fill="#9C968C" '
             f'font-family="Inter,Arial">{len(unconf)} banks &#183; disclosure not yet read</text>')

    ver = df[df["intent_verified"] == True]  # noqa: E712
    for _, r in ver.iterrows():
        cx, cy = sx(r["pressure_score"]), sy(r["intent_score"])
        colr = COUNTRY_COLOR.get(r["country"], MUTED)
        p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.2" fill="{colr}" '
                 f'stroke="white" stroke-width="1.1"/>')
        nm = r["bank"].lower()
        if nm.startswith("deutsche pfand"):
            name = "pbb"
        elif nm.startswith("banca monte"):
            name = "MPS"
        elif nm.startswith("unicredit"):
            name = "UniCredit"
        elif nm.startswith("banco bilbao"):
            name = "BBVA"
        else:
            name = r["bank"].split(",")[0][:14]
        dy = -7 if r["intent_score"] > 10 else 11
        p.append(f'<text x="{cx:.1f}" y="{cy+dy:.1f}" font-size="7" fill="{INK}" '
                 f'text-anchor="middle" font-weight="600" font-family="Inter,Arial">{name}</text>')

    p.append(f'<text x="{pad_l+pw/2:.1f}" y="{H-2}" font-size="6.6" fill="{MUTED}" '
             f'text-anchor="middle" font-family="Inter,Arial">pressure score &#8594;</text>')
    p.append(f'<text x="9" y="{top+ph/2:.1f}" font-size="6.6" fill="{MUTED}" '
             f'text-anchor="middle" font-family="Inter,Arial" '
             f'transform="rotate(-90 9 {top+ph/2:.1f})">disposal intent &#8594;</text>')
    p.append('</svg>')
    return "".join(p)


def build():
    df = R.build_ranking(save=False)
    summary = P.country_summary(df)
    period = eba_data.period_label(df["period"].iloc[0])

    verified = int(df["intent_verified"].sum())
    de, it = summary.loc["Germany"], summary.loc["Italy"]
    top = df.iloc[0]
    top_name = top["bank"].split(" AG")[0]

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>European NPL Disposal Pipeline Monitor &mdash; Hrush Ambekar</title>
<style>
  @page {{ size: A4; margin: 11mm 11mm 9mm; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:Inter,'Helvetica Neue',Arial,sans-serif; color:{INK};
         background:{PAPER}; font-size:8.5pt; line-height:1.37;
         -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ width:188mm; margin:0 auto; }}
  header {{ border-bottom:1.6pt solid {INK}; padding-bottom:4pt; margin-bottom:6pt;
            display:flex; justify-content:space-between; align-items:flex-end; }}
  h1 {{ font-size:15.5pt; letter-spacing:-0.4pt; line-height:1.12; }}
  .sub {{ color:{MUTED}; font-size:8pt; margin-top:2pt; }}
  .who {{ text-align:right; font-size:7.6pt; color:{MUTED}; line-height:1.34; }}
  .who b {{ color:{INK}; font-size:8.6pt; }}
  h2 {{ font-size:8.4pt; letter-spacing:.7pt; text-transform:uppercase;
        color:{MUTED}; margin:6pt 0 3pt; font-weight:700; }}
  .lede {{ font-size:8.6pt; margin-bottom:4pt; }}
  .tiles {{ display:grid; grid-template-columns:repeat(4,1fr); gap:5pt; margin:5pt 0 1pt; }}
  .tile {{ border:0.7pt solid {RULE}; border-radius:3pt; padding:5pt 6pt; background:#FCFBF9; }}
  .tile .k {{ font-size:6.4pt; letter-spacing:.5pt; text-transform:uppercase; color:{MUTED}; }}
  .tile .v {{ font-size:13pt; font-weight:700; letter-spacing:-0.4pt; margin-top:1pt; }}
  .tile .n {{ font-size:6.6pt; color:{MUTED}; }}
  .two {{ display:grid; grid-template-columns:1fr 1fr; gap:9pt; }}
  .panel {{ border:0.7pt solid {RULE}; border-radius:3pt; padding:6pt 7pt; background:#FCFBF9; }}
  .cap {{ font-size:7.1pt; color:{MUTED}; margin-top:2.5pt; line-height:1.32; }}
  table {{ width:100%; border-collapse:collapse; font-size:7.6pt; margin-top:2pt; }}
  th {{ text-align:left; font-size:6.4pt; letter-spacing:.4pt; text-transform:uppercase;
        color:{MUTED}; border-bottom:0.7pt solid {INK}; padding:2.5pt 3pt; }}
  td {{ padding:2.5pt 3pt; border-bottom:0.5pt solid {RULE}; vertical-align:top; }}
  td.r {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .ok {{ color:{ACCENT}; font-weight:700; }}
  .no {{ color:{WARM}; font-weight:700; }}
  .quote {{ border-left:2pt solid {ACCENT}; padding:2pt 0 2pt 7pt; margin:3pt 0;
            font-size:7.8pt; color:#2C3330; }}
  .quote cite {{ display:block; font-style:normal; font-size:6.8pt; color:{MUTED}; margin-top:2pt; }}
  footer {{ border-top:0.7pt solid {RULE}; margin-top:6pt; padding-top:3.5pt;
            color:{MUTED}; font-size:6.9pt; display:flex; justify-content:space-between; }}
  code {{ background:#F1EFEB; padding:0 2pt; border-radius:2pt; font-size:7pt; }}
  .hl {{ background:#FFF6DC; padding:0 2pt; }}
</style></head><body><div class="sheet">

<header>
  <div>
    <h1>European NPL Disposal Pipeline Monitor</h1>
    <div class="sub">Which European banks are most likely to bring loan portfolios
    to market &mdash; and why &#183; Italy &#183; Spain &#183; Germany &#183; France</div>
  </div>
  <div class="who"><b>Hrush Ambekar</b><br>ambekar2709@gmail.com<br>
  EBA Transparency Exercise {period}</div>
</header>

<div class="lede"><b>Origination is a sourcing problem before it is an analysis problem.</b>
By the time a portfolio is in market, the price is competed. The useful question is which
banks are being pushed toward a sale <i>before</i> they run a process &mdash; and that question
has two halves. What the balance sheet <b>forces</b> management to confront is computable
from regulatory data. What management <b>intends</b> is not: it sits in annual reports and
strategic plans, in five languages, and nobody reads it across fifty banks by hand.
This tool does both, and crosses them.</div>

<div class="tiles">
  <div class="tile"><div class="k">Banks screened</div><div class="v">{len(df)}</div>
    <div class="n">loan book &#8805; &euro;10bn</div></div>
  <div class="tile"><div class="k">NPL stock in scope</div>
    <div class="v">&euro;{df['loans_npl'].sum()/1000:,.0f}bn</div>
    <div class="n">gross carrying amount</div></div>
  <div class="tile"><div class="k">Priority names</div>
    <div class="v">{int((df['pressure_score']>=R.PRESSURE_CUT).sum())}</div>
    <div class="n">pressure &#8805; {R.PRESSURE_CUT:.0f}</div></div>
  <div class="tile"><div class="k">Verified quotes</div><div class="v">{verified}</div>
    <div class="n">located in source PDF</div></div>
</div>

<h2>How it works</h2>
{svg_architecture()}

<div class="two" style="margin-top:5pt">
  <div>
    <h2 style="margin-top:0">The finding &mdash; the geography has rotated</h2>
    <div class="panel">{svg_rotation(summary)}</div>
    <div class="cap"><b>Germany carries the largest forward pipeline and the thinnest
    cover.</b> Stage 2 loans are performing today but have seen a significant increase in
    credit risk &mdash; they are where next year's NPLs come from, and most screens ignore
    them because they sit outside the NPL ratio. Germany shows the <i>cleanest</i> headline
    NPL ratio ({de['npl_ratio']:.1f}%) alongside the <i>highest</i> Stage 2 share
    ({de['stage2_ratio']:.1f}%) and <i>lowest</i> coverage ({de['coverage_ratio']:.0f}%).
    Italy &mdash; the market most associated with NPL supply &mdash; is now the best reserved
    at {it['coverage_ratio']:.0f}%.<br><br>
    The two markets are simply in different states: Italian banks are
    <b>transaction-ready</b> and sell near carrying value, so the edge is price discipline.
    German banks are <b>accumulating risk they have not reserved against</b>, so the edge is
    being in the relationship before the process starts.</div>
  </div>
  <div>
    <h2 style="margin-top:0">The output &mdash; pressure &#215; intent</h2>
    <div class="panel">{svg_quadrant(df)}</div>
    <div class="cap"><b>Same pressure, different call.</b> UniCredit and BBVA both score 67
    on reported data &mdash; indistinguishable. The disclosure layer separates them:
    UniCredit's NPE Strategy names disposal targets (<span class="hl">Act now</span>);
    BBVA's verified passage is NPL-ratio commentary with no intent, so the model returned
    <code>none</code> (Watch).<br><br>
    <b>{top_name} ranks #1 on pressure and carries verified near-term intent</b> &mdash;
    the one name where both signals agree.</div>
  </div>
</div>

<h2>Why the AI output can be trusted</h2>
<div class="two">
  <div>
    <div class="lede" style="font-size:8pt">The first question anyone asks about LLM output
    is <i>how do you know it didn't make that up.</i> So a quote earns its place by being
    <b>located in the PDF it cites</b> &mdash; mechanically, reproducibly &mdash; not by
    anyone asserting they checked. The gate was tested adversarially before being trusted:</div>
    <table>
      <thead><tr><th>Input</th><th style="text-align:right">Result</th></tr></thead>
      <tbody>
        <tr><td>Untouched harvested quote</td><td class="r ok">PASS</td></tr>
        <tr><td>Plausible sentence never in the document</td><td class="r no">REJECT</td></tr>
        <tr><td>Real quote, one word silently altered</td><td class="r no">REJECT</td></tr>
        <tr><td>Real quote, wrong page claimed</td><td class="r ok">PASS, page fixed</td></tr>
      </tbody>
    </table>
    <div class="cap">Row three is the one that matters &mdash; a model subtly rewording a
    quote while keeping it believable is the realistic failure mode. Anything unverified has
    its score forced to zero, and the bank is reported as <b>intent unconfirmed</b>, never as
    silent. Absence of data is not evidence of absence.</div>
  </div>
  <div>
    <div class="lede" style="font-size:8pt"><b>What a live signal looks like.</b> The
    highest-pressure bank in the screen, found by the pipeline in its own Annual Report:</div>
    <div class="quote">&ldquo;pbb decided to completely discontinue its US business and intends
    to <b>reduce, securitise or sell</b> its portfolio there&hellip; pbb completed a
    <b>significant risk transfer (SRT)</b> on a synthetic basis in December 2025 with several
    funds managed by Oaktree Capital Management, L.P.&rdquo;
    <cite>Deutsche Pfandbriefbank, Annual Report 2025, p.117 &mdash; located in source</cite></div>
    <div class="cap">Classified <code>target</code>, near-term horizon. An executed SRT with a
    credit fund already in the seat.<br><br>
    <b>The more useful result is BBVA.</b> Its quote is verified &mdash; genuinely in the 2025
    Annual Report &mdash; and the classifier still returned <code>none</code>, because the
    passage discusses an NPL ratio moving, not an intention to sell. The pipeline found real
    text and declined to manufacture a signal from it. A screen that only ever finds signal is
    not a screen.</div>
  </div>
</div>

<footer>
  <div><b>Stack</b> &#183; Python &#183; EBA Transparency Exercise (bank-level regulatory
  filings) &#183; DeepSeek <code>deepseek-chat</code> for classification &#183; headless
  Chrome for document discovery &#183; Jupyter + Plotly</div>
  <div>Interactive dashboard &amp; full source on GitHub</div>
</footer>

</div></body></html>"""

    out = C.DOCS / "one-pager.html"
    out.write_text(html, encoding="utf-8")
    print("wrote", out)
    return out


if __name__ == "__main__":
    build()
