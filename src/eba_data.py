"""Load bank-level asset quality and capital data from the EBA Transparency Exercise.

The EBA publishes the full exercise as long-format CSVs: one row per
bank / period / item / dimension-combination. Totals are the rows where every
breakdown dimension is zero, with Perf_Status carrying the performing vs
non-performing split.
"""

from __future__ import annotations

import warnings

import pandas as pd

from . import config as C

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# Rows representing an unbroken total: no portfolio, country, exposure-class or
# default-status breakdown. Perf_Status is the one dimension we keep.
_TOTAL_DIMS = {"Portfolio": 0, "Country": 0, "Exposure": 0, "Status": 0}

# Perf_Status codes carrying signal for asset quality.
_PERF_KEEP = {
    0: "total",
    2: "npl",
    12: "stage2",  # performing but significant increase in credit risk
}


def load_institutions() -> pd.DataFrame:
    """Bank identity table: LEI, country, name."""
    df = pd.read_excel(
        C.RAW / "TR_Metadata.xlsx", sheet_name="List of Institutions", header=1
    )
    df = df[["Country", "Desc_country", "LEI_Code", "Name"]].dropna(subset=["LEI_Code"])
    return df.rename(
        columns={
            "Country": "country",
            "Desc_country": "country_name",
            "LEI_Code": "lei",
            "Name": "bank",
        }
    )


def _load_items(path, items, usecols, chunksize=500_000):
    keep = []
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=chunksize, low_memory=False):
        keep.append(chunk[chunk["Item"].isin(items)])
    return pd.concat(keep, ignore_index=True)


def load_asset_quality() -> pd.DataFrame:
    """Gross loans, NPLs, Stage 2 and NPL impairment per bank/period."""
    items = {C.ITEM["loans_gross"], C.ITEM["loans_impairment"], C.ITEM["npe_collateral"]}
    raw = _load_items(
        C.RAW / "tr_cre.csv",
        items,
        usecols=[
            "LEI_Code", "Period", "Item", "Portfolio", "Country",
            "Exposure", "Status", "Perf_Status", "Amount",
        ],
    )

    # Portfolio/Country/Status are always collapsed. Exposure is handled per
    # item below: the loan and impairment items carry an Exposure==0 total row,
    # the collateral item is only ever reported split by exposure class.
    for dim in ("Portfolio", "Country", "Status"):
        raw = raw[raw[dim] == _TOTAL_DIMS[dim]]

    out = {}
    totals = raw[raw["Exposure"] == 0]

    gross = totals[totals["Item"] == C.ITEM["loans_gross"]]
    for code, name in _PERF_KEEP.items():
        sel = gross[gross["Perf_Status"] == code]
        out[f"loans_{name}"] = sel.set_index(["LEI_Code", "Period"])["Amount"]

    imp = totals[
        (totals["Item"] == C.ITEM["loans_impairment"])
        & (totals["Perf_Status"] == C.PERF["non_performing"])
    ]
    out["impairment_npl"] = imp.set_index(["LEI_Code", "Period"])["Amount"]

    coll = raw[
        (raw["Item"] == C.ITEM["npe_collateral"])
        & (raw["Perf_Status"] == C.PERF["non_performing"])
    ]
    out["collateral_npl"] = coll.groupby(["LEI_Code", "Period"])["Amount"].sum()

    df = pd.DataFrame(out).reset_index()
    return df.rename(columns={"LEI_Code": "lei", "Period": "period"})


def load_capital() -> pd.DataFrame:
    """CET1 ratio (fully loaded), RWA and total assets per bank/period."""
    names = {
        C.ITEM["cet1_ratio"]: "cet1_ratio",
        C.ITEM["cet1_capital"]: "cet1_capital",
        C.ITEM["rwa"]: "rwa",
        C.ITEM["total_assets"]: "total_assets",
    }
    raw = _load_items(
        C.RAW / "tr_oth.csv",
        set(names),
        usecols=["LEI_Code", "Period", "Item", "Amount"],
    )
    # These items carry no further breakdown; guard against duplicate reporting
    # rows by taking the max reported value per bank/period/item.
    wide = raw.pivot_table(
        index=["LEI_Code", "Period"], columns="Item", values="Amount", aggfunc="max"
    ).reset_index()

    wide = wide.rename(columns={**names, "LEI_Code": "lei", "Period": "period"})
    # The EBA reports capital ratios as fractions; everything else here is a
    # percentage, so normalise once at the source.
    wide["cet1_ratio"] = 100 * wide["cet1_ratio"]
    return wide[["lei", "period"] + list(names.values())]


def build_bank_panel(latest_only: bool = True) -> pd.DataFrame:
    """Merged panel with derived asset-quality ratios, filtered to the mandate."""
    inst = load_institutions()
    aq = load_asset_quality()
    cap = load_capital()

    df = aq.merge(cap, on=["lei", "period"], how="left").merge(
        inst, on="lei", how="left"
    )

    if latest_only:
        df = df[df["period"] == df["period"].max()].copy()

    df["npl_ratio"] = 100 * df["loans_npl"] / df["loans_total"]
    df["stage2_ratio"] = 100 * df["loans_stage2"] / df["loans_total"]
    df["coverage_ratio"] = 100 * df["impairment_npl"] / df["loans_npl"]
    # Share of the NPL stock backed by collateral -- a secured book sells at a
    # very different price to an unsecured one.
    df["npl_secured_pct"] = 100 * df["collateral_npl"] / df["loans_npl"]
    df["cet1_headroom"] = df["cet1_ratio"] - C.CET1_REQUIREMENT_PROXY
    # Unreserved NPLs as a share of capital: the clearest single measure of how
    # much loss is still sitting unprovisioned relative to the buffer.
    df["net_npl_to_cet1"] = 100 * (df["loans_npl"] - df["impairment_npl"]) / df["cet1_capital"]

    df = df[df["country"].isin(C.TARGET_COUNTRIES)]
    df = df[df["loans_total"] >= C.MIN_LOAN_BOOK_EUR_M]

    return df.sort_values("npl_ratio", ascending=False).reset_index(drop=True)


def period_label(period: int) -> str:
    """202506 -> '2025-Q2'."""
    year, month = divmod(int(period), 100)
    return f"{year}-Q{(month - 1) // 3 + 1}"
