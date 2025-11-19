import requests
import json
import re
import unicodedata
import html
import os
import pandas as pd
from src.config import (
    LEAGUES,
    LEAGUE_KEYS,
    UNDERSTAT_BASE_URL,
    DATA_DIR,
    SEASONS,
    UNDERSTAT_SEASON_MAP,
)

def normalize_name(name):
    """Remove accents and convert to lowercase for matching"""
    # Remove accents: Matías -> Matias, Soulé -> Soule
    nfd = unicodedata.normalize('NFD', name)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return without_accents.lower().strip()

def _build_understat_url(league_key, season_code):
    understat_key = LEAGUES[league_key]['understat_key']
    season_suffix = UNDERSTAT_SEASON_MAP.get(season_code)
    if season_suffix:
        return f"{UNDERSTAT_BASE_URL}{understat_key}/{season_suffix}"
    return UNDERSTAT_BASE_URL + understat_key


def get_league_players(league_key, season_code):
    """Get all players from a league/season"""
    url = _build_understat_url(league_key, season_code)
    
    display_name = LEAGUES[league_key]['display_name']
    print(f"Fetching {display_name} data (season {season_code})...")
    response = requests.get(url)
    
    # Find the JavaScript variable with player data
    match = re.search(r"var playersData\s*=\s*JSON\.parse\('(.+?)'\)", response.text)
    
    if not match:
        print("Could not find player data!")
        return []
    
    # Decode hex-encoded string and parse JSON
    encoded = match.group(1)
    decoded = encoded.encode('utf-8').decode('unicode_escape')
    players = json.loads(decoded)
    
    # Decode HTML entities in player names (e.g., &#039; -> ')
    for player in players:
        player['player_name'] = html.unescape(player['player_name'])
    
    print(f"Found {len(players)} players")
    return players


def get_team_data(league_key, season_code):
    """Get team-level data (total goals, etc.) from Understat"""
    url = _build_understat_url(league_key, season_code)
    response = requests.get(url)

    # Find the JavaScript variable with team data
    match = re.search(r"var teamsData\s*=\s*JSON\.parse\('(.+?)'\)", response.text)

    # Decode hex-encoded string and parse JSON
    encoded = match.group(1)
    decoded = encoded.encode('utf-8').decode('unicode_escape')
    teams = json.loads(decoded)
    
    # Decode HTML entities in team names
    for team_id, team_data in teams.items():
        if 'title' in team_data:
            team_data['title'] = html.unescape(team_data['title'])
    
    print(f"Found {len(teams)} teams")
    return teams


def get_team_totals(league_key, season_code):
    """Calculate total goals scored by each team from match history
    
    Args:
        league_key: League key from config (e.g., 'serie_a')
    
    Returns:
        dict: {'Team Name': total_goals_scored, ...}
    """
    teams_data = get_team_data(league_key, season_code)
    
    team_totals = {}
    for team_id, team_info in teams_data.items():
        team_name = team_info['title']
        
        # Sum up goals scored across all matches in history
        total_goals = sum(match['scored'] for match in team_info['history'])
        team_totals[team_name] = total_goals
        
    
    return team_totals


def calculate_contributions(league_key, season_code):
    """Calculate contributions for all players in a league
    
    Args:
        league_key: League key from config (e.g., 'serie_a')
    
    Returns:
        List of dicts with player contribution data
    """
    contributions = []
    all_players = get_league_players(league_key, season_code)
    team_goals = get_team_totals(league_key, season_code)
    
    for player in all_players:
        player_team = player['team_title']
        
        # Skip multi-team players
        if ',' in player_team:
            continue
        
        # Get this team's total (keep dict intact)
        team_total = team_goals.get(player_team, 0)
        
        # Player stats
        goals = int(player['goals'])
        assists = int(player['assists'])
        total_contribs = goals + assists  
        
        # Calculate percentages using team_total
        contribution_pct = (total_contribs / team_total * 100) if team_total > 0 else 0
        goals_pct = (goals / team_total * 100) if team_total > 0 else 0
        assists_pct = (assists / team_total * 100) if team_total > 0 else 0
        
        contributions.append({
            'player': player['player_name'],
            'team': player_team,
            'goals': goals,
            'assists': assists,
            'contributions': total_contribs,
            'contribution_pct': round(contribution_pct, 1),
            'goals_pct': round(goals_pct, 1),
            'assists_pct': round(assists_pct, 1),
            'games': int(player['games']),
            'season': season_code,
        })
    
    contributions.sort(key=lambda x: x['contribution_pct'], reverse=True)
    return contributions


def print_table(contributions, league_key, season_code, top_n=20):
    """Print formatted table of top contributors
    
    Args:
        contributions: List of player contribution dicts
        league_key: League key from config (e.g., 'serie_a')
        top_n: Number of top players to display
    """
    # Slice to top N
    top_players = contributions[:top_n]
    
    # Print header
    display_name = LEAGUES[league_key]['display_name']
    print("\n" + "="*100)
    print(f"TOP {top_n} CONTRIBUTORS - {display_name.upper()} ({season_code})")
    print("="*100)
    print(f"{'Rank':<6} {'Player':<25} {'Team':<18} {'G':<5} {'A':<5} {'Total':<7} {'G%':<8} {'A%':<8} {'Cont%':<8}")
    print("-"*100)
    
    # Print data rows
    for i, p in enumerate(top_players, 1):
        print(f"{i:<6} {p['player']:<25} {p['team']:<18} {p['goals']:<5} {p['assists']:<5} {p['contributions']:<7} {p['goals_pct']:<8.1f} {p['assists_pct']:<8.1f} {p['contribution_pct']:<8.1f}")
    
    print("="*100)

def save_player_results(contributions, league_key, season_code):
    """Save player contributions to CSV
    
    Args:
        contributions: List of player contribution dicts
        league_key: League key from config (e.g., 'serie_a')
    """
    # Create file path using league folder
    folder = LEAGUES[league_key]['folder']
    league_folder = os.path.join(DATA_DIR, folder)
    file_path = os.path.join(league_folder, f'player_results_{season_code}.csv')
    
    # Ensure directory exists (shouldn't be needed, but safe)
    os.makedirs(league_folder, exist_ok=True)
    
    # Convert to DataFrame
    df = pd.DataFrame(contributions)
    
    # Save to CSV
    df.to_csv(file_path, index=False)
    
    print(f"   ✓ Saved player results to {file_path}")


def main():
    """Run player contribution analysis for all leagues/seasons."""
    print("\n" + "="*60)
    print("UNDERSTAT PLAYER CONTRIBUTION ANALYSIS")
    print("="*60)

    for season in SEASONS:
        for league_key in LEAGUE_KEYS:
            display_name = LEAGUES[league_key]['display_name']
            print(f"\n[Processing {display_name} - Season {season}]")

            try:
                players_contributions = calculate_contributions(league_key, season)
                save_player_results(players_contributions, league_key, season)
                print(f"   ✓ {len(players_contributions)} players processed")
            except Exception as e:
                print(f"   ✗ Failed: {e}")


if __name__ == "__main__":
    main()