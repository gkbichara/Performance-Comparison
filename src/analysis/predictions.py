"""
Match Predictions - XGBoost model for predicting match outcomes (H/D/A).

Trains per-league models using ELO, rolling form, xG, venue-specific stats,
and head-to-head features. Missing data left as NaN for XGBoost's native
handling (no imputation).
"""
import time
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score

from src.config import (
    TEAM_NAME_MAP, LEAGUE_KEYS, LEAGUES,
    CURRENT_SEASON, SEASONS, UNDERSTAT_SEASON_MAP,
)
from src.database import (
    get_raw_matches, get_elo_match_history, get_xg_matches,
    get_elo_ratings, upload_upcoming_fixtures, upload_predictions,
)
from src.scrapers.understat import get_upcoming_fixtures as scrape_fixtures


RESULT_ENCODE = {'H': 0, 'D': 1, 'A': 2}
RESULT_DECODE = {0: 'H', 1: 'D', 2: 'A'}
HOME_POINTS = {'H': 3, 'D': 1, 'A': 0}
AWAY_POINTS = {'H': 0, 'D': 1, 'A': 3}

TRAIN_SEASONS = ['2021', '2122', '2223', '2324']
VAL_SEASONS = ['2425']
TEST_SEASONS = ['2526']

ROLLING_W = 5
VENUE_MIN_PERIODS = 3

FEATURE_COLS = [
    'home_elo', 'away_elo', 'elo_diff',
    'home_form_5', 'away_form_5',
    'home_gf_5', 'away_gf_5',
    'home_ga_5', 'away_ga_5',
    'home_venue_form_5', 'away_venue_form_5',
    'home_venue_gf_5', 'away_venue_gf_5',
    'home_venue_ga_5', 'away_venue_ga_5',
    'home_xg_for_5', 'away_xg_for_5',
    'home_xg_against_5', 'away_xg_against_5',
    'home_venue_xg_5', 'away_venue_xg_5',
    'home_venue_xga_5', 'away_venue_xga_5',
    'h2h_home_win_pct', 'h2h_total_meetings', 'h2h_avg_goals',
    'home_season_ppg', 'away_season_ppg', 'season_progress',
    'form_diff', 'xg_diff', 'ppg_diff',
]


def _map_name(name):
    """Map Understat team name to football-data.co.uk name."""
    return TEAM_NAME_MAP.get(name, name)


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def _build_team_history(raw_df):
    """
    Expand match-level rows into per-team rows and compute rolling features.
    Each match produces two rows (home perspective + away perspective).
    """
    raw = raw_df.copy()
    raw['date'] = pd.to_datetime(raw['date'])

    home = pd.DataFrame({
        'team': raw['home_team'], 'opponent': raw['away_team'],
        'date': raw['date'], 'venue': 'H',
        'gf': raw['fthg'], 'ga': raw['ftag'],
        'points': raw['ftr'].map(HOME_POINTS),
        'league': raw['league'], 'season': raw['season'],
    })
    away = pd.DataFrame({
        'team': raw['away_team'], 'opponent': raw['home_team'],
        'date': raw['date'], 'venue': 'A',
        'gf': raw['ftag'], 'ga': raw['fthg'],
        'points': raw['ftr'].map(AWAY_POINTS),
        'league': raw['league'], 'season': raw['season'],
    })

    th = pd.concat([home, away], ignore_index=True)
    th = th.sort_values(['team', 'date']).reset_index(drop=True)

    # Overall rolling (last 5 matches, shifted to avoid leakage)
    for src, dst in [('points', 'form_r5'), ('gf', 'gf_r5'), ('ga', 'ga_r5')]:
        th[dst] = (
            th.groupby('team')[src]
            .transform(lambda s: s.shift(1).rolling(ROLLING_W, min_periods=1).mean())
        )

    # Season PPG (expanding mean within season, shifted)
    th['season_ppg'] = (
        th.groupby(['team', 'league', 'season'])['points']
        .transform(lambda s: s.shift(1).expanding(min_periods=1).mean())
    )

    # Season match count
    th['season_match'] = th.groupby(['team', 'league', 'season']).cumcount() + 1

    # Venue-specific rolling
    for venue_val in ['H', 'A']:
        mask = th['venue'] == venue_val
        sub = th.loc[mask].copy()
        for src, dst in [('points', f'v_form_r5'), ('gf', f'v_gf_r5'), ('ga', f'v_ga_r5')]:
            sub[dst] = (
                sub.groupby('team')[src]
                .transform(lambda s: s.shift(1).rolling(ROLLING_W, min_periods=VENUE_MIN_PERIODS).mean())
            )
        for col in ['v_form_r5', 'v_gf_r5', 'v_ga_r5']:
            th.loc[mask, col] = sub[col].values

    return th


