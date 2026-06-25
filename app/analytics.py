from __future__ import annotations

from dataclasses import dataclass
from math import log

import pandas as pd


MAIN_ANALYTICS_SERIES = [
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
    "US_Stocks": "U.S. Stocks",
    "Aggressive": "Aggressive Portfolio",
    "Canadian_Stocks": "Canadian Stocks",
    "Moderate": "Moderate Portfolio",
    "International_Stocks": "International Stocks",
    "Conservative": "Conservative Portfolio",
    "Bonds": "Bonds",
    "T_Bills": "T-Bills",
    "Inflation": "Inflation",
}

RETURN_SERIES = [
    "US_Stocks",
    "Aggressive",
    "Canadian_Stocks",
    "Moderate",
    "International_Stocks",
    "Conservative",
    "Bonds",
    "T_Bills",
]


@dataclass(frozen=True)
class SeriesMetrics:
    key: str
    name: str
    start_value: float
    end_value: float
    growth_multiple: float
    cagr: float
    annualized_volatility: float
    max_drawdown: float
    longest_drawdown_months: int
    worst_12m_return: float | None
    best_12m_return: float | None
    doubling_time_years: float | None
    months: int


@dataclass(frozen=True)
class DashboardMetrics:
    series: list[SeriesMetrics]
    primary: SeriesMetrics | None
    inflation: SeriesMetrics | None
    inflation_adjusted_primary_end: float | None
    window_label: str


@dataclass(frozen=True)
class RiskProfile:
    category: str
    composite_score: int
    stated_score: int
    behavior_score: int
    capacity_score: int
    income_adjustment: int
    explanation: str


def _years_between(series: pd.Series) -> float:
    return (series.index[-1] - series.index[0]).days / 365.25


def _longest_drawdown_months(series: pd.Series) -> int:
    running_peak = series.cummax()
    underwater = series < running_peak
    longest = 0
    peak_date = series.index[0]
    in_drawdown = False

    for date, is_underwater in underwater.items():
        if not in_drawdown and is_underwater:
            peak_date = series.loc[:date].idxmax()
            in_drawdown = True
        elif in_drawdown and not is_underwater:
            longest = max(longest, _month_distance(peak_date, date))
            in_drawdown = False

    if in_drawdown:
        longest = max(longest, _month_distance(peak_date, series.index[-1]))

    return longest


def _month_distance(start: pd.Timestamp, end: pd.Timestamp) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def calculate_series_metrics(series: pd.Series, key: str | None = None) -> SeriesMetrics:
    """Calculate compounding and risk metrics from a growth-index level series."""
    clean = series.dropna()
    if len(clean) < 2:
        raise ValueError("At least two observations are required.")

    key = key or str(series.name or "Series")
    returns = clean.pct_change().dropna()
    years = _years_between(clean)
    growth_multiple = clean.iloc[-1] / clean.iloc[0]
    cagr = growth_multiple ** (1 / years) - 1 if years > 0 else 0.0
    drawdowns = clean / clean.cummax() - 1
    rolling_12m = returns.rolling(12).apply(lambda values: (1 + values).prod() - 1)
    doubling_time = log(2) / log(1 + cagr) if cagr > 0 else None

    worst_12m = rolling_12m.min()
    best_12m = rolling_12m.max()

    return SeriesMetrics(
        key=key,
        name=DISPLAY_NAMES.get(key, key.replace("_", " ")),
        start_value=float(clean.iloc[0]),
        end_value=float(clean.iloc[-1]),
        growth_multiple=float(growth_multiple),
        cagr=float(cagr),
        annualized_volatility=float(returns.std() * (12**0.5)),
        max_drawdown=float(drawdowns.min()),
        longest_drawdown_months=_longest_drawdown_months(clean),
        worst_12m_return=None if pd.isna(worst_12m) else float(worst_12m),
        best_12m_return=None if pd.isna(best_12m) else float(best_12m),
        doubling_time_years=float(doubling_time) if doubling_time is not None else None,
        months=len(clean),
    )


def compute_dashboard_metrics(
    df: pd.DataFrame,
    start_year: int,
    visible: dict[str, bool] | None = None,
) -> DashboardMetrics:
    """Calculate visible-series dashboard metrics for the selected time window."""
    window = df.loc[f"{start_year}-01-01":]
    visible = visible or {key: True for key in MAIN_ANALYTICS_SERIES}

    series_metrics = []
    for key in MAIN_ANALYTICS_SERIES:
        if key not in window.columns or not visible.get(key, True):
            continue
        clean = window[key].dropna()
        if len(clean) < 2:
            continue
        series_metrics.append(calculate_series_metrics(clean, key=key))

    investable = [item for item in series_metrics if item.key in RETURN_SERIES]
    primary_candidates = investable or series_metrics
    primary = max(primary_candidates, key=lambda item: item.end_value / item.start_value, default=None)
    inflation = next((item for item in series_metrics if item.key == "Inflation"), None)
    real_end = None
    if primary is not None and "Inflation" in window.columns:
        inflation_series = window["Inflation"].dropna()
        if len(inflation_series) >= 2:
            inflation_growth = inflation_series.iloc[-1] / inflation_series.iloc[0]
            nominal_end = primary.end_value / primary.start_value * 1000
            real_end = float(nominal_end / inflation_growth)

    end_year = int(window.index.max().year) if not window.empty else start_year
    return DashboardMetrics(
        series=series_metrics,
        primary=primary,
        inflation=inflation,
        inflation_adjusted_primary_end=real_end,
        window_label=f"{start_year} -> {end_year}",
    )


def classify_risk_profile(
    horizon_years: int,
    stated_risk_score: int,
    drawdown_response: str,
    income_stability: str,
) -> RiskProfile:
    """Map simple questionnaire inputs to an explainable risk-tolerance profile."""
    stated = max(1, min(10, int(stated_risk_score)))
    behavior_scores = {
        "sell": 2,
        "do_nothing": 5,
        "rebalance": 7,
        "buy_more": 9,
    }
    behavior = behavior_scores.get(drawdown_response, 5)

    if horizon_years >= 20:
        capacity = 8
    elif horizon_years >= 10:
        capacity = 6
    elif horizon_years >= 5:
        capacity = 4
    else:
        capacity = 2

    income_adjustments = {
        "stable": 1,
        "variable": 0,
        "unstable": -1,
    }
    income_adjustment = income_adjustments.get(income_stability, 0)

    composite = round(0.45 * behavior + 0.30 * capacity + 0.25 * stated + income_adjustment)
    composite = max(1, min(10, composite))

    if composite >= 7:
        category = "Aggressive"
    elif composite >= 4:
        category = "Moderate"
    else:
        category = "Conservative"

    explanation = (
        f"{category} profile from behavior {behavior}/10, capacity {capacity}/10, "
        f"and stated risk {stated}/10."
    )
    if behavior + 1 < stated:
        explanation += " Behavioral score pulled the result down because actions matter more than intent."
    elif behavior > stated + 1:
        explanation += " Behavior increased the result because the user reports staying invested in drawdowns."

    return RiskProfile(
        category=category,
        composite_score=composite,
        stated_score=stated,
        behavior_score=behavior,
        capacity_score=capacity,
        income_adjustment=income_adjustment,
        explanation=explanation,
    )
