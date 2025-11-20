import requests
import json
import re
import unicodedata
import html
from src.config import (
    LEAGUES,
    UNDERSTAT_BASE_URL,
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

def fetch_understat_data(league_key, season_code):
    """
    Facade function to get both players and team totals in one go.
    
    Returns:
        tuple: (players_list, team_goals_dict)
    """
    players = get_league_players(league_key, season_code)
    team_goals = get_team_totals(league_key, season_code)
    return players, team_goals