def _build_xg_rolling(xg_df):
    """Compute rolling xG features per team, mapping names to football-data."""
    xg = xg_df.copy()
    xg['team_fd'] = xg['team'].map(_map_name)
    xg['date'] = pd.to_datetime(xg['match_date']).dt.normalize()
    xg = xg.sort_values(['team_fd', 'date']).reset_index(drop=True)

    for src, dst in [('xg_for', 'xg_for_r5'), ('xg_against', 'xg_ag_r5')]:
        xg[dst] = (
            xg.groupby('team_fd')[src]
            .transform(lambda s: s.shift(1).rolling(ROLLING_W, min_periods=1).mean())
        )

    for venue_val in ['h', 'a']:
        mask = xg['venue'] == venue_val
        sub = xg.loc[mask].copy()
        for src, dst in [('xg_for', 'v_xg_r5'), ('xg_against', 'v_xga_r5')]:
            sub[dst] = (
                sub.groupby('team_fd')[src]
                .transform(lambda s: s.shift(1).rolling(ROLLING_W, min_periods=VENUE_MIN_PERIODS).mean())
            )
        for col in ['v_xg_r5', 'v_xga_r5']:
            xg.loc[mask, col] = sub[col].values

    return xg


def _attach_h2h(matches_df, raw_df):
    """
    Compute head-to-head features for each match from all prior meetings
    (within the last 3 seasons).
    """
    raw = raw_df.copy()
    raw['date'] = pd.to_datetime(raw['date'])

    season_order = {s: i for i, s in enumerate(SEASONS)}

    pair_key = lambda h, a: tuple(sorted([h, a]))
    raw['pair'] = [pair_key(h, a) for h, a in zip(raw['home_team'], raw['away_team'])]

    pair_groups = {}
    for _, r in raw.iterrows():
        pair_groups.setdefault(r['pair'], []).append(r)

    h2h_home_win_pct = []
    h2h_meetings = []
    h2h_avg_goals = []

    for _, match in matches_df.iterrows():
        pk = pair_key(match['home_team'], match['away_team'])
        match_date = pd.to_datetime(match['date'])
        match_season_idx = season_order.get(match['season'], 0)

        priors = []
        for prev in pair_groups.get(pk, []):
            if pd.to_datetime(prev['date']) >= match_date:
                continue
            prev_season_idx = season_order.get(prev['season'], 0)
            if match_season_idx - prev_season_idx > 3:
                continue
            priors.append(prev)

        if not priors:
            h2h_home_win_pct.append(np.nan)
            h2h_meetings.append(0)
            h2h_avg_goals.append(np.nan)
            continue

        wins = 0
        total_goals = 0
        for prev in priors:
            if prev['home_team'] == match['home_team'] and prev['ftr'] == 'H':
                wins += 1
            elif prev['away_team'] == match['home_team'] and prev['ftr'] == 'A':
                wins += 1
            total_goals += (prev['fthg'] or 0) + (prev['ftag'] or 0)

        h2h_home_win_pct.append(wins / len(priors))
        h2h_meetings.append(len(priors))
        h2h_avg_goals.append(total_goals / len(priors))

    matches_df = matches_df.copy()
    matches_df['h2h_home_win_pct'] = h2h_home_win_pct
    matches_df['h2h_total_meetings'] = h2h_meetings
    matches_df['h2h_avg_goals'] = h2h_avg_goals
    return matches_df


