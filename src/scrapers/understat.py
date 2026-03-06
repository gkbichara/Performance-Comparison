import requests
import json
import re
import unicodedata
import html
import time
from src.config import (
    LEAGUES,
    UNDERSTAT_BASE_URL,
    UNDERSTAT_SEASON_MAP,
)

# Headers to mimic browser requests (helps avoid Cloudflare blocking)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Headers for API/XHR requests (required for getLeagueData endpoint)
API_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9',
    'X-Requested-With': 'XMLHttpRequest',
}

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
    response = requests.get(url, headers=HEADERS)
    
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
    response = requests.get(url, headers=HEADERS)

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
    """Calculate total goals AND xG for each team from match history
    
    Args:
        league_key: League key from config (e.g., 'serie_a')
    
    Returns:
        dict: {'Team Name': {'goals': X, 'xG': Y}, ...}
    """
    teams_data = get_team_data(league_key, season_code)
    
    team_totals = {}
    for team_id, team_info in teams_data.items():
        team_name = team_info['title']
        history = team_info['history']
        
        # Sum up goals and xG across all matches
        team_totals[team_name] = {
            'goals': sum(match['scored'] for match in history),
            'xG': sum(float(match['xG']) for match in history),
        }
    
    return team_totals

def fetch_understat_data(league_key, season_code):
    """
    Facade function to get both players and team totals in one go.
    Uses the API approach for reliability (HTML parsing gets blocked).
    
    Returns:
        tuple: (players_list, team_totals_dict)
               team_totals_dict: {'Team Name': {'goals': X, 'xG': Y}, ...}
    """
    api_data = get_league_data_api(league_key, season_code)
    
    if not api_data:
        print(f"Failed to fetch data for {league_key} {season_code}")
        return [], {}
    
    # Extract players
    players = api_data.get('players', [])
    
    # Decode HTML entities in player names
    for player in players:
        player['player_name'] = html.unescape(player['player_name'])
    
    # Calculate team totals from teams data
    teams_data = api_data.get('teams', {})
    team_totals = {}
    for team_id, team_info in teams_data.items():
        team_name = html.unescape(team_info['title'])
        history = team_info['history']
        
        team_totals[team_name] = {
            'goals': sum(match['scored'] for match in history),
            'xG': sum(float(match['xG']) for match in history),
        }
    
    return players, team_totals


def get_league_data_api(league_key, season_code):
    """
    Fetch league data from Understat's JSON API endpoint.
    This is cleaner than HTML parsing and includes npxG data.
    
    API endpoint: https://understat.com/getLeagueData/{league}/{year}
    
    Returns:
        dict: Raw API response with 'teams' and 'players' data
    """
    understat_key = LEAGUES[league_key]['understat_key']
    season_suffix = UNDERSTAT_SEASON_MAP.get(season_code)
    
    # API uses year format (e.g., 2025 for 2025/26 season)
    api_url = f"https://understat.com/getLeagueData/{understat_key}/{season_suffix}"
    referer_url = f"https://understat.com/league/{understat_key}/{season_suffix}"
    
    display_name = LEAGUES[league_key]['display_name']
    print(f"Fetching {display_name} xG data (season {season_code}) from API...")
    
    # Use API headers with Referer for XHR-like requests
    headers = {**API_HEADERS, 'Referer': referer_url}
    response = requests.get(api_url, headers=headers)
    
    if response.status_code != 200:
        print(f"API returned status {response.status_code}")
        return None
    
    try:
        data = response.json()
        teams_count = len(data.get('teams', {}))
        players_count = len(data.get('players', []))
        print(f"API returned {teams_count} teams, {players_count} players")
        return data
    except json.JSONDecodeError:
        print("Failed to parse API response as JSON")
        return None


