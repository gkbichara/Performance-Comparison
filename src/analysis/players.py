import os
import pandas as pd
from src.config import DATA_DIR, LEAGUES

def calculate_contribution_stats(player, team_total_goals):
    """
    Calculate contribution percentages for a single player.
    
    Args:
        player: Dict containing raw player stats (goals, assists, etc.)
        team_total_goals: Integer of total goals scored by the team
        
    Returns:
        Dict with calculated contribution metrics
    """
    goals = int(player['goals'])
    assists = int(player['assists'])
    total_contribs = goals + assists
    
    # Avoid division by zero
    if team_total_goals > 0:
        contribution_pct = (total_contribs / team_total_goals * 100)
        goals_pct = (goals / team_total_goals * 100)
        assists_pct = (assists / team_total_goals * 100)
    else:
        contribution_pct = 0
        goals_pct = 0
        assists_pct = 0
        
    return {
        'player': player['player_name'],
        'team': player['team_title'],
        'goals': goals,
        'assists': assists,
        'contributions': total_contribs,
        'contribution_pct': round(contribution_pct, 1),
        'goals_pct': round(goals_pct, 1),
        'assists_pct': round(assists_pct, 1),
        'games': int(player['games']),
    }


def process_league_players(all_players_raw, team_goals_dict, season_code):
    """
    Process raw player list into analyzed contribution stats.
    
    Args:
        all_players_raw: List of dicts from Understat scraper
        team_goals_dict: Dict mapping team names to total goals
        season_code: String season identifier (e.g., '2324')
        
    Returns:
        List of dicts sorted by contribution percentage
    """
    processed_stats = []
    
    for player in all_players_raw:
        player_team = player['team_title']
        
        # Skip multi-team players (business rule)
        if ',' in player_team:
            continue
            
        team_total = team_goals_dict.get(player_team, 0)
        
        stats = calculate_contribution_stats(player, team_total)
        stats['season'] = season_code
        
        processed_stats.append(stats)
        
    # Sort by contribution percentage descending
    processed_stats.sort(key=lambda x: x['contribution_pct'], reverse=True)
    
    return processed_stats


def save_player_results(contributions, league_key, season_code):
    """
    Save player contributions to CSV.
    
    Args:
        contributions: List of player contribution dicts
        league_key: League key from config (e.g., 'serie_a')
        season_code: Season identifier
    """
    # Create file path using league folder
    folder = LEAGUES[league_key]['folder']
    league_folder = os.path.join(DATA_DIR, folder)
    file_path = os.path.join(league_folder, f'player_results_{season_code}.csv')
    
    # Ensure directory exists
    os.makedirs(league_folder, exist_ok=True)
    
    # Convert to DataFrame
    df = pd.DataFrame(contributions)
    
    # Save to CSV
    df.to_csv(file_path, index=False)
    
    print(f"   ✓ Saved player results to {file_path}")
