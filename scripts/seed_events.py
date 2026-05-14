#!/usr/bin/env python3
"""
Write data/events.json — ~70 annotated events for the Big Picture chart.

Each event:
  date   : "YYYY-MM-DD" (first trading day of relevant month)
  text   : short label (≤ 30 chars)
  side   : "top" or "bottom" — alternated to reduce overlap

Run: python scripts/seed_events.py   (idempotent — overwrites each run)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT  = ROOT / "data" / "events.json"

EVENTS = [
    # ── 1950s ────────────────────────────────────────────────────────────────
    {"date": "1957-08-01", "text": "US recession '57–58",       "side": "top"},
    {"date": "1962-06-01", "text": "Kennedy Slide",              "side": "bottom"},
    {"date": "1963-11-01", "text": "JFK assassination",          "side": "top"},
    # ── 1970s ────────────────────────────────────────────────────────────────
    {"date": "1971-08-01", "text": "Bretton Woods ends",         "side": "bottom"},
    {"date": "1973-10-01", "text": "Arab oil embargo",           "side": "top"},
    {"date": "1974-08-01", "text": "Nixon resigns",              "side": "bottom"},
    {"date": "1975-01-01", "text": "Market recovery '75",        "side": "top"},
    {"date": "1979-01-01", "text": "Iranian revolution",         "side": "bottom"},
    {"date": "1979-10-01", "text": "Volcker rate shock",         "side": "top"},
    {"date": "1980-03-01", "text": "Silver Thursday",            "side": "bottom"},
    # ── 1980s ────────────────────────────────────────────────────────────────
    {"date": "1981-06-01", "text": "Prime rate 22.75%",          "side": "top"},
    {"date": "1982-08-01", "text": "Recession bottom '82",       "side": "bottom"},
    {"date": "1983-01-01", "text": "Bull market begins",         "side": "top"},
    {"date": "1987-10-01", "text": "Black Monday",               "side": "bottom"},
    {"date": "1989-01-01", "text": "S&L crisis",                 "side": "top"},
    # ── 1990s ────────────────────────────────────────────────────────────────
    {"date": "1990-08-01", "text": "Gulf War begins",            "side": "bottom"},
    {"date": "1991-03-01", "text": "Gulf War ends",              "side": "top"},
    {"date": "1993-02-01", "text": "CAD bond crisis",            "side": "bottom"},
    {"date": "1994-01-01", "text": "NAFTA begins",               "side": "top"},
    {"date": "1994-02-01", "text": "Bond massacre '94",          "side": "bottom"},
    {"date": "1994-12-01", "text": "Mexican peso crisis",        "side": "top"},
    {"date": "1995-10-01", "text": "Quebec referendum",          "side": "bottom"},
    {"date": "1997-07-01", "text": "Asian financial crisis",     "side": "top"},
    {"date": "1998-08-01", "text": "Russia default / LTCM",     "side": "bottom"},
    {"date": "1999-01-01", "text": "Y2K fears / tech peak",      "side": "top"},
    # ── 2000s ────────────────────────────────────────────────────────────────
    {"date": "2000-03-01", "text": "Dot-com peak",               "side": "bottom"},
    {"date": "2001-09-01", "text": "9/11",                       "side": "top"},
    {"date": "2001-12-01", "text": "Enron collapse",             "side": "bottom"},
    {"date": "2002-07-01", "text": "WorldCom bankrupt",          "side": "top"},
    {"date": "2003-03-01", "text": "Iraq War / market bottom",   "side": "bottom"},
    {"date": "2004-01-01", "text": "Recovery '04",               "side": "top"},
    {"date": "2007-08-01", "text": "Subprime crisis begins",     "side": "bottom"},
    {"date": "2008-03-01", "text": "Bear Stearns rescued",       "side": "top"},
    {"date": "2008-09-01", "text": "Lehman collapse",            "side": "bottom"},
    {"date": "2008-10-01", "text": "TARP enacted",               "side": "top"},
    {"date": "2009-03-01", "text": "Market bottom Mar '09",      "side": "bottom"},
    {"date": "2009-01-01", "text": "TFSA introduced (Canada)",   "side": "top"},
    # ── 2010s ────────────────────────────────────────────────────────────────
    {"date": "2010-05-01", "text": "Flash Crash",                "side": "bottom"},
    {"date": "2010-04-01", "text": "Greek debt crisis",          "side": "top"},
    {"date": "2011-08-01", "text": "US debt downgrade",          "side": "bottom"},
    {"date": "2011-09-01", "text": "European debt crisis",       "side": "top"},
    {"date": "2013-05-01", "text": "Taper tantrum",              "side": "bottom"},
    {"date": "2014-06-01", "text": "Oil price crash",            "side": "top"},
    {"date": "2015-08-01", "text": "China selloff",              "side": "bottom"},
    {"date": "2015-01-01", "text": "CAD below US dollar",        "side": "top"},
    {"date": "2016-06-01", "text": "Brexit vote",                "side": "bottom"},
    {"date": "2016-11-01", "text": "Trump elected",              "side": "top"},
    {"date": "2018-02-01", "text": "US-China trade war",         "side": "bottom"},
    {"date": "2018-12-01", "text": "Rate hike selloff",          "side": "top"},
    # ── 2020s ────────────────────────────────────────────────────────────────
    {"date": "2020-02-01", "text": "COVID crash",                "side": "bottom"},
    {"date": "2020-03-01", "text": "Fed QE unlimited",           "side": "top"},
    {"date": "2020-08-01", "text": "V-shaped recovery",          "side": "bottom"},
    {"date": "2021-01-01", "text": "Meme stocks (GME)",          "side": "top"},
    {"date": "2022-02-01", "text": "Ukraine invasion",           "side": "bottom"},
    {"date": "2022-03-01", "text": "BoC rate hikes begin",       "side": "top"},
    {"date": "2022-06-01", "text": "Inflation 8%+",              "side": "bottom"},
    {"date": "2022-11-01", "text": "FTX collapse",               "side": "top"},
    {"date": "2023-03-01", "text": "SVB collapse",               "side": "bottom"},
    {"date": "2024-06-01", "text": "BoC cuts rates",             "side": "top"},
    {"date": "2025-01-01", "text": "AI investment surge",        "side": "bottom"},
    # ── Canadian milestones ───────────────────────────────────────────────────
    {"date": "1980-10-01", "text": "National Energy Program",    "side": "top"},
    {"date": "1988-01-01", "text": "US-Canada FTA signed",       "side": "bottom"},
    {"date": "1995-02-01", "text": "CAD budget turnaround",      "side": "top"},
    # ── Market milestones ─────────────────────────────────────────────────────
    {"date": "1966-01-01", "text": "Dow 1,000",                  "side": "bottom"},
    {"date": "1999-03-01", "text": "Dow 10,000",                 "side": "top"},
    {"date": "2017-01-01", "text": "Dow 20,000",                 "side": "bottom"},
    {"date": "2024-05-01", "text": "Dow 40,000",                 "side": "top"},
]

if __name__ == "__main__":
    OUT.write_text(json.dumps(EVENTS, indent=2))
    print(f"Wrote {len(EVENTS)} events → {OUT.relative_to(ROOT)}")
