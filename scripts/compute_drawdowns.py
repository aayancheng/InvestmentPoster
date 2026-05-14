#!/usr/bin/env python3
"""
Compute drawdown episodes from the growth-of-$1000 series.

Outputs data/drawdowns.json:
  [
    {
      "peak_date": "1973-01-31",
      "trough_date": "1974-09-30",
      "recovery_date": "1976-06-30",   # null if not recovered by END
      "depth_pct": -48.2,              # negative, e.g. -48.2 = 48.2% loss
      "duration_months": 65            # peak to recovery (or peak to END if unrecovered)
    },
    ...
  ]

Run: python scripts/compute_drawdowns.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT    = Path(__file__).resolve().parent.parent
PARQUET = ROOT / "data" / "monthly_returns.parquet"
OUT     = ROOT / "data" / "drawdowns.json"

THRESHOLD = -0.15   # episodes with trough < -15% from peak are recorded


def find_drawdowns(series: pd.Series, threshold: float = THRESHOLD) -> list[dict]:
    """
    Identify discrete drawdown episodes using a peak-tracking algorithm.

    Algorithm:
      1. Walk the series left to right tracking the running maximum (peak).
      2. When the current value drops > |threshold| below the peak, an episode begins.
      3. The episode ends when the series recovers back to the peak level.
      4. Record: peak_date, trough_date (lowest point), recovery_date, depth_pct.
    """
    s = series.dropna()
    episodes = []

    in_drawdown = False
    peak_val = s.iloc[0]
    peak_date = s.index[0]
    trough_val = s.iloc[0]
    trough_date = s.index[0]

    for date, val in s.items():
        if not in_drawdown:
            if val > peak_val:
                peak_val = val
                peak_date = date
            drawdown_pct = (val - peak_val) / peak_val
            if drawdown_pct < threshold:
                in_drawdown = True
                trough_val = val
                trough_date = date
        else:
            # Track trough
            if val < trough_val:
                trough_val = val
                trough_date = date
            depth = (trough_val - peak_val) / peak_val

            # Recovery: back to peak
            if val >= peak_val:
                episodes.append({
                    "peak_date":     peak_date.strftime("%Y-%m-%d"),
                    "trough_date":   trough_date.strftime("%Y-%m-%d"),
                    "recovery_date": date.strftime("%Y-%m-%d"),
                    "depth_pct":     round(depth * 100, 1),
                    "duration_months": (date - peak_date).days // 30,
                })
                in_drawdown = False
                peak_val = val
                peak_date = date
                trough_val = val
                trough_date = date

    # Capture any unresolved drawdown at end of history
    if in_drawdown:
        depth = (trough_val - peak_val) / peak_val
        episodes.append({
            "peak_date":     peak_date.strftime("%Y-%m-%d"),
            "trough_date":   trough_date.strftime("%Y-%m-%d"),
            "recovery_date": None,
            "depth_pct":     round(depth * 100, 1),
            "duration_months": (s.index[-1] - peak_date).days // 30,
        })

    return episodes


def main() -> None:
    df = pd.read_parquet(PARQUET)
    episodes = find_drawdowns(df["US_Stocks"])

    print(f"Found {len(episodes)} drawdown episodes (threshold {THRESHOLD:.0%}):\n")
    for ep in episodes:
        rec = ep["recovery_date"] or "unrecovered"
        print(f"  {ep['peak_date']} → {ep['trough_date']} ({ep['depth_pct']:.1f}%) → {rec}")

    OUT.write_text(json.dumps(episodes, indent=2))
    print(f"\n✓ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