def get_team_match_xg(league_key, season_code):
    """
    Extract per-match xG data for all teams in a league/season.
    
    Uses API's 'dates' for direct team names (no lookup needed), 
    and enriches with npxG from 'teams.history'.
    
    Returns:
        list: List of dicts with match-level xG data (including npxG!)
    """
    api_data = get_league_data_api(league_key, season_code)
    
    if not api_data or 'dates' not in api_data:
        print(f"No data returned for {league_key} {season_code}")
        return []
    
    dates_data = api_data['dates']
    teams_data = api_data.get('teams', {})
    
    # Build lookup for npxG from teams.history
    # Key: (team_name, date, venue) -> {npxG, npxGA}
    # We use venue to distinguish home vs away perspective
    npxg_lookup = {}
    for team_id, team_info in teams_data.items():
        team_name = html.unescape(team_info['title'])
        for match in team_info['history']:
            key = (team_name, match['date'], match['h_a'])
            npxg_lookup[key] = {
                'npxG': match.get('npxG'),
                'npxGA': match.get('npxGA'),
            }
    
    # Track match numbers per team
    team_match_counts = {}
    
    records = []
    
    # Process only completed matches from dates
    for match in dates_data:
        if not match.get('isResult'):
            continue  # Skip future/unplayed matches
        
        home_team = html.unescape(match['h']['title'])
        away_team = html.unescape(match['a']['title'])
        match_datetime = match['datetime']
        
        goals_home = int(match['goals']['h'])
        goals_away = int(match['goals']['a'])
        xg_home = float(match['xG']['h'])
        xg_away = float(match['xG']['a'])
        
        # Determine results
        if goals_home > goals_away:
            result_home, result_away = 'W', 'L'
            pts_home, pts_away = 3, 0
        elif goals_home < goals_away:
            result_home, result_away = 'L', 'W'
            pts_home, pts_away = 0, 3
        else:
            result_home, result_away = 'D', 'D'
            pts_home, pts_away = 1, 1
        
        # Get npxG from lookup
        npxg_home_data = npxg_lookup.get((home_team, match_datetime, 'h'), {})
        npxg_away_data = npxg_lookup.get((away_team, match_datetime, 'a'), {})
        
        # Increment match counters
        team_match_counts[home_team] = team_match_counts.get(home_team, 0) + 1
        team_match_counts[away_team] = team_match_counts.get(away_team, 0) + 1
        
        # Home team record
        records.append({
            'league': league_key,
            'season': season_code,
            'team': home_team,
            'opponent': away_team,
            'venue': 'h',
            'match_date': match_datetime,
            'match_number': team_match_counts[home_team],
            'goals_for': goals_home,
            'goals_against': goals_away,
            'xg_for': round(xg_home, 2),
            'xg_against': round(xg_away, 2),
            'npxg_for': round(npxg_home_data['npxG'], 2) if npxg_home_data.get('npxG') else None,
            'npxg_against': round(npxg_home_data['npxGA'], 2) if npxg_home_data.get('npxGA') else None,
            'result': result_home,
            'points': pts_home,
        })
        
        # Away team record
        records.append({
            'league': league_key,
            'season': season_code,
            'team': away_team,
            'opponent': home_team,
            'venue': 'a',
            'match_date': match_datetime,
            'match_number': team_match_counts[away_team],
            'goals_for': goals_away,
            'goals_against': goals_home,
            'xg_for': round(xg_away, 2),
            'xg_against': round(xg_home, 2),
            'npxg_for': round(npxg_away_data['npxG'], 2) if npxg_away_data.get('npxG') else None,
            'npxg_against': round(npxg_away_data['npxGA'], 2) if npxg_away_data.get('npxGA') else None,
            'result': result_away,
            'points': pts_away,
        })
    
    print(f"Extracted {len(records)} team-match records for {league_key} {season_code}")
    return records


def get_upcoming_fixtures(league_key, season_code):
    """
    Extract upcoming (unplayed) fixtures from Understat's API.
    
    Returns:
        list: List of dicts with {league, season, home_team, away_team, match_date}
    """
    api_data = get_league_data_api(league_key, season_code)
    
    if not api_data or 'dates' not in api_data:
        print(f"No data returned for {league_key} {season_code}")
        return []
    
    dates_data = api_data['dates']
    
    fixtures = []
    for match in dates_data:
        if match.get('isResult'):
            continue
        
        home_team = html.unescape(match['h']['title'])
        away_team = html.unescape(match['a']['title'])
        match_datetime = match['datetime']
        
        fixtures.append({
            'league': league_key,
            'season': season_code,
            'home_team': home_team,
            'away_team': away_team,
            'match_date': match_datetime,
        })
    
    print(f"Found {len(fixtures)} upcoming fixtures for {league_key} {season_code}")
    return fixtures


# Legacy function for backwards compatibility
def get_matches_data(league_key, season_code):
    """Get match-level data from Understat's datesData (legacy approach)."""
    url = _build_understat_url(league_key, season_code)
    response = requests.get(url, headers=HEADERS)
    
    match = re.search(r"var datesData\s*=\s*JSON\.parse\('(.+?)'\)", response.text)
    if not match:
        print("Could not find datesData!")
        return []
    
    encoded = match.group(1)
    decoded = encoded.encode('utf-8').decode('unicode_escape')
    matches = json.loads(decoded)
    
    # Decode HTML entities in team names
    for m in matches:
        m['h']['title'] = html.unescape(m['h']['title'])
        m['a']['title'] = html.unescape(m['a']['title'])
    
    # Filter to only completed matches
    completed = [m for m in matches if m['isResult']]
    print(f"Found {len(completed)} completed matches")
    return completed
