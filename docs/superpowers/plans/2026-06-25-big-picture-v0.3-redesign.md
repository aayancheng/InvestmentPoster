# Big Picture v0.3 — Simplified USD Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the white-on-dark 9-series CAD poster view with a clean, dark, full-screen **USD** chart of 4 US core series, plus a scroll-down actionable ETF allocation section.

**Architecture:** Add 4 US/USD core series to the parquet (FRED), build a new `chart_landing.py` (2-row dark figure), add an allocation donut + dark theme to `chart_etf.py`, and rewrite `big_picture.py`'s layout (no sidebar/nav/cards). `chart_main.py` is retired from the page but kept in the repo for its `_rebase`/`_annualised_return` helpers.

**Tech Stack:** Python 3.11+, pandas, Plotly, Streamlit, FRED (fredapi), pytest. Run via `.venv/bin/python`. FRED key in `.env` (`export $(cat .env | xargs)`).

**Spec:** `docs/superpowers/specs/2026-06-25-big-picture-v0.3-redesign-design.md`

---

## Context: current state

- `data/monthly_returns.parquet` columns: `US_Stocks, Canadian_Stocks, International_Stocks, Bonds, T_Bills, Inflation, Aggressive, Moderate, Conservative, VOO_USD, VGT_USD, SCHD_USD, Simple_ETF_USD, USD_CAD, Prime_CA, Prime_US`. All growth series are CAD except the `_USD` ETF columns.
- `scripts/build_history.py`: `_fred(id)` fetches+caches FRED series (monthly, month-end). `_ret_to_level(rets)` → growth-of-$1000. `load_shiller()` returns the S&P 500 total-return index **in USD**, named `US_Stocks_USD` (currently consumed only via `to_cad`). `load_cdn_bond_tr()` builds bond TR from a yield series with duration=8. `load_tbills()` / `load_inflation()` patterns are reused below.
- `app/analytics.py`: `calculate_series_metrics(series, key) -> SeriesMetrics` with fields `growth_multiple, cagr, max_drawdown, doubling_time_years, end_value, start_value`. This is what the stat strip uses.
- `app/chart_main.py`: `_rebase(s)` and `_annualised_return(s)` helpers (importable). Builds the 4-row CAD figure (retired from the page after this work).
- `app/chart_etf.py`: `build_etf_panel(df, start_date="2006-11-30")`, constants `ETF_SERIES_ORDER`, `ETF_COLOURS`, `ETF_DISPLAY_NAMES`. Currently white background.

Run commands from `/Users/aayan/zzLearnAndCreate/InvestmentPortfolio/`.

---

## File structure

| File | Responsibility | Change |
|---|---|---|
| `scripts/build_history.py` | data pipeline | +4 US/USD loaders, bond-TR helper refactor, +4 parquet columns |
| `app/chart_landing.py` | NEW — 2-row dark USD landing figure | create |
| `app/chart_etf.py` | ETF growth panel + allocation donut | +donut, dark theme |
| `app/big_picture.py` | Streamlit page layout | rewrite landing + ETF section, drop sidebar/nav/cards/risk-profiler |
| `tests/test_history.py` | parquet schema/data tests | +US core USD tests |
| `tests/test_chart_landing.py` | NEW — landing chart smoke tests | create |
| `tests/test_chart_etf.py` | NEW — donut smoke test | create |
| `CLAUDE.md`, `README.md` | docs | update to v0.3 |

---

## BLOCK A — Data pipeline (US/USD core series)

### Task 1: Refactor bond-TR math into a shared helper

**Files:**
- Modify: `scripts/build_history.py` (the `load_cdn_bond_tr()` function, ~lines 301-319)
- Test: `tests/test_history.py`

- [ ] **Step 1.1: Add the shared helper above `load_cdn_bond_tr()`**

Insert this function immediately before `def load_cdn_bond_tr()`:

```python
def _bond_tr_from_yield(yield_pct: pd.Series, duration: float, name: str) -> pd.Series:
    """Constant-duration total-return index from a constant-maturity yield series.

    monthly TR ≈ yield/12  −  duration × Δyield   (ignores convexity; OK at log scale)
    Returns growth-of-$1000, rebased to 1000 at the first observation.
    """
    y = yield_pct.loc[START:] / 100
    rets = pd.Series(0.0, index=y.index)
    for i in range(1, len(y)):
        coupon    = y.iloc[i - 1] / 12
        price_chg = -duration * (y.iloc[i] - y.iloc[i - 1])
        rets.iloc[i] = coupon + price_chg
    return _ret_to_level(rets).rename(name)
```

