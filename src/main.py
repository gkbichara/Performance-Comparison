import os
import argparse
import time

from src.scrapers.matches import main as run_scraper
from src.analysis.teams import analyze_league, save_league_results, get_latest_standings
from src.analysis.elo import run_incremental_elo
from src.scrapers.understat import fetch_understat_data, get_team_match_xg
from src.analysis.players import process_league_players, save_player_results
from src.config import (
    LEAGUE_KEYS,
    LEAGUES,
    DATA_DIR,
    SEASONS,
    CURRENT_SEASON,
)
from src.database import update_player_stats, update_team_stats, update_understat_team_matches, get_matches_for_analysis


def main(full_backfill=False):
    # Determine which seasons to process
    if full_backfill:
        seasons_to_process = SEASONS
        mode = "FULL BACKFILL"
    else:
        seasons_to_process = [CURRENT_SEASON]
        mode = "CURRENT SEASON ONLY"
    
    print("="*60)
    print(f"FOOTBALL DATA PIPELINE - {mode}")
    print("="*60)
    print(f"Seasons: {', '.join(seasons_to_process)}")
    print("="*60)
    
    # Step 1: Scrape football-data.co.uk (team data)
    # By default, this now only scrapes the CURRENT season
    print("\n[1/3] Scraping team data...")
    try:
        run_scraper()
    except Exception as e:
        print(f"Scraper failed: {e}")
        print("→ Using existing data for analysis")
    
    # Step 2: Run ELO & YoY analysis
    print("\n[2/3] Running Analysis (ELO + YoY)...")
    try:
        # 2a. Incremental ELO (uses database)
        run_incremental_elo()

        # 2b. YoY Analysis (Compare adjacent seasons, using DB)
        print("\n--- Running YoY Differentials ---")
        for season_idx in range(1, len(SEASONS)):
            prev_season = SEASONS[season_idx - 1]
            cur_season = SEASONS[season_idx]
            print(f"\n=== Season comparison: {prev_season} → {cur_season} ===")

            for idx, league_key in enumerate(LEAGUE_KEYS, 1):
                league_info = LEAGUES[league_key]
                folder = league_info['folder']
                league_path = os.path.join(DATA_DIR, folder)

                # Query from database
                prev_df = get_matches_for_analysis(league_key, prev_season)
                cur_df = get_matches_for_analysis(league_key, cur_season)
                
                if len(prev_df) == 0 or len(cur_df) == 0:
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
    print("\n[3/4] Fetching player contribution data...")
    try:
        for season in seasons_to_process:
            print(f"\nSeason {season}:")
            for league_key in LEAGUE_KEYS:
                # New modular flow
                players_raw, team_goals = fetch_understat_data(league_key, season)
                contributions = process_league_players(players_raw, team_goals, season)
                
                save_player_results(contributions, league_key, season)

                # Upload to Supabase
                update_player_stats(league_key, season, contributions)
                
                time.sleep(1)  # Rate limiting

    except Exception as e:
        print(f"Understat scraper failed: {e}")
    
    # Step 4: Scrape Understat xG data (team match-level)
    print("\n[4/4] Fetching xG match data...")
    try:
        for season in seasons_to_process:
            print(f"\nSeason {season}:")
            for league_key in LEAGUE_KEYS:
                matches = get_team_match_xg(league_key, season)
                
                if matches:
                    update_understat_team_matches(league_key, season, matches)
                else:
                    print(f"   ⚠ No xG data for {league_key} {season}")
                
                time.sleep(1)  # Rate limiting

    except Exception as e:
        print(f"xG scraper failed: {e}")
    
    # Step 5: Generate match predictions
    print("\n[5/5] Generating match predictions...")
    try:
        from src.analysis.predictions import run_predictions_pipeline
        run_predictions_pipeline()
    except Exception as e:
        print(f"Predictions failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Pipeline complete!")
    print("="*60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Football Data Pipeline")
    parser.add_argument(
        "--full", 
        action="store_true", 
        help="Run full backfill for all seasons (default: current season only)"
    )
    args = parser.parse_args()
    
    main(full_backfill=args.full)
