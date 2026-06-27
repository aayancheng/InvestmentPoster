import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

PARQUET = Path(__file__).parent.parent / "data" / "monthly_returns.parquet"


@pytest.fixture(scope="module")
def df():
    return pd.read_parquet(PARQUET)


def test_landing_chart_builds(df):
    from chart_landing import build_landing_chart
    fig = build_landing_chart(df, start_year=1961)
    # 4 core line traces + 1 drawdown trace
    assert len(fig.data) == 5
    names = [t.name for t in fig.data if t.name]
    assert any(n.startswith("US Stocks") for n in names)
    assert any(n.startswith("Bonds") for n in names)


def test_landing_chart_is_dark(df):
    from chart_landing import build_landing_chart
    fig = build_landing_chart(df, start_year=1961)
    assert fig.layout.paper_bgcolor in ("rgba(0,0,0,0)", "rgba(0, 0, 0, 0)")
    assert fig.layout.plot_bgcolor in ("rgba(0,0,0,0)", "rgba(0, 0, 0, 0)")
