import math
import pandas as pd

class EloTracker:
    def __init__(self, k_factor_stable=20, k_factor_volatile=40, volatile_match_count=30, home_advantage=60, base_rating=1500):
        """
        Initialize the ELO tracking system with dynamic K-factors.
        
        Args:
            k_factor_stable (int): Standard K for established teams (default 20).
            k_factor_volatile (int): High K for new/provisionally rated teams (default 40).
            volatile_match_count (int): Number of matches a team plays before switching to stable K (default 30).
            home_advantage (int): Points added to home team rating for prediction.
            base_rating (int): Starting rating for new teams.
        """
        self.ratings = {}      # {team_name: rating}
        self.match_counts = {} # {team_name: count}
        self.history = []      # List of match dicts
        
        self.k_stable = k_factor_stable
        self.k_volatile = k_factor_volatile
        self.volatile_limit = volatile_match_count
        self.home_adv = home_advantage
        self.base = base_rating

    def get_rating(self, team):
        """Get current rating for a team, initializing if new."""
        return self.ratings.get(team, self.base)
    
    def get_k_factor(self, team):
        """Determine K-factor based on how many games the team has played."""
        count = self.match_counts.get(team, 0)
        if count < self.volatile_limit:
            return self.k_volatile
        return self.k_stable

    def _expected_score(self, rating_a, rating_b):
        """
        Calculate expected score (win probability) for team A vs team B.
        Standard logistic curve formula.
        """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def _get_margin_multiplier(self, goal_diff):
        """
        Calculate multiplier based on goal difference.
        Winning by more goals should yield more points.
        Formula roughly based on World Football ELO.
        """
        if goal_diff <= 0:
            return 1  # Should not happen for winner (logic handled in process_match)
        elif goal_diff == 1:
            return 1.0
        elif goal_diff == 2:
            return 1.5
        else:
            # Diminishing returns for huge blowouts: (11 + diff) / 8
            return (11 + goal_diff) / 8

    def process_match(self, home_team, away_team, fthg, ftag, date, season, league):
        """
        Update ratings based on a single match result.
        """
        # Get current state
        r_home = self.get_rating(home_team)
        r_away = self.get_rating(away_team)
        
        k_home = self.get_k_factor(home_team)
        k_away = self.get_k_factor(away_team)

        # Determine match outcome (1 = Home Win, 0.5 = Draw, 0 = Away Win)
        if fthg > ftag:
            actual_home = 1.0
            goal_diff = fthg - ftag
        elif fthg == ftag:
            actual_home = 0.5
            goal_diff = 0
        else:
            actual_home = 0.0
            goal_diff = ftag - fthg

        # Calculate Expected Score (Home team gets advantage boost for calculation only)
        expected_home = self._expected_score(r_home + self.home_adv, r_away)
        
        # Margin of Victory Multiplier (applies to both)
        g_mult = self._get_margin_multiplier(goal_diff)

        # Calculate Rating Deltas
        # Note: We calculate separate deltas because K-factors might differ!
        # Delta = K * G * (Actual - Expected)
        
        delta_home = k_home * g_mult * (actual_home - expected_home)
        
        # For away team, Expected_Away = 1 - Expected_Home
        # Actual_Away = 1 - Actual_Home
        # So (Actual_Away - Expected_Away) is just -(Actual_Home - Expected_Home)
        delta_away = k_away * g_mult * ((1 - actual_home) - (1 - expected_home))
        
        # Update Ratings
        new_home = r_home + delta_home
        new_away = r_away + delta_away

        self.ratings[home_team] = new_home
        self.ratings[away_team] = new_away
        
        # Update Match Counts
        self.match_counts[home_team] = self.match_counts.get(home_team, 0) + 1
        self.match_counts[away_team] = self.match_counts.get(away_team, 0) + 1

        # Log history
        self.history.append({
            'Date': date,
            'Season': season,
            'League': league,
            'HomeTeam': home_team,
            'AwayTeam': away_team,
            'FTHG': fthg,
            'FTAG': ftag,
            'HomeRating_Before': round(r_home, 2),
            'AwayRating_Before': round(r_away, 2),
            'HomeRating_After': round(new_home, 2),
            'AwayRating_After': round(new_away, 2),
            'Expected_Home_Win': round(expected_home, 3),
            'Rating_Change_Home': round(delta_home, 2),
            'Rating_Change_Away': round(delta_away, 2)
        })

    def process_league_season(self, df, season, league_key):
        """
        Process an entire season DataFrame chronologically.
        Expects DF to have columns: Date, HomeTeam, AwayTeam, FTHG, FTAG.
        """
        # Ensure chronological order
        if not pd.api.types.is_datetime64_any_dtype(df['Date']):
             df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
             
        df = df.sort_values('Date')
        
        for _, row in df.iterrows():
            self.process_match(
                home_team=row['HomeTeam'],
                away_team=row['AwayTeam'],
                fthg=row['FTHG'],
                ftag=row['FTAG'],
                date=row['Date'],
                season=season,
                league=league_key
            )

    def get_history_df(self):
        """Return the entire match history with ratings as a DataFrame."""
        return pd.DataFrame(self.history)

    def get_current_ratings_df(self):
        """Return current ratings for all teams."""
        data = [{'Team': k, 'Elo': round(v, 2), 'Matches': self.match_counts.get(k, 0)} for k, v in self.ratings.items()]
        df = pd.DataFrame(data).sort_values('Elo', ascending=False)
        df['Rank'] = range(1, len(df) + 1)
        return df[['Rank', 'Team', 'Elo', 'Matches']]
