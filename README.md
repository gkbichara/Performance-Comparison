# ⚽ Season Differentials — Real-Time Team Over/Underperformance Tracker

## Overview

**Season Differentials** is a data project that compares how every football (soccer) team across **Europe's Top 5 Leagues** is performing this season versus the same stage last season.

Instead of just showing current league tables, this tool measures *how much better or worse* each team is doing **against the same opponents and venues** they faced last year.

**Leagues Covered:**
- 🇮🇹 Serie A
- 🏴 Premier League  
- 🇪🇸 La Liga
- 🇩🇪 Bundesliga
- 🇫🇷 Ligue 1

For example:
> Arsenal drew 1–1 at Anfield last year but won 2–0 there this season — that fixture is worth **+2 points differential**.

By computing this for every team and aggregating across gameweeks, the project reveals which clubs are the biggest **overperformers** and **underperformers** relative to last year.

---

## 🔍 What It Does

For each team and gameweek:

1. **Match equivalence:** Find this season’s fixtures that have an exact equivalent last season (same opponent + same venue).
2. **Compute points:** Assign 3/1/0 for win/draw/loss for both seasons.
3. **Per-fixture differential:**  
   \[
   \text{Differential} = \text{Points}_{25/26} - \text{Points}_{24/25}
   \]
4. **Cumulative differential:** Track the running total through each gameweek.
5. **League-wide view:** Identify biggest over- and underperformers week by week.

Fixtures involving newly promoted or relegated teams are **excluded** to avoid biasing comparisons.

---

## 🧩 Example

| Opponent | Venue | 24/25 Result | 25/26 Result | 24/25 Pts | 25/26 Pts | Diff |
|-----------|--------|--------------|--------------|------------|------------|------|
| Newcastle | A | D | W | 1 | 3 | +2 |
| Liverpool | H | L | D | 0 | 1 | +1 |
| Fulham    | A | W | L | 3 | 0 | -3 |

**Cumulative Differential:** **0** after 3 GWs (overperformers and underperformers cancel out)

---

## 🛠️ Project Structure

```
Performance-Comparison/
├── analysis.py              # Main analysis script
├── scraper.py              # Data fetching from football-data.co.uk
├── run_update.sh           # Automated update script (cron job)
├── requirements.txt        # Python dependencies
├── data/
│   ├── SerieA/
│   │   ├── 2425.csv       # Historical season data
│   │   ├── 2526.csv       # Current season data
│   │   └── results.csv    # Analysis output
│   ├── PremierLeague/
│   ├── LaLiga/
│   ├── Bundesliga/
│   └── Ligue1/
├── logs/                   # Execution logs from automated runs
└── README.md
```

