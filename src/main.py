import os
import pandas as pd

from src.scrapers.matches import main as run_scraper
from src.analysis.teams import analyze_league, save_league_results, get_latest_standings
from src.analysis.elo import EloTracker
from src.scrapers.understat import fetch_understat_data
from src.analysis.players import process_league_players, save_player_results
from src.config import (
    LEAGUE_KEYS,
    LEAGUES,
    DATA_DIR,
    SEASONS,
)
from src.database import update_player_stats, update_team_stats

def main():
    print("="*60)
    print("FOOTBALL DATA PIPELINE - Starting")
    print("="*60)
    
    # Step 1: Scrape football-data.co.uk (team data)
    # By default, this now only scrapes the CURRENT season
    print("\n[1/3] Scraping team data...")
    try:
        run_scraper()
    except Exception as e:
        print(f"Scraper failed: {e}")
        print("→ Using existing data for analysis")
    
    # Initialize ELO Tracker (Global across all leagues/seasons)
    elo_tracker = EloTracker()

    # Step 2: Run ELO & YoY analysis
    print("\n[2/3] Running Analysis (ELO + YoY)...")
    try:
        # 2a. ELO Calculation (Must run chronologically from start of history)
        print("\n--- Updating ELO Ratings ---")
        for season in SEASONS:
            # We process ALL leagues for a season before moving to next season
            # (Strictly speaking, dates overlap, but processing by season-block is close enough)
            for league_key in LEAGUE_KEYS:
                league_info = LEAGUES[league_key]
                folder = league_info['folder']
                file_path = os.path.join(DATA_DIR, folder, f"{season}.csv")
                
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    elo_tracker.process_league_season(df, season, league_key)
        
        # Save current ELO ratings
        print("\nSaving ELO Ratings...")
        for league_key in LEAGUE_KEYS:
             league_info = LEAGUES[league_key]
             folder = league_info['folder']
             
             # Let's save a league-specific ELO table by filtering for teams present in current season CSV
             cur_path = os.path.join(DATA_DIR, folder, f"{SEASONS[-1]}.csv")
             if os.path.exists(cur_path):
                 cur_df = pd.read_csv(cur_path)
                 current_teams = set(cur_df['HomeTeam'].unique()) | set(cur_df['AwayTeam'].unique())
                 
                 all_ratings = elo_tracker.get_current_ratings_df()
                 league_ratings = all_ratings[all_ratings['Team'].isin(current_teams)].copy()
                 league_ratings['Rank'] = range(1, len(league_ratings) + 1) # Re-rank locally
                 
                 elo_path = os.path.join(DATA_DIR, folder, "elo_ratings.csv")
                 league_ratings.to_csv(elo_path, index=False)
                 print(f"   ✓ {league_info['display_name']}: Saved {elo_path}")
        
        # Save Match-by-Match ELO History (for ML)
        history_path = os.path.join(DATA_DIR, "elo_match_history.csv")
        history_df = elo_tracker.get_history_df()
        history_df.to_csv(history_path, index=False)
        print(f"   ✓ Global: Saved full ELO history to {history_path} ({len(history_df)} matches)")

        # 2b. YoY Analysis (Compare adjacent seasons)
        print("\n--- Running YoY Differentials ---")
        for season_idx in range(1, len(SEASONS)):
            prev_season = SEASONS[season_idx - 1]
            cur_season = SEASONS[season_idx]
            print(f"\n=== Season comparison: {prev_season} → {cur_season} ===")

            for idx, league_key in enumerate(LEAGUE_KEYS, 1):
                league_info = LEAGUES[league_key]
                display_name = league_info['display_name']
                folder = league_info['folder']
                league_path = os.path.join(DATA_DIR, folder)
                prev_path = os.path.join(league_path, f"{prev_season}.csv")
                cur_path = os.path.join(league_path, f"{cur_season}.csv")

                try:
                    prev_df = pd.read_csv(prev_path)
                    cur_df = pd.read_csv(cur_path)
                except FileNotFoundError:
                    continue

                results_df = analyze_league(cur_df, prev_df)
                results_df['Season'] = cur_season
                save_league_results(results_df, league_path, cur_season)
                
                update_team_stats(league_key, cur_season, results_df)
                
    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 3: Scrape Understat (player data - independent)
    print("\n[3/3] Fetching player contribution data...")
    try:
        for season in SEASONS:
            print(f"\nSeason {season}:")
            for league_key in LEAGUE_KEYS:
                # New modular flow
                players_raw, team_goals = fetch_understat_data(league_key, season)
                contributions = process_league_players(players_raw, team_goals, season)
                
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
