"""
Big Picture — Streamlit page (v0.3, dark USD redesign).

Landing: full-width dark USD growth chart of 4 US core series + drawdown strip,
a slim stat strip, and a plain-language headline. Scroll down to an actionable
ETF portfolio (50/25/25 VOO/VGT/SCHD donut + growth comparison).

Run: streamlit run app/big_picture.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from analytics import calculate_series_metrics
from chart_landing import build_landing_chart
from chart_etf import build_etf_panel, build_allocation_donut

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="2025 The Big Picture",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        html, body, [data-testid="stAppViewContainer"] { background: #0a0a0a; }
        .main .block-container {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-top: 1.2rem !important;
            padding-bottom: 1rem !important;
        }
        #MainMenu { display: none !important; }
        footer { display: none !important; }
        [data-testid="stDeployButton"] { display: none !important; }
        [data-testid="stHeader"] { display: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stAppViewContainer"] { padding-top: 0 !important; }
        [data-testid="stMain"] > div:first-child { padding-top: 0 !important; }

        h2 { color: #ededed; }
        /* slim stat strip (replaces KPI cards) */
        .ip-strip { display: flex; gap: 2.2rem; margin: 0.3rem 0 0.2rem; }
        .ip-strip .v { font-size: 1.15rem; font-weight: 700; color: #fff; line-height: 1.1; }
        .ip-strip .v.red { color: #e0685f; }
        .ip-strip .l { font-size: 0.62rem; letter-spacing: 0.05em; text-transform: uppercase;
                       color: #777; margin-top: 2px; }
        .ip-headline { font-size: 0.9rem; color: #cfcfcf; line-height: 1.55; margin-top: 0.4rem; }
        .ip-headline b { color: #fff; }
        .ip-headline .pos { color: #5fb98c; } .ip-headline .neg { color: #e0685f; }
        .ip-cue { text-align: center; color: #555; font-size: 0.72rem; margin: 0.6rem 0 1.4rem; }
        .ip-section-title { font-size: 1.3rem; font-weight: 700; color: #ededed; margin-top: 0.4rem; }
        .ip-sub { font-size: 0.8rem; color: #7a7a7a; margin-top: 0.2rem; margin-bottom: 0.4rem; }
        .ip-legend { font-size: 0.82rem; color: #cfcfcf; line-height: 1.85; margin-top: 0.4rem; }
        hr { border-color: #1c1c1c; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Data ──────────────────────────────────────────────────────────────────────
PARQUET = Path(__file__).parent.parent / "data" / "monthly_returns.parquet"


@st.cache_data
def load_data() -> pd.DataFrame:
    if not PARQUET.exists():
        st.error(
            "data/monthly_returns.parquet not found. "
            "Run `python scripts/build_history.py` first."
        )
        st.stop()
    return pd.read_parquet(PARQUET)


df = load_data()

# ── Landing: title, stat strip + slider, chart, headline ──────────────────────
st.markdown("## 2025 The Big Picture")

strip_col, slider_col = st.columns([3, 1])
with slider_col:
    start_year = st.slider("Start year", 1956, 2010, 1961, 1)

# Metrics over the selected window, so the strip/headline match the chart.
window = df.loc[f"{start_year}-01-01":]
m = calculate_series_metrics(window["US_Stocks_USD"].dropna(), key="US_Stocks_USD")
cpi = window["US_Inflation_USD"].dropna()
real_mult = m.growth_multiple / (cpi.iloc[-1] / cpi.iloc[0])

rebased_end = m.growth_multiple * 1000   # $1,000 → this, matches the chart's rebase

with strip_col:
    dbl = f"{m.doubling_time_years:.1f} yrs" if m.doubling_time_years else "—"
    st.markdown(
        "<div class='ip-strip'>"
        f"<div><div class='v'>${rebased_end:,.0f}</div><div class='l'>End value</div></div>"
        f"<div><div class='v'>{m.cagr*100:.1f}%</div><div class='l'>Per year</div></div>"
        f"<div><div class='v red'>{m.max_drawdown*100:.1f}%</div><div class='l'>Worst drop</div></div>"
        f"<div><div class='v'>{dbl}</div><div class='l'>To double</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

fig = build_landing_chart(df, start_year=start_year)
st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "<div class='ip-headline'>"
    f"<b>$1,000 → ${rebased_end:,.0f}</b> in US stocks since {start_year} — about "
    f"<b class='pos'>{m.cagr*100:.0f}% a year</b>, but you'd have ridden a "
    f"<b class='neg'>{m.max_drawdown*100:.0f}% drop</b> along the way "
    f"(${real_mult*1000:,.0f} after inflation)."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown("<div class='ip-cue'>↓ scroll for an actionable ETF portfolio</div>", unsafe_allow_html=True)

# ── Actionable ETF portfolio ──────────────────────────────────────────────────
st.markdown(
    "<div class='ip-section-title'>The power of a simple ETF portfolio</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='ip-sub'>Three broadly-held ETFs in a 50/25/25 mix — Core, Growth, Income. "
    "Growth of $1,000 USD, rebased 2006.</div>",
    unsafe_allow_html=True,
)

mix_col, growth_col = st.columns([1, 2])
with mix_col:
    st.plotly_chart(build_allocation_donut(), use_container_width=True)
    st.markdown(
        "<div class='ip-legend'>"
        "<b style='color:#2E86C1;'>VOO</b> &nbsp;S&P 500 · Core · <b>50%</b><br>"
        "<b style='color:#E67E22;'>VGT</b> &nbsp;Info Tech · Growth · <b>25%</b><br>"
        "<b style='color:#27AE60;'>SCHD</b> &nbsp;Dividend · Income · <b>25%</b>"
        "</div>",
        unsafe_allow_html=True,
    )
with growth_col:
    st.plotly_chart(build_etf_panel(df), use_container_width=True)

st.markdown(
    "<div class='ip-headline'>The <b>blend</b> beats holding VOO alone — the growth tilt lifts "
    "returns while income and core soften the ride.</div>",
    unsafe_allow_html=True,
)

# ── Methodology ───────────────────────────────────────────────────────────────
with st.expander("Methodology & data"):
    st.markdown(
        """
        **Currency** — this view is in **USD**. Each series is growth of $1,000, total return
        where available, rebased to the selected start year.

        **US core series (FRED):** US Stocks = S&P 500 total return (Shiller, spliced to SPY);
        Bonds = 10-year Treasury (GS10) constructed total return, constant 8-year duration;
        Cash = 3-month T-bill (TB3MS); Inflation = US CPI (CPIAUCSL).

        **ETF panel** — VOO / VGT / SCHD, proxy-backfilled to extend history: VOO←S&P 500 (1956),
        VGT←QQQ (1999), SCHD←VYM (2006). Proxies track closely but are not identical indices.

        **Drawdown strip** — running percentage below the prior all-time high for US Stocks.
        Not financial advice.
        """
    )
