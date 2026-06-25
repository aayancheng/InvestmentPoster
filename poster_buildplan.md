# Big Picture Poster — Build Plan

A phased plan for reproducing the *Investments Illustrated* "2025 The Big Picture" poster as a Streamlit + Plotly page inside this project. Read alongside `CLAUDE.md`.

## Goal

A single Streamlit page that renders an interactive, themeable approximation of the poster. Useful as a standalone "where you are on the historical map" view and as a smoke test for the historical-returns data pipeline that the allocation engine also needs.

Faithful to the *structure and content* of the original (same series, same panels, same drawdown overlay, same inset trio, same annotations). Not faithful to the *typography and decorative polish* — that is a Plotly ceiling we accept.

## Stack (locked)

- Python 3.11+, pandas, numpy
- Plotly (`plotly.graph_objects`, `plotly.subplots.make_subplots`)
- Streamlit for the shell, `@st.cache_data` for history loads
- pyarrow for `.parquet` storage
- Data: yfinance, FRED API (key in env), Robert Shiller's `ie_data.xls`, StatCan historical tables
- Built and iterated in Claude Code, not in Cowork. The chart needs file-by-file iterative tuning that the artifact one-shot model cannot support.

## Scope for v1

**In scope.** Nine line series on a log-scale main panel from 1956–2025, end-of-line labels with annualized return, drawdown-arrow strip across the top, USD/CAD exchange-rate band, inflation + prime-rate band, ~70 event annotations, decade-returns strip across the bottom, three inset panels (portfolio compositions, risk/return scatter, GIC returns), and a trailing-1yr-returns block. Light interactivity (hover, legend toggle, zoom).

**Out of scope for v1.** Pre-1956 history (paid data). Brand-matched typography. Hand-drawn arrow ornaments. Currency-swap toggle (CAD↔USD redoing the FX layer). Theming beyond a single default. Print/PDF export.

## Data window — locked at 1956–2025

The original poster uses paid CRSP-Canada and MSCI direct subscriptions to go back to 1934. A faithful free reproduction is not possible. We commit to 1956-onward and call the pre-1956 gap a known limitation in a footnote on the chart itself.

| Series | Free source | Window | Notes |
| --- | --- | --- | --- |
| S&P 500 total return | Shiller `ie_data.xls` | 1871+ | Splice with FRED `SP500` post-1957 if needed |
| S&P/TSX Composite | yfinance `^GSPTSE` + paper appendices | 1956+ | Acknowledged proxy pre-1979 |
| MSCI EAFE | Kenneth French developed-ex-US factor | 1990+ | Show as starting in 1990 honestly |
| Canadian 10Y bond TR | Constructed from BoC + FRED `IRLTLT01CAM156N` yields | 1960+ | TR index built from yield + duration assumption |
| Canadian T-bills | FRED / Bank of Canada | 1953+ | |
| Canadian CPI | StatCan + FRED `CPALTT01CAM659N` | 1956+ | |
| USD/CAD | FRED `DEXCAUS` | 1971+ | Hard-code 1.00 for Bretton Woods era (1956–1970) |
| US Prime Rate | FRED `MPRIME` | Long history | |
| Canadian Prime Rate | Bank of Canada | Long history | |

The data pipeline is the high-risk part of this project. Treat splice quality as the v0.1 acceptance bar.

## File layout to create

```
InvestmentPortfolio/
├── CLAUDE.md
├── poster_buildplan.md           # this file
├── data/
│   ├── raw/                      # untouched downloads (Shiller, FRED CSVs, StatCan)
│   ├── monthly_returns.parquet   # canonical history, used by poster AND allocation engine
│   ├── events.json               # annotation fixtures, hand-tunable
│   └── drawdowns.json            # drawdown-arrow positions, computed from price history
├── scripts/
│   ├── build_history.py          # splices raw sources → monthly_returns.parquet
│   ├── compute_drawdowns.py      # produces drawdowns.json from history
│   └── seed_events.py            # one-shot: writes events.json with the initial ~70 entries
├── app/
│   ├── big_picture.py            # the Streamlit page
│   ├── chart_main.py             # the four-row Plotly figure builder
│   ├── chart_insets.py           # the three inset figures
│   └── annotations.py            # helpers for placing event labels with leader lines
└── tests/
    └── test_history.py           # sanity checks: monotonic dates, no NaN gaps, expected series count
```

