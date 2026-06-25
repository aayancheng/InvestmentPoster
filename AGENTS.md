# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

# InvestmentPortfolio — Project Context

## Purpose

A personal, rules-based ETF portfolio operating system. Not a trading algorithm — a disciplined routine that keeps the user exposed to broad markets with risk-appropriate allocation between growth and income ETFs, with Codex in the loop for the judgment moments.

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

**Allocation rules.**
- Profile inputs: age, horizon, account type, income stability, stated risk score, behavioral questions (especially "what did you do in March 2020?").
- Growth-% anchor: roughly 110-minus-age, modified by risk score. Within growth: core / AI-tilt split based on concentration tolerance. Within non-growth: income / defensive split based on yield-now vs. stability-now preference.
- Behavioral risk signal weighted higher than stated risk score.

**Execution rules.**
- DCA on inflows: new contributions go to currently underweight sleeves (passive rebalancing, no tax events).
- Threshold rebalance: trigger trade tickets when any sleeve drifts >5% absolute or >20% relative from target.
- System produces trade tickets — user executes trades manually in their broker.

**Codex-in-the-loop responsibilities.**
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

## Current UI state — Big Picture v0.1.1

`app/big_picture.py` uses a static sidebar layout. Branch: `feature/dashboard-redesign` (PR #1 open).

- **Sidebar always open, non-collapsible.** `initial_sidebar_state="expanded"` + CSS hides `[data-testid="stSidebarHeader"]` (the collapse arrow) and `[data-testid="stHeader"]` (the top bar that holds Deploy + hamburger).
- **localStorage fix.** On load, a zero-height `streamlit.components.v1.html` component injects JS that clears Streamlit's cached sidebar key from `window.parent.localStorage`, so `initial_sidebar_state="expanded"` always wins — no manual DevTools step needed.
- **All controls live in the sidebar:** start-year slider, then per-series checkboxes. Each row uses `st.columns([5, 1])` — checkbox in the wide column, 3px colour swatch in the narrow column, inline to the right of the label.
- **Main area:** title, subtitle, Plotly chart, methodology expander. No controls.

**Run the app:**
```bash
export $(cat .env | xargs) && .venv/bin/streamlit run app/big_picture.py --server.port 8502
```

**Next planned step — v0.2 dashboard redesign:** dark shell (`#0a0a0a`) around a white chart, sidebar nav with coming-soon items, KPI cards (end value, CAGR, max drawdown, time window). Design spec at `docs/superpowers/specs/2026-05-14-big-picture-dashboard-redesign-design.md`.

## Parallel track: The Big Picture poster

A reproduction of the *Investments Illustrated* "2025 The Big Picture" poster — a 90-year log-scale chart of Canadian and US asset classes with drawdown overlay, FX band, inflation/prime band, ~70 event annotations, a decade-returns strip, and three inset panels (portfolio compositions, risk/return scatter, GIC returns).

Lives inside this project — not a separate repo — because it shares the historical-returns data pipeline with the allocation engine backtests. The same `data/monthly_returns.parquet` powers both.

**Stack (locked):** Streamlit + Plotly + pandas, built in Codex. Same stack as the rest of the project.

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

The tool should make it **harder, not easier**, to do impulsive things in volatile markets. Default to inaction. Confirmation delays on destructive actions. Required Codex check-in before any trade >10% of portfolio. This is the opposite of most fintech and must be preserved through every iteration.

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
        ├── app/chart_main.py          (poster main panel, 4-row Plotly figure)
        ├── app/chart_insets.py        (3 inset figures)
        ├── app/annotations.py         (event label helpers, reads data/events.json)
        ├── app/big_picture.py         (Streamlit page, @st.cache_data wrapper)
        └── allocation engine notebook (backtest uses same parquet)

scripts/compute_drawdowns.py
  └── reads monthly_returns.parquet → writes data/drawdowns.json

data/events.json          ← annotation positions — edit JSON, not figure builder code
data/drawdowns.json       ← computed drawdown rectangles for row 1 of poster
```

Key invariant: `monthly_returns.parquet` has a monthly DatetimeIndex and one named column per series. Both the poster and the allocation engine read it — any schema change requires a migration note in `poster_buildplan.md`.

## What to do at session start

1. Read this file.
2. If the request touches the Big Picture poster, also read `poster_buildplan.md`.
3. Check current state of the notebook / tool in this folder.
4. Ask the user which stage they want to work on if it's not obvious from the request.
