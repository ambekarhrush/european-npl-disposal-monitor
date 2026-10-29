"""Generate the four analysis notebooks.

Kept as a generator rather than hand-edited .ipynb files so the narrative and
the code stay in one reviewable place and the notebooks can be rebuilt from
scratch after any change to src/.
"""

import nbformat as nbf
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"

BOOT = """import sys, pathlib
sys.path.insert(0, str(pathlib.Path.cwd().parent))
import pandas as pd
pd.set_option("display.width", 180)
pd.set_option("display.max_columns", 40)
"""


def nb(cells):
    n = nbf.v4.new_notebook()
    n.cells = cells
    n.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    return n


md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell


# --- 01 ---------------------------------------------------------------------
n1 = nb([
    md("""# 01 - Universe and data

Bank-level asset quality for the four largest euro-area banking systems,
taken from the **EBA EU-wide Transparency Exercise**. This is supervisory
reporting, published per institution, so every figure here traces to a
regulatory submission rather than to a vendor estimate.

**Why these four.** The intended scope is Italy, Spain, Germany, France and the UK.
UK institutions left the EBA sample after Brexit, so the UK leg is not
addressable from this source. That is a stated gap, not a silent one."""),
    code(BOOT),
    code("""from src import eba_data as E

panel = E.build_bank_panel()
print("Reporting period:", E.period_label(panel['period'].iloc[0]))
print("Banks in universe:", len(panel))
panel['country_name'].value_counts()"""),
    md("""## What the exercise actually reports

The exercise is published long-format: one row per bank, period, item code and
dimension combination. Totals are the rows where every breakdown dimension is
zero. `Perf_Status` then carries the split we care about:

| code | meaning |
|---|---|
| 0 | total gross loans |
| 2 | non-performing |
| 12 | performing, but significant increase in credit risk (Stage 2) |

Stage 2 is the one most screens ignore. These loans are performing today, so
they sit outside the NPL ratio entirely -- but they are the population from
which next year's NPLs are drawn. For an origination desk that is the more
useful number, because it is forward-looking."""),
    code("""cols = ['bank','country','loans_total','loans_npl','npl_ratio',
        'stage2_ratio','coverage_ratio','cet1_ratio','net_npl_to_cet1']
panel[cols].head(15).round(1)"""),
    md("""## Sanity checks

A screen built on mis-parsed regulatory data is worse than no screen, so the
aggregates are checked against published EBA figures before anything is built
on top."""),
    code("""agg_npl = 100 * panel['loans_npl'].sum() / panel['loans_total'].sum()
agg_s2  = 100 * panel['loans_stage2'].sum() / panel['loans_total'].sum()
print(f"Weighted NPL ratio    : {agg_npl:.2f}%   (EBA publishes c.2% area)")
print(f"Weighted Stage 2 share: {agg_s2:.2f}%   (EBA publishes high single digit)")
print(f"CET1 range            : {panel['cet1_ratio'].min():.1f}% - {panel['cet1_ratio'].max():.1f}%")
print("\\nNulls across derived fields:")
print(panel[cols].isna().sum())"""),
])

