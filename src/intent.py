"""Disposal-intent extraction from bank disclosure text.

Regulatory data says what a bank CAN afford to hold. It cannot say what
management plans to do. That lives in prose -- strategic plan commentary, NPE
reduction targets, results-call language -- and nobody reads it across fifty
banks by hand. This module turns that prose into a scored, cited signal.

Design rules, in order of importance:

1. Every signal must carry the sentence it came from, plus a source URL.
   An extracted score with no quote behind it is not usable in a credit
   process and would rightly be ignored by anyone reading this.
2. The model never sees a number and never invents one. It classifies text
   into a fixed schema. All arithmetic happens in Python afterwards.
3. The pipeline degrades to a deterministic keyword scorer with no API key,
   so the notebook runs for anyone who clones the repository.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict

from . import config as C

CORPUS_PATH = C.RAW / "disclosure_corpus.json"
CACHE_PATH = C.PROCESSED / "intent_extractions.json"

# DeepSeek exposes an OpenAI-compatible endpoint, so the official openai SDK
# drives it with nothing but a base_url change.
MODEL = "deepseek-chat"
BASE_URL = "https://api.deepseek.com"
API_KEY_VAR = "DEEPSEEK_API_KEY"

# --- Extraction schema -----------------------------------------------------
# Ordered weakest to strongest. The ladder matters more than the labels: an
# announced programme is a different object to "we keep all options open".
SIGNAL_LADDER = {
    "none": 0,          # no disposal language found
    "denial": 0,        # explicitly ruling out disposals
    "monitoring": 25,   # generic "we keep the portfolio under review"
    "exploring": 50,    # actively assessing inorganic / market options
    "target": 75,       # a stated NPE ratio or reduction target with a date
    "programme": 100,   # a named, sized or announced disposal programme
}

HORIZON_MULTIPLIER = {
    "near": 1.00,    # within 12 months
    "medium": 0.75,  # 1-3 years
    "long": 0.50,    # beyond 3 years / no date
    "unknown": 0.60,
}

PROMPT_TEMPLATE = """You are reading disclosure text from a European bank to assess \
whether it intends to sell non-performing loan portfolios.

Bank: {bank}
Source: {source_document} ({period})

TEXT:
\"\"\"{quote}\"\"\"

Classify the disposal intent expressed in this text. Respond with JSON only:

{{
  "signal": one of ["none","denial","monitoring","exploring","target","programme"],
  "horizon": one of ["near","medium","long","unknown"],
  "evidence": the single most load-bearing sentence, copied verbatim from TEXT,
  "rationale": one sentence explaining the classification
}}

Rules:
- "evidence" MUST be copied character-for-character from TEXT. Never paraphrase.
- If the text does not discuss NPL/NPE disposals at all, return "none" with
  evidence "".
- Do not infer intent from the bank's reputation or from anything you know
  outside TEXT. Classify only what the text says.
