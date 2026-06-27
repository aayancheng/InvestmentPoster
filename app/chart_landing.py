"""
Big Picture landing chart — dark, USD, 2 rows.

Row 1 (log): growth of $1,000 USD for 4 US core series, rebased at start_year,
             with inline end-of-line labels.
Row 2:       underwater drawdown strip of US Stocks (running % below all-time high).

No FX row, no macro band, no event annotations. Dark/transparent so it sits
flush on the #0a0a0a Streamlit shell.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from chart_main import _rebase

LANDING_SERIES = ["US_Stocks_USD", "US_Bonds_USD", "US_TBills_USD", "US_Inflation_USD"]

LANDING_COLOURS = {
    "US_Stocks_USD":    "#E8896B",   # warm coral
    "US_Bonds_USD":     "#5B9BD5",   # blue
    "US_TBills_USD":    "#9AA6B2",   # grey
    "US_Inflation_USD": "#C9A227",   # gold
}

LANDING_NAMES = {
    "US_Stocks_USD":    "US Stocks",
    "US_Bonds_USD":     "Bonds",
    "US_TBills_USD":    "Cash",
    "US_Inflation_USD": "Inflation",
}

_TICK_VALS = [1_000, 3_000, 10_000, 30_000, 100_000, 300_000, 1_000_000]
_TICK_TEXT = [f"${v:,.0f}" for v in _TICK_VALS]


def _compact_money(v: float) -> str:
    """1077932 -> $1.08M, 38394 -> $38k, 950 -> $950."""
    if v >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}k"
    return f"${v:,.0f}"


def build_landing_chart(df: pd.DataFrame, start_year: int = 1961) -> go.Figure:
    """Build the 2-row dark USD landing figure."""
    panel = df.loc[f"{start_year}-01-01":]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.82, 0.18], vertical_spacing=0.04,
    )

    # ── Row 1: USD growth lines ───────────────────────────────────────────────
    for col in LANDING_SERIES:
        raw = panel[col].dropna()
        if raw.empty:
            continue
        s = _rebase(raw)
        colour = LANDING_COLOURS[col]
        name = LANDING_NAMES[col]
        # Value goes in the legend label (not inline), so the plot can use the
        # full width on any screen — inline end-labels forced a wide right margin
        # that crushed the chart on mobile.
        legend_name = f"{name} · {_compact_money(s.iloc[-1])}"
        fig.add_trace(
            go.Scatter(
                x=s.index, y=s.values, name=legend_name, mode="lines",
                line=dict(color=colour, width=2.4 if col == "US_Stocks_USD" else 1.7),
                hovertemplate=f"<b>{name}</b><br>%{{x|%b %Y}}<br>$%{{y:,.0f}}<extra></extra>",
            ),
            row=1, col=1,
        )

    fig.update_yaxes(
        type="log", row=1, col=1, tickmode="array",
        tickvals=_TICK_VALS, ticktext=_TICK_TEXT,
        tickfont=dict(color="#9a9a9a", size=10), gridcolor="#1c1c1c",
    )

    # ── Row 2: underwater drawdown strip (US Stocks) ──────────────────────────
    us = panel["US_Stocks_USD"].dropna()
    dd = (us - us.cummax()) / us.cummax() * 100
    fig.add_trace(
        go.Scatter(
            x=dd.index, y=dd.values, fill="tozeroy", mode="lines",
            line=dict(color="#C0392B", width=0.8),
            fillcolor="rgba(192,57,43,0.35)", showlegend=False,
            hovertemplate="%{x|%b %Y}  Drawdown %{y:.1f}%<extra></extra>",
            name="Drawdown",
        ),
        row=2, col=1,
    )
    fig.add_hline(y=0, line_width=0.8, line_color="#333333", row=2, col=1)
    fig.update_yaxes(
        row=2, col=1, range=[max(dd.min(), -60) - 2, 4],
        tickmode="array", tickvals=[-50, -25, 0], ticktext=["-50%", "-25%", "0"],
        tickfont=dict(size=8, color="#777777"), showgrid=False, zeroline=False,
    )

    # ── Dark layout ───────────────────────────────────────────────────────────
    fig.update_xaxes(
        showgrid=True, gridcolor="#161616", tickformat="%Y", dtick="M120",
        tickfont=dict(color="#9a9a9a", size=11),
    )
    fig.update_layout(
        height=560,
        margin=dict(l=54, r=16, t=44, b=30),
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.0,
            xanchor="left", x=0,
            font=dict(color="#cfcfcf", size=11),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
