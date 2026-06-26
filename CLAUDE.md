# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# InvestmentPortfolio — Project Context

## Purpose

A personal, rules-based ETF portfolio operating system. Not a trading algorithm — a disciplined routine that keeps the user exposed to broad markets with risk-appropriate allocation between growth and income ETFs, with Claude in the loop for the judgment moments.

Eventual end state: a small tool (Streamlit first, then web app) that other retail investors can use to design and operate their own portfolio.

**Not financial advice.** This is a system-design and personal-tooling project. The tool helps the user execute their own decisions with discipline; it does not make portfolio decisions for them.

## User context

YanCheng (aayancheng@gmail.com). Background in credit risk analytics / financial services. Comfortable with Python notebooks, pandas, basic ML, and reading research papers. Wants to keep the design simple and explainable, not quant-fund clever.

## Core design decisions (locked unless explicitly revisited)

**Framing.** "Portfolio operating routine," not a trading system. ~6–12 actions per year, not 600. Optimize for asset allocation, contribution discipline, behavioral resistance, and tax efficiency — not for signals or execution.

**Four sleeves:**
1. Core broad-market (e.g., VT, VTI, VOO)
2. Growth tilt — AI-themed (e.g., QQQ, VGT, SOXX)
3. Income (e.g., SCHD, VYM, JEPI/JEPQ, VIG)
4. Defensive (e.g., BND, SGOV, TIPS)

The Big Picture poster now *illustrates* sleeves 1–3 with a live spliced chart: Core = VOO, Growth = VGT, Income = SCHD, plus a blended "Simple 3-ETF Portfolio" (see "Power of a simple ETF portfolio" panel below).

**Allocation rules.**
- Profile inputs: age, horizon, account type, income stability, stated risk score, behavioral questions (especially "what did you do in March 2020?").
- Growth-% anchor: roughly 110-minus-age, modified by risk score. Within growth: core / AI-tilt split based on concentration tolerance. Within non-growth: income / defensive split based on yield-now vs. stability-now preference.
- Behavioral risk signal weighted higher than stated risk score.

**Execution rules.**
- DCA on inflows: new contributions go to currently underweight sleeves (passive rebalancing, no tax events).
- Threshold rebalance: trigger trade tickets when any sleeve drifts >5% absolute or >20% relative from target.
- System produces trade tickets — user executes trades manually in their broker.

**Claude-in-the-loop responsibilities.**
- Risk-profiling conversation (probes behavioral, not just stated).
- Drawdown coaching at >15% portfolio drawdown — surfaces the user's pre-committed rules.
- Education on demand (e.g., explain JEPI covered-call mechanics).

## Non-goals

- No auto-trading or brokerage execution.
- No leverage, options, or short positions.
- No "market regime detection" or signal-based timing.
- No day trading, swing trading, or anything resembling active management.
- No personalized financial advice — the tool surfaces the user's own rules.
- v1 has no brokerage integration. Plaid read-only aggregation is a v2 question only.

## Build stages

1. **Allocation engine notebook** (current focus). Python notebook: profile dict → target sleeve allocation. Backtest 3–4 sample profiles against 2015–2025 history.
2. **Risk-profiling conversation.** Designed and tested on YanCheng first. Output is a profile the user actually agrees with.
3. **Streamlit MVP.** Single-file app wrapping the engine + conversation. CSV import of current holdings, drift dashboard, trade-ticket export.
4. **Stress test as real user.** Run on a hypothetical portfolio, refine awkward parts.
5. **(Optional) Web app.** Next.js + FastAPI + SQLite. Multi-user. No brokerage integration.

## Current UI state — Big Picture v0.3 (dark USD redesign)

`app/big_picture.py` is a simplified, dark, **USD** dashboard. Current work lives on branch `codex/betteranalytics` (the `main` and `feature/dashboard-redesign` branches are older). Design spec: `docs/superpowers/specs/2026-06-25-big-picture-v0.3-redesign-design.md`; plan: `docs/superpowers/plans/2026-06-25-big-picture-v0.3-redesign.md`.

