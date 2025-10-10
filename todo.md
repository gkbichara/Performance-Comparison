# 🧾 TODO — Season Differentials Project

A running list of features, improvements, and checkpoints for the project.

---

## ✅ Phase 1 — Setup & One-Team Prototype (Serie A)
- [x] Create initial project structure (`analysis.py`, `scraper.py`, data files)
- [x] Load Serie A 2024/25 and 2025/26 data (from football-data.co.uk)
- [x] Normalize team names (handled implicitly via exact match)
- [x] Write helper to compute result → points (3/1/0)
- [x] Implement function to find equivalent fixtures (same opponent + venue)
- [x] Exclude promoted and relegated teams from comparison
- [x] Compute per-fixture differentials (points_25_26 – points_24_25)
- [x] Build cumulative differential by GW for one team (Roma)
- [ ] Visualize line plot (cumulative diff vs GW)
- [x] Verify output manually for Roma

---

## 🧩 Phase 2 — League-Wide Extension (Serie A)
- [x] Generalize logic for all Serie A teams
- [x] Create per-league leaderboard: overperformers vs underperformers
- [ ] Plot cumulative differentials for all teams on one chart
- [ ] Export CSV summaries (`per_fixture_differentials.csv`, `cumulative_differentials.csv`)
- [ ] Add league-level summary bar chart for latest GW
- [x] Refactor into reusable functions (modular architecture)

---

## 🕸️ Phase 2.5 — Web Scraping & Automation Setup
- [x] Build `scraper.py` to fetch latest CSV files from football-data.co.uk
- [x] Create league URL mapping (Serie A, Premier League, La Liga, etc.)
- [x] Implement download and update logic for current season data
- [x] Add error handling and retry logic
- [x] Create automated update script (`run_update.sh`)
- [x] Set up cron job for twice-weekly execution (Mon & Thu 9 AM)
- [x] Implement logging system for monitoring
- [x] Install web scraping dependencies (requests, beautifulsoup4, selenium)

---

## 🌍 Phase 3 — Multi-League Expansion (Top 5 Leagues)
- [x] Collect Serie A datasets (2024/25–2025/26) ✓
- [x] Collect datasets for Premier League, La Liga, Bundesliga, Ligue 1 ✓
- [x] Apply normalization across leagues (handled via direct CSV structure)
- [x] Run comparison logic for all leagues
- [x] Export CSV results for each league (`data/[League]/results.csv`)
- [ ] Merge into one global dashboard/table
- [ ] Add simple filter for league/team in notebooks or Streamlit app

---

## 📈 Phase 4 — Advanced Metrics
- [ ] Integrate goal difference differential
- [ ] Add expected goals (xG) differential (Understat API)
- [ ] Include Strength of Schedule adjustment (last-season finish or ELO)
- [ ] Highlight fixtures with biggest point swings (+3 or –3)
- [ ] Add rolling chart to show trend per team over recent GWs

---

## 🧠 Phase 5 — Automation & Deployment
- [x] Automate weekly data updates (via cron job - Mon & Thu 9 AM)
- [x] Automatically pull new results and recompute metrics
- [x] Logging system for monitoring execution
- [ ] Publish updated charts weekly (e.g., `/plots/week_X.png`)
- [ ] Optional: post summary chart to X/Twitter
- [ ] Optional: Deploy via GitHub Actions for cloud automation

---

## 💄 Phase 6 — Documentation & Polish
- [x] Write detailed docstrings for each function
- [x] Add setup instructions in `requirements.txt` 
- [ ] Refine README with latest plots and results
- [ ] Add references section (data sources, credits)
- [ ] Final QA pass before sharing or publishing results

---

## 🧩 Optional Stretch Ideas
- [ ] Create an interactive Streamlit dashboard (filters by team, league, GW)
- [ ] Compare goal differentials and xG swings side-by-side
- [ ] Add support for domestic cups or continental competitions
- [ ] Historical mode (compare 3–5 past seasons instead of just 2)
- [ ] “Manager impact” mode — show differential before and after manager changes

---

## 📅 Progress Tracker
| Date | Milestone | Status |
|------|------------|--------|
| 2025-10-08 | Initial repo setup | ✅ Complete |
| 2025-10-08 | One-team prototype (Roma) | ✅ Complete |
| 2025-10-08 | Full Serie A analysis | ✅ Complete |
| 2025-10-08 | Refactored to modular functions | ✅ Complete |
| 2025-10-10 | Web scraper development | ✅ Complete |
| 2025-10-10 | Top 5 leagues integration | ✅ Complete |
| 2025-10-10 | CSV export system | ✅ Complete |
| 2025-10-10 | Cron automation setup | ✅ Complete |
| 2025-10-10 | Logging system | ✅ Complete |
| 2025-11 | Visualization & plotting | ☐ Pending |
| 2025-12 | Dashboard development | ☐ Pending |

---

**Author:** Galal Bichara  
**Inspiration:** [@DrRitzyy](https://x.com/DrRitzyy/status/1972362982484271109) — “same fixtures, new season” analytics  