- [ ] **Step 1.2: Rewrite `load_cdn_bond_tr()` to use the helper**

Replace the body of `load_cdn_bond_tr()` with:

```python
def load_cdn_bond_tr() -> pd.Series:
    """Canadian 10-year government bond total-return index in CAD.

    FRED IRLTLT01CAM156N (10-year yield, % p.a.), constant modified duration 8.0y.
    """
    return _bond_tr_from_yield(_fred("IRLTLT01CAM156N"), 8.0, "Bonds")
```

- [ ] **Step 1.3: Run existing history tests to confirm no regression**

Run: `.venv/bin/pytest tests/test_history.py -q`
Expected: PASS (the refactor is behaviour-preserving; tests read the existing parquet which is unchanged so far).

- [ ] **Step 1.4: Commit**

```bash
git add scripts/build_history.py
git commit -m "refactor: extract _bond_tr_from_yield helper in build_history"
```

---

### Task 2: Add the four US/USD core loaders

**Files:**
- Modify: `scripts/build_history.py` (add loaders after `load_us_inflation`/`load_schd` block, before `load_cdn_bond_tr` is fine; and wire into `main()`)

- [ ] **Step 2.1: Add the three new US loaders**

Insert after `_bond_tr_from_yield` (and after `load_cdn_bond_tr`/`load_tbills`/`load_inflation` exist — placement anywhere among the loaders is fine):

```python
def load_us_bonds_usd() -> pd.Series:
    """US 10-year Treasury total-return index in USD.

    FRED GS10 (10-Year Treasury Constant Maturity, % p.a., monthly), duration 8.0y.
    """
    return _bond_tr_from_yield(_fred("GS10"), 8.0, "US_Bonds_USD")


def load_us_tbills_usd() -> pd.Series:
    """US 3-month T-bill total-return index in USD.

    FRED TB3MS (3-Month Treasury Bill, Secondary Market Rate, % p.a., monthly).
    Monthly TR = rate/12.
    """
    rates = _fred("TB3MS").loc[START:] / 100
    return _ret_to_level(rates / 12).rename("US_TBills_USD")


def load_us_inflation_usd() -> pd.Series:
    """US CPI rebased to $1000 at START. FRED CPIAUCSL (CPI-U, index, monthly)."""
    cpi = _fred("CPIAUCSL").loc[START:]
    full_idx = pd.date_range(cpi.index[0], pd.Timestamp(END) + pd.offsets.MonthEnd(0), freq="ME")
    cpi = cpi.reindex(full_idx).ffill()
    return (cpi / cpi.iloc[0] * 1000).rename("US_Inflation_USD")
```

(`US_Stocks_USD` needs no new loader — `load_shiller()` already returns it.)

- [ ] **Step 2.2: Wire the new series into `main()`**

In `main()`, the line `us_usd = load_shiller()` already exists. After the ETF sleeve load block (the `load_voo/vgt/schd` lines), add:

```python
    print("\nLoading US core sleeve (USD, FRED):")
    us_bonds_usd     = load_us_bonds_usd()
    us_tbills_usd    = load_us_tbills_usd()
    us_inflation_usd = load_us_inflation_usd()
```

- [ ] **Step 2.3: Append the 4 columns to the output DataFrame**

In the `out = pd.DataFrame({...})` assembly, add these entries (place them right after the ETF `_USD` columns, before `"USD_CAD"`):

```python
        # US core sleeve — USD, NOT FX-adjusted to CAD
        "US_Stocks_USD":     us_usd,
        "US_Bonds_USD":      us_bonds_usd,
        "US_TBills_USD":     us_tbills_usd,
        "US_Inflation_USD":  us_inflation_usd,
```

- [ ] **Step 2.4: Add a print line for the new series in the summary block**

After the existing `etf_summary` print loop, add:

```python
    us_summary = out[["US_Stocks_USD", "US_Bonds_USD", "US_TBills_USD", "US_Inflation_USD"]].iloc[-1]
    print("\nEnd-of-history growth of $1,000 USD (US core sleeve):")
    for col, val in us_summary.items():
        print(f"  {col:<18} ${val:>12,.0f}")
```

- [ ] **Step 2.5: Rebuild the parquet**

```bash
export $(cat .env | xargs) && .venv/bin/python scripts/build_history.py
```

