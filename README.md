# InvestmentPortfolio

A personal, rules-based ETF portfolio operating system — and a reproduction of the *2025 The Big Picture* poster as an interactive Streamlit dashboard.

> **Not financial advice.** This is a system-design and personal-tooling project. The tool surfaces your own rules; it makes no portfolio decisions for you.

---

## What's in here

### 1 · The Big Picture dashboard (live, v0.3)

An interactive, dark, **USD** dashboard. The landing is a full-screen log-scale chart of four US core series — **US Stocks, Bonds, Cash, Inflation** — from 1956 to 2025, with an underwater drawdown strip. Scroll down for an actionable **3-ETF portfolio**.

```bash
export $(cat .env | xargs) && streamlit run app/big_picture.py --server.port 8502
```

Open `http://localhost:8502`. The page has two sections:

- **Landing** — title, a slim **stat strip** (end value · CAGR · worst drawdown · doubling time, window-scoped), and a **start-year slider** that rebases every line to $1,000 on the chosen date. The full-width dark chart shows the four core series with inline end-of-line labels and an underwater drawdown strip; a plain-language headline sums up the growth-vs-drawdown tradeoff.
- **The power of a simple ETF portfolio** — a 50/25/25 allocation **donut** (VOO Core / VGT Growth / SCHD Income) next to a growth comparison of the three ETFs and the blended portfolio. Each ETF is proxy-backfilled so its line reaches back before inception.

> Earlier views — the CAD multi-asset poster (`app/chart_main.py`), USD/CAD FX band, inflation/prime band, KPI cards, and risk-tolerance check — are retired from the page but remain in the repo.

### 2 · Allocation engine (planned)

A Python-based portfolio operating routine. Profile inputs → target sleeve allocation across four sleeves (core broad-market, AI-tilt growth, income, defensive). Produces threshold-triggered trade tickets; you execute them manually in your broker. DCA-on-inflow and 5%/20% rebalance rules built in. The risk-tolerance classifier above is the first piece of this.

---

## Quick start

```bash
# 1. Create and activate a virtual environment
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your FRED API key (free at fred.stlouisfed.org)
#    Either export it, or drop it in a .env file (gitignored):
echo "FRED_API_KEY=your_key_here" > .env

# 4. Build the canonical data file from raw sources
export $(cat .env | xargs) && python scripts/build_history.py

# 5. (Optional) Recompute drawdown positions / reseed events
python scripts/compute_drawdowns.py
python scripts/seed_events.py

# 6. Run the dashboard
export $(cat .env | xargs) && streamlit run app/big_picture.py --server.port 8502
```

`build_history.py` fetches from yfinance and FRED and caches raw downloads in `data/raw/` (gitignored), so the first build is the slow one.

---

## Project structure

```
InvestmentPortfolio/
├── app/
│   ├── big_picture.py        # Streamlit dashboard (entry point, v0.3 dark USD)
│   ├── chart_landing.py      # v0.3 landing: dark USD growth chart + drawdown strip
│   ├── chart_etf.py          # USD ETF panel + allocation donut (VOO/VGT/SCHD + blend)
│   ├── chart_main.py         # legacy 4-row CAD poster (retired from page; helpers reused)
│   ├── annotations.py        # event tick marks + hover labels (legacy)
│   └── analytics.py          # series metrics + risk-profile classifier
├── data/
│   ├── monthly_returns.parquet   # Canonical history — shared by poster + engine (gitignored)
│   ├── events.json               # ~70 annotation positions, hand-tunable
│   ├── drawdowns.json            # Drawdown episodes for the top strip
│   └── raw/                      # Cached source downloads (gitignored)
├── scripts/
│   ├── build_history.py      # Splices raw sources → monthly_returns.parquet
│   ├── compute_drawdowns.py  # Reads history → writes drawdowns.json
│   └── seed_events.py        # Writes events.json
├── tests/
│   ├── test_history.py       # Parquet schema + data sanity (incl. ETF + US core series)
│   ├── test_chart_landing.py # Landing chart smoke tests
│   ├── test_chart_etf.py     # ETF donut + dark-theme smoke tests
│   └── test_analytics.py     # Metrics + risk classifier
├── docs/superpowers/         # Design specs and implementation plans
├── poster_buildplan.md       # Phased build plan + schema migration log
├── postersample.jpg          # Reference photo of the physical poster
├── requirements.txt
└── CLAUDE.md                 # AI coding instructions and design decisions
```

