"""
Build the four-row Big Picture Plotly figure.

Row 1 (8%  height): drawdown strip — placeholder in v0.1
Row 2 (55% height): log-scale growth-of-$1000 main panel
Row 3 (12% height): USD/CAD exchange-rate band
Row 4 (12% height): Canadian inflation + prime rate overlay

Shared x-axis across all rows.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DATA_DIR = Path(__file__).parent.parent / "data"

# ── Colour palette (approximate the poster's warm-on-dark look) ───────────────
COLOURS = {
    "US_Stocks":            "#C0392B",   # dark red
    "Aggressive":           "#E74C3C",   # bright red
    "Canadian_Stocks":      "#922B21",   # deep red
    "Moderate":             "#E59866",   # orange-tan
    "International_Stocks": "#F0B27A",   # light orange
    "Conservative":         "#AED6F1",   # light blue
    "Bonds":                "#2E86C1",   # blue
    "T_Bills":              "#85929E",   # grey
    "Inflation":            "#7D6608",   # dark gold
}

# Display order on chart (top line to bottom)
MAIN_SERIES_ORDER = [
    "US_Stocks",
    "Aggressive",
    "Canadian_Stocks",
    "Moderate",
    "International_Stocks",
    "Conservative",
    "Bonds",
    "T_Bills",
    "Inflation",
]

DISPLAY_NAMES = {
    "US_Stocks":            "U.S. Stocks",
    "Aggressive":           "Aggressive Portfolio",
    "Canadian_Stocks":      "Canadian Stocks",
    "Moderate":             "Moderate Portfolio",
    "International_Stocks": "International Stocks",
    "Conservative":         "Conservative Portfolio",
    "Bonds":                "Bonds",
    "T_Bills":              "T-Bills",
    "Inflation":            "Inflation",
}


def _annualised_return(s: pd.Series) -> float:
    """CAGR from first non-NaN to last non-NaN value."""
    clean = s.dropna()
    if len(clean) < 2:
        return float("nan")
    years = (clean.index[-1] - clean.index[0]).days / 365.25
    return (clean.iloc[-1] / clean.iloc[0]) ** (1 / years) - 1


def _rebase(s: pd.Series, base: float | None = None) -> pd.Series:
    """Rebase series so its first non-NaN value equals base (default 1000)."""
    if base is None:
        base = 1000.0
    clean = s.dropna()
    if clean.empty:
        return s
    return s / clean.iloc[0] * base


def build_figure(
    df: pd.DataFrame,
    start_year: int = 1956,
    visible: dict[str, bool] | None = None,
) -> go.Figure:
    """
    Build the four-row Big Picture figure.

    Parameters
    ----------
    df         : output of build_history.py — monthly_returns.parquet
    start_year : rebase every series to $1,000 on the first available date
                 at or after this year
    visible    : dict of series key → bool; omit to show all
    """
    if visible is None:
        visible = {k: True for k in MAIN_SERIES_ORDER}

    df = df.loc[f"{start_year}-01-01":]

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.08, 0.55, 0.12, 0.13],
        vertical_spacing=0.02,
    )

    # ── Row 1: underwater drawdown area chart (US Stocks, running from ATH) ──────
    us = df["US_Stocks"].dropna()
    dd_pct = (us - us.cummax()) / us.cummax() * 100   # 0 at ATH, negative in drawdown

    # Hover text: show depth at each point; suppress tooltip when not in drawdown
    hover = dd_pct.apply(
        lambda v: f"Drawdown: {v:.1f}%" if v < -0.5 else "At all-time high"
    )

    fig.add_trace(
        go.Scatter(
            x=dd_pct.index,
            y=dd_pct.values,
            fill="tozeroy",
            mode="lines",
            line=dict(color="#C0392B", width=0.8),
            fillcolor="rgba(192,57,43,0.35)",
            showlegend=False,
            hovertemplate="%{x|%b %Y}  %{customdata}<extra></extra>",
            customdata=hover.values,
        ),
        row=1, col=1,
    )
    # Zero line = "at all-time high"
    fig.add_hline(y=0, line_width=0.8, line_color="#CCCCCC", row=1, col=1)

    # Y-axis: fixed range so the worst episode (~-50%) always fits
    worst = max(dd_pct.min(), -55)
    fig.update_yaxes(
        row=1, col=1,
        range=[worst - 2, 4],
        tickmode="array",
        tickvals=[-50, -40, -30, -20, -10, 0],
        ticktext=["-50%", "-40%", "-30%", "-20%", "-10%", "0"],
        tickfont=dict(size=7, color="#888888"),
        showgrid=False,
        zeroline=False,
    )

    # ── Row 2: main log-scale panel ───────────────────────────────────────────
    for col in MAIN_SERIES_ORDER:
        if col not in df.columns:
            continue
        if not visible.get(col, True):
            continue
        raw = df[col].dropna()
        if raw.empty:
            continue

        s = _rebase(raw)
        cagr = _annualised_return(s)
        end_val = s.iloc[-1]
        label = f"  ${end_val:,.0f}  {cagr*100:.1f}%p.a."

        fig.add_trace(
            go.Scatter(
                x=s.index,
                y=s.values,
                name=DISPLAY_NAMES[col],
                mode="lines+text",
                line=dict(color=COLOURS.get(col, "#555555"), width=1.5),
                text=[""] * (len(s) - 1) + [label],
                textposition="middle right",
                textfont=dict(size=7.5, color=COLOURS.get(col, "#555555")),
                showlegend=True,
                legendgroup=col,
                hovertemplate=(
                    f"<b>{DISPLAY_NAMES[col]}</b><br>"
                    "%{x|%b %Y}<br>"
                    "$%{y:,.0f}<extra></extra>"
                ),
            ),
            row=2, col=1,
        )

    # tickmode="array" with explicit values guarantees $ on every label
    _tick_vals = [500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000,
                  100_000, 200_000, 500_000, 1_000_000, 2_000_000]
    _tick_text = [f"${v:,.0f}" for v in _tick_vals]
    fig.update_yaxes(
        type="log", row=2, col=1,
        tickmode="array",
        tickvals=_tick_vals,
        ticktext=_tick_text,
        tickfont=dict(color="#111111", size=10),
        gridcolor="#E0E0E0",
    )

    # ── Row 3: Exchange rate — USD per CAD (poster convention: 1/DEXCAUS) ────
    # DEXCAUS = CAD/USD; poster shows USD/CAD (how many USD buys 1 CAD)
    fx_raw = df["USD_CAD"].dropna()
    fx = (1 / fx_raw).rename("USD_per_CAD")
    fig.add_trace(
        go.Scatter(
            x=fx.index, y=fx.values,
            name="USD per CAD",
            fill="tozeroy",
            line=dict(color="#1A5276", width=1),
            fillcolor="rgba(26,82,118,0.3)",
            hovertemplate="USD per CAD: %{y:.4f}<extra></extra>",
        ),
        row=3, col=1,
    )
    fig.update_yaxes(
        title_text="USD/CAD",
        title_font=dict(size=9, color="#111111"),
        tickfont=dict(color="#111111", size=9),
        row=3, col=1,
    )

    # ── Row 4: Inflation (YoY %) + Prime rate ─────────────────────────────────
    # Use year-over-year % to match poster's smooth curve (not noisy MoM)
    cpi_pct = df["Inflation"].pct_change(12) * 100   # 12-month trailing %
    prime_ca = df["Prime_CA"].dropna()

    fig.add_trace(
        go.Scatter(
            x=cpi_pct.dropna().index,
            y=cpi_pct.dropna().values,
            name="Inflation (Canada, ann.)",
            fill="tozeroy",
            line=dict(color="#7D6608", width=1),
            fillcolor="rgba(125,102,8,0.2)",
            hovertemplate="Inflation (YoY): %{y:.1f}%<extra></extra>",
        ),
        row=4, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=prime_ca.index,
            y=prime_ca.values,
            name="Prime Rate (Canada)",
            line=dict(color="#6C3483", width=1.2),
            hovertemplate="Prime Rate: %{y:.2f}%<extra></extra>",
        ),
        row=4, col=1,
    )
    fig.update_yaxes(
        title_text="% p.a.",
        title_font=dict(size=9, color="#111111"),
        tickfont=dict(color="#111111", size=9),
        row=4, col=1,
    )

    # ── Global layout ─────────────────────────────────────────────────────────
    fig.update_layout(
        height=860,
        margin=dict(l=60, r=210, t=20, b=40),
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            x=1.01,
            y=0.98,
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor="#CCCCCC",
            borderwidth=1,
            font=dict(size=10, color="#111111"),
            tracegroupgap=2,
        ),
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="#FFFFFF",
    )

    # Shared x-axis ticks at decade boundaries
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#E0E0E0",
        tickformat="%Y",
        dtick="M120",
        tickfont=dict(color="#111111", size=11),
    )

    # ── Event annotations (row 2) ─────────────────────────────────────────────
    from annotations import add_event_annotations
    add_event_annotations(fig, df, DATA_DIR / "events.json")

    return fig
