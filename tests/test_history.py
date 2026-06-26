"""
Sanity checks for data/monthly_returns.parquet.

Run: python -m pytest tests/test_history.py -v
"""

from pathlib import Path
import pandas as pd
import pytest

PARQUET = Path(__file__).parent.parent / "data" / "monthly_returns.parquet"

MAIN_SERIES = [
    "US_Stocks", "Canadian_Stocks", "International_Stocks",
    "Bonds", "T_Bills", "Inflation",
    "Aggressive", "Moderate", "Conservative",
]
SUPPLEMENTARY = ["USD_CAD", "Prime_CA", "Prime_US"]
# Simple ETF sleeve — USD growth-of-$1000, proxy-backfilled (not CAD-converted).
ETF_SERIES = ["VOO_USD", "VGT_USD", "SCHD_USD", "Simple_ETF_USD"]
US_CORE_USD = ["US_Stocks_USD", "US_Bonds_USD", "US_TBills_USD", "US_Inflation_USD"]
ALL_COLS = MAIN_SERIES + SUPPLEMENTARY + ETF_SERIES + US_CORE_USD


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    assert PARQUET.exists(), f"Run scripts/build_history.py first — {PARQUET} not found"
    return pd.read_parquet(PARQUET)


def test_columns_present(df):
    missing = [c for c in ALL_COLS if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"


def test_index_is_monthly_and_continuous(df):
    """No gaps in the month-end DatetimeIndex."""
    expected = pd.date_range(df.index[0], df.index[-1], freq="ME")
    assert len(df) == len(expected), (
        f"Expected {len(expected)} months, got {len(df)}. "
        "There may be gaps in the index."
    )


def test_date_range(df):
    assert df.index[0].year == 1956
    assert df.index[-1].year == 2025


def test_growth_series_start_at_1000(df):
    """All growth-of-$1000 series should start very close to 1000."""
    for col in MAIN_SERIES:
        first_valid = df[col].dropna().iloc[0]
        assert abs(first_valid - 1000.0) < 1.0, (
            f"{col} first non-NaN value is {first_valid:.2f}, expected ~1000"
        )


def test_no_nan_in_core_windows(df):
    """US Stocks and Bonds should have no NaN from 1956 onward."""
    for col in ["US_Stocks", "Bonds", "T_Bills", "Inflation"]:
        nan_count = df[col].isna().sum()
        assert nan_count == 0, f"{col} has {nan_count} NaN values"


def test_canadian_stocks_starts_1979(df):
    """^GSPTSE data starts ~1979; rows before that should be NaN."""
    assert df.loc["1975-01-31", "Canadian_Stocks"] != df.loc["1975-01-31", "Canadian_Stocks"]  # NaN
    assert df.loc["1985-01-31", "Canadian_Stocks"] > 0


def test_canadian_stocks_cagr_reasonable(df):
    """With dividends included via XIU splice, TSX CAGR should be 8–12%."""
    cdn = df["Canadian_Stocks"].dropna()
    years = (cdn.index[-1] - cdn.index[0]).days / 365.25
    cagr = (cdn.iloc[-1] / cdn.iloc[0]) ** (1 / years) - 1
    assert 0.07 < cagr < 0.13, (
        f"Canadian_Stocks CAGR = {cagr:.1%}; expected 7–13% with dividends"
    )


def test_international_stocks_starts_around_1990(df):
    """After Step 0b, international data should reach back to 1990 (or 2001 fallback)."""
    first_valid = df["International_Stocks"].first_valid_index()
    assert first_valid.year <= 2001, (
        f"International_Stocks starts {first_valid} — expected 1990 or 2001 fallback"
    )
    assert df.loc["2005-01-31", "International_Stocks"] > 0


def test_growth_series_are_positive(df):
    for col in MAIN_SERIES:
        valid = df[col].dropna()
        assert (valid > 0).all(), f"{col} has non-positive values"


def test_growth_series_end_values(df):
    """Ballpark sanity on 2025-12 terminal values (USD FX-adjusted to CAD)."""
    end = df.loc["2025-12-31"]
    # US Stocks: Shiller data + SPY splice, FX-adj to CAD. S&P 500 grew ~780x in USD
    # from 1956; CAD has weakened vs USD slightly over this period.
    assert 200_000 < end["US_Stocks"] < 2_000_000, f"US_Stocks = {end['US_Stocks']:.0f}"
    assert end["Bonds"] > end["T_Bills"] > end["Inflation"], (
        "Expected Bonds > T-Bills > Inflation in terminal value"
    )


def test_usdcad_bretton_woods(df):
    """USD/CAD should be 1.00 during the Bretton Woods era (pre-1971)."""
    pre_71 = df.loc["1956-01-31":"1970-12-31", "USD_CAD"]
    assert (pre_71 == 1.0).all(), "Bretton Woods USD/CAD should be hard-coded 1.00"


def test_prime_rates_are_percentages(df):
    """Prime rates should be percent p.a., typically between 0 and 25."""
    for col in ["Prime_CA", "Prime_US"]:
        valid = df[col].dropna()
        assert valid.between(0, 30).all(), f"{col} has out-of-range values: {valid.describe()}"


# ── Simple ETF sleeve (USD) ──────────────────────────────────────────────────

def test_etf_series_start_at_1000(df):
    """Each ETF/blend series rebases to ~1000 at its first valid date."""
    for col in ETF_SERIES:
        first_valid = df[col].dropna().iloc[0]
        assert abs(first_valid - 1000.0) < 1.0, (
            f"{col} first non-NaN value is {first_valid:.2f}, expected ~1000"
        )


def test_etf_series_are_positive(df):
    for col in ETF_SERIES:
        valid = df[col].dropna()
        assert (valid > 0).all(), f"{col} has non-positive values"


def test_etf_backfill_start_dates(df):
    """Proxy splices extend each ETF back to its proxy's start.

    VOO ← Shiller S&P 500 (1956), VGT ← QQQ (1999), SCHD ← VYM (2006).
    The blend starts wherever its earliest component (VOO) starts.
    """
    assert df["VOO_USD"].first_valid_index().year <= 1956, "VOO should backfill to 1956"
    assert df["VGT_USD"].first_valid_index().year <= 2000, "VGT should backfill to ~1999 via QQQ"
    schd_start = df["SCHD_USD"].first_valid_index()
    assert schd_start.year <= 2007, f"SCHD should backfill to ~2006 via VYM, got {schd_start}"
    assert df["Simple_ETF_USD"].first_valid_index().year <= 1956


def test_voo_is_usd_not_cad(df):
    """VOO is the S&P 500 in USD; US_Stocks is the same index FX-adjusted to CAD.

    CAD weakened vs USD over the period, so the CAD line ends higher than the
    USD line. This guards against accidentally routing VOO through to_cad().
    """
    end = df.loc["2025-12-31"]
    assert end["VOO_USD"] < end["US_Stocks"], (
        "VOO_USD (USD) should end below US_Stocks (CAD); did it get FX-converted?"
    )
    # Sanity: VOO in USD should still be a large multiple of the $1000 base.
    assert 100_000 < end["VOO_USD"] < 1_500_000, f"VOO_USD = {end['VOO_USD']:.0f}"


def test_simple_etf_blend_between_components(df):
    """The blend's terminal value lies between the weakest and strongest sleeve.

    Compared over the common window where all three components exist (SCHD's
    proxy start, ~2006-11), each series rebased to that date.
    """
    common = df[["VOO_USD", "VGT_USD", "SCHD_USD", "Simple_ETF_USD"]].dropna()
    rebased = common / common.iloc[0] * 1000
    end = rebased.iloc[-1]
    lo = min(end["VOO_USD"], end["VGT_USD"], end["SCHD_USD"])
    hi = max(end["VOO_USD"], end["VGT_USD"], end["SCHD_USD"])
    assert lo <= end["Simple_ETF_USD"] <= hi, (
        f"Blend {end['Simple_ETF_USD']:.0f} outside component range [{lo:.0f}, {hi:.0f}]"
    )


# ── US core sleeve (USD) ──────────────────────────────────────────────────────

def test_us_core_usd_start_at_1000(df):
    for col in US_CORE_USD:
        first_valid = df[col].dropna().iloc[0]
        assert abs(first_valid - 1000.0) < 1.0, f"{col} starts at {first_valid:.2f}, expected ~1000"


def test_us_core_usd_reach_1956(df):
    for col in US_CORE_USD:
        assert df[col].first_valid_index().year <= 1956, (
            f"{col} starts {df[col].first_valid_index()}, expected <= 1956"
        )


def test_us_core_usd_positive(df):
    for col in US_CORE_USD:
        valid = df[col].dropna()
        assert (valid > 0).all(), f"{col} has non-positive values"


def test_us_stocks_usd_below_cad(df):
    """US_Stocks_USD (USD) ends below US_Stocks (CAD) — CAD weakened vs USD.
    Guards against accidentally routing the USD series through to_cad()."""
    end = df.loc["2025-12-31"]
    assert end["US_Stocks_USD"] < end["US_Stocks"], "US_Stocks_USD should be < US_Stocks (CAD)"