# --- 02 ---------------------------------------------------------------------
n2 = nb([
    md("""# 02 - Pressure score

How hard is each bank being pushed to do something about its non-performing book.

This layer uses reported data only. It measures **capacity and constraint** --
what a balance sheet can afford to carry. It says nothing about management
intent, which is a separate signal and is handled in notebook 03. Conflating
the two is the most common weakness in screens like this."""),
    code(BOOT),
    code("""from src import eba_data as E, pressure as P, config as C

panel  = E.build_bank_panel()
scored = P.add_pressure_score(panel)
C.PRESSURE_WEIGHTS"""),
    md("""## Factor design

Four factors, percentile-ranked within the universe so the score is a relative
league table rather than an absolute claim:

- **NPL ratio** - how bad the book is relative to its own size
- **Unreserved NPLs / CET1** - the loss still to be taken, against the buffer
  that has to absorb it. This is the binding constraint in practice.
- **Stage 2 share** - forward pipeline of new NPL formation
- **Absolute NPL stock** (log) - is the position large enough to be investable
  at fund scale

They are deliberately non-overlapping. Coverage enters only through
`net_npl_to_cet1`, so a weakly provisioned bank is not penalised twice."""),
    code("""P.factor_table(scored, 15).round(1)"""),
    md("""## Coverage is not pressure

A low coverage ratio is usually read as distress. It is better understood as
two opposing forces:

- a weakly provisioned bank faces **more** supervisory pressure to act, but
- crystallises a **larger** P&L hit when it sells, so it moves slower

A well-provisioned bank can transact near carrying value without taking further
pain. It is *readier*, not more desperate. So coverage is reported separately as
transaction readiness rather than folded into the pressure score."""),
    code("""ready = scored.groupby('transaction_ready')['bank'].count()
print("Banks able to sell near carrying value (coverage >= "
      f"{C.READINESS_COVERAGE_FLOOR:.0f}%):\\n{ready.to_string()}")

P.country_summary(scored).round(1)"""),
    md("""## The rotation

Germany shows the highest Stage 2 share and the lowest coverage of the four
systems. Italy -- the market most associated with NPL supply -- is now the best
provisioned.

The implication is not that Italy is uninteresting. It is that Italian banks are
*transaction-ready* while German banks are *accumulating a problem they have not
yet reserved against*. Those two states call for different origination
behaviour: price discipline in Italy, early relationship work in Germany."""),
])

# --- 03 ---------------------------------------------------------------------
n3 = nb([
    md("""# 03 - Disposal intent from disclosure text

Reported data cannot tell you what management plans to do. That lives in prose:
strategic plan commentary, NPE reduction targets, results-call language. Nobody
reads it across fifty banks by hand, in five languages, every quarter.

This is where the LLM earns its place -- not as a summariser, but as a
classifier over text that would otherwise go unread."""),
    code(BOOT),
    code("""from src import intent as I

print("DEEPSEEK_API_KEY present:", I.api_available())
print("Model:", I.MODEL)
I.SIGNAL_LADDER"""),
    md("""## The schema

Intent is graded on a ladder, weakest to strongest. The ladder matters more than
the labels: an announced, sized programme is a different object from "we keep
all options under review".

A horizon multiplier then discounts anything without a near-term date, because
a 2030 target is not an origination signal."""),
    code("""print(I.HORIZON_MULTIPLIER)
corpus = I.load_corpus()
print(f"\\nCorpus entries: {len(corpus)}")
print(I.build_prompt(corpus[0]))"""),
    md("""## Three rules that make this usable

1. **Every signal carries its source sentence and a URL.** An extracted score
   with no quote behind it cannot be used in a credit process and would rightly
   be ignored.
2. **The model never sees or produces a number.** It classifies text into a
   fixed schema; all arithmetic happens in Python afterwards.
3. **Quotes are verified character-for-character against the source.** If the
   model returns evidence that does not appear in the input text, the evidence
   is dropped and the signal is flagged. This is the answer to the first
   question any credit professional asks about LLM output."""),
    code("""signals = I.run_extraction()   # live LLM where a key is present
for s in signals:
    print(f"{s.bank[:40]:<40} {s.signal:<11} {s.horizon:<8} "
          f"verified={str(s.verified):<5} score={s.score():>5.0f}")"""),
    md("""## Provenance gating

`IntentSignal.score()` returns **0** for anything not marked
`VERIFIED_VERBATIM`, and a quote earns that mark only by being *located in the
PDF it claims to come from* (`scripts/promote_candidates.py` re-opens the
cached document and matches the text). Verification is mechanical and
reproducible rather than someone asserting they checked.

Every entry in the corpus has passed that check. Earlier builds carried
labelled placeholder text to exercise the pipeline before real documents were
reachable; it has been removed now that the pipeline demonstrably runs on real
filings, because invented sentences attached to real bank names are a liability
in a public repository even when correctly flagged and scored at zero.

A bank absent from the corpus is reported as **intent unconfirmed**, never as
silent -- absence of data is not evidence of absence."""),
    code("""from collections import Counter
print(Counter(s.provenance for s in signals))

print("\\nScored vs held:")
for s_ in signals:
    mark = "VERIFIED" if s_.verified else "held"
    print(f"  {s_.bank[:34]:<34} {s_.signal:<11} {mark:<9} {s_.score():>5.0f}")"""),
    md("""## The case that proves the gate is working

BBVA is the useful result, not UniCredit.

Its quote is **verified** -- genuinely located in the 2025 Annual Report -- and
the classifier still returned `none`, because the passage discusses an NPL ratio
moving rather than any intention to sell. The pipeline found text, confirmed it
was real, and then declined to manufacture a signal from it.

A screen that only ever finds signal is not a screen. Being able to point at a
verified input that correctly scored zero is what makes the non-zero scores
worth anything.

To extend coverage: `scripts/harvest_disclosures.py`, review the candidates,
then `scripts/promote_candidates.py --apply`."""),
])