Create this layout incrementally during the phases below — don't scaffold the whole thing up front.

## Phase v0.1 — Looks Like The Poster (data + skeleton)

Acceptance: the four-row figure renders with all nine series, end-labels don't overlap, x-axes line up cleanly. No annotations, no insets, no drawdown arrows yet.

Tasks, roughly in order:

1. `scripts/build_history.py`: pull raw sources into `data/raw/`, splice into a single monthly-indexed DataFrame with one column per series (US Stocks, Aggressive Portfolio, Canadian Stocks, Moderate Portfolio, International Stocks, Conservative Portfolio, Bonds, T-Bills, Inflation). Write to `data/monthly_returns.parquet`. The three "Portfolio" series are computed from the asset-class series using the compositions from the poster sidebar (e.g. Aggressive = 10% US Small Cap + 15% US Stocks + 20% Cdn Stocks + 25% Int'l Stocks + 25% Bonds + 5% Cash, annually rebalanced).
2. `tests/test_history.py`: monthly index continuity, no NaNs in expected windows, series count == 9, growth-of-$1k sanity check against poster's final values (within 10%).
3. `app/chart_main.py`: `make_subplots(rows=4, shared_xaxes=True, row_heights=[0.08, 0.55, 0.12, 0.12], vertical_spacing=0.02)`. Row 1 placeholder for drawdowns. Row 2 main log-scale lines. Row 3 FX band. Row 4 inflation + prime overlay. Right-edge labels via `mode='lines+text'` + `textposition='middle right'`.
4. `app/big_picture.py`: a Streamlit page that loads the parquet (cached), calls the figure builder, and renders it edge-to-edge (`st.set_page_config(layout='wide')`, hide menu/footer via config).

Don't tune annotations or drawdown arrows yet. Resist the urge.

## Phase v0.2 — Drawdowns and Events

Acceptance: drawdown arrows appear in row 1 at the right depths and durations. Event annotations are placed on the main panel and are mostly readable.

1. `scripts/compute_drawdowns.py`: from the Canadian Stocks series, identify peak-to-trough declines ≥20%, write `data/drawdowns.json` with `{peak_date, trough_date, recovery_date, depth_pct}` for each.
2. `app/chart_main.py`: render drawdowns in row 1 as red rectangles (width = recovery duration, height = depth) with depth label on top. This won't match the poster's exact arrow ornament — accept that.
3. `scripts/seed_events.py`: write `data/events.json` with the ~70 events visible in the original (wars, market crashes, oil prices, home prices, gold prices, TFSA introduction, Dow milestones, etc.). Each entry: `{date, y_value_or_anchor, text, dy_offset_px}`.
4. `app/annotations.py`: render events on the main panel using Plotly `add_annotation` with `ax`/`ay` offsets pulled from the JSON. Tuning the `dy_offset_px` values is iterative — expect to hand-edit the JSON across multiple sessions.

## Phase v0.3 — The Three Insets

Acceptance: portfolio-composition stacked bars, risk/return scatter, and GIC bar chart all render and look readable. Don't try to embed them inside the main figure — render them side-by-side in Streamlit columns above or below the main chart.

1. `app/chart_insets.py`: three independent `go.Figure` builders.
2. Portfolio compositions: stacked horizontal bars for Aggressive / Moderate / Conservative with the six asset-class slices.
3. Risk/return scatter: stdev × annualized return for each series, computed from `monthly_returns.parquet`. Label each point with the series name.
4. GIC returns: bar chart of Cdn Stocks / Bonds / GICs / Inflation since 1952. GIC return series will need to be sourced separately (BoC has it) or hard-coded from the poster.

## Phase v0.4 — Interactivity

Acceptance: hover tooltips show value+return at the cursor's date across all series. Legend toggle hides individual lines. Zoom/pan works on x-axis only (y-axes are intentionally fixed).

This is mostly Plotly configuration, not new code. The harder pieces:

1. Synchronized hover across all four subplot rows.
2. A toggle for log vs linear y-axis on the main panel — `updatemenus` button.
3. A start-year slider in the Streamlit sidebar that re-filters the parquet and re-renders.

## Phase v0.5 — Theming (optional)

Acceptance: chart works in light and dark mode using CSS variables, colors pulled from a single config dict.

Low priority. Only attempt if v0.1–v0.4 have stabilized.

## Working conventions specific to this sub-project

- **Annotation positions are data, not code.** Always edit `data/events.json` or `data/drawdowns.json`, never inline coordinates in the figure builder. This keeps regenerations cheap.
- **The data pipeline is the contract.** `monthly_returns.parquet` has a stable schema (datetime index, named columns, monthly frequency). Both the poster and the allocation engine read it. Schema changes require a migration note in this file.
- **Never silently fill data gaps.** If MSCI EAFE doesn't start until 1990, the line starts in 1990 — do not back-fill with zeros or proxy returns without an explicit note in the chart legend.
- **Splice provenance lives in code.** Every spliced series in `build_history.py` has a comment naming the sources and the splice date.
- **Don't reach for D3 or React.** If a Plotly limitation feels worth switching stacks for, write it in the "Open questions" section below first and revisit at v1 retro.

## Schema migrations

- **2026-06 — Added USD ETF sleeve.** Four new columns appended to `monthly_returns.parquet`:
  `VOO_USD`, `VGT_USD`, `SCHD_USD`, `Simple_ETF_USD`. These are growth-of-$1000 in **USD**
  (NOT FX-adjusted to CAD — they back the "Power of a simple ETF portfolio" panel, a
  deliberately US-market illustration). All other growth columns remain CAD. Any consumer
  computing cross-series comparisons must not mix `_USD` columns with the CAD columns without
  converting. Splice provenance: VOO←Shiller S&P 500 TR (1956), VGT←QQQ (1999), SCHD←VYM (2006);
  blend weights in `SIMPLE_ETF_WEIGHTS` (`scripts/build_history.py`). Rendered by `app/chart_etf.py`.

## Open questions

These need answers before or during the build — don't block on them, but flag them.

1. **GIC return series.** The poster shows GICs back to 1952. Bank of Canada has 5-year GIC posted rates, but those overstate realized GIC returns. Acceptable to use posted rates with a footnote? Or hard-code from the poster?
2. **Portfolio reblance frequency.** The poster footnote says "rebalanced each January, all other years U.S. CRSP/Stats Canada total return index." Match that, or rebalance monthly? January-only is the right answer for poster fidelity.
3. **Bond total-return index.** Building a TR series from yield assumes a constant 10-year duration and ignores convexity. Fine for a chart at log scale? Probably yes, but worth noting in the chart's "methodology" expander.
4. **Inflation series.** Canadian or US CPI? Poster shows Canadian. Make sure `build_history.py` uses StatCan, not BLS.
5. **Currency.** Poster is in CAD. Confirm all USD series are FX-converted to CAD before computing growth-of-$1k. Bretton Woods era (1956–1970) uses 1.00 hard-coded — flag this as a known approximation.
6. **Page width.** Streamlit defaults are too narrow for a 2000px poster. Use `layout='wide'` plus a custom max-width CSS injection, or accept that the chart scales down?

## What "done for v1" looks like

A user can open Streamlit, see the four-row chart with nine lines, three insets, drawdown overlay, and event annotations, hover to inspect any year, toggle series via the legend, and adjust the start year. The chart is recognizably the same as the poster on the wall, missing only the decorative typography and hand-drawn ornamentation. The `monthly_returns.parquet` it reads is the same file that Build stage 1's allocation engine backtests will consume.
