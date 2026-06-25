# InvestmentPortfolio

A personal, rules-based ETF portfolio operating system — and a reproduction of the *2025 The Big Picture* poster as an interactive Streamlit dashboard.

> **Not financial advice.** This is a system-design and personal-tooling project. The tool surfaces your own rules; it makes no portfolio decisions for you.

---

## What's in here

### 1 · The Big Picture dashboard (live, v0.2)

An interactive dark-shell dashboard built around a reproduction of the *Investments Illustrated "2025 The Big Picture"* poster — a log-scale chart of major Canadian and US asset classes from 1956 to 2025, with an underwater drawdown strip, USD/CAD band, inflation/prime-rate band, and ~70 event annotations (rendered as hover-enabled tick marks).

```bash
export $(cat .env | xargs) && streamlit run app/big_picture.py --server.port 8502
```

Open `http://localhost:8502`. The page has three layers:

- **KPI cards + narrative** — end value, CAGR, max drawdown, annualised volatility, worst rolling 12-month return, longest drawdown, and historical doubling time for the strongest visible series, plus a plain-language "long-term investing lens" and a **risk-tolerance check** that classifies you from a few behavioural questions (`app/analytics.py`).
- **Main poster chart** — the four-row Plotly figure. A static, always-open sidebar holds a start-year slider (rebases every series to a chosen date) and per-series toggles with inline colour swatches.
- **"Power of a simple ETF portfolio" panel** — a second, USD-denominated chart comparing **VOO** (Core / S&P 500), **VGT** (Growth / Info Tech), **SCHD** (Income / Dividend) against a blended **50/25/25 Simple 3-ETF Portfolio**. Each ETF is proxy-backfilled so its line reaches back before inception.

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
│   ├── big_picture.py        # Streamlit dashboard (entry point)
│   ├── chart_main.py         # 4-row Plotly figure (drawdown strip, main, FX, macro)
│   ├── chart_etf.py          # USD ETF comparison panel (VOO/VGT/SCHD + blend)
│   ├── annotations.py        # Event tick marks + hover labels
│   └── analytics.py          # Dashboard metrics + risk-profile classifier
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
│   ├── test_history.py       # Parquet schema + data sanity (incl. ETF series)
│   └── test_analytics.py     # Metrics + risk classifier
├── docs/superpowers/         # Design specs and implementation plans
├── poster_buildplan.md       # Phased build plan + schema migration log
├── postersample.jpg          # Reference photo of the physical poster
├── requirements.txt
└── CLAUDE.md                 # AI coding instructions and design decisions
```

**Key invariant:** `data/monthly_returns.parquet` has a monthly `DatetimeIndex` and one named column per series. Both the poster and the allocation engine read it — any schema change requires a migration note in `poster_buildplan.md`. Columns suffixed `_USD` (`VOO_USD`, `VGT_USD`, `SCHD_USD`, `Simple_ETF_USD`) are kept in **USD**; all other growth series are CAD.

---

## Data sources

All growth series are growth-of-$1,000, total return where available, FX-adjusted to **CAD** unless noted.

| Series | Source | Window | Notes |
|---|---|---|---|
| S&P 500 (US Stocks) | Shiller `ie_data.xls`, spliced to SPY | 1956+ | Total return |
| S&P/TSX (Canadian Stocks) | `^GSPTSE` + 3% yield, spliced to XIU.TO from 1999 | 1979+ | TR approximation pre-1999 |
| MSCI EAFE (International) | EFA ETF (Fama-French/`^MXEA` backfill currently unavailable) | 2001+ | Starts 2001 in practice |
| Canadian bonds | FRED 10Y yield → constructed TR (8yr duration) | 1956+ | Ignores convexity |
| Canadian T-bills | FRED 3-month rate | 1956+ | |
| Canadian CPI (Inflation) | FRED `CANCPIALLMINMEI` | 1956+ | |
| USD/CAD | FRED `DEXCAUS` | 1971+ | 1.00 for Bretton Woods era |
| Prime rate | FRED | Long history | |
| **ETF panel (USD):** VOO / VGT / SCHD | yfinance, proxy-backfilled | see below | Not FX-adjusted |

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
| Three inset panels (compositions, risk/return, GIC) | Planned (v0.3) |
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
