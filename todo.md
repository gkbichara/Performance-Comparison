# 🧾 Roadmap — The Gaffer’s Notebook

A living plan for the data platform. Use this to track what’s done, what’s in-flight, and what’s coming next.

---

## ✅ Foundation (Complete)
- Built YoY fixture-differential engine with promoted/relegated filtering
- Expanded to all Top 5 European leagues (team CSVs + Supabase uploads)
- Added Understat player contribution pipeline (goals + assists + percentages)
- Automated nightly runs (GitHub Actions + Supabase secrets + log artifacts)
- Refactored repo into `src/` package and documented `python -m src.*` commands

---

## 🚧 Active Focus
- [ ] Add Makefile targets (`run`, `scrape`, `lint`, `format`)
- [ ] Document `.env` creation + Supabase secret setup in README / onboarding notes
- [x] Refresh README with new branding + structure

---

## 🎯 Near-Term Backlog
- [ ] Extend `SEASONS` / `UNDERSTAT_SEASON_MAP` to include 23/24 and 22/23
- [ ] Re-run team YoY differentials for each season pair and store `season_pair` metadata in Supabase
- [ ] Capture player xG (`player_xg`, `team_xg`, `%_of_team_xg`) from Understat
- [ ] Persist `team_goals` alongside every player row for easier aggregation
- [ ] Backfill Supabase with the new columns + historical seasons
- [ ] Add email/Slack notification when GitHub Action fails

---

## ♟️ Advanced Analytics (Planned)
- [ ] Implement Elo rating model per league (match-level pre/post ratings)
- [ ] Create `elo_history` table (date, opponents, pre/post ratings, result, K-factor)
- [ ] Create `elo_current` snapshot table (latest rating per team/league/season)
- [ ] Upload Elo data during nightly pipeline run

---

## 🌐 Frontend & Visualization (Later)
- [ ] Choose stack (Streamlit prototype vs Next.js + Supabase Auth)
- [ ] Build league/team explorer that queries Supabase REST API
- [ ] Visualize player contribution trends, Elo trajectories, YoY differential charts

---

## 🧪 Testing & QA (Later)
- [ ] Unit tests for `analyze_league`, Understat aggregation, Supabase formatters
- [ ] Integration smoke test that runs `python -m src.main` on sample data and validates DB schemas
- [ ] Regression fixtures for YoY differential logic and Elo calculations

---

## 📅 Progress Tracker
| Date | Milestone | Status |
|------|-----------|--------|
| 2025‑10‑08 | Initial repo setup + Serie A prototype | ✅ |
| 2025‑10‑10 | Top 5 leagues integrated, automation scripts | ✅ |
| 2025‑10‑26 | Cron/logging hardening | ✅ |
| 2025‑11‑11 | GitHub Actions + Supabase pipeline | ✅ |
| 2025‑11‑12 | `src/` refactor + documentation refresh | ✅ |
| 2025‑12 | Dashboard / frontend work | ☐ Pending |

---

**Author:** Galal Bichara  
**Inspiration:** [@DrRitzyy](https://x.com/DrRitzyy/status/1972362982484271109) — “same fixtures, new season” analytics  

