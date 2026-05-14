"""
Event annotation helpers for the Big Picture chart.

Strategy
--------
Text labels for 67 events crammed into one strip are unreadable.
Instead we draw subtle vertical tick marks (Plotly shapes, anchored to
row 2's paper-coordinate band) and an invisible Scatter trace that gives
hover support. Hovering anywhere near an event tick shows the label.

Row 2 paper-y bounds (computed from row_heights=[0.08,0.55,0.12,0.13],
vertical_spacing=0.02):
    y_bottom ≈ 0.307   y_top ≈ 0.8945
"""

from __future__ import annotations
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

# Paper-coordinate bounds of row 2 (main panel).
# Keep in sync with make_subplots call in chart_main.py.
_ROW2_BOTTOM = 0.307
_ROW2_TOP    = 0.8945
_TICK_HEIGHT = 0.022   # tick marks span this fraction of paper height


def add_event_annotations(
    fig: go.Figure,
    df: pd.DataFrame,
    events_path: Path,
    row: int = 2,
) -> None:
    """
    Render event markers on row 2 of the Big Picture figure.

    Visible element : a short vertical tick line at the bottom or top edge
                      of row 2, coloured by side.
    Hover element   : an invisible Scatter trace at y=1000 (the rebase
                      starting value, always in the visible range) that
                      shows the event label on hover.

    No text is rendered directly on the chart — hover is the only label.
    """
    if not events_path.exists():
        return

    events = json.loads(events_path.read_text())
    date_min = df.index.min()
    date_max = df.index.max()

    top_dates, top_texts = [], []
    bot_dates, bot_texts = [], []

    for ev in events:
        try:
            date = pd.Timestamp(ev["date"])
        except Exception:
            continue
        if date < date_min or date > date_max:
            continue
        if ev.get("side", "top") == "top":
            top_dates.append(date)
            top_texts.append(ev["text"])
        else:
            bot_dates.append(date)
            bot_texts.append(ev["text"])

    all_dates = top_dates + bot_dates
    all_texts = top_texts + bot_texts
    if not all_dates:
        return

    # ── Invisible Scatter trace for hover ────────────────────────────────────
    # y=1000 is the rebase starting value; always in the visible y-range.
    fig.add_trace(
        go.Scatter(
            x=all_dates,
            y=[1000.0] * len(all_dates),
            mode="markers",
            marker=dict(
                symbol="line-ns-open",
                size=14,
                color="rgba(0,0,0,0)",
                line=dict(color="rgba(0,0,0,0)", width=1),
            ),
            text=all_texts,
            hovertemplate="<b>%{text}</b><br>%{x|%b %Y}<extra></extra>",
            showlegend=False,
            name="",
        ),
        row=row, col=1,
    )

    # ── Visible tick marks (shapes) at bottom edge of row 2 ──────────────────
    # "top" events: tick at the TOP of the main panel
    # "bottom" events: tick at the BOTTOM of the main panel
    for date in top_dates:
        fig.add_shape(
            type="line",
            x0=date, x1=date,
            y0=_ROW2_TOP - _TICK_HEIGHT,
            y1=_ROW2_TOP,
            xref="x",
            yref="paper",
            line=dict(color="rgba(100,100,180,0.55)", width=1),
        )

    for date in bot_dates:
        fig.add_shape(
            type="line",
            x0=date, x1=date,
            y0=_ROW2_BOTTOM,
            y1=_ROW2_BOTTOM + _TICK_HEIGHT,
            xref="x",
            yref="paper",
            line=dict(color="rgba(180,100,100,0.55)", width=1),
        )
