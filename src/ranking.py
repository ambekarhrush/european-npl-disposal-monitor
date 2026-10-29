"""Combine the structured pressure score with extracted disposal intent.

The two signals answer different questions and neither is sufficient alone:

    pressure  -- what the balance sheet forces management to deal with
    intent    -- what management has actually said it will do

Crossing them is the output. A bank under heavy pressure that has said nothing
is a different call from one that has announced a programme, and both are
different from a bank that is comfortable but opportunistic.
"""

from __future__ import annotations

import pandas as pd

from . import config as C
from . import eba_data, intent as intent_mod, pressure as pressure_mod

# Pressure is a percentile score, so the cut is a percentile too.
PRESSURE_CUT = 65.0
INTENT_CUT = 40.0

QUADRANT_ACTION = {
    "Act now": "High pressure, stated intent. Engage directly -- a process is likely within 12 months.",
    "Watch": "High pressure, no stated intent. The constraint does not go away; expect a process without a public signal first.",
    "Opportunistic": "Lower pressure, stated intent. Will transact but is price-sensitive, not forced.",
    "Deprioritise": "Lower pressure, no stated intent. No reason to spend origination time here this cycle.",
    "Act now (intent unconfirmed)": "High pressure. Disclosure layer not yet verified for this name, so intent is unknown rather than absent.",
}


def assign_quadrant(pressure_score: float, intent_score: float, intent_known: bool) -> str:
    """Place a bank on the pressure x intent grid."""
    high_pressure = pressure_score >= PRESSURE_CUT
    # An unverified or missing intent reading is explicitly NOT the same as a
    # bank having said nothing. Absence of data is not evidence of silence.
    if not intent_known:
        return "Act now (intent unconfirmed)" if high_pressure else "Deprioritise"
    high_intent = intent_score >= INTENT_CUT
    if high_pressure and high_intent:
        return "Act now"
    if high_pressure:
        return "Watch"
    if high_intent:
        return "Opportunistic"
    return "Deprioritise"


def _rationale(row) -> str:
    """One line a human can argue with, naming the binding constraint."""
    bits = [f"NPL ratio {row['npl_ratio']:.1f}%"]
    if row["stage2_ratio"] >= 12:
        bits.append(f"Stage 2 at {row['stage2_ratio']:.1f}% signals further formation")
    if row["coverage_ratio"] < C.READINESS_COVERAGE_FLOOR:
        bits.append(f"coverage only {row['coverage_ratio']:.0f}% so a sale crystallises loss")
    else:
        bits.append(f"coverage {row['coverage_ratio']:.0f}% allows a sale near carrying value")
    if row["net_npl_to_cet1"] >= 25:
        bits.append(f"unreserved NPLs equal {row['net_npl_to_cet1']:.0f}% of CET1")
    return "; ".join(bits) + "."


def build_ranking(panel=None, signals=None, save=True) -> pd.DataFrame:
    """Full pipeline: panel -> pressure -> intent merge -> quadrant."""
    if panel is None:
        panel = eba_data.build_bank_panel()
    scored = pressure_mod.add_pressure_score(panel)

    if signals is None:
        try:
            signals = intent_mod.load_cached()
        except FileNotFoundError:
            signals = intent_mod.run_extraction()
    intent_df = intent_mod.intent_frame(signals)

    keep = ["lei", "signal", "horizon", "evidence", "rationale", "source_url",
            "intent_score", "intent_verified", "method"]
    if intent_df.empty:
        for col in keep[1:]:
            scored[col] = None
        scored["intent_score"] = 0.0
        scored["intent_verified"] = False
    else:
        scored = scored.merge(intent_df[keep], on="lei", how="left")
        scored["intent_score"] = scored["intent_score"].fillna(0.0)
        scored["intent_verified"] = scored["intent_verified"].fillna(False)

    scored["quadrant"] = [
        assign_quadrant(r["pressure_score"], r["intent_score"], bool(r["intent_verified"]))
        for _, r in scored.iterrows()
    ]
    scored["why"] = [_rationale(r) for _, r in scored.iterrows()]

    scored = scored.sort_values(
        ["pressure_score", "intent_score"], ascending=False
    ).reset_index(drop=True)
    scored.insert(0, "rank", range(1, len(scored) + 1))

    if save:
        C.PROCESSED.mkdir(parents=True, exist_ok=True)
        scored.to_csv(C.PROCESSED / "pipeline_ranking.csv", index=False)
    return scored


def pipeline_table(df: pd.DataFrame, top: int = 15) -> pd.DataFrame:
    cols = ["rank", "bank", "country", "loans_npl", "npl_ratio", "stage2_ratio",
            "coverage_ratio", "net_npl_to_cet1", "pressure_score", "quadrant"]
    return df[cols].head(top)


def coverage_note(df: pd.DataFrame) -> str:
    """One-line statement of how much of the intent layer is actually live."""
    verified = int(df["intent_verified"].sum())
    return (
        f"{verified} of {len(df)} banks carry a provenance-verified disclosure quote. "
        f"The remaining {len(df) - verified} are ranked on structured data only and "
        "are reported as intent-unconfirmed rather than as silent."
    )
