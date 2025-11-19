import requests
import os
from src.config import LEAGUES, LEAGUE_KEYS, SEASONS, FBDATA_BASE_URL, DATA_DIR


def download_league_data(league_key, season):
    """
    Download CSV data for a specific league and season.
    
    Args:
        league_key: League key from config (e.g., 'serie_a')
        season: Season code (e.g., '2526')
    """
    league_info = LEAGUES[league_key]
    display_name = league_info['display_name']
    fbdata_code = league_info['fbdata_code']
    folder_name = league_info['folder']
    
    # Construct URL
    url = f"{FBDATA_BASE_URL}/{season}/{fbdata_code}.csv"
    
    # Create directory structure: data/league_folder/
    league_dir = os.path.join(DATA_DIR, folder_name)
    os.makedirs(league_dir, exist_ok=True)
    
    # File path: data/league_folder/season.csv
    file_path = os.path.join(league_dir, f"{season}.csv")
    
    try:
        print(f"Downloading {display_name} {season}... ", end="")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise error for bad status codes
        
        # Save to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"✓ Saved to {file_path}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed: {e}")
        return False


def main():
    """Download all league data for all seasons."""
    print("=" * 50)
    print("Football Data Scraper")
    print("=" * 50)
    
    total_downloads = len(LEAGUE_KEYS) * len(SEASONS)
    successful = 0
    
    for league_key in LEAGUE_KEYS:
        display_name = LEAGUES[league_key]['display_name']
        print(f"\n{display_name}:")
        for season in SEASONS:
            if download_league_data(league_key, season):
                successful += 1
    
    print("\n" + "=" * 50)
    print(f"Download complete! {successful}/{total_downloads} files downloaded")
    print("=" * 50)
    
    return successful == total_downloads


if __name__ == "__main__":
    main()