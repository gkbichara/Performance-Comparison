from pathlib import Path

import pandas as pd

from src import analysis, config
from src.analysis import compare_seasons, save_league_results
from src.config import CURRENT_SEASON


def make_match_df(rows):
    """Helper to build DataFrame with required columns."""
    return pd.DataFrame(
        rows,
        columns=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"],
    )


def test_compare_seasons_excludes_missing_previous_season():
    cur_df = make_match_df(
        [
            ("01/08/2024", "Alpha", "Beta", 2, 0),   # home win
            ("08/08/2024", "Gamma", "Alpha", 1, 1),  # away draw
            ("15/08/2024", "Alpha", "Delta", 3, 1),  # opponent missing in prev season
        ]
    )

    prev_df = make_match_df(
        [
            ("01/08/2023", "Alpha", "Beta", 1, 1),   # home draw
            ("08/08/2023", "Gamma", "Alpha", 0, 2),  # away win
        ]
    )

    result = compare_seasons(cur_df, prev_df, "Alpha")

    # Only opponents present in both seasons should remain (Delta removed)
    assert set(result["Opponent"]) == {"Beta", "Gamma"}
    assert "Delta" not in result["Opponent"].values

    # Verify ordering and calculations
    beta_row = result[result["Opponent"] == "Beta"].iloc[0]
    gamma_row = result[result["Opponent"] == "Gamma"].iloc[0]

    assert beta_row["Result"] == "W"
    assert beta_row["Differential"] == 2  # 3 (win) - 1 (draw)
    assert gamma_row["Result"] == "D"
    assert gamma_row["Differential"] == -2  # 1 (draw) - 3 (previous win)
    assert gamma_row["Cumulative"] == 0  # 2 + (-2)


def test_save_league_results_writes_season_and_alias(tmp_path):
    df = pd.DataFrame(
        {
            "Season": [CURRENT_SEASON],
            "Team": ["Alpha"],
            "Match_Number": [1],
            "Date": ["01/08/2025"],
            "Opponent": ["Beta"],
            "Venue": ["H"],
            "Result": ["W"],
            "FTHG": [2],
            "FTAG": [0],
            "Points_cur": [3],
            "Points_prev": [1],
            "Differential": [2],
            "Cumulative": [2],
        }
    )

    save_league_results(df, tmp_path, CURRENT_SEASON)

    season_file = tmp_path / f"results_{CURRENT_SEASON}.csv"
    alias_file = tmp_path / "results.csv"

    assert season_file.exists(), "Season-specific results file not written"
    assert alias_file.exists(), "Alias results.csv not written for current season"


def test_analysis_main_writes_multi_season_results(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    league_dir = data_dir / "serie_a"
    league_dir.mkdir(parents=True)

    prev_matches = make_match_df(
        [
            ("01/08/2021", "Alpha", "Beta", 2, 0),
            ("08/08/2021", "Gamma", "Alpha", 0, 1),
        ]
    )
    cur_matches = make_match_df(
        [
            ("01/08/2022", "Alpha", "Beta", 1, 1),
            ("08/08/2022", "Gamma", "Alpha", 2, 0),
        ]
    )

    prev_file = league_dir / "2021.csv"
    cur_file = league_dir / "2122.csv"
    prev_matches.to_csv(prev_file, index=False)
    cur_matches.to_csv(cur_file, index=False)

    monkeypatch.setattr(config, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(config, "SEASONS", ["2021", "2122"])
    monkeypatch.setattr(config, "CURRENT_SEASON", "2122")
    monkeypatch.setattr(config, "LEAGUE_KEYS", ["serie_a"])
    monkeypatch.setattr(analysis, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(analysis, "SEASONS", ["2021", "2122"])
    monkeypatch.setattr(analysis, "CURRENT_SEASON", "2122")
    monkeypatch.setattr(analysis, "LEAGUE_KEYS", ["serie_a"])

    analysis.main()

    season_file = league_dir / "results_2122.csv"
    alias_file = league_dir / "results.csv"

    assert season_file.exists()
    assert alias_file.exists()

    df = pd.read_csv(season_file)

    # Entire file should be tagged with the current season
    assert df["Season"].nunique() == 1
    assert df["Season"].iloc[0] == 2122

    alpha_rows = df[df["Team"] == "Alpha"].sort_values("Match_Number")
    assert alpha_rows["Season"].tolist() == [2122, 2122]
    assert alpha_rows["Match_Number"].tolist() == [1, 2]
    assert alpha_rows["Differential"].tolist() == [-2, -3]

