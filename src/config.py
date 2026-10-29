"""Shared configuration: EBA item codes, universe definition, scoring weights."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"
FIGURES = DOCS / "figures"

# --- EBA 2025 EU-wide Transparency Exercise -------------------------------
# Source: https://www.eba.europa.eu/risk-and-data-analysis/risk-analysis/
#         eu-wide-transparency-exercise  (Full database, 2025 exercise)
EBA_BASE = "https://www.eba.europa.eu/assets/TE2025/Full_database/883401"
EBA_FILES = {
    "tr_cre.csv": f"{EBA_BASE}/tr_cre.csv",
    "tr_oth.csv": f"{EBA_BASE}/tr_oth.csv",
    "TR_Metadata.xlsx": f"{EBA_BASE}/TR_Metadata.xlsx",
}

# Item codes, verified against TR_Metadata.xlsx label fields.
ITEM = {
    "loans_gross": 2520603,       # Gross carrying amount, loans & advances
    "loans_impairment": 2520613,  # Accumulated impairment, loans & advances
    "npe_collateral": 2520625,    # Collateral/guarantees held against NPE loans
    # The fully-loaded CET1 series (2520146) stops reporting after 2024-Q4:
    # transitional arrangements have run off, so the transitional ratio is now
    # the live series and the two are equivalent.
    "cet1_ratio": 2520140,        # CET1 ratio, transitional (reported as a fraction)
    "cet1_capital": 2520102,      # CET1 capital, absolute
    "rwa": 2520138,               # Total risk exposure amount
    "total_assets": 2521010,      # Total assets
}

# Perf_Status dimension (metadata sheet 'Perf_status')
PERF = {"total": 0, "performing": 1, "non_performing": 2}

# Target geographies. The intended scope is Italy, Spain, Germany, France and
# the UK, but the EBA exercise covers EU/EEA banks only -- UK institutions left
# the sample after Brexit, so that leg is not addressable from this source.
# Recorded in MANDATE_GAP rather than silently dropped.
TARGET_COUNTRIES = {"IT": "Italy", "ES": "Spain", "DE": "Germany", "FR": "France"}
MANDATE_GAP = {"GB": "United Kingdom - not in EBA sample post-Brexit"}

# Minimum loan book to stay in the universe. Below this a portfolio trade is
# too small to matter to a credit fund operating at institutional scale.
MIN_LOAN_BOOK_EUR_M = 10_000

# --- Pressure score weights -----------------------------------------------
# Deliberately exposed and summing to 1.0 so a reader can disagree with the
# weighting and re-run, rather than having to trust a black box.
# Each factor is percentile-ranked within the universe, so the score is a
# relative league table, not an absolute claim. Factors are deliberately
# non-overlapping: coverage enters only through net_npl_to_cet1, so a weakly
# provisioned bank is not penalised twice.
PRESSURE_WEIGHTS = {
    "npl_ratio": 0.30,        # how bad the book is, relative to its own size
    "net_npl_to_cet1": 0.30,  # unreserved loss against the capital buffer
    "stage2_ratio": 0.20,     # forward pipeline of new NPL formation
    "npl_stock": 0.20,        # absolute stock -- is it investable at fund scale
}

# Coverage is reported separately as "transaction readiness" rather than folded
# into pressure. The two pull in opposite directions and conflating them is the
# most common error in this kind of screen: a weakly provisioned bank is under
# MORE supervisory pressure to act, but crystallises a LARGER P&L hit when it
# sells, so it is slower to transact. A well-provisioned bank can sell at market
# without taking further pain -- it is readier, not more desperate.
READINESS_COVERAGE_FLOOR = 45.0

# SREP-style CET1 requirement proxy. Used to turn a reported CET1 ratio into
# headroom. Banks disclose bank-specific requirements; 10.5% is the common
# Pillar 1 + CCB + typical P2R floor used here as a transparent approximation.
CET1_REQUIREMENT_PROXY = 10.5