### Data Source
All match data is sourced from [football-data.co.uk](https://www.football-data.co.uk/), which provides comprehensive historical results and statistics for major European leagues.

The script automatically:
- Fetches latest data via `scraper.py`
- Computes points for both home and away sides (W=3, D=1, L=0)
- Matches equivalent fixtures (same opponent + venue)
- Excludes promoted/relegated teams to ensure fair comparisons

---

## 🧮 Outputs

Each league produces a `results.csv` file in `data/[League]/` containing:

| Column | Description |
|--------|-------------|
| `Team` | Team name |
| `Match_Number` | Sequential match number (1, 2, 3...) |
| `Date` | Match date |
| `Opponent` | Opposition team |
| `Venue` | Home (H) or Away (A) |
| `FTHG` / `FTAG` | Full-time goals (home/away) |
| `Points_cur` | Points earned this season |
| `Points_prev` | Points earned last season (same fixture) |
| `Differential` | Points difference (cur - prev) |
| `Cumulative` | Running total of differentials |

### Example Output (Roma):
```
Team  Match_Number  Opponent    Differential  Cumulative
Roma  1             Bologna     +3.0          +3.0
Roma  2             Torino      -3.0          0.0
Roma  3             Lazio       +2.0          +2.0
Roma  4             Verona      0.0           +2.0
Roma  5             Fiorentina  +3.0          +5.0
```

---

## 🚀 How to Use

### 1. Setup

```bash
# Clone the repo
git clone https://github.com/galalbichara/season-differentials.git
cd Performance-Comparison

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Download Latest Data

```bash
python scraper.py
```

This fetches the latest match data for all 5 leagues from football-data.co.uk.

### 3. Run Analysis

```bash
python analysis.py
```

Output:
```
============================================================
FOOTBALL PERFORMANCE COMPARISON - SEASON DIFFERENTIALS
============================================================

[1/5] Analyzing Serie A...
✓ Saved results to data/SerieA/results.csv
   Top: Cagliari (+5)
   Bottom: Fiorentina (-7)

[2/5] Analyzing Premier League...
...
```

### 4. View Results

Results are saved in `data/[League]/results.csv` files. Open with any spreadsheet application or pandas:

```python
import pandas as pd

# Load Serie A results
df = pd.read_csv('data/SerieA/results.csv')

# View Roma's performance
roma = df[df['Team'] == 'Roma']
print(roma[['Match_Number', 'Opponent', 'Differential', 'Cumulative']])
```

### 5. Automation (Optional)

The project includes automated updates via cron job:

```bash
# View current schedule
crontab -l

# Edit schedule
crontab -e
```

**Default Schedule:** Twice weekly (Monday & Thursday at 9 AM)
```
0 9 * * 1,4 /Users/gkb/Desktop/Performance-Comparison/run_update.sh
```

**Check Logs:**
```bash
# View latest execution log
ls -t logs/ | head -1 | xargs -I {} cat logs/{}

# Monitor logs directory
tail -f logs/update_*.log
```

The `run_update.sh` script:
- ✅ Activates virtual environment
- ✅ Runs scraper to fetch latest data
- ✅ Runs analysis on all leagues
- ✅ Logs all output with timestamps
- ✅ Keeps last 10 log files automatically

---

## 📊 Current Results (2025/26 vs 2024/25)

### Top Performers by League

| League | Best Team | Differential | Worst Team | Differential |
|--------|-----------|-------------|------------|-------------|
| 🇮🇹 Serie A | Cagliari | +5 | Fiorentina | -7 |
| 🏴 Premier League | Bournemouth | +8 | Brighton | -9 |
| 🇪🇸 La Liga | Espanol | +6 | Celta | -7 |
| 🇩🇪 Bundesliga | Stuttgart | +8 | Freiburg | -7 |
| 🇫🇷 Ligue 1 | Lyon | +6 | Nantes | -5 |

*Data as of October 2025*

---

## 🎯 Key Features

✅ **Multi-League Coverage** - Analyzes all Top 5 European leagues  
✅ **Match-by-Match Tracking** - See progression through the season  
✅ **Fair Comparisons** - Same opponent, same venue only  
✅ **Automated Data Fetching** - Built-in scraper for football-data.co.uk  
✅ **Scheduled Updates** - Cron job runs twice weekly (Mon & Thu 9 AM)  
✅ **Comprehensive Logging** - All executions tracked with timestamps  
✅ **CSV Exports** - Easy to analyze in Excel, pandas, or other tools  
✅ **Promoted Team Handling** - Automatically excludes teams without comparison data

---

## 🔮 Coming Soon

- 📊 Visualization dashboard with line plots and bar charts
- 🌐 Interactive web interface with team/league filters
- 📈 Additional metrics (goal differential, xG comparison)
- ☁️ Cloud deployment via GitHub Actions
- 📱 Mobile-friendly dashboard
- 🐦 Automated Twitter/X posts with weekly summaries

---

## 🙏 Credits

**Author:** Galal Bichara  
**Data Source:** [football-data.co.uk](https://www.football-data.co.uk/)  
**Inspiration:** [@DrRitzyy](https://x.com/DrRitzyy/status/1972362982484271109) — "same fixtures, new season" analytics

---

## 📄 License

This project is open source and available for educational and personal use.
