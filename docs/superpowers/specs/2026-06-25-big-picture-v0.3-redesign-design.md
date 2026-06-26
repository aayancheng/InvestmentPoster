# Big Picture v0.3 — Simplified USD Redesign

**Date:** 2026-06-25
**Status:** Design approved, ready for implementation plan

## Context

The current dashboard (v0.2) renders a Plotly chart with `paper_bgcolor="#FFFFFF"` inside a dark (`#0a0a0a`) Streamlit shell, producing an ugly white-panel-on-dark clash. It also shows nine series (4 asset classes + 3 portfolios + inflation, plus an FX row and a macro band), a left control rail, top nav, and a row of bulky KPI cards — too much for a beginner and too much chrome competing with the chart.

The white clash is **not** a Streamlit constraint; it is a Plotly theming choice. Plotly fully supports transparent/dark backgrounds.

This redesign makes the landing a clean, full-screen **USD** growth chart of the essentials, and turns the scroll-down ETF panel into an **actionable** recommended-allocation view.

## Goals

- Dark, flush-with-the-shell charts (fix the white clash).
- Beginner-simple landing: **4 core US/USD series only** — US Stocks, Bonds, Cash, Inflation.
- Maximum chart real estate: no left rail, no top nav, no bulky KPI cards.
- Key analytics surfaced lightly: a **slim stat strip** + a plain-language **headline sentence** + **inline end-of-line labels**.
- Scroll down to an **actionable ETF portfolio**: explicit 50/25/25 donut + growth comparison.

## Non-goals

- Contribution calculator / "invest $X/month" math (deferred).
- Allocation engine, full risk-profiler (risk-tolerance check is **dropped** from this version).
- Keeping the Canadian/CAD poster view, FX row, macro band, or the 3 portfolios in the UI.
- Deleting existing CAD data/columns or modules from the repo (they stay, just unused by the page).

## Locked design decisions

| Decision | Choice |
|---|---|
| Currency | **USD**, all-US series |
| Core series | US Stocks, Bonds (10Y Treasury), Cash (3-mo T-bill), Inflation (US CPI) |
| Bonds/Cash/Inflation basis | **US** (FRED), not Canadian |
| Analytics callout | Slim stat strip + headline sentence + inline line labels (no KPI cards) |
| Layout | No left rail, no nav; title top-left; stat strip left + start-year slider right-aligned to chart edge |
| Supporting panels kept | Drawdown strip (under main chart); ETF section |
| Supporting panels dropped | USD/CAD FX row, inflation/prime band, KPI cards, risk-tolerance check |
| ETF section | Donut 50/25/25 (VOO/VGT/SCHD) left + growth chart right + takeaway |
| Chart code structure | **New focused modules** — `chart_landing.py`; donut added to `chart_etf.py`; `chart_main.py` retired from the page (kept in repo) |
| Event annotations | **Not** rendered on the v0.3 landing chart (keep it clean; revisit later) |

## Architecture

```
scripts/build_history.py
  └── + 4 new US/USD core columns in monthly_returns.parquet:
        US_Stocks_USD, US_Bonds_USD, US_TBills_USD, US_Inflation_USD
        (existing CAD columns + ETF _USD columns unchanged)
        │
        ├── app/chart_landing.py   NEW — 2-row dark USD figure (main log + drawdown strip)
        ├── app/chart_etf.py       + build_allocation_donut(); re-theme build_etf_panel dark
        ├── app/analytics.py       unchanged API; fed the USD series
        └── app/big_picture.py     rewritten layout (no sidebar/nav/cards)

  retired from page (still in repo): app/chart_main.py, app/annotations.py
```

### Data pipeline — `scripts/build_history.py`

Add four loaders, reusing existing construction patterns, all **USD**, never passed through `to_cad()`:

- `US_Stocks_USD` — `load_shiller()` already returns the S&P 500 total-return index in USD (it is currently consumed only via `to_cad`). Store its USD output directly as a column.
- `US_Bonds_USD` — FRED **GS10** (10Y Treasury market yield, monthly, 1953+) → constructed TR using the same constant-duration (8yr) method as `load_cdn_bond_tr()`. Factor that bond-TR math into a shared helper taking a yield series, so the CAD and US bond builders share it.
- `US_TBills_USD` — FRED **TB3MS** (3-month T-bill secondary market rate, monthly, 1934+) → `_ret_to_level(rate/12)`, same as `load_tbills()`.
- `US_Inflation_USD` — FRED **CPIAUCSL** (US CPI, monthly, 1947+) → rebased to 1000, same as `load_inflation()`.

All four span 1956–2025 (S&P is the binding start at 1956). Append the columns to the output `out` DataFrame.

### Landing chart — `app/chart_landing.py` (new)