# --- 04 ---------------------------------------------------------------------
n4 = nb([
    md("""# 04 - Pipeline ranking and dashboard

Crossing the two signals.

| | **intent stated** | **intent absent** |
|---|---|---|
| **high pressure** | Act now | Watch |
| **low pressure** | Opportunistic | Deprioritise |

A bank under heavy pressure that has said nothing is a different call from one
that has announced a programme, and both differ from a comfortable bank being
opportunistic."""),
    code(BOOT),
    code("""from src import ranking as R, pressure as P, viz as V

ranked  = R.build_ranking()
summary = P.country_summary(ranked)
print(R.coverage_note(ranked))
R.pipeline_table(ranked, 15).round(1)"""),
    md("""## Why each name is on the list

The ranking is only useful if it can be argued with. Each row carries the
binding constraint in plain language, so a reader who disagrees can see exactly
which input to push back on."""),
    code("""for _, r in ranked.head(8).iterrows():
    print(f"{r['rank']:>2}. {r['bank'][:46]:<46} {r['quadrant']}")
    print(f"    {r['why']}\\n")"""),
    code("""ranked['quadrant'].value_counts()"""),
    md("""## Figures and dashboard"""),
    code("""V.fig_pressure_map(ranked)"""),
    code("""V.fig_country_comparison(summary)"""),
    code("""import pathlib
root = pathlib.Path.cwd().parent
path = V.build_dashboard(ranked, summary)
V.export_figures(ranked, summary)
print("Dashboard written to:", pathlib.Path(path).relative_to(root))"""),
    md("""## Known limits

- **UK is out of scope.** UK banks left the EBA sample after Brexit, so one leg
  of the mandate is not addressable from this source.
- **The intent layer is not yet live.** See notebook 03 -- the pipeline runs but
  the corpus needs verified quotes before it produces signal.
- **The CET1 requirement is a proxy.** Banks disclose institution-specific SREP
  requirements; a single 10.5% floor is used here as a transparent
  approximation, set in `src/config.py`.
- **Percentile scoring is relative.** If every bank in the universe is
  comfortable, someone still ranks first. The score ranks within this universe;
  it is not an absolute distress measure."""),
])


def main():
    NB.mkdir(parents=True, exist_ok=True)
    for name, n in [
        ("01_data_universe", n1),
        ("02_pressure_score", n2),
        ("03_intent_ai", n3),
        ("04_pipeline_dashboard", n4),
    ]:
        path = NB / f"{name}.ipynb"
        nbf.write(n, str(path))
        print("wrote", path.name)


if __name__ == "__main__":
    main()
