# `notebooks/` — the worked analysis

Read in order. Each one answers a single question and hands its output to the
next. All four ship with outputs saved, so they can be read without running
anything.

| # | notebook | the question it answers |
|---|---|---|
| 01 | `01_data_universe.ipynb` | What is in the data, and can it be trusted? |
| 02 | `02_pressure_score.ipynb` | Which banks are under the most balance-sheet pressure? |
| 03 | `03_intent_ai.ipynb` | What has management actually said about selling? |
| 04 | `04_pipeline_dashboard.ipynb` | Crossing the two — who do you call first? |

---

### 01 · Universe and data

Builds the 48-bank panel from the EBA Transparency Exercise and **checks it
before building anything on it**. Aggregates are compared against published EBA
figures — weighted NPL ratio ~2.4%, Stage 2 share ~9% — because a screen built on
a mis-parsed regulatory file is worse than no screen at all.

Also explains why Stage 2 matters: those loans are performing today, so they sit
outside the NPL ratio entirely, but they are the population next year's NPLs come
from. Most screens never look at them.

### 02 · Pressure score

The four factors, the weights, and the argument for why **coverage is not
pressure** — the distinction most screens get wrong. Ends with the country
summary that produces the rotation finding.

### 03 · Disposal intent

The LLM layer. Schema, prompt, the verbatim-check gate, and the provenance rule
that forces unverified text to score zero.

The most useful cell is the one where **BBVA scores zero on a verified quote**.
The passage is genuinely in its 2025 Annual Report, the classifier read it, and
returned `none` — because it discusses an NPL ratio moving, not an intention to
sell. A screen that only ever finds signal is not a screen.

### 04 · Ranking and dashboard

Crosses the two signals, writes `docs/dashboard.html` and the README figures, and
closes with a plain statement of what this does **not** cover — UK banks are
outside the EBA sample, most disclosures are still unread, the CET1 requirement
is a proxy, and percentile scoring is relative by construction.

---

## Running them

```bash
pip install -r ../requirements.txt
python ../scripts/fetch_data.py     # EBA source, ~130 MB
jupyter lab
```

`DEEPSEEK_API_KEY` in a project-root `.env` enables the live classifier in 03.
Without it that notebook uses the deterministic fallback and everything else is
unchanged.

## A note on how these are maintained

The notebooks are **generated** by `../scripts/make_notebooks.py`, not hand-edited.
Narrative and code live together in one reviewable file, and the whole set can be
rebuilt and re-executed after any change to `src/`. Editing a `.ipynb` directly
will be overwritten on the next regeneration.
