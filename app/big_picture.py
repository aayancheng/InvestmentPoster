"""
Big Picture — Streamlit page.

Run: streamlit run app/big_picture.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from chart_main import build_figure, COLOURS, DISPLAY_NAMES, MAIN_SERIES_ORDER

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="2025 The Big Picture",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Clear Streamlit's cached sidebar state from localStorage so initial_sidebar_state="expanded"
# always wins, even when a prior session left the sidebar collapsed.
components.html(
    "<script>"
    "const k = Object.keys(window.parent.localStorage)"
    "    .find(k => k.toLowerCase().includes('sidebar'));"
    "if (k) window.parent.localStorage.removeItem(k);"
    "</script>",
    height=0,
)

st.markdown(
    """
    <style>
        .main .block-container {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
        }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        /* Remove the top header bar entirely (contains Deploy + hamburger) */
        [data-testid="stHeader"] { display: none !important; }
        /* Reclaim the space the header bar occupied */
        [data-testid="stAppViewContainer"] { padding-top: 0 !important; }
        [data-testid="stMain"] > div:first-child { padding-top: 0 !important; }
        /* Hide the sidebar header row — only contains the collapse arrow */
        [data-testid="stSidebarHeader"] { display: none !important; }
        .stCheckbox { margin-bottom: 0 !important; }
        .stCheckbox label { font-size: 0.82rem !important; }
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

# ── Initialise checkbox session state once ────────────────────────────────────
for _key in MAIN_SERIES_ORDER:
    if f"cb_{_key}" not in st.session_state:
        st.session_state[f"cb_{_key}"] = True

# ── Sidebar ───────────────────────────────────────────────────────────────────
SHORT_NAMES = {
    "US_Stocks":            "U.S. Stocks",
    "Aggressive":           "Aggressive",
    "Canadian_Stocks":      "Canada",
    "Moderate":             "Moderate",
    "International_Stocks": "International",
    "Conservative":         "Conservative",
    "Bonds":                "Bonds",
    "T_Bills":              "T-Bills",
    "Inflation":            "Inflation",
}

with st.sidebar:
    st.markdown("### Controls")
    start_year = st.slider("Start year", 1956, 2010, 1956, 1)
    st.markdown("---")
    st.markdown("**Series**")
    visible: dict[str, bool] = {}
    for key in MAIN_SERIES_ORDER:
        color = COLOURS.get(key, "#888888")
        col_cb, col_swatch = st.columns([5, 1])
        with col_cb:
            visible[key] = st.checkbox(SHORT_NAMES[key], key=f"cb_{key}")
        with col_swatch:
            st.markdown(
                f"<div style='height:3px;background:{color};border-radius:2px;"
                f"margin-top:14px;'></div>",
                unsafe_allow_html=True,
            )

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("## 2025 The Big Picture")
st.markdown(
    "<p style='font-size:0.85rem;color:#888;margin-top:-0.5rem;'>"
    "Hypothetical growth of $1,000 CAD reinvested &mdash; major asset classes, 1956&ndash;2025. "
    "All USD series FX-adjusted to CAD. "
    "Changing the start year rebases every series to $1,000 on that date."
    "</p>",
    unsafe_allow_html=True,
)

# ── Main chart ────────────────────────────────────────────────────────────────
fig = build_figure(df, start_year=start_year, visible=visible)
st.plotly_chart(fig, use_container_width=True)

# ── Methodology ───────────────────────────────────────────────────────────────
with st.expander("Methodology & data gaps"):
    st.markdown(
        """
        **Growth index** — each series is rebased to $1,000 at the selected start year.
        Dividends are reinvested (where available). Portfolios rebalanced each January.

        **Bond total return** — constructed from FRED 10Y Canadian government bond yields
        using constant modified duration = 8 years. Ignores convexity; acceptable at log scale.

        **Inflation** — Canadian CPI (FRED CANCPIALLMINMEI, 2015 = 100).

        **Portfolio compositions:**
        - *Aggressive*: 10% US SC / 15% US / 20% CDN / 25% Intl / 25% Bonds / 5% Cash
        - *Moderate*: 20% US / 25% CDN / 15% Intl / 35% Bonds / 5% Cash *(approx)*
        - *Conservative*: 10% US / 10% CDN / 10% Intl / 60% Bonds / 10% Cash *(approx)*

        **Known data gaps:**
        Canadian Stocks from 1979 (^GSPTSE, price-only — dividends not included, CAGR understated).
        International Stocks from 2001 (EFA ETF).
        Bretton Woods era 1956–1970: USD/CAD hard-coded to 1.00.
        """
    )
