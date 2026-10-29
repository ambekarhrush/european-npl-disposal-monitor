# `docs/` — the outputs

Four artefacts, aimed at three different readers.

| file | reader | time to understand |
|---|---|---|
| `Ambekar_NPL-Monitor_one-pager.pdf` | someone deciding whether to read further | 60 seconds |
| `dashboard.html` | someone who wants to interrogate a specific bank | 10 minutes |
| `figures/*.png` | the repository README | at a glance |
| `one-pager.html` | the print source for the PDF | — |

---

## `Ambekar_NPL-Monitor_one-pager.pdf`

A single A4 page: the finding, the architecture, the verification discipline, and
the live example. Self-contained by design — a reader who never opens anything
else still gets the whole argument.

Three hand-drawn SVG diagrams rather than exported screenshots:

- the pipeline flow, showing the two signals crossing at the verbatim gate
- the rotation bars, Stage 2 vs NPL vs coverage by system
- the 2×2, with the verified banks plotted where they actually fall

**All numbers are generated from live pipeline output.** There is no hard-coded
figure anywhere in `scripts/build_onepager.py`, so the page cannot quietly drift
away from what the repository produces. The flip side: **re-run it after any data
change**, or it becomes a confident, out-of-date document.

The layout is tuned to fit one sheet with a few millimetres of headroom. Adding
content pushes it onto a second page, so check the fit after editing:

```js
// in the browser console, with one-pager.html open
document.querySelector('.sheet').getBoundingClientRect().height / (96/25.4)
// must stay under 277mm (A4 less the 11mm/9mm margins)
```

---

## `dashboard.html`

Self-contained Plotly — open it in any browser, no server, no build step. Hover
any bubble for that bank's NPL stock, Stage 2 share, unreserved NPLs against
CET1, and pressure score.

Four sections: where the stock sits, the rotation, pressure against stated
intent, and the ranked pipeline with the binding constraint stated per name.

Two honesty behaviours worth knowing about, because both were bugs first:

- **The coverage banner scales rather than disappearing.** It used to vanish the
  moment a single bank was verified, implying full coverage at 4 of 48. Partial
  coverage is the dangerous state — enough signal to look finished, not enough to
  be — so the banner now reports the actual fraction.
- **Unread banks are not plotted at zero.** They sit on a separate "not yet read"
  band below the axis. Plotting them at zero asserts they said nothing, which is
  not what the data says.

---

## `figures/`

| file | used by |
|---|---|
| `pressure_map.png` | repository README, headline chart |
| `country_rotation.png` | repository README, the finding |

Exported at 2× scale by `src/viz.export_figures()`.

---

## Regenerating

```bash
python scripts/build_onepager.py        # -> one-pager.html
```

```bash
# -> dashboard.html + figures/
python -c "from src import ranking as R, pressure as P, viz as V; \
df=R.build_ranking(); s=P.country_summary(df); \
V.build_dashboard(df,s); V.export_figures(df,s)"
```

```bash
# one-pager.html -> PDF
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="docs/Ambekar_NPL-Monitor_one-pager.pdf" \
  "file://$(pwd)/docs/one-pager.html"
```

Notebook `04_pipeline_dashboard.ipynb` does the dashboard and figures as its last
cell, so running the notebooks refreshes them too.
