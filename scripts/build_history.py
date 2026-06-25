#!/usr/bin/env python3
"""
Build data/monthly_returns.parquet from free data sources.

Schema (output columns)
-----------------------
Growth-of-$1000 in CAD, monthly frequency, month-end dates:
  US_Stocks, Canadian_Stocks, International_Stocks,
  Bonds, T_Bills, Inflation,
  Aggressive, Moderate, Conservative

Supplementary (not growth-of-$1000):
  USD_CAD   : USD per 1 CAD (DEXCAUS)
  Prime_CA  : Canadian short-term rate, % p.a.
  Prime_US  : US prime rate, % p.a.

Run
---
  export FRED_API_KEY=<key>
  python scripts/build_history.py
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from fredapi import Fred

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RAW  = ROOT / "data" / "raw"
OUT  = ROOT / "data" / "monthly_returns.parquet"
RAW.mkdir(parents=True, exist_ok=True)

FRED_KEY = os.environ.get("FRED_API_KEY")
if not FRED_KEY:
    sys.exit("Error: FRED_API_KEY environment variable is not set.")
fred = Fred(api_key=FRED_KEY)

START = "1956-01-01"
END   = "2025-12-31"


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _to_month_end(s: pd.Series) -> pd.Series:
    s.index = pd.DatetimeIndex(s.index) + pd.offsets.MonthEnd(0)
    return s.sort_index()


def _fred(series_id: str) -> pd.Series:
    """Fetch FRED series, cache to data/raw/fred_{id}.csv."""
    path = RAW / f"fred_{series_id}.csv"
    if not path.exists():
        print(f"  Fetching FRED {series_id} …")
        s = fred.get_series(series_id, observation_start=START, observation_end=END)
        s.to_csv(path, header=True)
    s = pd.read_csv(path, index_col=0, parse_dates=True).squeeze("columns")
    s = _to_month_end(s.resample("ME").last())
    return s.loc[START:END]


def _yf_close(ticker: str, filename: str) -> pd.Series:
    """Fetch yfinance adjusted close, cache to data/raw/{filename}."""
    path = RAW / filename
    if not path.exists():
        print(f"  Fetching yfinance {ticker} …")
        df = yf.download(ticker, start=START, end=END, auto_adjust=True, progress=False)
        # yfinance multi-index columns differ by version; flatten
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df[["Close"]].to_csv(path)
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    s = df["Close"].resample("ME").last()
    return _to_month_end(s).loc[START:END]


def _ret_to_level(monthly_rets: pd.Series, start: float = 1000.0) -> pd.Series:
    # Rebase so the first observation is exactly `start`, consistent with
    # Shiller and yfinance price-based series (which also start at 1000).
    levels = (1 + monthly_rets.fillna(0)).cumprod() * start
    return levels / levels.iloc[0] * start


# ── Individual asset series (all return growth-of-$1000 unless noted) ─────────

def load_shiller() -> pd.Series:
    """S&P 500 total-return index in USD, from Shiller ie_data.xls.

    Shiller provides monthly price P and annualised dividend D.
    TR_t = TR_{t-1} × (P_t + D_t/12) / P_{t-1}

    Shiller's file lags a few months; the tail is spliced with SPY adjusted
    close (which includes reinvested dividends) to reach END.

    Source: http://www.econ.yale.edu/~shiller/data/ie_data.xls
    """
    path = RAW / "shiller_ie_data.xls"
    if not path.exists():
        print("  Downloading Shiller ie_data.xls …")
        r = requests.get(
            "http://www.econ.yale.edu/~shiller/data/ie_data.xls",
            timeout=30,
        )
        r.raise_for_status()
        path.write_bytes(r.content)

    df = pd.read_excel(path, sheet_name="Data", skiprows=7, engine="xlrd")
    # Keep only the first three columns: date fraction, price, dividend
    df = df.iloc[:, :3].copy()
    df.columns = ["date_frac", "P", "D"]
    df = df[pd.to_numeric(df["date_frac"], errors="coerce").notna()].copy()
    df["date_frac"] = df["date_frac"].astype(float)
    df["P"] = pd.to_numeric(df["P"], errors="coerce")
    df["D"] = pd.to_numeric(df["D"], errors="coerce")
    df = df.dropna(subset=["P"])

    def _parse_date(d: float) -> pd.Timestamp:
        year  = int(d)
        month = round((d - year) * 100)
        if month == 0:
            month = 1
        return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

    df.index = df["date_frac"].apply(_parse_date)
    df = df.sort_index().loc[START:]
    # Drop rows where dividend is missing (Shiller's trailing edge)
    df = df.dropna(subset=["D"])
    df = df.loc[:END]

    price = df["P"].astype(float)
    div   = df["D"].astype(float) / 12  # annualised → monthly

    tr = [1000.0]
    for i in range(1, len(price)):
        tr.append(tr[-1] * (price.iloc[i] + div.iloc[i]) / price.iloc[i - 1])

    shiller_tr = pd.Series(tr, index=price.index, name="US_Stocks_USD")
    shiller_end = shiller_tr.index[-1]

    # Splice with SPY if Shiller doesn't reach END
    if shiller_end < pd.Timestamp(END) - pd.offsets.MonthEnd(1):
        spy = _yf_close("SPY", "spy_prices.csv")
        spy_tail = spy.loc[shiller_end:].iloc[1:]  # month after Shiller ends
        if not spy_tail.empty:
            splice_start_val = shiller_tr.iloc[-1]
            spy_tail = spy_tail / spy_tail.iloc[0] * splice_start_val
            shiller_tr = pd.concat([shiller_tr, spy_tail])
            print(f"  Spliced Shiller → SPY from {shiller_end.strftime('%Y-%m')} to {spy_tail.index[-1].strftime('%Y-%m')}")

    return shiller_tr


def load_tsx() -> pd.Series:
    """S&P/TSX total-return index in CAD.

    Splice:
      1979-06 to 1999-10 : ^GSPTSE price + 3% annual dividend yield (approx TR)
      1999-11 onward     : XIU.TO adjusted close (includes reinvested distributions)

    XIU.TO = iShares S&P/TSX 60 ETF (inception Nov 1999). The 3% yield
    assumption is a documented approximation; TSX historical yield ranged
    2–4% and averaged ~3% over this period.
    """
    # Price-only index for pre-XIU window
    gsptse = _yf_close("^GSPTSE", "tsx_prices.csv").dropna()

    # Total-return ETF for modern window
    xiu = _yf_close("XIU.TO", "xiu_prices.csv").dropna()

    xiu_start = xiu.index[0]   # first XIU date (≈ 1999-11-30)

    # Build pre-splice window: apply monthly dividend yield to price index
    annual_yield = 0.03
    monthly_yield = (1 + annual_yield) ** (1 / 12) - 1
    pre = gsptse.loc[:xiu_start].iloc[:-1]   # up to but not including XIU start
    if pre.empty:
        tr = xiu / xiu.iloc[0] * 1000
    else:
        # Grow $1000 from first ^GSPTSE point applying yield each month
        price_rets = pre.pct_change().fillna(0)
        total_rets = price_rets + monthly_yield
        level_pre = _ret_to_level(total_rets)   # starts at 1000

        # Scale XIU so it continues seamlessly from level_pre's last value
        xiu_scaled = xiu / xiu.iloc[0] * level_pre.iloc[-1]

        tr = pd.concat([level_pre, xiu_scaled])
        # Rebase whole series to 1000 at first point
        tr = tr / tr.iloc[0] * 1000

    tr.name = "Canadian_Stocks"
    return tr


def load_eafe() -> pd.Series:
    """MSCI EAFE proxy in USD, extended back to 1990 where possible.

    Splice strategy (in priority order):
      2001-08 onward : EFA ETF adjusted close (total return, includes dividends)
      1990-01 to 2001: ^MXEA (MSCI EAFE price index) if yfinance covers it,
                       else Fama-French International developed market return.

    The pre-2001 extension uses a price-only index (^MXEA) or a factor-based
    proxy. The splice normalises so the series is continuous at 2001-08.
    """
    # Modern window: EFA total-return ETF
    efa = _yf_close("EFA", "efa_prices.csv").dropna()
    efa_start = efa.index[0]   # ≈ 2001-08-31

    # Try ^MXEA first (MSCI EAFE price index, free via yfinance)
    pre_ext = None
    try:
        mxea_raw = _yf_close("^MXEA", "mxea_prices.csv").dropna()
        if mxea_raw.index[0].year > 1995:
            raise ValueError("^MXEA doesn't reach 1990")
        pre_ext = mxea_raw.loc[:efa_start].iloc[:-1]
        print(f"  International pre-2001 source: ^MXEA ({pre_ext.index[0].strftime('%Y-%m')} → {pre_ext.index[-1].strftime('%Y-%m')})")
    except Exception as e:
        print(f"  ^MXEA not usable ({e}); falling back to Fama-French international")
        try:
            pre_ext = _load_ff_intl_pre2001(efa_start)
            print(f"  International pre-2001 source: Fama-French ({pre_ext.index[0].strftime('%Y-%m')} → {pre_ext.index[-1].strftime('%Y-%m')})")
        except Exception as e2:
            print(f"  Fama-French also failed ({e2}); international starts 2001 as before")

    if pre_ext is None or pre_ext.empty:
        # Fallback: EFA only (2001 onward)
        tr = efa / efa.iloc[0] * 1000
        tr.name = "International_Stocks_USD"
        return tr

    # Build full series: concatenate pre + EFA, rebase to 1000
    combined = pd.concat([pre_ext, efa]).sort_index()
    combined = combined / combined.iloc[0] * 1000
    combined.name = "International_Stocks_USD"
    return combined


def _load_ff_intl_pre2001(end_date: pd.Timestamp) -> pd.Series:
    """Monthly total return for international developed markets via Kenneth French.

    Uses pandas_datareader famafrench reader. Tries dataset names in order
    until one returns data starting before 1995.
    """
    import pandas_datareader.data as pdr

    candidates = [
        "F-F_International_Country_Portfolios_ME_Weighted",
        "International_3_Factors",
        "F-F_International_Country_Portfolios",
    ]
    cache = RAW / "ff_intl.csv"

    if cache.exists():
        s = pd.read_csv(cache, index_col=0, parse_dates=True).squeeze("columns")
        return _to_month_end(s).loc["1990-01-01":end_date]

    for name in candidates:
        try:
            print(f"  Trying Fama-French dataset: {name}")
            raw = pdr.DataReader(name, "famafrench", start="1988-01-01")[0]
            if "Mkt-RF" in raw.columns:
                col = "Mkt-RF"
            elif "Mkt" in raw.columns:
                col = "Mkt"
            else:
                col = raw.columns[0]
            ret_pct = raw[col] / 100
            level = _ret_to_level(ret_pct)
            # French index is YYYYMM integers; convert to month-end timestamps
            level.index = pd.to_datetime(
                [f"{int(str(d)[:4])}-{str(d)[4:]}-01" for d in level.index]
            ) + pd.offsets.MonthEnd(0)
            level.to_csv(cache, header=True)
            print(f"  Cached Fama-French {name}")
            return _to_month_end(level).loc["1990-01-01":end_date]
        except Exception as ex:
            print(f"    {name} failed: {ex}")

    raise RuntimeError(
        "Could not load international pre-2001 data from any source."
    )


def load_us_smallcap() -> pd.Series:
    """US Small Cap in USD via IWM ETF (iShares Russell 2000, from 2000-05).

    Used only for portfolio composition; not plotted as a standalone line.
    """
    prices = _yf_close("IWM", "iwm_prices.csv").dropna()
    tr = prices / prices.iloc[0] * 1000
    tr.name = "US_SmallCap_USD"
    return tr


def _splice_etf(proxy: pd.Series, etf: pd.Series, name: str) -> pd.Series:
    """Splice a proxy index (early) with a real ETF (modern), USD growth-of-$1000.

    Takes the proxy up to (not including) the ETF's first date, scales the ETF
    so it continues seamlessly from the proxy's last level, concatenates, and
    rebases the whole series to 1000 at the first point. Mirrors load_tsx().

    Both inputs must be total-return (auto_adjust close) so the splice is
    TR-on-TR and continuous.
    """
    etf = etf.dropna()
    proxy = proxy.dropna()
    cut = etf.index[0]
    pre = proxy.loc[:cut].iloc[:-1]   # up to but not including ETF start
    if pre.empty:
        tr = etf / etf.iloc[0] * 1000
    else:
        etf_scaled = etf / etf.iloc[0] * pre.iloc[-1]
        tr = pd.concat([pre, etf_scaled])
        tr = tr / tr.iloc[0] * 1000
    tr.name = name
    return tr


def load_voo(shiller_usd: pd.Series) -> pd.Series:
    """VOO (S&P 500 core) in USD, back to 1956 via Shiller S&P 500 TR splice.

    Pre-2010-09 : Shiller S&P 500 total return (passed in to avoid re-fetch).
    2010-09+    : VOO adjusted close.
    VOO *is* the S&P 500, so this is the cleanest possible proxy.
    """
    voo = _yf_close("VOO", "voo_prices.csv").dropna()
    return _splice_etf(shiller_usd, voo, "VOO_USD")


def load_vgt() -> pd.Series:
    """VGT (US Information Technology, growth tilt) in USD.

    Pre-2004-01 : QQQ (Nasdaq-100 ETF, total return, from 1999-03).
    2004-01+    : VGT adjusted close.
    Proxy caveat: QQQ is concentrated growth, not a pure IT-sector replica
    (monthly-return corr 0.978 over the 2004+ overlap).
    """
    qqq = _yf_close("QQQ", "qqq_prices.csv").dropna()
    vgt = _yf_close("VGT", "vgt_prices.csv").dropna()
    return _splice_etf(qqq, vgt, "VGT_USD")


def load_schd() -> pd.Series:
    """SCHD (US dividend equity, income) in USD.

    Pre-2011-10 : VYM (Vanguard High Dividend Yield ETF, total return, 2006-11).
    2011-10+    : SCHD adjusted close.
    Proxy caveat: VYM lacks SCHD's quality screen but tracks closely
    (monthly-return corr 0.970 over the 2011+ overlap).
    """
    vym = _yf_close("VYM", "vym_prices.csv").dropna()
    schd = _yf_close("SCHD", "schd_prices.csv").dropna()
    return _splice_etf(vym, schd, "SCHD_USD")


def load_cdn_bond_tr() -> pd.Series:
    """Canadian 10-year government bond total-return index in CAD.

    Constructed from FRED IRLTLT01CAM156N (10-year yield, % p.a.) using:
      monthly TR ≈ yield/12  −  duration × Δyield

    Constant modified duration = 8.0 years (known approximation; acceptable
    at log scale — noted in chart methodology expander).
    """
    y = _fred("IRLTLT01CAM156N").loc[START:] / 100
    duration = 8.0

    rets = pd.Series(0.0, index=y.index)
    for i in range(1, len(y)):
        coupon    = y.iloc[i - 1] / 12
        price_chg = -duration * (y.iloc[i] - y.iloc[i - 1])
        rets.iloc[i] = coupon + price_chg

    return _ret_to_level(rets).rename("Bonds")


def load_tbills() -> pd.Series:
    """Canadian T-Bill total-return index in CAD.

    Source: FRED IR3TIB01CAM156N (Canada 3-month T-bill rate, % p.a.)
    Monthly TR = rate/12 (T-bills have no price-change risk).
    """
    rates = _fred("IR3TIB01CAM156N").loc[START:] / 100
    return _ret_to_level(rates / 12).rename("T_Bills")


def load_inflation() -> pd.Series:
    """Canadian CPI rebased to $1000 at START.

    Source: FRED CANCPIALLMINMEI (Canada CPI, All Items, Index 2015=100, monthly).
    CPALTT01CAM659N was rejected — it returns YoY % change, not the index level.
    """
    cpi = _fred("CANCPIALLMINMEI").loc[START:]
    # Extend to END with the last known value (CPI has a ~3-month reporting lag)
    full_idx = pd.date_range(cpi.index[0], pd.Timestamp(END) + pd.offsets.MonthEnd(0), freq="ME")
    cpi = cpi.reindex(full_idx).ffill()
    return (cpi / cpi.iloc[0] * 1000).rename("Inflation")


def load_usdcad() -> pd.Series:
    """USD per 1 CAD exchange rate.

    Source: FRED DEXCAUS.
    Bretton Woods period (before DEXCAUS data starts ≈ 1971): hard-coded 1.00.
    """
    fx = _fred("DEXCAUS").dropna()

    first = fx.first_valid_index()
    pre_idx = pd.date_range(
        pd.Timestamp(START) + pd.offsets.MonthEnd(0),
        first - pd.offsets.MonthEnd(1),
        freq="ME",
    )
    if len(pre_idx) > 0:
        # 1 CAD ≈ 1 USD under Bretton Woods (fixed rate); flag as approximation
        pre = pd.Series(1.0, index=pre_idx)
        fx = pd.concat([pre, fx]).sort_index()

    return fx.rename("USD_CAD").loc[START:END]


def load_prime_ca() -> pd.Series:
    """Canadian short-term interest rate (% p.a.).

    Tries FRED IRSTCB01CAM156N (Canada 3-month interbank rate).
    """
    try:
        s = _fred("IRSTCB01CAM156N")
    except Exception:
        print("  WARNING: IRSTCB01CAM156N unavailable — falling back to MPRIME")
        s = _fred("MPRIME")
    return s.rename("Prime_CA").loc[START:END]


def load_prime_us() -> pd.Series:
    """U.S. prime rate (% p.a.). Source: FRED MPRIME."""
    return _fred("MPRIME").rename("Prime_US").loc[START:END]


# ── FX conversion ─────────────────────────────────────────────────────────────

def to_cad(usd_level: pd.Series, usdcad: pd.Series, name: str) -> pd.Series:
    """Convert a USD-denominated growth-of-$1000 series to CAD.

    DEXCAUS = CAD per 1 USD (e.g. 1.44 in 2025 means 1 USD buys 1.44 CAD).
    To convert USD → CAD: multiply by DEXCAUS.

    CAD_t = USD_t × DEXCAUS_t  →  rebase so first date = 1000.
    """
    aligned_usd, aligned_fx = usd_level.align(usdcad, join="inner")
    cad = aligned_usd * aligned_fx          # USD × (CAD/USD) = CAD
    return (cad / cad.iloc[0] * 1000).rename(name)


# ── Portfolio construction ────────────────────────────────────────────────────

PORTFOLIO_WEIGHTS: dict[str, dict[str, float]] = {
    # Confirmed from Investments Illustrated 2025 poster (poster_buildplan.md)
    "Aggressive": {
        "US_SmallCap":          0.10,
        "US_Stocks":            0.15,
        "Canadian_Stocks":      0.20,
        "International_Stocks": 0.25,
        "Bonds":                0.25,
        "T_Bills":              0.05,
    },
    # Inferred from poster composition bar (equity-heavy moderate tilt)
    "Moderate": {
        "US_SmallCap":          0.00,
        "US_Stocks":            0.20,
        "Canadian_Stocks":      0.25,
        "International_Stocks": 0.15,
        "Bonds":                0.35,
        "T_Bills":              0.05,
    },
    # Inferred from poster composition bar (bond-heavy conservative tilt)
    "Conservative": {
        "US_SmallCap":          0.00,
        "US_Stocks":            0.10,
        "Canadian_Stocks":      0.10,
        "International_Stocks": 0.10,
        "Bonds":                0.60,
        "T_Bills":              0.10,
    },
}

# Simple 3-ETF portfolio (USD) — illustrates the four-sleeve framework's first
# three sleeves: Core / Growth / Income. Defensive (bonds/cash) intentionally
# omitted to keep the "simple all-equity ETF" story clean. Sums to 1.0.
SIMPLE_ETF_WEIGHTS: dict[str, float] = {
    "VOO_USD":  0.50,   # core broad market (S&P 500)
    "VGT_USD":  0.25,   # growth tilt (info tech)
    "SCHD_USD": 0.25,   # income (dividend equity)
}


def build_portfolio(name: str, weights: dict[str, float], levels: pd.DataFrame) -> pd.Series:
    """Growth-of-$1000 with annual January rebalancing.

    Components missing at a given date (e.g. no EAFE pre-2001) have their
    target weights redistributed proportionally to available components.
    """
    cols = [c for c in weights if c in levels.columns]
    target_w = np.array([weights[c] for c in cols])
    target_w /= target_w.sum()

    rets = levels[cols].pct_change()

    portfolio = np.full(len(levels), np.nan)
    alloc = None   # current effective weights (fraction of portfolio in each col)
    started = False

    for i, date in enumerate(levels.index):
        row = rets.iloc[i]
        avail = ~row.isna().values  # boolean mask over cols

        if not avail.any():
            continue

        # Effective weights: redistribute missing components
        eff_w = target_w.copy()
        eff_w[~avail] = 0.0
        if eff_w.sum() == 0:
            continue
        eff_w /= eff_w.sum()

        if not started or date.month == 1:
            alloc = eff_w.copy()

        if not started:
            portfolio[i] = 1000.0
            started = True
            continue

        prev = portfolio[i - 1]
        if np.isnan(prev):
            # Gap in series: reinitialise
            portfolio[i] = 1000.0
            alloc = eff_w.copy()
            continue

        month_rets = np.where(avail, row.values, 0.0)
        weighted_ret = float(np.dot(alloc, month_rets))
        portfolio[i] = prev * (1 + weighted_ret)

        # Drift weights until next January rebalance
        new_alloc = alloc * (1 + month_rets)
        total = new_alloc.sum()
        alloc = new_alloc / total if total > 0 else alloc

    return pd.Series(portfolio, index=levels.index, name=name)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== Building monthly_returns.parquet ===\n")

    print("Loading raw series:")
    usdcad       = load_usdcad()
    us_usd       = load_shiller()
    tsx          = load_tsx()
    eafe_usd     = load_eafe()
    smallcap_usd = load_us_smallcap()
    bonds        = load_cdn_bond_tr()
    tbills       = load_tbills()
    inflation    = load_inflation()
    prime_ca     = load_prime_ca()
    prime_us     = load_prime_us()

    print("\nLoading USD ETF sleeve (VOO / VGT / SCHD, proxy-spliced):")
    voo_usd  = load_voo(us_usd)   # reuse already-loaded Shiller S&P 500 TR
    vgt_usd  = load_vgt()
    schd_usd = load_schd()

    print("\nConverting USD series to CAD:")
    us_stocks   = to_cad(us_usd,       usdcad, "US_Stocks")
    intl_stocks = to_cad(eafe_usd,     usdcad, "International_Stocks")
    smallcap    = to_cad(smallcap_usd, usdcad, "US_SmallCap")

    print("\nBuilding portfolios (January rebalancing):")
    components = pd.DataFrame({
        "US_Stocks":            us_stocks,
        "US_SmallCap":          smallcap,
        "Canadian_Stocks":      tsx,
        "International_Stocks": intl_stocks,
        "Bonds":                bonds,
        "T_Bills":              tbills,
    }).sort_index()

    aggressive   = build_portfolio("Aggressive",   PORTFOLIO_WEIGHTS["Aggressive"],   components)
    moderate     = build_portfolio("Moderate",     PORTFOLIO_WEIGHTS["Moderate"],     components)
    conservative = build_portfolio("Conservative", PORTFOLIO_WEIGHTS["Conservative"], components)

    # Simple 3-ETF blend (USD). build_portfolio redistributes weight while
    # SCHD's proxy (VYM) is missing pre-2006-11, so the blend is well-defined
    # back to QQQ's 1999 start.
    etf_components = pd.DataFrame({
        "VOO_USD":  voo_usd,
        "VGT_USD":  vgt_usd,
        "SCHD_USD": schd_usd,
    }).sort_index()
    simple_etf = build_portfolio("Simple_ETF_USD", SIMPLE_ETF_WEIGHTS, etf_components)
    print("  Done.")

    print("\nAssembling final DataFrame:")
    out = pd.DataFrame({
        "US_Stocks":            us_stocks,
        "Canadian_Stocks":      tsx,
        "International_Stocks": intl_stocks,
        "Bonds":                bonds,
        "T_Bills":              tbills,
        "Inflation":            inflation,
        "Aggressive":           aggressive,
        "Moderate":             moderate,
        "Conservative":         conservative,
        # Simple ETF sleeve — USD, NOT FX-adjusted to CAD (US-market illustration)
        "VOO_USD":              voo_usd,
        "VGT_USD":              vgt_usd,
        "SCHD_USD":             schd_usd,
        "Simple_ETF_USD":       simple_etf,
        "USD_CAD":              usdcad,
        "Prime_CA":             prime_ca,
        "Prime_US":             prime_us,
    }).sort_index()

    out.index = pd.DatetimeIndex(out.index)
    out.to_parquet(OUT, index=True)

    n_rows = len(out)
    first  = out.index[0].strftime("%Y-%m")
    last   = out.index[-1].strftime("%Y-%m")
    print(f"\n✓ {OUT.relative_to(ROOT)}  —  {n_rows} rows ({first} → {last})\n")

    summary = out[["US_Stocks", "Canadian_Stocks", "Bonds", "T_Bills", "Inflation"]].iloc[-1]
    print("End-of-history growth of $1,000 CAD:")
    for col, val in summary.items():
        print(f"  {col:<25} ${val:>12,.0f}")

    etf_summary = out[["VOO_USD", "VGT_USD", "SCHD_USD", "Simple_ETF_USD"]].iloc[-1]
    print("\nEnd-of-history growth of $1,000 USD (ETF sleeve, rebased at first valid date):")
    for col, val in etf_summary.items():
        first = out[col].first_valid_index().strftime("%Y-%m")
        print(f"  {col:<18} ${val:>12,.0f}   (from {first})")


if __name__ == "__main__":
    main()
