# config.py
"""
Configuration file for Football Performance Comparison project.
Contains league definitions, folder paths, and shared constants.
"""

# League configuration with all necessary mappings
LEAGUES = {
    'serie_a': {
        'display_name': 'Serie A',
        'folder': 'serie_a',
        'fbdata_code': 'I1',
        'understat_key': 'Serie_A'
    },
    'premier_league': {
        'display_name': 'Premier League',
        'folder': 'premier_league',
        'fbdata_code': 'E0',
        'understat_key': 'EPL'
    },
    'la_liga': {
        'display_name': 'La Liga',
        'folder': 'la_liga',
        'fbdata_code': 'SP1',
        'understat_key': 'La_Liga'
    },
    'bundesliga': {
        'display_name': 'Bundesliga',
        'folder': 'bundesliga',
        'fbdata_code': 'D1',
        'understat_key': 'Bundesliga'
    },
    'ligue_1': {
        'display_name': 'Ligue 1',
        'folder': 'ligue_1',
        'fbdata_code': 'F1',
        'understat_key': 'Ligue_1'
    }
}

# Ordered list of league keys for iteration
LEAGUE_KEYS = ['serie_a', 'premier_league', 'la_liga', 'bundesliga', 'ligue_1']

# Season codes
SEASONS = ['2425', '2526']
PREVIOUS_SEASON = SEASONS[0]
CURRENT_SEASON = SEASONS[-1]

# Mapping between internal season codes and Understat season identifiers
# Understat uses the starting calendar year of the season (e.g., 2024 for 2024/25)
UNDERSTAT_SEASON_MAP = {
    '2425': '2024',
    '2526': '2025',
}

# Base paths
DATA_DIR = 'data'
LOGS_DIR = 'logs'

# External API URLs
FBDATA_BASE_URL = "https://www.football-data.co.uk/mmz4281"
UNDERSTAT_BASE_URL = "https://understat.com/league/"