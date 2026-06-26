import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
PARQUET = Path(__file__).parent.parent / "data" / "monthly_returns.parquet"


@pytest.fixture(scope="module")
def df():
    return pd.read_parquet(PARQUET)


def test_allocation_donut_builds():
    from chart_etf import build_allocation_donut
    fig = build_allocation_donut()
    assert len(fig.data) == 1
    assert sum(fig.data[0].values) == 100
    assert set(fig.data[0].labels) == {"VOO", "VGT", "SCHD"}


def test_etf_panel_is_dark(df):
    from chart_etf import build_etf_panel
    fig = build_etf_panel(df)
    assert fig.layout.paper_bgcolor in ("rgba(0,0,0,0)", "rgba(0, 0, 0, 0)")