**Key invariant:** `data/monthly_returns.parquet` has a monthly `DatetimeIndex` and one named column per series. Both the poster and the allocation engine read it — any schema change requires a migration note in `poster_buildplan.md`. Columns suffixed `_USD` are kept in **USD** (the ETF sleeve `VOO_USD/VGT_USD/SCHD_USD/Simple_ETF_USD` and the v0.3 US core sleeve `US_Stocks_USD/US_Bonds_USD/US_TBills_USD/US_Inflation_USD`); all other growth series are CAD.

---

## Data sources

The v0.3 landing is **USD**. Legacy CAD series remain in the parquet for the retired poster view. All growth series are growth-of-$1,000, total return where available.

**v0.3 US core sleeve (USD):**

| Series | Source | Window | Notes |
|---|---|---|---|
| US Stocks | Shiller `ie_data.xls` (S&P 500 TR), spliced to SPY | 1956+ | Total return |
| Bonds | FRED `GS10` (10Y Treasury) → constructed TR, 8yr duration | 1956+ | Ignores convexity |
| Cash | FRED `TB3MS` (3-month T-bill) | 1956+ | |
| Inflation | FRED `CPIAUCSL` (US CPI-U) | 1956+ | |

**ETF panel (USD):** VOO / VGT / SCHD, yfinance, proxy-backfilled (see below).

**Legacy CAD series (retired poster view):** S&P/TSX (`^GSPTSE`+XIU), MSCI EAFE (EFA), Canadian bonds/T-bills/CPI (FRED), USD/CAD (`DEXCAUS`), prime rate — all FX-adjusted to CAD.

**ETF proxy backfill** (total return): VOO ← Shiller S&P 500 (1956), VGT ← QQQ (1999, corr 0.98), SCHD ← VYM (2006, corr 0.97). Proxies are close but not identical — see the panel's in-app methodology note. Pre-1956 Canadian data requires paid CRSP-Canada, out of scope for v1.

---

## Roadmap

| Stage | Status |
|---|---|
| Big Picture v0.1 — data pipeline + 4-panel chart | ✅ Done |
| Big Picture v0.1.1 — static sidebar, inline swatches, localStorage fix | ✅ Done |
| Big Picture v0.2 — dark-shell dashboard, KPI cards, analytics, risk-tolerance check | ✅ Done |
| Drawdown underwater strip + event tick marks | ✅ Done |
| "Power of a simple ETF portfolio" panel (VOO/VGT/SCHD + blend) | ✅ Done |
| Big Picture v0.3 — dark USD redesign (4 US core series, no FX/cards/sidebar) | ✅ Done |
| Three inset panels (compositions, risk/return, GIC) | Planned |
| Allocation engine notebook | Planned |
| Risk-profiling conversation (full) | Planned |
| Streamlit MVP (profile → drift dashboard → trade tickets) | Planned |

---

## Testing

```bash
.venv/bin/pytest tests/ -v
```

The data-pipeline tests assert the parquet schema, monthly-continuous index, growth-series sanity, and ETF inception/backfill behaviour. They read whatever `monthly_returns.parquet` is currently built, so run `build_history.py` first.

---

## Tech stack

- Python 3.11+, pandas, numpy, pyarrow
- Streamlit ≥ 1.32 · Plotly ≥ 5.20
- yfinance (price data) · FRED API (macro data)
- pytest for data-pipeline and analytics tests

---

## Design principles

- **Inaction by default.** The tool makes it harder, not easier, to act impulsively in volatile markets.
- **Explainable rules.** Every allocation rule has a docstring explaining the reasoning.
- **No lookahead.** Backtests are walk-forward only, with 0.05% slippage on rebalance trades.
- **Readable over clever.** Comment the *why*, not the *what*.
- **The parquet is the contract.** Data shape changes get a migration note in `poster_buildplan.md`.