"""


@dataclass
class IntentSignal:
    lei: str
    bank: str
    signal: str
    horizon: str
    evidence: str
    rationale: str
    source_document: str
    source_url: str
    period: str
    method: str  # "llm" or "keyword"
    provenance: str = "SYNTHETIC_ILLUSTRATIVE"

    @property
    def verified(self) -> bool:
        return self.provenance == "VERIFIED_VERBATIM"

    def score(self) -> float:
        """Intent score, or 0 if the underlying quote is not yet verified.

        Unverified text cannot generate a tradeable signal. Scoring it would
        let placeholder language flow into the ranking indistinguishably from
        real disclosure, which is the one failure this repository must not have.
        """
        if not self.verified:
            return 0.0
        base = SIGNAL_LADDER.get(self.signal, 0)
        return base * HORIZON_MULTIPLIER.get(self.horizon, 0.6)


# --- Deterministic fallback ------------------------------------------------
# Used when no API key is present. Crude by design -- its job is to keep the
# notebook runnable and to give the LLM something to be measured against, not
# to be good.
_KEYWORD_RULES = [
    ("programme", r"(disposal programme|securitisation of|gacs|npe sale|portfolio sale|signed an agreement to (sell|dispose))"),
    ("target", r"(npe ratio (of|below|to)|reduce .{0,30}(npe|npl).{0,30}(to|below)|target.{0,20}(npe|npl))"),
    ("exploring", r"(inorganic|evaluating .{0,30}options|exploring .{0,30}(sale|disposal)|assessing .{0,30}disposal)"),
    ("monitoring", r"(under review|monitor.{0,20}portfolio|keep .{0,20}options)"),
    ("denial", r"(no plans to sell|do not intend to dispose|retain the portfolio)"),
]

_HORIZON_RULES = [
    ("near", r"(by (the end of )?(this|the current) year|within (the next )?12 months|in 202[5-6])"),
    ("medium", r"(by 202[7-8]|over the next (two|three) years|2026-202[78])"),
    ("long", r"(by 20[3-9]\d|over the medium to long term)"),
]


def _keyword_extract(entry: dict) -> IntentSignal:
    text = entry["quote"].lower()
    signal, horizon = "none", "unknown"
    for name, pattern in _KEYWORD_RULES:
        if re.search(pattern, text):
            signal = name
            break
    for name, pattern in _HORIZON_RULES:
        if re.search(pattern, text):
            horizon = name
            break
    evidence = entry["quote"].split(".")[0].strip() + "." if signal != "none" else ""
    return IntentSignal(
        lei=entry["lei"], bank=entry["bank"], signal=signal, horizon=horizon,
        evidence=evidence, rationale="Matched deterministic keyword rule.",
        source_document=entry["source_document"], source_url=entry.get("source_url", ""),
        period=entry.get("period", ""), method="keyword",
        provenance=entry.get("provenance", "SYNTHETIC_ILLUSTRATIVE"),
    )


# --- LLM path --------------------------------------------------------------

def build_prompt(entry: dict) -> str:
    return PROMPT_TEMPLATE.format(
        bank=entry["bank"],
        source_document=entry["source_document"],
        period=entry.get("period", "n/a"),
        quote=entry["quote"],
    )


def _llm_extract(entry: dict, client) -> IntentSignal:
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=600,
        temperature=0,  # classification, not generation
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": build_prompt(entry)}],
    )
    raw = resp.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    parsed = json.loads(raw)

    evidence = parsed.get("evidence", "")
    # Verification gate: the model is only allowed to cite text that actually
    # appears in the source. This is what makes the output auditable, and it is
    # the whole reason an LLM is acceptable in a credit workflow at all.
    if evidence and evidence not in entry["quote"]:
        evidence = ""
        parsed["rationale"] = (
            "Quote failed verbatim check against source; evidence dropped. "
            + parsed.get("rationale", "")
        )

    return IntentSignal(
        lei=entry["lei"], bank=entry["bank"],
        signal=parsed.get("signal", "none"), horizon=parsed.get("horizon", "unknown"),
        evidence=evidence, rationale=parsed.get("rationale", ""),
        source_document=entry["source_document"], source_url=entry.get("source_url", ""),
        period=entry.get("period", ""), method="llm",
        provenance=entry.get("provenance", "SYNTHETIC_ILLUSTRATIVE"),
    )


def _load_env():
    """Pick up a project-local .env so the key never has to be exported by hand.

    Deliberately does not override an already-set environment variable, so an
    exported key still wins over a stale file.
    """
    try:
        from dotenv import load_dotenv

        load_dotenv(C.ROOT / ".env", override=False)
    except ImportError:
        pass


def api_available() -> bool:
    _load_env()
    return bool(os.environ.get(API_KEY_VAR))


def make_client():
    """OpenAI-compatible client pointed at DeepSeek."""
    from openai import OpenAI

    _load_env()
    key = os.environ.get(API_KEY_VAR)
    if not key:
        raise RuntimeError(
            f"{API_KEY_VAR} not set. Put it in {C.ROOT / '.env'} as "
            f"{API_KEY_VAR}=sk-... or export it in the shell."
        )
    return OpenAI(api_key=key, base_url=BASE_URL)


def load_corpus() -> list[dict]:
    with open(CORPUS_PATH) as fh:
        return json.load(fh)["entries"]


def run_extraction(entries=None, use_llm=None, cache=True) -> list[IntentSignal]:
    """Extract intent for each corpus entry, preferring the LLM when available."""
    entries = entries if entries is not None else load_corpus()
    use_llm = api_available() if use_llm is None else use_llm

    client = None
    if use_llm:
        try:
            client = make_client()
        except Exception as exc:
            print(f"[intent] LLM unavailable ({exc}); using keyword fallback.")
            use_llm = False

    out = []
    for entry in entries:
        if use_llm and client is not None:
            try:
                out.append(_llm_extract(entry, client))
                continue
            except Exception as exc:
                # Surface rather than swallow: a silent fallback would make a
                # broken API key look like a bank with nothing to say.
                print(f"[intent] {entry['bank'][:34]}: LLM call failed ({exc}); "
                      "falling back to keyword rule for this entry.")
        out.append(_keyword_extract(entry))

    if cache:
        C.PROCESSED.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "w") as fh:
            json.dump([asdict(s) for s in out], fh, indent=2)
    return out


def load_cached() -> list[IntentSignal]:
    with open(CACHE_PATH) as fh:
        return [IntentSignal(**d) for d in json.load(fh)]


def intent_frame(signals: list[IntentSignal]):
    """Collapse to one row per bank, keeping the strongest signal found."""
    import pandas as pd

    rows = [
        {**asdict(s), "intent_score": s.score(), "intent_verified": s.verified}
        for s in signals
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    idx = df.groupby("lei")["intent_score"].idxmax()
    return df.loc[idx].reset_index(drop=True)
