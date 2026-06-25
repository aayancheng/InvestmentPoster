"""
Big Picture — Streamlit page.

Run: streamlit run app/big_picture.py
"""

from __future__ import annotations

from pathlib import Path
from html import escape

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from analytics import compute_dashboard_metrics, classify_risk_profile
from chart_main import build_figure, COLOURS, DISPLAY_NAMES, MAIN_SERIES_ORDER
from chart_etf import build_etf_panel

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
        html, body, [data-testid="stAppViewContainer"] {
            background: #0a0a0a;
        }
        .main .block-container {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
        }
        #MainMenu { display: none !important; }
        footer { display: none !important; }
        [data-testid="stDeployButton"] { display: none !important; }
        /* Remove the top header bar entirely (contains Deploy + hamburger) */
        [data-testid="stHeader"] { display: none !important; }
        /* Reclaim the space the header bar occupied */
        [data-testid="stAppViewContainer"] { padding-top: 0 !important; }
        [data-testid="stMain"] > div:first-child { padding-top: 0 !important; }
        /* Hide the sidebar header row — only contains the collapse arrow */
        [data-testid="stSidebarHeader"] { display: none !important; }
        .stCheckbox { margin-bottom: 0 !important; }
        .stCheckbox label { font-size: 0.82rem !important; }
        [data-testid="stSidebar"] {
            background: #0d0d0d;
            border-right: 1px solid #1c1c1c;
        }
        .ip-brand {
            padding: 0.25rem 0 1.1rem 0;
            border-bottom: 1px solid #1f1f1f;
            margin-bottom: 1rem;
        }
        .ip-brand-title {
            color: #ededed;
            font-size: 0.95rem;
            font-weight: 700;
            line-height: 1.2;
        }
        .ip-brand-subtitle {
            color: #777;
            font-size: 0.72rem;
            margin-top: 0.2rem;
        }
        .ip-nav-item {
            border-left: 3px solid transparent;
            padding: 0.45rem 0.55rem;
            margin-bottom: 0.25rem;
            color: #d5d5d5;
            border-radius: 0 6px 6px 0;
            font-size: 0.82rem;
        }
        .ip-nav-item.active {
            border-left-color: #d97757;
            background: #1a1a1a;
            color: #ededed;
        }
        .ip-nav-item.disabled {
            opacity: 0.35;
            cursor: not-allowed;
        }
        .ip-nav-sub {
            display: block;
            color: #888;
            font-size: 0.64rem;
            margin-top: 0.1rem;
        }
        .ip-subtitle {
            color: #9a9a9a;
            font-size: 0.86rem;
            margin-top: -0.65rem;
            max-width: 980px;
        }
        .ip-card-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.65rem;
            margin: 1rem 0 0.75rem 0;
        }
        .ip-card {
            border: 1px solid #1c1c1c;
            background: #0f0f0f;
            border-radius: 6px;
            padding: 0.7rem 0.8rem;
            min-height: 74px;
        }
        .ip-card-value {
            color: #ededed;
            font-size: 1rem;
            font-weight: 700;
            line-height: 1.25;
        }
        .ip-card-value.red { color: #e05252; }
        .ip-card-label {
            color: #707070;
            font-size: 0.65rem;
            font-weight: 650;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-top: 0.35rem;
            line-height: 1.25;
        }
        .ip-panel {
            border: 1px solid #1c1c1c;
            background: #0f0f0f;
            border-radius: 6px;
            padding: 0.95rem 1rem;
            margin: 0.75rem 0;
        }
        .ip-panel h3 {
            color: #ededed;
            font-size: 1rem;
            margin: 0 0 0.45rem 0;
        }
        .ip-panel p {
            color: #a8a8a8;
            font-size: 0.84rem;
            line-height: 1.55;
            margin: 0.35rem 0;
        }
        .ip-result {
            border-left: 3px solid #d97757;
            background: #121212;
            border-radius: 0 6px 6px 0;
            padding: 0.7rem 0.8rem;
            margin-top: 0.5rem;
        }
        .ip-result strong { color: #ededed; }
        @media (max-width: 900px) {
            .main .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            .ip-card-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
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


def fmt_money(value: float | None) -> str:
    if value is None:
        return "&mdash;"
    return f"${value:,.0f}"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "&mdash;"
    return f"{value * 100:.1f}%"


def fmt_years(value: float | None) -> str:
    if value is None:
        return "&mdash;"
    return f"{value:.1f} years"


def metric_card(value: str, label: str, *, red: bool = False) -> str:
    value_class = "ip-card-value red" if red else "ip-card-value"
    return (
        "<div class='ip-card'>"
        f"<div class='{value_class}'>{value}</div>"
        f"<div class='ip-card-label'>{escape(label)}</div>"
        "</div>"
    )


def render_card_grid(cards: list[str]) -> None:
    st.markdown(
        "<div class='ip-card-grid'>" + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


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
    st.markdown(
        """
        <div class="ip-brand">
            <div class="ip-brand-title">Investment Portfolio</div>
            <div class="ip-brand-subtitle">Personal portfolio OS</div>
        </div>
        <div class="ip-nav-item active">The Big Picture</div>
        <div class="ip-nav-item disabled">Portfolio Analyzer<span class="ip-nav-sub">Coming soon</span></div>
        <div class="ip-nav-item disabled">Risk Profiler<span class="ip-nav-sub">Coming soon</span></div>
        <div class="ip-nav-item disabled">Trade Tickets<span class="ip-nav-sub">Coming soon</span></div>
        """,
        unsafe_allow_html=True,
    )
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

# ── Dashboard analytics ───────────────────────────────────────────────────────
dashboard = compute_dashboard_metrics(df, start_year=start_year, visible=visible)
primary = dashboard.primary
primary_nominal_end = primary.growth_multiple * 1000 if primary else None

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("## 2025 The Big Picture")
st.markdown(
    "<p class='ip-subtitle'>"
    "Hypothetical growth of $1,000 CAD reinvested &mdash; major asset classes, 1956&ndash;2025. "
    "All USD series are FX-adjusted to CAD. The analytics below translate the poster into "
    "compounding, drawdown, and risk-tolerance questions."
    "</p>",
    unsafe_allow_html=True,
)

if primary is None:
    render_card_grid(
        [
            metric_card("&mdash;", "End value"),
            metric_card("&mdash;", "CAGR"),
            metric_card("&mdash;", "Max drawdown", red=True),
            metric_card(dashboard.window_label, "Time window"),
        ]
    )
else:
    render_card_grid(
        [
            metric_card(fmt_money(primary_nominal_end), f"{primary.name} end value"),
            metric_card(fmt_pct(primary.cagr), f"CAGR - {primary.name}"),
            metric_card(fmt_pct(primary.max_drawdown), f"Max drawdown - {primary.name}", red=True),
            metric_card(dashboard.window_label, "Time window"),
        ]
    )
    render_card_grid(
        [
            metric_card(fmt_pct(primary.annualized_volatility), "Annualized volatility"),
            metric_card(fmt_pct(primary.worst_12m_return), "Worst rolling 12 months", red=True),
            metric_card(f"{primary.longest_drawdown_months} months", "Longest drawdown"),
            metric_card(fmt_years(primary.doubling_time_years), "Historical doubling time"),
        ]
    )

if primary is not None:
    st.markdown(
        f"""
        <div class="ip-panel">
            <h3>Long-term investing lens</h3>
            <p>
                Since {start_year}, the strongest visible investable series is
                <strong>{escape(primary.name)}</strong>. A $1,000 starting value became
                <strong>{fmt_money(primary_nominal_end)}</strong> nominally, or about
                <strong>{fmt_money(dashboard.inflation_adjusted_primary_end)}</strong>
                after Canadian inflation.
            </p>
            <p>
                The tradeoff is behavioral: the same path included a maximum drawdown of
                <strong>{fmt_pct(primary.max_drawdown)}</strong> and a worst rolling 12-month return of
                <strong>{fmt_pct(primary.worst_12m_return)}</strong>. The point is not to predict the
                future; it is to decide whether the user can stay with a rule through periods like that.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.expander("Risk tolerance check", expanded=False):
    st.caption(
        "This does not recommend a portfolio. It converts self-reported behavior and capacity "
        "into a profile to compare against historical drawdowns."
    )
    col_a, col_b, col_c, col_d = st.columns([1, 1, 1.25, 1.25])
    with col_a:
        horizon_years = st.number_input("Horizon", min_value=1, max_value=50, value=20, step=1)
    with col_b:
        stated_risk = st.slider("Stated risk", 1, 10, 6)
    with col_c:
        drawdown_label = st.selectbox(
            "In a 30% decline",
            [
                "I would sell or reduce risk",
                "I would do nothing",
                "I would rebalance back to target",
                "I would buy more",
            ],
            index=1,
        )
    with col_d:
        income_label = st.selectbox(
            "Income stability",
            ["Stable", "Variable", "Unstable"],
            index=0,
        )

    drawdown_map = {
        "I would sell or reduce risk": "sell",
        "I would do nothing": "do_nothing",
        "I would rebalance back to target": "rebalance",
        "I would buy more": "buy_more",
    }
    income_map = {"Stable": "stable", "Variable": "variable", "Unstable": "unstable"}
    profile = classify_risk_profile(
        horizon_years=int(horizon_years),
        stated_risk_score=int(stated_risk),
        drawdown_response=drawdown_map[drawdown_label],
        income_stability=income_map[income_label],
    )
    st.markdown(
        f"""
        <div class="ip-result">
            <strong>{escape(profile.category)} risk profile</strong><br>
            Composite score: {profile.composite_score}/10. {escape(profile.explanation)}
        </div>
        """,
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
        Dividends are reinvested where available. Portfolios rebalance each January.

        **Analytics** — risk metrics are derived from month-to-month changes in the
        growth-index level series. CAGR, volatility, drawdown, worst 12-month return,
        and doubling time are descriptive history, not forecasts.

        **Bond total return** — constructed from FRED 10Y Canadian government bond yields
        using constant modified duration = 8 years. Ignores convexity; acceptable at log scale.

        **Inflation** — Canadian CPI (FRED CANCPIALLMINMEI, 2015 = 100), rebased to $1,000.

        **Portfolio compositions:**
        - *Aggressive*: 10% US SC / 15% US / 20% CDN / 25% Intl / 25% Bonds / 5% Cash
        - *Moderate*: 20% US / 25% CDN / 15% Intl / 35% Bonds / 5% Cash
        - *Conservative*: 10% US / 10% CDN / 10% Intl / 60% Bonds / 10% Cash

        **Known data gaps and approximations:**
        Canadian Stocks start in 1979; pre-XIU history uses ^GSPTSE plus a 3% dividend-yield
        approximation, then XIU.TO adjusted close from 1999 onward.
        International Stocks extend to 1990 where free data is available, with EFA used from 2001.
        Bretton Woods era 1956-1970: USD/CAD hard-coded to 1.00.
        """
    )

# ── The power of a simple ETF portfolio (USD) ──────────────────────────────────
st.markdown("## The power of a simple ETF portfolio")
st.markdown(
    "<p class='ip-subtitle'>"
    "Growth of $1,000 <strong>USD</strong> &mdash; three broadly-held ETFs versus a blended "
    "50/25/25 simple portfolio (Core / Growth / Income). Each ETF is backfilled with a close "
    "proxy index so the lines reach back before its inception. Shown in USD, not CAD, because "
    "this is a US-market illustration."
    "</p>",
    unsafe_allow_html=True,
)

etf_fig = build_etf_panel(df, start_date="2006-11-30")
st.plotly_chart(etf_fig, use_container_width=True)

with st.expander("ETF panel — methodology & proxies"):
    st.markdown(
        """
        **Currency** — this panel is in **USD** (the rest of the poster is CAD). The three
        ETFs illustrate the first three sleeves of the portfolio framework: Core (VOO),
        Growth (VGT), Income (SCHD). The blend is 50% VOO / 25% VGT / 25% SCHD, rebalanced
        each January.

        **Proxy backfill** — each ETF is spliced onto a close proxy index (total return) to
        extend its history before inception:
        - **VOO** (S&P 500, inception 2010) &larr; Shiller S&P 500 total return, back to 1956.
          VOO *is* the S&P 500 — the cleanest possible proxy.
        - **VGT** (Info Tech, inception 2004) &larr; **QQQ** (Nasdaq-100) back to 1999.
          Monthly-return correlation 0.98. *Caveat:* QQQ is concentrated growth, not a pure
          IT-sector replica, so the 1999&ndash;2004 segment reads as "growth," not "tech sector."
        - **SCHD** (Dividend, inception 2011) &larr; **VYM** (high-dividend yield) back to 2006.
          Correlation 0.97. *Caveat:* VYM lacks SCHD's quality screen — pre-2011 is "a dividend
          strategy," not SCHD specifically.

        **2008 caveat** — the global financial crisis sits inside the proxy window, so the
        blend's pre-2011 drawdown is driven by proxies rather than the real ETFs. Fine for
        illustration; not a literal backtest of these tickers.
        """
    )
