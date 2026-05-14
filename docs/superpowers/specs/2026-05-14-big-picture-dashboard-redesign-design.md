# Big Picture — Dashboard Redesign Design

**Date:** 2026-05-14  
**Status:** Approved — ready for implementation  
**Scope:** `app/big_picture.py`, `app/chart_main.py`, new `.streamlit/config.toml`

---

## Design decisions (locked)

| Decision | Choice |
|---|---|
| Direction | Modern dashboard polish — dark shell, designed feel |
| Visual vibe | Linear/Vercel — minimal, geometric, system-ui font, thin 1px borders |
| Chart background | Light (white) — chart stays white, framed by dark shell |
| Layout | Sidebar for controls and nav |
| Chart legend | Removed — end-of-line labels + sidebar toggles are sufficient |
| KPI cards | End value + CAGR (top series), max drawdown (red), time window |
| Coming-soon nav | Portfolio Analyzer, Risk Profiler, Trade Tickets — greyed at 35% opacity |

---

## Approach: theme-first (Approach 1)

Use `.streamlit/config.toml` for the dark base theme. Add a single focused CSS block (~50 lines) via `st.markdown(unsafe_allow_html=True)` in `big_picture.py` for the sidebar nav, KPI card layout, and typography. Keep all Streamlit widgets (`st.sidebar`, `st.slider`, `st.checkbox`) — style them with the theme, don't replace them. Plotly chart gets explicit `paper_bgcolor="white"` and `plot_bgcolor="white"`.

**Why not Approach 2 (heavy CSS override):** Streamlit's internal CSS class names change between minor versions — comprehensive overrides create maintenance debt.  
**Why not Approach 3 (st.columns sidebar):** Slider and checkbox widgets in narrow columns have layout edge cases; `st.sidebar` handles collapse and mobile gracefully.

---

## Section 1 — Page chrome

**File:** `.streamlit/config.toml` (new file)

```toml
[theme]
base = "dark"
backgroundColor = "#0a0a0a"
secondaryBackgroundColor = "#0d0d0d"
textColor = "#ededed"
font = "sans serif"
```

**CSS injected in `big_picture.py`:**
- Hide the Streamlit Deploy button: `[data-testid="stDeployButton"] { display: none; }`
- Hide the hamburger menu: `#MainMenu { display: none; }`
- Hide the footer: `footer { display: none; }`
- Set page padding: reduce default top padding so the title sits higher

---

## Section 2 — Sidebar

**File:** `app/big_picture.py`

Structure (top to bottom inside `st.sidebar`):

1. **Brand header** — "Investment Portfolio" / "Personal portfolio OS" — injected as HTML via `st.sidebar.markdown`
2. **Nav section** — injected as HTML:
   - Active page: "The Big Picture" with a `#d97757` left-border accent, `background: #1a1a1a`
   - Coming-soon items at `opacity: 0.35`, `cursor: not-allowed`, with a "Coming soon" sublabel beneath each:
     - Portfolio Analyzer
     - Risk Profiler
     - Trade Tickets
3. **Start Year** — `st.sidebar.slider("Start year", 1956, 2024, 1956)` — existing, keep as-is
4. **Series toggles** — render each series as a pair: a coloured line swatch (3px tall `<span>` injected via `st.sidebar.markdown`) immediately above the `st.sidebar.checkbox(...)`. The checkbox label stays plain text (Streamlit doesn't support HTML in checkbox labels). The swatch acts as a visual key only.

**Sidebar width:** Streamlit default (~21rem). Do not fight it.

**Color accent:** `#d97757` (warm orange — carries through from existing chart line colors).

---

## Section 3 — KPI cards

**File:** `app/big_picture.py`

Four cards rendered as a single `st.markdown` HTML block immediately below the page title, above the chart. Cards are a flex row.

| Card | Value | Label | Color |
|---|---|---|---|
| 1 | End value of the highest end-value series among those currently checked on | "{series} end value" | `#ededed` |
| 2 | CAGR of same series | "CAGR · {series}" | `#ededed` |
| 3 | Max drawdown of same series (peak-to-trough from start year) | "Max drawdown · {series}" | `#e05252` (red) |
| 4 | Time window | "{start} → 2025" | `#ededed` |

**Fallback:** if all series are unchecked, show `—` in all value cards.

**Data source:** computed from `data/monthly_returns.parquet` — already loaded in `big_picture.py`. KPI values update when the start-year slider changes (they are inside the main render path, not cached separately).

**Card style:** `border: 1px solid #1c1c1c`, `background: #0f0f0f`, `border-radius: 6px`, `padding: 8px 12px`. Value: 13px, weight 600. Label: 8px, uppercase, `#555`, `letter-spacing: 0.06em`.

---

## Section 4 — Chart changes

**File:** `app/chart_main.py`

Changes only — do not restyle anything else:

1. **Remove legend:** `fig.update_layout(showlegend=False)`
2. **White chart background:** `fig.update_layout(paper_bgcolor="white", plot_bgcolor="white")`
3. **Reduce right margin:** current right margin is wide to accommodate the legend. Set `margin=dict(r=80)` to give end-of-line labels room without excess whitespace.
4. **Axis line colors:** set `gridcolor="#f0f0f0"` and `zerolinecolor="#e0e0e0"` so grid lines are subtle on the white background (they may already be correct — verify and adjust only if needed).

No other Plotly changes. Series colors, line weights, drawdown panel, FX band, macro band, event markers — all unchanged.

---

## Files changed

| File | Change type |
|---|---|
| `.streamlit/config.toml` | New — dark theme config |
| `app/big_picture.py` | Modified — CSS injection, sidebar HTML, KPI cards |
| `app/chart_main.py` | Modified — remove legend, set white bg, adjust margins |

**Not changed:** `data/`, `scripts/`, `tests/`, `app/annotations.py`, `poster_buildplan.md`.

---

## What this is NOT

- Not a redesign of the chart data or series — chart content is unchanged
- Not a multi-page Streamlit app — this is still a single-page app; the nav items are HTML with no routing
- Not mobile-optimised — that is out of scope for this pass
- Not a change to the allocation engine or any other planned feature

---

## Acceptance criteria

- [ ] App loads at `localhost:8502` with a dark page background and white chart area
- [ ] Streamlit Deploy button, hamburger, and footer are hidden
- [ ] Sidebar shows brand header, 4 nav items (1 active, 3 greyed), start-year slider, series checkboxes
- [ ] KPI cards update correctly when start-year slider changes
- [ ] Chart has no legend; end-of-line labels are readable; right margin is not excessive
- [ ] All existing chart interactions (hover, zoom, series toggle) still work
- [ ] `python -m pytest tests/ -v` passes unchanged