def build_feature_matrix(raw_df, elo_df, xg_df):
    """
    Build a complete feature matrix from historical data.
    Returns a DataFrame with one row per match and all features + target.
    """
    print("   Building team history and rolling stats...")
    th = _build_team_history(raw_df)

    print("   Building xG rolling stats...")
    xg_roll = _build_xg_rolling(xg_df)

    # Prepare match-level base from raw_matches
    matches = raw_df[['league', 'season', 'date', 'home_team', 'away_team', 'fthg', 'ftag', 'ftr']].copy()
    matches['date'] = pd.to_datetime(matches['date'])
    matches = matches.dropna(subset=['ftr'])

    # --- Join home team features ---
    home_cols = {
        'form_r5': 'home_form_5', 'gf_r5': 'home_gf_5', 'ga_r5': 'home_ga_5',
        'v_form_r5': 'home_venue_form_5', 'v_gf_r5': 'home_venue_gf_5',
        'v_ga_r5': 'home_venue_ga_5', 'season_ppg': 'home_season_ppg',
        'season_match': 'home_season_match',
    }
    home_th = th[th['venue'] == 'H'][['team', 'date'] + list(home_cols.keys())].copy()
    home_th = home_th.rename(columns=home_cols)
    matches = matches.merge(home_th, left_on=['home_team', 'date'], right_on=['team', 'date'], how='left')
    matches = matches.drop(columns=['team'], errors='ignore')

    # --- Join away team features ---
    away_cols = {
        'form_r5': 'away_form_5', 'gf_r5': 'away_gf_5', 'ga_r5': 'away_ga_5',
        'v_form_r5': 'away_venue_form_5', 'v_gf_r5': 'away_venue_gf_5',
        'v_ga_r5': 'away_venue_ga_5', 'season_ppg': 'away_season_ppg',
        'season_match': 'away_season_match',
    }
    away_th = th[th['venue'] == 'A'][['team', 'date'] + list(away_cols.keys())].copy()
    away_th = away_th.rename(columns=away_cols)
    matches = matches.merge(away_th, left_on=['away_team', 'date'], right_on=['team', 'date'], how='left')
    matches = matches.drop(columns=['team'], errors='ignore')

    # --- Join home team xG ---
    home_xg_cols = {
        'xg_for_r5': 'home_xg_for_5', 'xg_ag_r5': 'home_xg_against_5',
        'v_xg_r5': 'home_venue_xg_5', 'v_xga_r5': 'home_venue_xga_5',
    }
    home_xg = xg_roll[xg_roll['venue'] == 'h'][['team_fd', 'date'] + list(home_xg_cols.keys())].copy()
    home_xg = home_xg.rename(columns=home_xg_cols)
    matches = matches.merge(home_xg, left_on=['home_team', 'date'], right_on=['team_fd', 'date'], how='left')
    matches = matches.drop(columns=['team_fd'], errors='ignore')

    # --- Join away team xG ---
    away_xg_cols = {
        'xg_for_r5': 'away_xg_for_5', 'xg_ag_r5': 'away_xg_against_5',
        'v_xg_r5': 'away_venue_xg_5', 'v_xga_r5': 'away_venue_xga_5',
    }
    away_xg = xg_roll[xg_roll['venue'] == 'a'][['team_fd', 'date'] + list(away_xg_cols.keys())].copy()
    away_xg = away_xg.rename(columns=away_xg_cols)
    matches = matches.merge(away_xg, left_on=['away_team', 'date'], right_on=['team_fd', 'date'], how='left')
    matches = matches.drop(columns=['team_fd'], errors='ignore')

    # --- Join ELO (pre-match ratings) ---
    print("   Joining ELO ratings...")
    elo = elo_df[['date', 'league', 'home_team', 'away_team',
                   'home_elo_before', 'away_elo_before']].copy()
    elo['date'] = pd.to_datetime(elo['date'])
    elo = elo.rename(columns={'home_elo_before': 'home_elo', 'away_elo_before': 'away_elo'})
    matches = matches.merge(
        elo, on=['date', 'league', 'home_team', 'away_team'], how='left'
    )

    # --- H2H ---
    print("   Computing head-to-head features...")
    matches = _attach_h2h(matches, raw_df)

    # --- Derived features ---
    matches['elo_diff'] = matches['home_elo'] - matches['away_elo']
    matches['form_diff'] = matches['home_form_5'] - matches['away_form_5']
    matches['xg_diff'] = matches['home_xg_for_5'] - matches['away_xg_for_5']
    matches['ppg_diff'] = matches['home_season_ppg'] - matches['away_season_ppg']

    max_match_per_league = matches.groupby(['league', 'season'])['home_season_match'].transform('max')
    matches['season_progress'] = matches['home_season_match'] / max_match_per_league.replace(0, np.nan)

    # Target
    matches['target'] = matches['ftr'].map(RESULT_ENCODE)

    print(f"   Feature matrix: {len(matches)} matches, {len(FEATURE_COLS)} features")
    return matches


