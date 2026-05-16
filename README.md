# InvestmentPortfolio

A personal, rules-based ETF portfolio operating system — and a reproduction of the *2025 The Big Picture* poster as an interactive Streamlit app.

> **Not financial advice.** This is a system-design and personal-tooling project. The tool surfaces your own rules; it makes no portfolio decisions for you.

---

## What's in here

### 1 · The Big Picture (live at v0.1)

An interactive reproduction of the *Investments Illustrated "2025 The Big Picture"* poster — a log-scale chart of major Canadian and US asset classes from 1956 to 2025, with drawdown overlay, USD/CAD band, inflation/prime-rate band, and ~70 event annotations.

```
streamlit run app/big_picture.py
```

Open `http://localhost:8502`. The static sidebar holds all controls: a start-year slider to rebase every series to a chosen date, and per-series toggles with inline colour swatches.

### 2 · Allocation Engine (in progress)

A Python-based portfolio operating routine. Profile inputs → target sleeve allocation across four sleeves (core broad-market, AI-tilt growth, income, defensive). Produces threshold-triggered trade tickets; you execute them manually in your broker. DCA-on-inflow and 5%/20% rebalance rules built in.

---

## Quick start

```bash
# 1. Create and activate a virtual environment
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your FRED API key (free at fred.stlouisfed.org)
export FRED_API_KEY=your_key_here

# 4. Build the canonical data file from raw sources
python scripts/build_history.py

# 5. (Optional) Recompute drawdown positions
python scripts/compute_drawdowns.py

# 6. Run the Streamlit app
streamlit run app/big_picture.py
```

---

## Project structure

```
InvestmentPortfolio/
├── app/
│   ├── big_picture.py        # Streamlit page (entry point)
│   ├── chart_main.py         # 4-row Plotly figure (drawdowns, main, FX, macro)
│   └── annotations.py        # Event label helpers
├── data/
│   ├── monthly_returns.parquet   # Canonical history — shared by poster + allocation engine
│   ├── events.json               # ~70 annotation positions, hand-tunable
│   ├── drawdowns.json            # Drawdown rectangles for the top panel
│   └── raw/                      # Untouched source files (Shiller, FRED, StatCan)
├── scripts/
│   ├── build_history.py      # Splices raw sources → monthly_returns.parquet
│   ├── compute_drawdowns.py  # Reads history → writes drawdowns.json
│   └── seed_events.py        # One-shot: seeds events.json with initial entries
├── tests/
│   └── test_history.py
├── poster_buildplan.md       # Phased build plan for the Big Picture poster
├── requirements.txt
└── CLAUDE.md                 # AI coding instructions and design decisions
```

**Key invariant:** `data/monthly_returns.parquet` has a monthly `DatetimeIndex` and one named column per series. Both the poster and the allocation engine read it — any schema change requires a migration note in `poster_buildplan.md`.

---

## Data sources

| Series | Source | Window |
|---|---|---|
| S&P 500 total return | Shiller `ie_data.xls` | 1956+ |
| S&P/TSX Composite | yfinance `^GSPTSE` | 1956+ |
| MSCI EAFE | Kenneth French data library | 1990+ |
| Canadian bonds | BoC + FRED yields (constructed TR) | 1960+ |
| Canadian T-bills | FRED / Bank of Canada | 1956+ |
| Canadian CPI | StatCan + FRED | 1956+ |
| USD/CAD | FRED `DEXCAUS` | 1971+ (1.00 for Bretton Woods era) |
| Prime Rate | FRED + Bank of Canada | Long history |

Pre-1956 Canadian data requires paid CRSP-Canada — out of scope for v1.

---

## Roadmap

| Stage | Status |
|---|---|
| Big Picture poster v0.1 — data pipeline + 4-panel chart | ✅ Done |
| Big Picture v0.1.1 — static sidebar, controls, UI polish | ✅ Done |
| Big Picture v0.2 — drawdown annotations + event labels | 🔜 Next |
| Allocation engine notebook | 🔜 Next |
| Risk-profiling conversation | Planned |
| Streamlit MVP (profile → drift dashboard → trade tickets) | Planned |

---

## Tech stack

- Python 3.11+, pandas, numpy, pyarrow
- Streamlit ≥ 1.32 · Plotly ≥ 5.20
- yfinance (price data) · FRED API (macro data)
- pytest for data-pipeline tests

---

## Design principles

- **Inaction by default.** The tool makes it harder, not easier, to act impulsively in volatile markets.
- **Explainable rules.** Every allocation rule has a docstring explaining the reasoning.
- **No lookahead.** Backtests are walk-forward only, with 0.05% slippage on rebalance trades.
- **Readable over clever.** Comment the *why*, not the *what*.
