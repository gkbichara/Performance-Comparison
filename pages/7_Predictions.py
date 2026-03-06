"""
Match Predictions - XGBoost model predictions for upcoming fixtures.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.database import get_predictions
from src.config import LEAGUE_DISPLAY_NAMES, CURRENT_SEASON, SEASON_DISPLAY_NAMES

st.set_page_config(
    page_title="Predictions | Gaffer's Notebook",
    layout="wide"
)

st.title("Match Predictions")
st.markdown("XGBoost model predictions for the next gameweek, trained on ELO, form, xG, and head-to-head data.")
st.divider()


@st.cache_data(ttl=3600)
def load_predictions():
    return get_predictions(season=CURRENT_SEASON)


preds_df = load_predictions()

if len(preds_df) == 0:
    st.warning("No predictions available yet. Run the pipeline to generate predictions.")
    st.stop()

preds_df['league_display'] = preds_df['league'].map(LEAGUE_DISPLAY_NAMES)
preds_df['match_date'] = pd.to_datetime(preds_df['match_date'])

# --- League selector ---
leagues = sorted(preds_df['league_display'].dropna().unique().tolist())
selected_league = st.selectbox(
    "League",
    options=leagues,
    index=0,
    key="pred_league"
)

league_df = preds_df[preds_df['league_display'] == selected_league].copy()
league_df = league_df.sort_values('match_date')

if len(league_df) == 0:
    st.info("No predictions for this league.")
    st.stop()

# Model accuracy badge
model_acc = league_df['model_accuracy'].iloc[0]
season_display = SEASON_DISPLAY_NAMES.get(CURRENT_SEASON, CURRENT_SEASON)

st.caption(
    f"Model accuracy on {season_display} test set: **{model_acc:.1%}** · "
    f"{len(league_df)} fixtures predicted"
)

st.divider()

# --- Fixture predictions ---
RESULT_LABELS = {'H': 'Home Win', 'D': 'Draw', 'A': 'Away Win'}
RESULT_COLORS = {'H': '#22c55e', 'D': '#f59e0b', 'A': '#ef4444'}


def confidence_level(prob):
    if prob >= 0.60:
        return "high"
    elif prob >= 0.40:
        return "medium"
    return "low"


def confidence_color(level):
    return {'high': '#22c55e', 'medium': '#f59e0b', 'low': '#6b7280'}[level]


for _, match in league_df.iterrows():
    pred = match['predicted_result']
    h_prob = match['home_win_prob']
    d_prob = match['draw_prob']
    a_prob = match['away_win_prob']
    low_conf = match.get('low_confidence', False)
    winning_prob = max(h_prob, d_prob, a_prob)
    conf = confidence_level(winning_prob)

    # Match container
    with st.container():
        col_home, col_vs, col_away, col_pred = st.columns([3, 1, 3, 4])

        with col_home:
            home_style = "**" if pred == 'H' else ""
            st.markdown(
                f"<div style='text-align:right; font-size:1.1em; padding-top:8px;'>"
                f"{home_style}{match['home_team']}{home_style}</div>",
                unsafe_allow_html=True,
            )

        with col_vs:
            st.markdown(
                "<div style='text-align:center; color:#6b7280; padding-top:8px;'>vs</div>",
                unsafe_allow_html=True,
            )

        with col_away:
            away_style = "**" if pred == 'A' else ""
            st.markdown(
                f"<div style='font-size:1.1em; padding-top:8px;'>"
                f"{away_style}{match['away_team']}{away_style}</div>",
                unsafe_allow_html=True,
            )

        with col_pred:
            pred_color = RESULT_COLORS[pred]
            conf_color = confidence_color(conf)
            low_tag = " · ⚠ low data" if low_conf else ""

            st.markdown(
                f"<div style='display:flex; align-items:center; gap:8px; padding-top:4px;'>"
                f"<span style='background:{pred_color}; color:white; padding:2px 10px; "
                f"border-radius:4px; font-weight:600; font-size:0.85em;'>"
                f"{RESULT_LABELS[pred]}</span>"
                f"<span style='color:{conf_color}; font-size:0.8em;'>"
                f"{winning_prob:.0%} confidence{low_tag}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Probability bar
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=[''], x=[h_prob], name='Home', orientation='h',
                marker_color='#22c55e', text=f'{h_prob:.0%}',
                textposition='inside', textfont=dict(size=11, color='white'),
                hovertemplate='Home Win: %{x:.1%}<extra></extra>',
            ))
            fig.add_trace(go.Bar(
                y=[''], x=[d_prob], name='Draw', orientation='h',
                marker_color='#f59e0b', text=f'{d_prob:.0%}',
                textposition='inside', textfont=dict(size=11, color='white'),
                hovertemplate='Draw: %{x:.1%}<extra></extra>',
            ))
            fig.add_trace(go.Bar(
                y=[''], x=[a_prob], name='Away', orientation='h',
                marker_color='#ef4444', text=f'{a_prob:.0%}',
                textposition='inside', textfont=dict(size=11, color='white'),
                hovertemplate='Away Win: %{x:.1%}<extra></extra>',
            ))
            fig.update_layout(
                barmode='stack',
                height=32, margin=dict(l=0, r=0, t=0, b=0),
                showlegend=False,
                xaxis=dict(visible=False, range=[0, 1]),
                yaxis=dict(visible=False),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("<hr style='margin:4px 0; border-color:#333;'>", unsafe_allow_html=True)


# --- Model performance expander ---
with st.expander("Model Performance", expanded=False):
    st.markdown(f"**{selected_league}** — {season_display}")
    st.metric("Test Set Accuracy", f"{model_acc:.1%}")
    st.caption(
        "The model is trained on seasons 2020/21 through 2023/24, validated on 2024/25, "
        f"and tested on {season_display} completed matches. "
        "It uses ELO ratings, rolling form (overall + venue-specific), xG stats, "
        "and head-to-head history as features. Missing data (e.g. promoted teams) "
        "is handled natively by XGBoost."
    )

    # Summary table
    summary_data = {
        'Prediction': ['Home Win', 'Draw', 'Away Win'],
        'Count': [
            len(league_df[league_df['predicted_result'] == 'H']),
            len(league_df[league_df['predicted_result'] == 'D']),
            len(league_df[league_df['predicted_result'] == 'A']),
        ],
        'Avg Confidence': [
            league_df[league_df['predicted_result'] == 'H']['home_win_prob'].mean(),
            league_df[league_df['predicted_result'] == 'D']['draw_prob'].mean(),
            league_df[league_df['predicted_result'] == 'A']['away_win_prob'].mean(),
        ],
    }
    summary = pd.DataFrame(summary_data)
    summary['Avg Confidence'] = summary['Avg Confidence'].map(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
    st.dataframe(summary, hide_index=True, use_container_width=True)
