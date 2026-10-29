"""Structured pressure score: how hard is this bank being pushed to sell.

Everything here is derived from reported regulatory data. It measures capacity
and constraint -- what a bank can afford to keep on balance sheet -- and says
nothing about whether management intends to act. Intent is the separate signal
in `intent.py`; combining the two is the point of the exercise.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

# Direction of each factor: +1 where a higher raw value means more pressure.
_FACTOR_SIGN = {
    "npl_ratio": +1,
    "net_npl_to_cet1": +1,
    "stage2_ratio": +1,
    "npl_stock": +1,
}


def _percentile(series: pd.Series, sign: int) -> pd.Series:
    """Rank to 0-100 within the universe. Ties share the average rank."""
    return 100 * (sign * series).rank(pct=True, na_option="keep")


def add_pressure_score(panel: pd.DataFrame) -> pd.DataFrame:
    """Attach per-factor percentiles and the weighted pressure score."""
    df = panel.copy()

    # Absolute stock enters in log space: the gap between a EUR 1bn and a
    # EUR 5bn book matters far more than between EUR 30bn and EUR 34bn.
    df["npl_stock"] = np.log(df["loans_npl"].clip(lower=1))

    for factor, sign in _FACTOR_SIGN.items():
        df[f"pct_{factor}"] = _percentile(df[factor], sign)

    df["pressure_score"] = sum(
        C.PRESSURE_WEIGHTS[f] * df[f"pct_{f}"] for f in _FACTOR_SIGN
    )

    # Readiness is deliberately NOT part of pressure -- see config for why.
    df["transaction_ready"] = df["coverage_ratio"] >= C.READINESS_COVERAGE_FLOOR

    # Collateral received can be reported above the exposure it secures, so the
    # secured share is capped for interpretation. Uncapped value kept for audit.
    df["npl_secured_pct_capped"] = df["npl_secured_pct"].clip(upper=100)

    return df.sort_values("pressure_score", ascending=False).reset_index(drop=True)


def factor_table(df: pd.DataFrame, top: int = 15) -> pd.DataFrame:
    """Readable breakdown of what is driving each bank's score."""
    cols = [
        "bank", "country", "loans_total", "loans_npl", "npl_ratio",
        "stage2_ratio", "coverage_ratio", "net_npl_to_cet1", "cet1_ratio",
        "pressure_score", "transaction_ready",
    ]
    return df[cols].head(top)


def country_summary(df: pd.DataFrame) -> pd.DataFrame:
    """System-level view: where is the stock, and how well reserved is it."""
    rows = []
    for name, x in df.groupby("country_name"):
        rows.append(
            {
                "country": name,
                "banks": len(x),
                "loans_total_eur_bn": x["loans_total"].sum() / 1000,
                "npl_stock_eur_bn": x["loans_npl"].sum() / 1000,
                "npl_ratio": 100 * x["loans_npl"].sum() / x["loans_total"].sum(),
                "coverage_ratio": 100 * x["impairment_npl"].sum() / x["loans_npl"].sum(),
                "stage2_ratio": 100 * x["loans_stage2"].sum() / x["loans_total"].sum(),
                "mean_pressure": x["pressure_score"].mean(),
            }
        )
    out = pd.DataFrame(rows).set_index("country")
    return out.sort_values("npl_stock_eur_bn", ascending=False)
