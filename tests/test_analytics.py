import pandas as pd
import pytest

from app.analytics import (
    MAIN_ANALYTICS_SERIES,
    calculate_series_metrics,
    classify_risk_profile,
    compute_dashboard_metrics,
)


def test_calculate_series_metrics_reports_compounding_and_drawdown():
    index = pd.date_range("2020-01-31", periods=25, freq="ME")
    values = pd.Series([100, 110, 121] + [121] * 22, index=index, name="Demo")

    metrics = calculate_series_metrics(values)

    assert metrics.start_value == pytest.approx(100)
    assert metrics.end_value == pytest.approx(121)
    assert metrics.growth_multiple == pytest.approx(1.21)
    assert metrics.cagr == pytest.approx(0.10, rel=0.02)
    assert metrics.max_drawdown == pytest.approx(0.0)
    assert metrics.months == 25


def test_calculate_series_metrics_derives_risk_from_level_series():
    index = pd.date_range("2021-01-31", periods=5, freq="ME")
    values = pd.Series([100, 80, 120, 90, 150], index=index, name="Volatile")

    metrics = calculate_series_metrics(values)

    assert metrics.max_drawdown == pytest.approx(-0.25)
    assert metrics.worst_12m_return is None
    assert metrics.annualized_volatility > 0
    assert metrics.longest_drawdown_months == 2


def test_compute_dashboard_metrics_uses_only_visible_series():
    index = pd.date_range("2020-01-31", periods=25, freq="ME")
    df = pd.DataFrame(
        {
            "US_Stocks": [100 * (1.01**i) for i in range(25)],
            "Bonds": [100 * (1.002**i) for i in range(25)],
            "Inflation": [100 * (1.001**i) for i in range(25)],
        },
        index=index,
    )
    visible = {key: False for key in MAIN_ANALYTICS_SERIES}
    visible["Bonds"] = True

    dashboard = compute_dashboard_metrics(df, start_year=2020, visible=visible)

    assert dashboard.primary.key == "Bonds"
    assert [item.key for item in dashboard.series] == ["Bonds"]
    assert dashboard.inflation_adjusted_primary_end is not None
    assert dashboard.window_label == "2020 -> 2022"


def test_classify_risk_profile_weights_behavior_more_than_stated_score():
    profile = classify_risk_profile(
        horizon_years=25,
        stated_risk_score=8,
        drawdown_response="sell",
        income_stability="stable",
    )

    assert profile.category == "Moderate"
    assert profile.behavior_score < profile.stated_score
    assert "Behavioral score pulled the result down" in profile.explanation


def test_classify_risk_profile_rewards_long_horizon_and_hold_behavior():
    profile = classify_risk_profile(
        horizon_years=30,
        stated_risk_score=6,
        drawdown_response="buy_more",
        income_stability="stable",
    )

    assert profile.category == "Aggressive"
    assert profile.composite_score >= 7
