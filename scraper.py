import requests
import os

# Base URL for football-data.co.uk
BASE_URL = "https://www.football-data.co.uk/mmz4281"

# League configuration: {Display Name: (Code, Folder Name)}
LEAGUES = {
    'Serie A': ('I1', 'SerieA'),
    'Premier League': ('E0', 'PremierLeague'),
    'Ligue 1': ('F1', 'Ligue1'),
    'Bundesliga': ('D1', 'Bundesliga'),
    'La Liga': ('SP1', 'LaLiga')
}

# Seasons to download
SEASONS = ['2425', '2526']


def download_league_data(league_name, league_code, folder_name, season):
    """
    Download CSV data for a specific league and season.
    
    Args:
        league_name: Display name of the league (e.g., 'Serie A')
        league_code: Football-data.co.uk code (e.g., 'I1')
        folder_name: Folder name for saving (e.g., 'SerieA')
        season: Season code (e.g., '2526')
    """
    # Construct URL
    url = f"{BASE_URL}/{season}/{league_code}.csv"
    
    # Create directory structure: data/leagueName/
    league_dir = os.path.join('data', folder_name)
    os.makedirs(league_dir, exist_ok=True)
    
    # File path: data/leagueName/season.csv
    file_path = os.path.join(league_dir, f"{season}.csv")
    
    try:
        print(f"Downloading {league_name} {season}... ", end="")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise error for bad status codes
        
        # Save to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"✓ Saved to {file_path}")
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed: {e}")


def main():
    """Download all league data for all seasons."""
    print("=" * 50)
    print("Football Data Scraper")
    print("=" * 50)
    
    for league_name, (league_code, folder_name) in LEAGUES.items():
        print(f"\n{league_name}:")
        for season in SEASONS:
            download_league_data(league_name, league_code, folder_name, season)
    
    print("\n" + "=" * 50)
    print("Download complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()