- **Dark, flush charts.** Both Plotly figures use `paper_bgcolor`/`plot_bgcolor = "rgba(0,0,0,0)"` so they sit flush on the `#0a0a0a` shell (`.streamlit/config.toml` `base="dark"`). The old white-panel-on-dark clash is gone.
- **No sidebar, no nav, no KPI cards.** CSS hides `[data-testid="stSidebar"]` and the Streamlit header. The previous sidebar/localStorage hack, the `.ip-card*` grid, and the risk-tolerance check are all removed.
- **Landing (above the fold):** title top-left; one row with a slim **stat strip** (End value · Per year · Worst drop · To double) on the left and the **start-year slider** right-aligned; a full-width 2-row `app/chart_landing.py` figure (log USD growth + underwater drawdown strip); a plain-language headline; a scroll cue. Metrics are window-scoped (`calculate_series_metrics` on `US_Stocks_USD.loc[start_year:]`) and the headline end value uses `growth_multiple*1000` so it matches the chart's rebase.
- **Four core series (all US, USD):** `US_Stocks_USD` (S&P 500 TR), `US_Bonds_USD` (FRED GS10, constructed TR), `US_TBills_USD` (FRED TB3MS), `US_Inflation_USD` (FRED CPIAUCSL). Built in `scripts/build_history.py` via `_bond_tr_from_yield` + `load_us_*` loaders; NOT passed through `to_cad()`.
- **Scroll-down ETF section:** `build_allocation_donut()` (50/25/25 VOO/VGT/SCHD) + ticker legend on the left, dark-themed `build_etf_panel()` growth chart on the right, takeaway line. Both in `app/chart_etf.py`.
- **Analytics** (`app/analytics.py`): `calculate_series_metrics(series, key)` powers the stat strip. `compute_dashboard_metrics()` / `classify_risk_profile()` remain in the module but are no longer wired into the page.
- **Retired from the page (kept in repo):** `app/chart_main.py` (the 4-row CAD poster — `chart_landing.py` imports its `_rebase`/`_annualised_return` helpers) and `app/annotations.py` (event ticks). The USD/CAD FX row, inflation/prime band, Canadian series, and 3 portfolios are no longer plotted.

**Run the app:**
```bash
export $(cat .env | xargs) && .venv/bin/streamlit run app/big_picture.py --server.port 8502
```

**Next steps — beginner-focused, long-term-investing (v0.4 candidates):**
1. **Monthly contribution simulator** — an "If I invest $X/month" input that overlays dollar-cost-averaged contributions on the US-stocks path (total contributed vs. ending value). Reframes the abstract $1,000 into the user's own plan. (Deferred "contribution math" option from the v0.3 brainstorm.)
2. **Stay-invested drawdown coaching** — make the drawdown strip teach: hover shows "recovered by {year}, took {N} months"; a headline stat like "every major drop fully recovered — longest took {N} years"; optional "what if you sold at the bottom" comparison. Serves the project's behavioral-discipline goal (panic-selling resistance).
3. **Real (inflation-adjusted) toggle** — switch the chart between nominal and real dollars, making the Inflation line the explicit "beat this" baseline. Teaches purchasing power over decades.

**Other candidates:** allocation engine notebook (Build stage 1); optional ETF-panel start-date slider; the three inset panels (poster track). The CAD poster (`chart_main.py`) can be reintroduced as a separate view if desired. Full write-up of the three v0.4 ideas is in `docs/superpowers/specs/2026-06-25-big-picture-v0.3-redesign-design.md` ("Next steps" section).

## Parallel track: The Big Picture poster

A reproduction of the *Investments Illustrated* "2025 The Big Picture" poster — a 90-year log-scale chart of Canadian and US asset classes with drawdown overlay, FX band, inflation/prime band, ~70 event annotations, a decade-returns strip, and three inset panels (portfolio compositions, risk/return scatter, GIC returns).

