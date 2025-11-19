import os
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError("Missing Supabase credentials in .env file")

supabase: Client = create_client(url, key)

def get_db():
    
    return supabase


def update_player_stats(league_key, season, player_data_list):
    """
    Upserts player stats into Supabase.
    
    Args:
        league_key: e.g. 'serie_a'
        season: e.g. '2526'
        player_data_list: List of dicts from understat_scraper
    """
    client = get_db()
    
    # Prepare data for Supabase (match columns to SQL table)
    records = []
    for p in player_data_list:
        record = {
            "league": league_key,
            "season": season,
            "player_name": p['player'],
            "team": p['team'],
            "goals": p['goals'],
            "assists": p['assists'],
            "contributions": p['contributions'],
            "contribution_pct": p['contribution_pct'],
            "goals_pct": p['goals_pct'],
            "assists_pct": p['assists_pct'],
            "games_played": p['games'],
            # updated_at defaults to NOW() in SQL, but we can force it here too if we want
        }
        records.append(record)
        
    # Perform Upsert
    # on_conflict matches the UNIQUE constraint we created in SQL
    try:
        response = client.table("player_stats").upsert(records, on_conflict="player_name, team, league, season").execute()
        print(f"   ✓ Uploaded {len(records)} records to Supabase")
        return True
    except Exception as e:
        print(f"   ✗ Database Upload Failed: {e}")
        return False

    

def update_team_stats(league_key, season, results_df):
    """
    Upserts team stats into Supabase.
    
    Args:
        league_key: e.g. 'serie_a'
        season: e.g. '2526'
        results_df: DataFrame from analyze_league()
    """
    client = get_db()
    
    # Convert DataFrame to list of dicts
    # Replace NaN with None for SQL compatibility
    records = []
    
    for _, row in results_df.iterrows():
        # Handle NaN values safely
        def clean(val):
            return None if pd.isna(val) else val

        record = {
            "league": league_key,
            "season": season,
            "team_name": row['Team'],
            "match_number": int(row['Match_Number']),
            "date": str(row['Date'].date()) if pd.notna(row['Date']) else None,
            "opponent": row['Opponent'],
            "venue": row['Venue'],
            "goals_for": int(row['FTHG']) if row['Venue'] == 'H' else int(row['FTAG']),
            "goals_against": int(row['FTAG']) if row['Venue'] == 'H' else int(row['FTHG']),
            "points_current": int(row['Points_cur']),
            "points_previous": int(row['Points_prev']) if pd.notna(row['Points_prev']) else None,
            "differential": int(row['Differential']) if pd.notna(row['Differential']) else None,
            "cumulative_differential": int(row['Cumulative']) if pd.notna(row['Cumulative']) else None,
        }
        records.append(record)
        
    # Perform Upsert (batch in chunks if necessary, but 1000 rows is fine for Supabase)
    try:
        # Supabase has a request size limit, so let's chunk it if it's huge
        chunk_size = 1000
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            client.table("team_stats").upsert(chunk, on_conflict="team_name, match_number, league, season").execute()
            
        print(f"   ✓ Uploaded {len(records)} team match records to Supabase")
        return True
    except Exception as e:
        print(f"   ✗ Team Stats Upload Failed: {e}")
        return False