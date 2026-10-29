# `scripts/` — command-line tools

Five scripts. The first three move data through the pipeline; the last two build
what a reader actually sees.

```
fetch_data.py  →  harvest_disclosures.py  →  promote_candidates.py --apply
                                                        │
                                          make_notebooks.py · build_onepager.py
```

| script | what it does | safe to re-run |
|---|---|---|
| `fetch_data.py` | download the EBA Transparency Exercise (~130 MB) | yes, skips existing |
| `harvest_disclosures.py` | pull candidate passages from bank reports | yes, PDFs cached |
| `promote_candidates.py` | verify candidates, write them to the corpus | yes, dedupes |
| `make_notebooks.py` | regenerate the four notebooks | yes, overwrites |
| `build_onepager.py` | rebuild the one-page PDF source | yes, overwrites |

---

## The three-step document workflow

This is the part worth understanding, because the steps are deliberately
separate and each one can be inspected before the next runs.

### 1 · `harvest_disclosures.py` — find candidates

Crawls the IR entry points in `data/raw/ir_sources.json`, pulls report PDFs,
extracts passages that name a non-performing exposure **and** an action taken
against it. Requiring both is what separates *"our NPL ratio fell 68bps"*
(commentary) from *"the NPE strategy sets disposal targets"* (intent).

Output is a **review queue**, not a corpus. Nothing it finds is trusted.

Banks it cannot reach are printed as a targeted worklist rather than silently
dropped — a short, specific task instead of an open-ended search.

### 2 · Review

Open `data/processed/harvest_candidates.json`. Keep the passages that genuinely
discuss disposal intent; the extractor is tuned for recall and will surface some
accounting boilerplate.

### 3 · `promote_candidates.py` — verify and write

Re-opens each candidate's source PDF and **locates the text in it**. Only
passages that are found get written to the corpus as `VERIFIED_VERBATIM`.
Anything that cannot be located is rejected and reported.

Runs as a dry run by default. Pass `--apply` to write.

```bash
python scripts/promote_candidates.py           # show what would happen
python scripts/promote_candidates.py --apply   # write it
```

The gate was tested adversarially before being trusted:

| input | result |
|---|---|
| untouched harvested quote | pass |
| plausible sentence never in the document | reject |
| real quote, one word silently altered | **reject** |
| real quote, wrong page claimed | pass, page corrected |

The third row is the one that matters — a model subtly rewording a quote while
keeping it believable is the realistic failure mode.

---

## Extending coverage to a blocked bank

Most IR sites render their document lists in JavaScript, so a plain HTTP fetch
sees an empty shell and finds nothing. Discovery needs a real browser;
downloading does not.

1. Open the bank's IR page in a browser, find its annual/interim report PDFs
2. Add those URLs to its `direct_pdfs` array in `data/raw/ir_sources.json`
3. `python scripts/harvest_disclosures.py`
4. Review, then `python scripts/promote_candidates.py --apply`

About ten minutes per bank.

---

## Rebuilding outputs

Both of these read live pipeline output, so **re-run them after any data change**
or the figures and the one-pager will quietly disagree with the repository.

```bash
python scripts/make_notebooks.py
python scripts/build_onepager.py
```

`build_onepager.py` writes `docs/one-pager.html`. To produce the PDF:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="docs/Ambekar_NPL-Monitor_one-pager.pdf" \
  "file://$(pwd)/docs/one-pager.html"
```

The page is sized to fit a single A4 sheet with a few millimetres of headroom.
Adding content will push it to two pages, so check the fit after editing.
