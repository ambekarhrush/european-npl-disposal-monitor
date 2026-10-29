# `src/` — the pipeline

Seven modules, each with one job. They are listed in dependency order; nothing
imports anything below it.

| module | responsibility |
|---|---|
| `config.py` | EBA item codes, universe definition, scoring weights, paths |
| `eba_data.py` | parse the Transparency Exercise into a bank panel |
| `pressure.py` | structured pressure score from reported data |
| `harvest.py` | find candidate disclosure passages, and verify them |
| `intent.py` | classify disposal intent from verified text |
| `ranking.py` | cross pressure × intent into an action |
| `viz.py` | figures and the HTML dashboard |

---

## The split that matters: `harvest` vs `intent`

These could have been one module. Keeping them apart is the design decision the
rest of the repository rests on.

```
harvest.py                    intent.py
─────────                     ─────────
finds candidate passages      judges what a passage means
verifies they are real        never sees an unverified passage
                              never produces a number
```

**Finding**, **proving**, and **judging** are three different operations. If the
component that finds a quote is also the component that decides what it means,
nothing independent is checking it — a model that surfaces a passage and then
grades its own passage can drift in one direction without anything catching it.

`harvest.verify_candidate()` re-opens the cached source PDF and locates the text.
That gate sits between the two, and it is mechanical: same document in, same
answer out, no judgement involved.

---

## `eba_data.py` — reading the regulatory filings

The EBA publishes long-format: one row per bank, period, item code and dimension
combination. Totals are the rows where **every** breakdown dimension is zero,
with `Perf_Status` carrying the split that matters:

| code | meaning |
|---|---|
| 0 | total gross loans |
| 2 | non-performing |
| 12 | performing, but significant increase in credit risk (Stage 2) |

Two traps this module handles, both found by checking aggregates against
published EBA figures rather than trusting the parse:

- **The collateral item has no total row.** Item `2520625` is only ever reported
  split by exposure class, so it must be summed rather than filtered on
  `Exposure == 0` like its neighbours. Filtering returns silent nulls.
- **The fully-loaded CET1 series stops in 2024.** Transitional arrangements have
  run off, so `2520146` is empty from 2025-Q1 and the transitional ratio
  (`2520140`) is now the live series. Ratios are also reported as fractions, not
  percentages, so they are normalised once at the source.

---

## `pressure.py` — what the balance sheet forces

Four factors, percentile-ranked within the universe, deliberately
non-overlapping so nothing is counted twice:

- NPL ratio — how bad the book is relative to its own size
- Unreserved NPLs ÷ CET1 — loss still to take against the buffer absorbing it
- Stage 2 share — forward NPL formation
- Absolute NPL stock, log — is it investable at fund scale

**Coverage is excluded on purpose.** It pulls in two directions at once: a weakly
provisioned bank faces *more* supervisory pressure but crystallises a *larger*
P&L hit on sale, so it moves slower. A well-provisioned bank can transact near
carrying value — readier, not more desperate. Folding those into one number
destroys the distinction, so coverage is reported separately as
`transaction_ready`. Coverage still reaches the score, but only through
`net_npl_to_cet1`, where it belongs.

---

## `intent.py` — classifying disclosure prose

DeepSeek (`deepseek-chat`, `temperature=0`, JSON mode) via the OpenAI-compatible
endpoint. Three constraints:

1. **The model never sees or emits a number.** It picks a label from a fixed
   ladder; all arithmetic happens in Python afterwards.
2. **Evidence must be copied character-for-character.** If the returned quote is
   not a substring of the input, the evidence is dropped and the signal flagged.
3. **Unverified text scores zero.** `IntentSignal.score()` returns 0 unless
   provenance is `VERIFIED_VERBATIM`. Default-deny: anything arriving without
   explicit provenance fails closed.

Falls back to a deterministic keyword scorer with no API key, so the notebooks
run for anyone who clones this. Failures print loudly rather than degrading
silently — a broken key should not look like a bank with nothing to say.

---

## `ranking.py` — the cross

|  | intent stated | intent absent |
|---|---|---|
| **high pressure** | Act now | Watch |
| **low pressure** | Opportunistic | Deprioritise |

With one extra state the grid does not have: a bank whose disclosure has not been
read is **not** placed in "intent absent". It gets
`Act now (intent unconfirmed)`. Absence of data is not evidence of absence, and
collapsing the two would be the most expensive error this tool could make.
