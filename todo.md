# Project To-Do List

## 🚨 High Priority / Refactoring
- [x] **Fix "God Object" Scrapers**: Split `scraper.py` and `understat_scraper.py` into distinct extraction and analysis modules.
  - [x] Create `src/scrapers/` and `src/analysis/`
  - [x] Refactor `scraper.py` → `src/scrapers/matches.py`
  - [x] Refactor `understat_scraper.py` → `src/scrapers/understat.py` + `src/analysis/players.py`
  - [x] Update `src/analysis.py` → `src/analysis/teams.py`
- [x] **Modularize Main**: Update `main.py` to use the new modular structure.
- [x] **Fix Virtual Environment**: Recreate venv to handle project folder rename.
- [x] **Update Documentation**: Ensure README and scripts reflect "Gaffer's Notebook" name.

## 📈 Analytics & Metrics
- [ ] **xG Differentials**: Incorporate Expected Goals (xG) into the YoY comparison.
  - *Goal:* "Are they winning lucky, or playing better?"
- [ ] **Player YoY Tracking**: Compare player output this season vs last season.
- [ ] **Opponent Difficulty**: Weight differentials based on opponent strength (e.g., beating City away is worth more than beating Luton at home).

## 🛠️ Infrastructure & Ops
- [x] **GitHub Actions**: Setup daily automated scraping.
- [x] **Supabase Integration**: Push results to a cloud database.
- [ ] **Error Monitoring**: Add Slack/Discord webhook alerts on pipeline failure.

## 📊 Visualization / Frontend
- [ ] **Streamlit Dashboard**: Build a simple interactive web app to browse results.
- [ ] **Trend Plots**: Visualize the `Cumulative` differential over time (line chart).
- [ ] **Scatter Plots**: Plot "Goals Scored vs xG" for player analysis.

## 🧹 Tech Debt / Clean Code
- [ ] **Type Hinting**: Add strict `mypy` types to all functions.
- [ ] **Unit Tests**: Add `pytest` coverage for the calculation logic in `src/analysis/`.
- [ ] **Async Scraping**: Use `aiohttp` if we expand to more leagues/seasons to speed up downloads.
