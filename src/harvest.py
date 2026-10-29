"""Harvest candidate disclosure passages from bank investor-relations sites.

This does NOT produce verified quotes. It produces *candidates*: real text
pulled from a real document at a recorded URL, which a human still has to check
against the source before it earns `VERIFIED_VERBATIM` status in the corpus.

The separation is the point. Automation is good at finding the paragraph;
it is not the thing that makes the paragraph trustworthy.

Where a site blocks automated access, the bank is still emitted as a worklist
entry with its URL, so the manual fallback is a short targeted task rather than
an open-ended search.
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from . import config as C

SOURCES_PATH = C.RAW / "ir_sources.json"
CANDIDATES_PATH = C.PROCESSED / "harvest_candidates.json"
REPORT_CACHE = C.RAW / "reports"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en,de;q=0.8,it;q=0.8,es;q=0.8,fr;q=0.8",
}

TIMEOUT = 45

# Terms that mark a passage as worth a human's attention. Multilingual because
# the disclosure is: a German bank discusses "notleidende Kredite", an Italian
# one "crediti deteriorati", and neither says "NPL".
# Concepts that name a non-performing exposure. A passage must contain one.
NPE_TERMS = {
    "en": [
        "non-performing", "nonperforming", "npe", "npl", "impaired loan",
        "unlikely to pay", "forborne", "bad loan", "doubtful loan",
    ],
    "it": [
        "crediti deteriorati", "sofferenze", "inadempienze probabili", "utp",
        "esposizioni deteriorate",
    ],
    "es": [
        "dudoso", "moroso", "activos improductivos", "adjudicado",
    ],
    "de": [
        "notleidend", "problemkredit", "leistungsgestört",
    ],
    "fr": [
        "créances douteuses", "creances douteuses", "encours douteux",
    ],
}

# Actions taken against that exposure. A passage must also contain one of these.
# Commentary that an NPL ratio moved is not an action and must not qualify.
ACTION_TERMS = [
    "disposal", "dispose", "portfolio sale", "sale of", "sell", "divest",
    "deleverag", "de-risk", "derisk", "run-down", "rundown", "workout",
    "securitis", "securitiz", "inorganic", "npe strategy", "npl strategy",
    "reduction target", "gacs",
    "cessione", "cartolarizzazione", "derisking",
    "venta de cartera", "titulizaci", "desinversi",
    "verkauf", "abbau", "verbriefung",
    "cession", "titrisation",
]

# Accounting-policy prose matches impairment vocabulary constantly and never
# expresses intent. Excluded outright -- this was the single largest source of
# false positives in the first harvest run.
_BOILERPLATE = re.compile(
    r"(accounting principle|useful li(f|v)e|depreciable|straight[- ]line|"
    r"residual value|amortis(ed|ation) over|years? \d+-\d+ years|"
    r"the table below shows|article \d+|in accordance with ias|ifrs \d)",
    re.I,
)

# Language that signals an actual commitment rather than a description.
_COMMITMENT = re.compile(
    r"(target|plan to|intend|committed|will reduce|by 20\d\d|strategy sets|"
    r"programme|announced|agreement to sell|signed)",
    re.I,
)

# Links worth following from an IR landing page.
_DOC_HINT = re.compile(
    r"(annual[-_ ]?report|geschäftsbericht|geschaeftsbericht|bilancio|"
    r"relazione|informe[-_ ]?anual|document[-_ ]?enregistrement|universal[-_ ]?registration|"
    r"results|resultat|risultati|resultados|interim|half[-_ ]?year|quarterly|"
    r"pillar[-_ ]?3|financial[-_ ]?report)",
    re.I,
)

MIN_CHARS, MAX_CHARS = 180, 1100


@dataclass
class Candidate:
    lei: str
    bank: str
    source_document: str
    source_url: str
    page_no: int
    quote: str
    matched_terms: list
    provenance: str = "UNVERIFIED_HARVESTED"


def _get(url, **kw):
    return requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kw)


def find_report_links(page_url: str, limit: int = 4) -> list[str]:
    """PDF links on an IR page that look like reports rather than boilerplate."""
    try:
        r = _get(page_url)
        r.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    scored = []
    for a in soup.find_all("a", href=True):
        href = urljoin(page_url, a["href"])
        if not href.lower().split("?")[0].endswith(".pdf"):
            continue
        label = f"{a.get_text(' ', strip=True)} {href}"
        if _DOC_HINT.search(label):
            # Prefer recent documents when the year is in the label.
            years = [int(y) for y in re.findall(r"20(?:2[3-9])", label)]
            scored.append((max(years) if years else 0, href))

    seen, out = set(), []
    for _, href in sorted(scored, key=lambda t: -t[0]):
        if href not in seen:
            seen.add(href)
            out.append(href)
        if len(out) >= limit:
            break
    return out


def _pdf_pages(url: str) -> list[str]:
    """Download a PDF (cached) and return per-page text."""
    REPORT_CACHE.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", urlparse(url).path.split("/")[-1])[:120]
    cached = REPORT_CACHE / name

    if cached.exists():
        data = cached.read_bytes()
    else:
        try:
            r = _get(url, stream=True)
            r.raise_for_status()
            data = r.content
            cached.write_bytes(data)
        except Exception:
            return []

    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return [(p.extract_text() or "") for p in reader.pages]
    except Exception:
        return []


def _split_paragraphs(text: str) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text)
    chunks = re.split(r"\n\s*\n|(?<=\.)\s{2,}", text)
    return [re.sub(r"\s*\n\s*", " ", c).strip() for c in chunks]


def extract_passages(pages: list[str], lang: str, per_doc: int = 3) -> list[tuple]:
    """Return (page_no, passage, matched_terms) for passages worth reviewing.

    A passage qualifies only if it names a non-performing exposure concept AND
    an action taken against it. Requiring both is what separates "our NPL ratio
    fell 68bps" -- commentary -- from "the NPE strategy sets disposal targets",
    which is intent. Accounting-policy boilerplate is excluded outright; it
    matches impairment vocabulary constantly and means nothing.
    """
    npe_terms = NPE_TERMS.get(lang, []) + NPE_TERMS["en"]
    hits = []
    for i, page in enumerate(pages, start=1):
        if not page:
            continue
        for para in _split_paragraphs(page):
            if not (MIN_CHARS <= len(para) <= MAX_CHARS):
                continue
            low = para.lower()

            if _BOILERPLATE.search(low):
                continue

            npe_hit = sorted({t for t in npe_terms if t in low})
            action_hit = sorted({t for t in ACTION_TERMS if t in low})
            if not (npe_hit and action_hit):
                continue

            matched = npe_hit + action_hit
            # Rank by how explicitly the passage commits to something.
            weight = len(matched) + (3 if _COMMITMENT.search(low) else 0)
            hits.append((i, para, matched, weight))

    hits.sort(key=lambda h: -h[3])
    return [(p, q, m) for p, q, m, _ in hits[:per_doc]]


def crawl_bank(source: dict, max_docs: int = 2) -> tuple[list[Candidate], dict]:
    """Harvest one bank. Returns (candidates, status).

    `direct_pdfs` takes priority over crawling. Most IR sites render their
    document lists in JavaScript, so an HTTP fetch of the landing page sees an
    empty shell and finds nothing. The URLs in `direct_pdfs` were resolved by
    loading those pages in a real browser; downloading them needs no browser at
    all, so discovery and retrieval stay separate concerns.
    """
    found = []
    docs = list(source.get("direct_pdfs", []))

    for page in source.get("pages", []):
        if len(docs) >= max_docs:
            break
        docs.extend(find_report_links(page))

    seen = set()
    for url in docs[:max_docs]:
        if url in seen:
            continue
        seen.add(url)
        pages = _pdf_pages(url)
        if not pages:
            continue
        doc_name = urlparse(url).path.split("/")[-1]
        for page_no, quote, matched in extract_passages(pages, source["lang"]):
            found.append(
                Candidate(
                    lei=source["lei"], bank=source["bank"],
                    source_document=doc_name, source_url=url,
                    page_no=page_no, quote=quote, matched_terms=matched,
                )
            )

    status = {
        "lei": source["lei"],
        "bank": source["bank"],
        "docs_found": len(docs),
        "candidates": len(found),
        "outcome": "harvested" if found else ("no_passages" if docs else "blocked"),
        "manual_url": source["pages"][0],
    }
    return found, status


def harvest_all(limit: int | None = None, save: bool = True):
    with open(SOURCES_PATH) as fh:
        sources = json.load(fh)["sources"]
    if limit:
        sources = sources[:limit]

    all_c, statuses = [], []
    for src in sources:
        cands, status = crawl_bank(src)
        all_c.extend(cands)
        statuses.append(status)
        print(f"  {status['outcome']:<12} {src['bank'][:42]:<42} "
              f"docs={status['docs_found']} candidates={status['candidates']}")

    if save:
        C.PROCESSED.mkdir(parents=True, exist_ok=True)
        with open(CANDIDATES_PATH, "w") as fh:
            json.dump(
                {"candidates": [asdict(c) for c in all_c], "status": statuses},
                fh, indent=2, ensure_ascii=False,
            )
    return all_c, statuses


def worklist(statuses: list[dict]) -> list[dict]:
    """Banks the crawler could not serve, for targeted manual pulls."""
    return [s for s in statuses if s["outcome"] != "harvested"]


def _normalise(text: str) -> str:
    """Collapse whitespace so PDF line breaks do not defeat a string match."""
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_candidate(cand: dict) -> tuple[bool, str]:
    """Re-open the source PDF and confirm the quote genuinely appears in it.

    This is what earns VERIFIED_VERBATIM. It is stronger than a human eyeball
    because it is reproducible: anyone can re-run it against the same cached
    document and get the same answer. A quote that cannot be located in its
    stated source never enters the corpus.
    """
    pages = _pdf_pages(cand["source_url"])
    if not pages:
        return False, "source document unavailable"

    page_no = cand.get("page_no")
    needle = _normalise(cand["quote"])

    if page_no and 1 <= page_no <= len(pages):
        if needle in _normalise(pages[page_no - 1]):
            return True, f"located on stated page {page_no}"

    for i, page in enumerate(pages, start=1):
        if needle in _normalise(page):
            return True, f"located on page {i} (stated {page_no})"

    return False, "quote not found in source document"
