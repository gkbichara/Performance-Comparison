import pandas as pd
import numpy as np
import os
from src.config import LEAGUES, SEASONS, LEAGUE_KEYS, DATA_DIR, CURRENT_SEASON


def calculate_points_home(df):
    """Calculate points for home team matches."""
    return np.where(
        df['FTHG'] > df['FTAG'], 3,  # Win
        np.where(df['FTHG'] == df['FTAG'], 1, 0)  # Draw or Loss
    )


def calculate_points_away(df):
    """Calculate points for away team matches."""
    return np.where(
        df['FTAG'] > df['FTHG'], 3,  # Win
        np.where(df['FTAG'] == df['FTHG'], 1, 0)  # Draw or Loss
    )


def split_by_venue(df, team_name):
    """
    Split a team's matches into home and away with opponent and points.
    
    Args:
        df: DataFrame with all matches for a team
        team_name: Name of the team
        
    Returns:
        home_df, away_df: DataFrames with Opponent, Venue, and Points columns added
    """
    # Home matches
    home = df[df['HomeTeam'] == team_name].copy()
    home['Opponent'] = home['AwayTeam']
    home['Venue'] = 'H'
    home['Points'] = calculate_points_home(home)
    
    # Away matches
    away = df[df['AwayTeam'] == team_name].copy()
    away['Opponent'] = away['HomeTeam']
    away['Venue'] = 'A'
    away['Points'] = calculate_points_away(away)
    
    return home, away


def compare_seasons(cur_season_df, prev_season_df, team_name):
    """
    Compare a team's performance across two seasons.
    
    Args:
        cur_season_df: Current season matches DataFrame
        prev_season_df: Previous season matches DataFrame
        team_name: Name of the team to analyze
        
    Returns:
        DataFrame with comparison results including differentials and cumulative totals
    """
    # Filter for this team
    cur_team = cur_season_df[(cur_season_df['HomeTeam'] == team_name) | 
                              (cur_season_df['AwayTeam'] == team_name)]
    prev_team = prev_season_df[(prev_season_df['HomeTeam'] == team_name) | 
                                (prev_season_df['AwayTeam'] == team_name)]
    
    # Split by venue for both seasons
    cur_home, cur_away = split_by_venue(cur_team, team_name)
    prev_home, prev_away = split_by_venue(prev_team, team_name)
    
    # Merge home games (current with previous on Opponent)
    home_comparison = pd.merge(
        cur_home[['Date', 'Opponent', 'Venue', 'FTHG', 'FTAG', 'Points']],
        prev_home[['Opponent', 'Points']],
        on='Opponent',
        how='left',
        suffixes=('_cur', '_prev')
    )
    
    # Merge away games (current with previous on Opponent)
    away_comparison = pd.merge(
        cur_away[['Date', 'Opponent', 'Venue', 'FTHG', 'FTAG', 'Points']],
        prev_away[['Opponent', 'Points']],
        on='Opponent',
        how='left',
        suffixes=('_cur', '_prev')
    )
    
    # Concatenate home and away
    all_comparisons = pd.concat([home_comparison, away_comparison], ignore_index=True)
    
    # Sort by date to see chronological progression
    all_comparisons['Date'] = pd.to_datetime(all_comparisons['Date'], format='%d/%m/%Y')
    all_comparisons = all_comparisons.sort_values('Date').reset_index(drop=True)
    
    # Remove promoted/relegated teams (NaN in previous season)
    all_comparisons = all_comparisons.dropna(subset=['Points_prev'])
    
    # Add match number for this team (1, 2, 3...)
    all_comparisons['Match_Number'] = range(1, len(all_comparisons) + 1)
    
    # Determine match result (W/D/L) for current season
    def determine_result(row):
        if row['Venue'] == 'H':
            if row['FTHG'] > row['FTAG']:
                return 'W'
            if row['FTHG'] == row['FTAG']:
                return 'D'
            return 'L'
        else:
            if row['FTAG'] > row['FTHG']:
                return 'W'
            if row['FTAG'] == row['FTHG']:
                return 'D'
            return 'L'

    all_comparisons['Result'] = all_comparisons.apply(determine_result, axis=1)

    # Calculate differential
    all_comparisons['Differential'] = all_comparisons['Points_cur'] - all_comparisons['Points_prev']
    
    # Calculate cumulative differential
    all_comparisons['Cumulative'] = all_comparisons['Differential'].cumsum()
    
    # Add team name column
    all_comparisons['Team'] = team_name
    
    return all_comparisons


