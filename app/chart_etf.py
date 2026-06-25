"""
Build the "Power of a Simple ETF Portfolio" comparison panel.

A single-row, log-scale, growth-of-$1,000 **USD** chart (not CAD — these
illustrate the US broad market directly). Four lines:

    Simple 3-ETF Portfolio   50% VOO / 25% VGT / 25% SCHD, Jan-rebalanced
    VOO  — S&P 500 (Core)        backfilled with Shiller S&P 500 TR to 1956
    VGT  — Info Tech (Growth)    backfilled with QQQ to 1999
    SCHD — Dividend (Income)     backfilled with VYM to 2006

The blend is computed at parquet-build time (scripts/build_history.py); this
module is a pure view. Rebase logic and CAGR are reused from chart_main.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from chart_main import _rebase, _annualised_return

# Display order: blend first so it draws underneath, then the three sleeves.
ETF_SERIES_ORDER = [
    "Simple_ETF_USD",
    "VOO_USD",
    "VGT_USD",
    "SCHD_USD",
]

ETF_COLOURS = {
    "Simple_ETF_USD": "#111111",   # near-black — the headline line
    "VOO_USD":        "#2E86C1",   # blue   — core
    "VGT_USD":        "#E67E22",   # orange — growth
    "SCHD_USD":       "#27AE60",   # green  — income
}

ETF_DISPLAY_NAMES = {
    "Simple_ETF_USD": "Simple 3-ETF Portfolio",
    "VOO_USD":        "VOO — S&P 500 (Core)",
    "VGT_USD":        "VGT — Info Tech (Growth)",
    "SCHD_USD":       "SCHD — Dividend (Income)",
}

# Width emphasis: the blend is the story, draw it heavier.
_LINE_WIDTH = {"Simple_ETF_USD": 3.0}

# Log-scale tick list (same idiom as chart_main): $ on every label.
_TICK_VALS = [500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000]
_TICK_TEXT = [f"${v:,.0f}" for v in _TICK_VALS]


def build_etf_panel(df: pd.DataFrame, start_date: str = "2006-11-30") -> go.Figure:
    """
    Build the single-panel USD ETF comparison figure.

    Parameters
    ----------
    df         : the monthly_returns DataFrame (must contain the *_USD columns)
    start_date : rebase every series to $1,000 on the first available date at
                 or after this date (default 2006-11, when all three proxy
                 families — Shiller, QQQ, VYM — are live).
    """
    panel = df.loc[start_date:]

    fig = go.Figure()

    for col in ETF_SERIES_ORDER:
        if col not in panel.columns:
            continue
        raw = panel[col].dropna()
        if raw.empty:
            continue

        s = _rebase(raw)
        cagr = _annualised_return(s)
        end_val = s.iloc[-1]
        label = f"  ${end_val:,.0f}  {cagr*100:.1f}%p.a."
        colour = ETF_COLOURS.get(col, "#555555")

        fig.add_trace(
            go.Scatter(
                x=s.index,
                y=s.values,
                name=ETF_DISPLAY_NAMES.get(col, col),
                mode="lines+text",
                line=dict(color=colour, width=_LINE_WIDTH.get(col, 1.6)),
                text=[""] * (len(s) - 1) + [label],
                textposition="middle right",
                textfont=dict(size=8, color=colour),
                hovertemplate=(
                    f"<b>{ETF_DISPLAY_NAMES.get(col, col)}</b><br>"
                    "%{x|%b %Y}<br>"
                    "$%{y:,.0f}<extra></extra>"
                ),
            )
        )

    fig.update_yaxes(
        type="log",
        tickmode="array",
        tickvals=_TICK_VALS,
        ticktext=_TICK_TEXT,
        tickfont=dict(color="#111111", size=10),
        gridcolor="#E0E0E0",
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#E0E0E0",
        tickformat="%Y",
        dtick="M24",
        tickfont=dict(color="#111111", size=11),
    )
    fig.update_layout(
        height=460,
        margin=dict(l=60, r=180, t=20, b=40),
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.0,
            xanchor="left", x=0.0,
            font=dict(size=10, color="#111111"),
        ),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
    )

    return fig