`build_landing_chart(df, start_year=1961) -> go.Figure`:
- 2-row `make_subplots` (`row_heights≈[0.82, 0.18]`, shared x): **row 1** log-scale USD growth of `US_Stocks_USD`, `US_Bonds_USD`, `US_TBills_USD`, `US_Inflation_USD`, rebased to $1,000 at `start_year`; **row 2** the underwater drawdown strip of `US_Stocks_USD` (port the existing logic from `chart_main.py`).
- Each line: `lines+text`, label only on the last point — `"  US Stocks · $912k · 11.1%/yr"` style.
- Reuse `_rebase` and `_annualised_return` (import from `chart_main`, which stays in the repo).
- **Dark theme:** `paper_bgcolor="rgba(0,0,0,0)"`, `plot_bgcolor="rgba(0,0,0,0)"`, light tick/grid colours (`#888` text, `#1a1a1a` grid), legend off (inline labels do the work).
- No FX row, no macro band, no event annotations.

### ETF section — `app/chart_etf.py`

- `build_allocation_donut() -> go.Figure` — a `go.Pie(hole≈0.62)` of `SIMPLE_ETF_WEIGHTS` (50/25/25), coloured VOO blue / VGT orange / SCHD green, dark/transparent background, centre text "3 ETFs". Slice labels show ticker + %.
- `build_etf_panel(...)` — re-theme to dark/transparent (same treatment as the landing chart); blend line stays bold near-white on dark.

### Page — `app/big_picture.py`

- **Remove** the sidebar entirely (and the localStorage sidebar hack), the top nav, and the `.ip-card*` KPI grid.
- Landing block: title (`## 2025 The Big Picture`) → a row via `st.columns([3, 1])`: left = slim stat strip (compact custom-HTML: End value · Per year · Worst drop · To double from `compute_dashboard_metrics(df["US_Stocks_USD"])`), right = `st.slider("Start year", …)` → full-width `st.plotly_chart(build_landing_chart(...))` → headline sentence (`st.markdown`, generated from the metrics) → scroll cue.
- ETF section: heading + sub → `st.columns([1, 2])`: left = `build_allocation_donut()`, right = `build_etf_panel(df)` → takeaway line.
- New CSS: `.ip-strip` (slim borderless stat row) replaces `.ip-card*`; keep the dark shell styles.

## Testing

- `tests/test_history.py`: add the 4 new columns to `ALL_COLS`; assert each starts ≈1956, starts ≈$1,000, stays positive; USD-not-CAD sanity (`US_Stocks_USD` 2025 terminal `< US_Stocks` CAD terminal).
- New `tests/test_chart_landing.py` (light): `build_landing_chart` returns a figure with 4 main-row line traces + a drawdown trace, transparent backgrounds set.
- Manual: run the app, confirm both charts are dark/flush, landing fills the viewport, stat strip + slider share one row, ETF donut + growth render, scroll flow reads top-to-bottom.

## Open risks

- **New FRED series availability** at build time — mitigated by the existing `data/raw/` CSV cache and the same fetch pattern as current loaders.
- **US bond TR approximation** — constant 8yr duration ignores convexity, identical caveat to the existing Canadian bond series; acceptable at log scale.
- **Start-year vs data coverage** — all four US series reach 1956, so the slider range is unaffected; default stays 1961.
- **Retiring `chart_main.py` from the page** leaves it unused; keep it imported only for the `_rebase`/`_annualised_return` helpers (or lift those into a tiny shared util if cleaner during implementation).

## Next steps — beginner-focused, long-term-investing (v0.4 candidates)

These build on v0.3 to help a first-time investor *internalise* long-horizon discipline rather than just read a chart. Each is self-contained and could be its own spec.

1. **Monthly contribution simulator — "If I invest $X/month."**
   Beginners save monthly, not in lump sums. Add an input (default ~$200/month) that overlays the growth of dollar-cost-averaged contributions on the US-stocks path, showing **total contributed vs. ending value** (and ideally the same for the 3-ETF blend). Reframes the abstract "$1,000 → $X" into the user's own plan and makes the compounding tangible. This is the "contribution math" option deferred during the v0.3 brainstorm. Data already exists; this is a UI + small projection-math task (reuse the monthly index; sum contributions × forward growth).

2. **Stay-invested drawdown coaching.**
   Beginners panic-sell in crashes — the behaviour the whole project is designed to resist. Turn the passive drawdown strip into a teaching tool: on hover show **"recovered by {year}, took {N} months"** (data is already in `data/drawdowns.json` / `compute_drawdowns.py`); add a one-line stat such as **"every major drop fully recovered — the longest took {N} years"**; optionally a **"what if you sold at the bottom and stayed in cash"** comparison line to quantify the cost of panic. Directly advances the "make impulsive action harder" UX principle.

3. **Real (inflation-adjusted) toggle.**
   Beginners underestimate inflation over decades. Add a toggle to switch the chart between **nominal and real (inflation-adjusted)** dollars, making the `US_Inflation_USD` line the explicit "beat this to actually grow" baseline. Teaches why cash and bonds barely grow in real terms and why a long equity horizon matters. Cheap to implement: divide each series by the rebased CPI index before plotting when the toggle is on.

**Sequencing suggestion:** (2) is the highest-leverage for the project's behavioural mission and reuses existing drawdown data; (1) is the most motivating for a beginner; (3) is the smallest lift. A natural v0.4 bundles (2) + (3) (both chart-level, low risk) and treats (1) as its own follow-up.