def analyze_league(cur_season_df, prev_season_df):
    """
    Analyze all teams in a league across two seasons.
    
    Args:
        cur_season_df: Current season matches DataFrame
        prev_season_df: Previous season matches DataFrame
        
    Returns:
        DataFrame with all teams' comparisons
    """
    # Get unique teams from current season
    teams_home = set(cur_season_df['HomeTeam'].unique())
    teams_away = set(cur_season_df['AwayTeam'].unique())
    all_teams = sorted(teams_home | teams_away)
    
    # Compare each team
    all_results = []
    for team in all_teams:
        try:
            team_comparison = compare_seasons(cur_season_df, prev_season_df, team)
            all_results.append(team_comparison)
        except Exception as e:
            print(f"Warning: Could not analyze {team}: {e}")
    
    # Concatenate all results
    league_comparison = pd.concat(all_results, ignore_index=True)
    
    return league_comparison


def get_latest_standings(league_comparison_df):
    """
    Get the latest cumulative differential for each team.
    
    Args:
        league_comparison_df: DataFrame from analyze_league()
        
    Returns:
        DataFrame with teams ranked by cumulative differential
    """
    # Get the most recent match for each team (latest cumulative)
    latest = league_comparison_df.groupby('Team').last().reset_index()
    latest = latest[['Team', 'Cumulative']].sort_values('Cumulative', ascending=False)
    latest['Rank'] = range(1, len(latest) + 1)
    
    return latest[['Rank', 'Team', 'Cumulative']]


def save_league_results(league_comparison_df, league_folder, season):
    """
    Save league comparison results to CSV.
    
    Args:
        league_comparison_df: DataFrame from analyze_league()
        league_folder: Path to league folder (e.g., 'data/serie_a')
    """
    output_path = os.path.join(league_folder, f"results_{season}.csv")
    
    # Select and order columns nicely
    columns = ['Season', 'Team', 'Match_Number', 'Date', 'Opponent', 'Venue', 'Result',
               'FTHG', 'FTAG', 'Points_cur', 'Points_prev', 'Differential', 'Cumulative']
    
    # Save to CSV
    league_comparison_df[columns].to_csv(output_path, index=False)
    print(f"✓ Saved results to {output_path}")

    # Keep a canonical "current season" file for convenience
    if season == CURRENT_SEASON:
        alias_path = os.path.join(league_folder, "results.csv")
        league_comparison_df[columns].to_csv(alias_path, index=False)
        print(f"   ↳ Updated {alias_path}")


def main():
    """Main execution function."""
    print("=" * 60)
    print("FOOTBALL PERFORMANCE COMPARISON - SEASON DIFFERENTIALS")
    print("=" * 60)

    for season_idx in range(1, len(SEASONS)):
        prev_season = SEASONS[season_idx - 1]
        cur_season = SEASONS[season_idx]
        print(f"\n=== Season comparison: {prev_season} → {cur_season} ===")

        for idx, league_key in enumerate(LEAGUE_KEYS, 1):
            league_info = LEAGUES[league_key]
            display_name = league_info['display_name']
            folder = league_info['folder']
            league_path = os.path.join(DATA_DIR, folder)

            print(f"\n[{idx}/{len(LEAGUE_KEYS)}] {display_name}")

            try:
                prev = pd.read_csv(os.path.join(league_path, f"{prev_season}.csv"))
                cur = pd.read_csv(os.path.join(league_path, f"{cur_season}.csv"))
            except FileNotFoundError:
                print(f"   ⚠ Skipped: Missing CSV files for {display_name} ({prev_season}/{cur_season})")
                continue

            results = analyze_league(cur, prev)
            results['Season'] = cur_season
            save_league_results(results, league_path, cur_season)

            standings = get_latest_standings(results)
            print(f"   Top: {standings.iloc[0]['Team']} ({standings.iloc[0]['Cumulative']:+.0f})")
            print(f"   Bottom: {standings.iloc[-1]['Team']} ({standings.iloc[-1]['Cumulative']:+.0f})")

    print("\n" + "=" * 60)
    print("Analysis complete! Results saved to data/[League]/results_<season>.csv (plus results.csv for the current season)")
    print("=" * 60)


if __name__ == "__main__":
    main()