def _latest_team_features(th, xg_roll):
    """
    Get the most recent rolling features for every team.
    Returns dict: team_name -> {feature: value, ...}
    """
    latest_th = th.sort_values('date').groupby('team').last()
    latest_xg = xg_roll.sort_values('date').groupby('team_fd').last()

    team_feats = {}
    for team in latest_th.index:
        row = latest_th.loc[team]
        feats = {
            'form_r5': row.get('form_r5'),
            'gf_r5': row.get('gf_r5'),
            'ga_r5': row.get('ga_r5'),
            'season_ppg': row.get('season_ppg'),
            'season_match': row.get('season_match'),
        }
        # Venue-specific (use the latest for this team's relevant venue rows)
        for col in ['v_form_r5', 'v_gf_r5', 'v_ga_r5']:
            feats[col] = row.get(col)

        if team in latest_xg.index:
            xr = latest_xg.loc[team]
            feats['xg_for_r5'] = xr.get('xg_for_r5')
            feats['xg_ag_r5'] = xr.get('xg_ag_r5')
            feats['v_xg_r5'] = xr.get('v_xg_r5')
            feats['v_xga_r5'] = xr.get('v_xga_r5')

        team_feats[team] = feats

    return team_feats


def build_fixture_features(fixtures_df, raw_df, elo_ratings_df, th, xg_roll):
    """
    Build features for upcoming fixtures using latest available data.
    Returns DataFrame aligned with FEATURE_COLS.
    """
    team_feats = _latest_team_features(th, xg_roll)

    # Latest venue-specific form from team history
    venue_th = {}
    for venue_val in ['H', 'A']:
        venue_th[venue_val] = th[th['venue'] == venue_val].sort_values('date').groupby('team').last()

    # Latest venue-specific xG from xg rolling
    venue_xg = {}
    for venue_val in ['h', 'a']:
        venue_xg[venue_val] = xg_roll[xg_roll['venue'] == venue_val].sort_values('date').groupby('team_fd').last()

    elo_lookup = {}
    if len(elo_ratings_df) > 0:
        for _, r in elo_ratings_df.iterrows():
            elo_lookup[r['team']] = r['elo_rating']

    raw = raw_df.copy()
    raw['date'] = pd.to_datetime(raw['date'])
    season_order = {s: i for i, s in enumerate(SEASONS)}
    current_season_idx = season_order.get(CURRENT_SEASON, len(SEASONS))

    def _safe_get(df, team, col):
        if df is not None and team in df.index:
            val = df.loc[team].get(col)
            return val if pd.notna(val) else np.nan
        return np.nan

    rows = []
    for _, fix in fixtures_df.iterrows():
        ht = fix['home_team']
        at = fix['away_team']

        hf = team_feats.get(ht, {})
        af = team_feats.get(at, {})

        home_elo = elo_lookup.get(ht, 1500)
        away_elo = elo_lookup.get(at, 1500)

        # H2H
        priors = raw[
            ((raw['home_team'] == ht) & (raw['away_team'] == at)) |
            ((raw['home_team'] == at) & (raw['away_team'] == ht))
        ]
        priors = priors[priors['season'].map(lambda s: current_season_idx - season_order.get(s, 0) <= 3)]

        if len(priors) > 0:
            h2h_wins = sum(
                ((priors['home_team'] == ht) & (priors['ftr'] == 'H')) |
                ((priors['away_team'] == ht) & (priors['ftr'] == 'A'))
            )
            h2h_pct = h2h_wins / len(priors)
            h2h_goals = ((priors['fthg'].fillna(0) + priors['ftag'].fillna(0)).sum()) / len(priors)
            h2h_n = len(priors)
        else:
            h2h_pct = np.nan
            h2h_goals = np.nan
            h2h_n = 0

        home_sm = hf.get('season_match') or 0
        away_sm = af.get('season_match') or 0
        max_sm = max(home_sm, away_sm, 1)

        h_form = hf.get('form_r5')
        a_form = af.get('form_r5')
        h_xg = hf.get('xg_for_r5')
        a_xg = af.get('xg_for_r5')
        h_ppg = hf.get('season_ppg')
        a_ppg = af.get('season_ppg')

        row = {
            'home_elo': home_elo, 'away_elo': away_elo,
            'elo_diff': home_elo - away_elo,
            'home_form_5': h_form, 'away_form_5': a_form,
            'home_gf_5': hf.get('gf_r5'), 'away_gf_5': af.get('gf_r5'),
            'home_ga_5': hf.get('ga_r5'), 'away_ga_5': af.get('ga_r5'),
            'home_venue_form_5': _safe_get(venue_th.get('H'), ht, 'v_form_r5'),
            'away_venue_form_5': _safe_get(venue_th.get('A'), at, 'v_form_r5'),
            'home_venue_gf_5': _safe_get(venue_th.get('H'), ht, 'v_gf_r5'),
            'away_venue_gf_5': _safe_get(venue_th.get('A'), at, 'v_gf_r5'),
            'home_venue_ga_5': _safe_get(venue_th.get('H'), ht, 'v_ga_r5'),
            'away_venue_ga_5': _safe_get(venue_th.get('A'), at, 'v_ga_r5'),
            'home_xg_for_5': hf.get('xg_for_r5'),
            'away_xg_for_5': af.get('xg_for_r5'),
            'home_xg_against_5': hf.get('xg_ag_r5'),
            'away_xg_against_5': af.get('xg_ag_r5'),
            'home_venue_xg_5': _safe_get(venue_xg.get('h'), ht, 'v_xg_r5'),
            'away_venue_xg_5': _safe_get(venue_xg.get('a'), at, 'v_xg_r5'),
            'home_venue_xga_5': _safe_get(venue_xg.get('h'), ht, 'v_xga_r5'),
            'away_venue_xga_5': _safe_get(venue_xg.get('a'), at, 'v_xga_r5'),
            'h2h_home_win_pct': h2h_pct, 'h2h_total_meetings': h2h_n,
            'h2h_avg_goals': h2h_goals,
            'home_season_ppg': h_ppg, 'away_season_ppg': a_ppg,
            'season_progress': home_sm / max_sm if max_sm else np.nan,
            'form_diff': (h_form - a_form) if (h_form is not None and a_form is not None) else np.nan,
            'xg_diff': (h_xg - a_xg) if (h_xg is not None and a_xg is not None) else np.nan,
            'ppg_diff': (h_ppg - a_ppg) if (h_ppg is not None and a_ppg is not None) else np.nan,
        }
        rows.append(row)

    return pd.DataFrame(rows, columns=FEATURE_COLS)


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------