Expected: the build prints a "US core sleeve" summary with 4 values; `US_Stocks_USD` ≈ \$1.0M+, the others much lower. No crash.

- [ ] **Step 2.6: Commit**

```bash
git add scripts/build_history.py data/drawdowns.json
git commit -m "feat: add US core USD series (stocks/bonds/cash/inflation) to parquet"
```

---

### Task 3: Tests for the US core series

**Files:**
- Modify: `tests/test_history.py`

- [ ] **Step 3.1: Add the US core list to the column contract**

After the `ETF_SERIES = [...]` line and the `ALL_COLS = ...` line near the top, change them to:

```python
ETF_SERIES = ["VOO_USD", "VGT_USD", "SCHD_USD", "Simple_ETF_USD"]
US_CORE_USD = ["US_Stocks_USD", "US_Bonds_USD", "US_TBills_USD", "US_Inflation_USD"]
ALL_COLS = MAIN_SERIES + SUPPLEMENTARY + ETF_SERIES + US_CORE_USD
```

- [ ] **Step 3.2: Write the US core tests at the end of the file**

```python
def test_us_core_usd_start_at_1000(df):
    for col in US_CORE_USD:
        first_valid = df[col].dropna().iloc[0]
        assert abs(first_valid - 1000.0) < 1.0, f"{col} starts at {first_valid:.2f}, expected ~1000"


def test_us_core_usd_reach_1956(df):
    for col in US_CORE_USD:
        assert df[col].first_valid_index().year <= 1956, (
            f"{col} starts {df[col].first_valid_index()}, expected <= 1956"
        )


def test_us_core_usd_positive(df):
    for col in US_CORE_USD:
        valid = df[col].dropna()
        assert (valid > 0).all(), f"{col} has non-positive values"


def test_us_stocks_usd_below_cad(df):
    """US_Stocks_USD (USD) ends below US_Stocks (CAD) — CAD weakened vs USD.
    Guards against accidentally routing the USD series through to_cad()."""
    end = df.loc["2025-12-31"]
    assert end["US_Stocks_USD"] < end["US_Stocks"], "US_Stocks_USD should be < US_Stocks (CAD)"
```

- [ ] **Step 3.3: Run the history tests**

Run: `.venv/bin/pytest tests/test_history.py -v`
Expected: all PASS, including the 4 new tests.

- [ ] **Step 3.4: Commit**

```bash
git add tests/test_history.py
git commit -m "test: cover US core USD series in parquet"
```

---

## BLOCK B — Charts

### Task 4: New landing chart module

**Files:**
- Create: `app/chart_landing.py`
- Test: `tests/test_chart_landing.py`

- [ ] **Step 4.1: Write the failing smoke test**

Create `tests/test_chart_landing.py`:

```python
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
    assert "US Stocks" in names and "Bonds" in names


def test_landing_chart_is_dark(df):
    from chart_landing import build_landing_chart
    fig = build_landing_chart(df, start_year=1961)
    assert fig.layout.paper_bgcolor in ("rgba(0,0,0,0)", "rgba(0, 0, 0, 0)")
    assert fig.layout.plot_bgcolor in ("rgba(0,0,0,0)", "rgba(0, 0, 0, 0)")
```

- [ ] **Step 4.2: Run it to verify failure**

Run: `.venv/bin/pytest tests/test_chart_landing.py -q`
Expected: FAIL (`No module named 'chart_landing'`).

- [ ] **Step 4.3: Create `app/chart_landing.py`**

```python
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

from chart_main import _rebase, _annualised_return

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
        cagr = _annualised_return(s)
        colour = LANDING_COLOURS[col]
        name = LANDING_NAMES[col]
        if col == "US_Stocks_USD":
            label = f"  {name} · ${s.iloc[-1]:,.0f} · {cagr*100:.1f}%/yr"
        else:
            label = f"  {name} · ${s.iloc[-1]:,.0f}"
        fig.add_trace(
            go.Scatter(
                x=s.index, y=s.values, name=name, mode="lines+text",
                line=dict(color=colour, width=2.4 if col == "US_Stocks_USD" else 1.7),
                text=[""] * (len(s) - 1) + [label],
                textposition="middle right",
                textfont=dict(size=9, color=colour),
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
        margin=dict(l=54, r=170, t=10, b=30),
        hovermode="x unified",
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
```