Lives inside this project — not a separate repo — because it shares the historical-returns data pipeline with the allocation engine backtests. The same `data/monthly_returns.parquet` powers both.

**Stack (locked):** Streamlit + Plotly + pandas, built in Claude Code. Same stack as the rest of the project.

**Data window (locked):** 1956–2025 from free sources. Pre-1956 Canadian stocks requires paid CRSP-Canada data and is out of scope for v1.

**Aesthetic ceiling:** Plotly-quality, not framed-poster-quality. v0.1 reads as "the same chart, missing detail," not "a different chart."

See `poster_buildplan.md` for the phased build plan, file layout, data-source splice details, and open questions.

## Tech stack

- Python 3.11+, pandas, numpy
- yfinance for price data (free)
- FRED API for macro (free, key in env)
- Streamlit for MVP UI
- Plotly for charts (interactive) or matplotlib (static)
- Later: Next.js, FastAPI, SQLite

## UX principles

The tool should make it **harder, not easier**, to do impulsive things in volatile markets. Default to inaction. Confirmation delays on destructive actions. Required Claude check-in before any trade >10% of portfolio. This is the opposite of most fintech and must be preserved through every iteration.

## Working conventions

- Keep code readable over clever. Comment the *why*, not the *what*.
- Every allocation rule has a docstring explaining the reasoning.
- Sample profiles live in a fixtures file and double as test cases.
- Backtests assume realistic costs (no commissions on ETFs at major brokers, but include 0.05% slippage on rebalance trades and reinvest dividends).
- Never use lookahead data. Walk-forward only.

## Development commands

```bash
# Run the Streamlit app (once app/ exists)
streamlit run app/big_picture.py

# Rebuild the canonical history parquet from raw sources
python scripts/build_history.py

# Recompute drawdown positions
python scripts/compute_drawdowns.py

# Run tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_history.py -v

# Install dependencies (once requirements.txt exists)
pip install -r requirements.txt
```

Environment: set `FRED_API_KEY` before running any script that pulls macro data.

## Architecture and data flow

```
scripts/build_history.py
  └── pulls raw sources → data/raw/
  └── splices into data/monthly_returns.parquet   ← canonical, shared contract
        │
        ├── app/chart_landing.py       (v0.3 dark USD landing: 4 US core series + drawdown strip)
        ├── app/chart_main.py          (legacy 4-row CAD poster — retired from page, helpers reused)
        ├── app/chart_etf.py           (USD ETF panel + allocation donut: VOO/VGT/SCHD + blend)
        ├── app/annotations.py         (event tick marks + hover, reads data/events.json)
        ├── app/analytics.py           (dashboard metrics + risk-profile classifier)
        ├── app/big_picture.py         (Streamlit page, @st.cache_data wrapper)
        └── allocation engine notebook (backtest uses same parquet, planned)

        (app/chart_insets.py — 3 inset figures — is a planned v0.3 item, not yet built)

scripts/compute_drawdowns.py
  └── reads monthly_returns.parquet → writes data/drawdowns.json

data/events.json          ← annotation positions — edit JSON, not figure builder code
data/drawdowns.json       ← computed drawdown rectangles for row 1 of poster
```

Key invariant: `monthly_returns.parquet` has a monthly DatetimeIndex and one named column per series. Both the poster and the allocation engine read it — any schema change requires a migration note in `poster_buildplan.md`. Columns suffixed `_USD` are kept in USD and must NOT be passed through `to_cad()`; all other growth series are CAD. USD columns: the ETF sleeve (`VOO_USD, VGT_USD, SCHD_USD, Simple_ETF_USD`) and the v0.3 US core sleeve (`US_Stocks_USD, US_Bonds_USD, US_TBills_USD, US_Inflation_USD`).

## What to do at session start

1. Read this file.
2. If the request touches the Big Picture poster, also read `poster_buildplan.md`.
3. Check current state of the notebook / tool in this folder.
4. Ask the user which stage they want to work on if it's not obvious from the request.