def train_and_evaluate(X_train, y_train, X_val, y_val, X_test, y_test):
    """
    Train XGBoost multiclass model with early stopping on val set.
    Returns (model, test_accuracy, test_predictions).
    """
    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=FEATURE_COLS, enable_categorical=False)
    dval = xgb.DMatrix(X_val, label=y_val, feature_names=FEATURE_COLS, enable_categorical=False)
    dtest = xgb.DMatrix(X_test, label=y_test, feature_names=FEATURE_COLS, enable_categorical=False)

    params = {
        'objective': 'multi:softprob',
        'num_class': 3,
        'eval_metric': 'mlogloss',
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 5,
        'seed': 42,
        'verbosity': 0,
    }

    model = xgb.train(
        params, dtrain,
        num_boost_round=500,
        evals=[(dval, 'val')],
        early_stopping_rounds=30,
        verbose_eval=False,
    )

    # Evaluate on test
    probs = model.predict(dtest)
    preds = probs.argmax(axis=1)
    acc = accuracy_score(y_test, preds)

    return model, acc


def retrain_full(X_all, y_all, best_rounds):
    """Retrain on all available data with the known best iteration count."""
    dall = xgb.DMatrix(X_all, label=y_all, feature_names=FEATURE_COLS, enable_categorical=False)

    params = {
        'objective': 'multi:softprob',
        'num_class': 3,
        'eval_metric': 'mlogloss',
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 5,
        'seed': 42,
        'verbosity': 0,
    }

    model = xgb.train(params, dall, num_boost_round=best_rounds)
    return model


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_predictions_pipeline():
    """End-to-end: scrape fixtures, build features, train, predict, store."""
    print("\n--- Match Predictions Pipeline ---")

    # 1. Load all historical data
    print("\n[1/6] Loading historical data...")
    raw_df = get_raw_matches()
    elo_df = get_elo_match_history()
    xg_df = get_xg_matches()
    elo_ratings = get_elo_ratings()
    print(f"   raw_matches: {len(raw_df)}, elo_history: {len(elo_df)}, xg: {len(xg_df)}")

    # 2. Build feature matrix
    print("\n[2/6] Building feature matrix...")
    fm = build_feature_matrix(raw_df, elo_df, xg_df)

    # Pre-compute team histories for fixture features later
    th = _build_team_history(raw_df)
    xg_roll = _build_xg_rolling(xg_df)

    # 3. Scrape upcoming fixtures
    print("\n[3/6] Scraping upcoming fixtures...")
    all_fixtures = []
    for league_key in LEAGUE_KEYS:
        season_code = CURRENT_SEASON
        fixtures = scrape_fixtures(league_key, season_code)
        all_fixtures.extend(fixtures)
        time.sleep(1)

    # Map Understat names to football-data names
    for f in all_fixtures:
        f['home_team'] = _map_name(f['home_team'])
        f['away_team'] = _map_name(f['away_team'])

    upload_upcoming_fixtures(all_fixtures)
    fixtures_df = pd.DataFrame(all_fixtures)
    print(f"   Total upcoming fixtures: {len(fixtures_df)}")

    if len(fixtures_df) == 0:
        print("   No upcoming fixtures found. Skipping predictions.")
        return

    # 4. Train per-league models and predict
    print("\n[4/6] Training per-league models...")
    all_predictions = []

    for league_key in LEAGUE_KEYS:
        display = LEAGUES[league_key]['display_name']
        league_fm = fm[fm['league'] == league_key].copy()

        if len(league_fm) < 50:
            print(f"   {display}: insufficient data ({len(league_fm)} matches), skipping")
            continue

        train_mask = league_fm['season'].isin(TRAIN_SEASONS)
        val_mask = league_fm['season'].isin(VAL_SEASONS)
        test_mask = league_fm['season'].isin(TEST_SEASONS)

        X_train = league_fm.loc[train_mask, FEATURE_COLS]
        y_train = league_fm.loc[train_mask, 'target']
        X_val = league_fm.loc[val_mask, FEATURE_COLS]
        y_val = league_fm.loc[val_mask, 'target']
        X_test = league_fm.loc[test_mask, FEATURE_COLS]
        y_test = league_fm.loc[test_mask, 'target']

        # Drop rows with missing target
        for X, y, name in [(X_train, y_train, 'train'), (X_val, y_val, 'val'), (X_test, y_test, 'test')]:
            valid = y.notna()
            X, y = X[valid], y[valid]

        if len(X_train) < 30 or len(X_val) < 10:
            print(f"   {display}: insufficient split sizes, skipping")
            continue

        # Train with early stopping
        model, test_acc = train_and_evaluate(
            X_train.values, y_train.values.astype(int),
            X_val.values, y_val.values.astype(int),
            X_test.values if len(X_test) > 0 else X_val.values,
            y_test.values.astype(int) if len(y_test) > 0 else y_val.values.astype(int),
        )

        best_rounds = model.best_iteration + 1 if hasattr(model, 'best_iteration') else 200
        print(f"   {display}: test acc={test_acc:.3f} (n={len(X_test)}), best_rounds={best_rounds}")

        # Retrain on all data
        X_all = league_fm.loc[league_fm['target'].notna(), FEATURE_COLS]
        y_all = league_fm.loc[league_fm['target'].notna(), 'target'].astype(int)
        final_model = retrain_full(X_all.values, y_all.values, best_rounds)

        # 5. Predict upcoming fixtures for this league
        league_fixtures = fixtures_df[fixtures_df['league'] == league_key].copy()
        if len(league_fixtures) == 0:
            continue

        # Find the next gameweek (earliest batch of fixtures)
        league_fixtures['match_date_dt'] = pd.to_datetime(league_fixtures['match_date'])
        min_date = league_fixtures['match_date_dt'].min()
        next_gw = league_fixtures[
            league_fixtures['match_date_dt'] <= min_date + pd.Timedelta(days=4)
        ]

        X_pred = build_fixture_features(next_gw, raw_df, elo_ratings, th, xg_roll)
        dpred = xgb.DMatrix(X_pred.values, feature_names=FEATURE_COLS)
        probs = final_model.predict(dpred)

        for i, (_, fix) in enumerate(next_gw.iterrows()):
            h_prob, d_prob, a_prob = probs[i]
            pred_class = int(probs[i].argmax())

            nan_count = X_pred.iloc[i].isna().sum()
            low_conf = nan_count > len(FEATURE_COLS) / 2

            all_predictions.append({
                'league': league_key,
                'season': CURRENT_SEASON,
                'home_team': fix['home_team'],
                'away_team': fix['away_team'],
                'match_date': fix['match_date'],
                'predicted_result': RESULT_DECODE[pred_class],
                'home_win_prob': float(h_prob),
                'draw_prob': float(d_prob),
                'away_win_prob': float(a_prob),
                'model_accuracy': float(test_acc),
                'low_confidence': bool(low_conf),
            })

    # 6. Store predictions
    print(f"\n[5/6] Storing {len(all_predictions)} predictions...")
    if all_predictions:
        upload_predictions(all_predictions)

    print("\n[6/6] Predictions pipeline complete!")
    return all_predictions
