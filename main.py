import os
import pandas as pd

from scraper import main as run_scraper
from analysis import analyze_league, save_league_results, get_latest_standings
from understat_scraper import calculate_contributions, save_player_results
from config import (
    LEAGUE_KEYS,
    LEAGUES,
    DATA_DIR,
    PREVIOUS_SEASON,
    CURRENT_SEASON,
    SEASONS,
)
from database import update_player_stats, update_team_stats

def main():
    print("="*60)
    print("FOOTBALL DATA PIPELINE - Starting")
    print("="*60)
    
    # Step 1: Scrape football-data.co.uk (team data)
    print("\n[1/3] Scraping team data...")
    try:
        run_scraper()
    except Exception as e:
        print(f"Scraper failed: {e}")
        print("→ Using existing data for analysis")
    
    # Step 2: Run YoY analysis & upload team stats
    print("\n[2/3] Running YoY analysis...")
    try:
        for idx, league_key in enumerate(LEAGUE_KEYS, 1):
            league_info = LEAGUES[league_key]
            display_name = league_info['display_name']
            folder = league_info['folder']
            league_path = os.path.join(DATA_DIR, folder)
            prev_path = os.path.join(league_path, f"{PREVIOUS_SEASON}.csv")
            cur_path = os.path.join(league_path, f"{CURRENT_SEASON}.csv")

            print(f"\n[{idx}/{len(LEAGUE_KEYS)}] Analyzing {display_name}...")
            try:
                prev_df = pd.read_csv(prev_path)
                cur_df = pd.read_csv(cur_path)
            except FileNotFoundError:
                print(f"   ⚠ Skipped: Missing CSV files for {display_name}")
                continue

            results_df = analyze_league(cur_df, prev_df)
            save_league_results(results_df, league_path)

            standings = get_latest_standings(results_df)
            print(f"   Top: {standings.iloc[0]['Team']} ({standings.iloc[0]['Cumulative']:+.0f})")
            print(f"   Bottom: {standings.iloc[-1]['Team']} ({standings.iloc[-1]['Cumulative']:+.0f})")

            update_team_stats(league_key, CURRENT_SEASON, results_df)
    except Exception as e:
        print(f"Analysis failed: {e}")
    
    # Step 3: Scrape Understat (player data - independent)
    print("\n[3/3] Fetching player contribution data...")
    try:
        for season in SEASONS:
            print(f"\nSeason {season}:")
            for league_key in LEAGUE_KEYS:
                contributions = calculate_contributions(league_key, season)
                save_player_results(contributions, league_key, season)

                # Upload to Supabase
                update_player_stats(league_key, season, contributions)

    except Exception as e:
        print(f"Understat scraper failed: {e}")
    
    print("\n" + "="*60)
    print("Pipeline complete!")
    print("="*60)


if __name__ == "__main__":
    main()