- [ ] **Step 4.4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_chart_landing.py -q`
Expected: PASS (2 tests).

- [ ] **Step 4.5: Commit**

```bash
git add app/chart_landing.py tests/test_chart_landing.py
git commit -m "feat: add dark USD landing chart (chart_landing.py)"
```

---

### Task 5: Allocation donut + dark theme for the ETF panel

**Files:**
- Modify: `app/chart_etf.py`
- Test: `tests/test_chart_etf.py`

- [ ] **Step 5.1: Write the failing donut test**

Create `tests/test_chart_etf.py`:

```python
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
```

- [ ] **Step 5.2: Run it to verify failure**

Run: `.venv/bin/pytest tests/test_chart_etf.py -q`
Expected: FAIL (`build_allocation_donut` not defined; panel still white).

- [ ] **Step 5.3: Add `build_allocation_donut()` to `app/chart_etf.py`**

Append this function at the end of `app/chart_etf.py`:

```python
def build_allocation_donut() -> go.Figure:
    """Donut of the 50/25/25 VOO/VGT/SCHD recommended mix, dark/transparent."""
    labels = ["VOO", "VGT", "SCHD"]
    values = [50, 25, 25]
    colours = [ETF_COLOURS["VOO_USD"], ETF_COLOURS["VGT_USD"], ETF_COLOURS["SCHD_USD"]]

    fig = go.Figure(
        go.Pie(
            labels=labels, values=values, hole=0.62,
            marker=dict(colors=colours, line=dict(color="#0a0a0a", width=2)),
            textinfo="label+percent", textfont=dict(color="#ffffff", size=12),
            sort=False, direction="clockwise", showlegend=False,
            hovertemplate="%{label} · %{value}%<extra></extra>",
        )
    )
    fig.add_annotation(text="3 ETFs", showarrow=False,
                       font=dict(color="#ffffff", size=15, family="sans-serif"))
    fig.update_layout(
        height=240, margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
```

- [ ] **Step 5.4: Re-theme `build_etf_panel` to dark**

In `app/chart_etf.py`, inside `build_etf_panel`, find the `fig.update_layout(...)` call and change the two background lines from white to transparent, and lighten fonts/grid. Specifically set:

```python
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
```

and in the `fig.update_yaxes(...)` / `fig.update_xaxes(...)` calls within that function, set `tickfont=dict(color="#9a9a9a", size=10)` and `gridcolor="#1c1c1c"`. Also change the blend line colour `ETF_COLOURS["Simple_ETF_USD"]` from near-black `#111111` to near-white `#f2f2f2` (near the top of the file) so it reads on dark.

- [ ] **Step 5.5: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_chart_etf.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5.6: Commit**

```bash
git add app/chart_etf.py tests/test_chart_etf.py
git commit -m "feat: dark theme + allocation donut for ETF section"
```

---

## BLOCK C — Page layout

### Task 6: Rewrite `big_picture.py` (landing + ETF section)

**Files:**
- Modify: `app/big_picture.py`

This task is a layout rewrite. Streamlit pages are not unit-tested; verification is an import smoke test plus manual visual check.

- [ ] **Step 6.1: Update imports**

Replace the three chart/analytics import lines (currently importing `build_figure`, `compute_dashboard_metrics`, `classify_risk_profile`, `build_etf_panel`) with:

```python
from analytics import calculate_series_metrics
from chart_landing import build_landing_chart
from chart_etf import build_etf_panel, build_allocation_donut
```

- [ ] **Step 6.2: Simplify page config and remove the localStorage hack**

Set `initial_sidebar_state="collapsed"` in `st.set_page_config(...)` and **delete** the entire `components.html(...)` block (the localStorage sidebar script) and the `import streamlit.components.v1 as components` line.

- [ ] **Step 6.3: Replace the KPI-card CSS with a slim stat strip and hide the sidebar**

In the big `st.markdown("""<style>...""")` block, remove the `.ip-card*`, `.ip-brand*`, `.ip-nav*` rules and add:

```css
        [data-testid="stSidebar"] { display: none !important; }
        .ip-strip { display: flex; gap: 2.2rem; margin: 0.3rem 0 0.2rem; }
        .ip-strip .v { font-size: 1.15rem; font-weight: 700; color: #fff; line-height: 1.1; }
        .ip-strip .v.red { color: #e0685f; }
        .ip-strip .l { font-size: 0.62rem; letter-spacing: 0.05em; text-transform: uppercase;
                       color: #777; margin-top: 2px; }
        .ip-headline { font-size: 0.9rem; color: #cfcfcf; line-height: 1.55; margin-top: 0.4rem; }
        .ip-headline b { color: #fff; } .ip-headline .pos { color: #5fb98c; } .ip-headline .neg { color: #e0685f; }
        .ip-cue { text-align: center; color: #555; font-size: 0.72rem; margin: 0.6rem 0 1.4rem; }
        .ip-section-title { font-size: 1.3rem; font-weight: 700; margin-top: 0.4rem; }
        .ip-sub { font-size: 0.8rem; color: #7a7a7a; margin-top: 0.2rem; }
```

- [ ] **Step 6.4: Delete the sidebar block, the card helpers, and the risk-profiler section**

Remove:
- the `for _key in MAIN_SERIES_ORDER:` session-state loop,
- the `SHORT_NAMES = {...}` dict,
- the entire `with st.sidebar:` block,
- the `metric_card`, `render_card_grid` helper functions and all calls to them,
- the entire "Risk tolerance check" expander / `classify_risk_profile` section,
- the old `build_figure(...)` chart render and the old methodology expander tied to the CAD chart.

Keep `load_data()` / the `df = load_data()` call and the `fmt_*` helpers if still referenced (otherwise remove unused ones).

- [ ] **Step 6.5: Add the new landing block**

Where the hero/cards used to be, add:

```python
# ── Controls + metrics ────────────────────────────────────────────────────────
m = calculate_series_metrics(df["US_Stocks_USD"].dropna(), key="US_Stocks_USD")
# Real (inflation-adjusted) end value for the headline
cpi = df["US_Inflation_USD"].dropna()
real_mult = m.growth_multiple / (cpi.iloc[-1] / cpi.iloc[0])

st.markdown("## 2025 The Big Picture")

strip_col, slider_col = st.columns([3, 1])
with slider_col:
    start_year = st.slider("Start year", 1956, 2010, 1961, 1)
with strip_col:
    dbl = f"{m.doubling_time_years:.1f} yrs" if m.doubling_time_years else "—"
    st.markdown(
        "<div class='ip-strip'>"
        f"<div><div class='v'>${m.end_value:,.0f}</div><div class='l'>End value</div></div>"
        f"<div><div class='v'>{m.cagr*100:.1f}%</div><div class='l'>Per year</div></div>"
        f"<div><div class='v red'>{m.max_drawdown*100:.1f}%</div><div class='l'>Worst drop</div></div>"
        f"<div><div class='v'>{dbl}</div><div class='l'>To double</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

fig = build_landing_chart(df, start_year=start_year)
st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "<div class='ip-headline'>"
    f"<b>$1,000 → ${m.end_value:,.0f}</b> in US stocks since {start_year} — about "
    f"<b class='pos'>{m.cagr*100:.0f}% a year</b>, but you'd have ridden a "
    f"<b class='neg'>{m.max_drawdown*100:.0f}% drop</b> along the way "
    f"(${real_mult*1000:,.0f} after inflation)."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown("<div class='ip-cue'>↓ scroll for an actionable ETF portfolio</div>", unsafe_allow_html=True)
```

Note: `start_year` must be defined before `build_landing_chart` is called — the `st.columns` block above does that. The stat strip uses the **full-history** metric `m`; that's acceptable for v0.3 (the strip headline numbers reflect the whole US-stocks record). The chart itself still respects `start_year`.

- [ ] **Step 6.6: Add the ETF section**

After the landing block:

```python
# ── Actionable ETF portfolio ──────────────────────────────────────────────────
st.markdown("<div class='ip-section-title'>The power of a simple ETF portfolio</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='ip-sub'>Three broadly-held ETFs in a 50/25/25 mix — Core, Growth, Income. "
    "Growth of $1,000 USD, rebased 2006.</div>",
    unsafe_allow_html=True,
)

mix_col, growth_col = st.columns([1, 2])
with mix_col:
    st.plotly_chart(build_allocation_donut(), use_container_width=True)
    st.markdown(
        "<div style='font-size:0.78rem;color:#cfcfcf;line-height:1.7;'>"
        "<b style='color:#2E86C1;'>VOO</b> S&P 500 · Core · 50%<br>"
        "<b style='color:#E67E22;'>VGT</b> Info Tech · Growth · 25%<br>"
        "<b style='color:#27AE60;'>SCHD</b> Dividend · Income · 25%"
        "</div>",
        unsafe_allow_html=True,
    )
with growth_col:
    st.plotly_chart(build_etf_panel(df), use_container_width=True)

st.markdown(
    "<div class='ip-headline'>The <b>blend</b> beats holding VOO alone — the growth tilt lifts "
    "returns while income and core soften the ride.</div>",
    unsafe_allow_html=True,
)
```

- [ ] **Step 6.7: Smoke-test the import (catches syntax / NameErrors)**

Run:
```bash
cd app && ../.venv/bin/python -c "import ast; ast.parse(open('big_picture.py').read()); print('parse OK')" && cd ..
```
Expected: `parse OK`. Then verify all referenced names resolve:
```bash
cd app && ../.venv/bin/python -c "import chart_landing, chart_etf, analytics; print('imports OK')" && cd ..
```
Expected: `imports OK`.

- [ ] **Step 6.8: Manual visual check**

```bash
export $(cat .env | xargs) && .venv/bin/streamlit run app/big_picture.py --server.port 8502 --server.headless true
```
Open `http://localhost:8502`. Confirm: dark charts flush on the shell (no white panels); landing = title + stat strip (left) + slider (right) + full-width 4-line USD chart + drawdown strip + headline + scroll cue; no sidebar/nav/cards; scroll down shows the donut + ticker list + dark ETF growth chart + takeaway.

- [ ] **Step 6.9: Commit**

```bash
git add app/big_picture.py
git commit -m "feat: v0.3 dark USD landing + actionable ETF section; drop sidebar/cards/FX"
```

---

## BLOCK D — Docs

### Task 7: Update CLAUDE.md and README.md to v0.3

**Files:**
- Modify: `CLAUDE.md`, `README.md`

- [ ] **Step 7.1: Update CLAUDE.md "Current UI state" section**

Retitle the section to `## Current UI state — Big Picture v0.3 (dark USD redesign)` and replace its body bullets to describe: dark transparent charts; the landing (no sidebar/nav/cards, title + stat strip + right-aligned slider, full-width `chart_landing.py` figure with 4 US/USD core series + drawdown strip + headline); the scroll-down ETF section (`build_allocation_donut` + dark `build_etf_panel`); and note that `chart_main.py` + `annotations.py` are retired from the page but kept in the repo, and the FX row / macro band / KPI cards / risk-profiler are removed. Update the data-flow tree: add `app/chart_landing.py`, and note the 4 new USD columns (`US_Stocks_USD, US_Bonds_USD, US_TBills_USD, US_Inflation_USD`).

- [ ] **Step 7.2: Update README.md**

In the "What's in here" and "Project structure" sections, describe the v0.3 dark USD landing + actionable ETF section, add `app/chart_landing.py`, and update the data-source table to note the US core series (FRED GS10 / TB3MS / CPIAUCSL, USD). Update the roadmap: mark "v0.3 — dark USD redesign" done.

- [ ] **Step 7.3: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: update CLAUDE.md + README for v0.3 dark USD redesign"
```

---

### Task 8: Final verification

- [ ] **Step 8.1: Run the full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: all PASS (history + analytics + chart_landing + chart_etf).

- [ ] **Step 8.2: Confirm the app renders end-to-end** (repeat Step 6.8 if not already open) and visually confirm both sections look right in dark theme.

---

## Self-Review

**Spec coverage:**
- Dark theme → Tasks 4, 5, 6 (transparent bg on both charts + shell).
- 4 US/USD core series → Tasks 1–3.
- Stat strip + headline + inline labels (no cards) → Tasks 4, 6.
- No rail / no nav / slider right of strip → Task 6.
- Drawdown strip kept → Task 4 (row 2).
- ETF donut + dark growth chart → Task 5, 6.
- Dropped FX row / macro band / cards / risk-profiler → Task 6.
- chart_main retired but kept (helpers imported) → Tasks 4, 6.
- Tests → Tasks 3, 4, 5, 8.
- Docs → Task 7.

**Placeholder scan:** none — every code step has full code.

**Type consistency:** `build_landing_chart(df, start_year)`, `build_allocation_donut()`, `build_etf_panel(df)`, `calculate_series_metrics(series, key) -> SeriesMetrics` (fields `end_value, cagr, max_drawdown, doubling_time_years, growth_multiple`) used consistently. Column names `US_Stocks_USD / US_Bonds_USD / US_TBills_USD / US_Inflation_USD` identical across pipeline, charts, tests, and page.
