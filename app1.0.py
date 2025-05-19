import streamlit as st
st.set_page_config(layout="wide")

# --- Simple password protection ---
PASSWORD = "!EASY_WEIGHT!1234!"
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if not st.session_state['authenticated']:
    st.title("Athlete Training Progress Viewer (Aggregated)")
    pw = st.text_input("Enter password to access the app:", type="password")
    if pw == PASSWORD:
        st.session_state['authenticated'] = True
        st.rerun()
    elif pw:
        st.error("Incorrect password. Please try again.")
    st.stop()
# --- End password protection ---

import pandas as pd
import os
import plotly.graph_objects as go

AGGREGATED_DIR = "aggregated_athletes"

st.title("Athlete Training Progress Viewer (Aggregated)")
# List available athlete CSVs
def get_athlete_files():
    files = [f for f in os.listdir(AGGREGATED_DIR) if f.endswith('.csv')]
    return files
athlete_files = get_athlete_files()
athlete_file = st.selectbox("Select athlete:", athlete_files)

if 'athlete_file' in locals() and athlete_file:
    df = pd.read_csv(os.path.join(AGGREGATED_DIR, athlete_file))
    # Standardize category capitalization
    if 'Category' in df.columns:
        df['Category'] = df['Category'].astype(str).str.strip().str.title()
        # Remove rows with missing, empty, or 'Nan' category
        df = df[df['Category'].notna() & (df['Category'] != '') & (df['Category'].str.lower() != 'nan')]
    # Ensure 'Volume' column exists for all downstream operations
    if 'Volume' not in df.columns:
        df['Volume'] = df['Set_Reps'] * df['Set_Weight']
    with st.expander("Data for Week", expanded=False):
        weeks = sorted(df['Week'].dropna().unique())
        selected_week = st.selectbox("Select week:", weeks)
        week_df = df[df['Week'] == selected_week]
        st.subheader(f"Data for Week: {selected_week}")
        st.dataframe(week_df)
        # Calculate volume per set
        week_df['Volume'] = week_df['Set_Reps'] * week_df['Set_Weight']
        # Weekly/category metrics for the selected week
        st.header("Weekly Metrics by Category (Selected Week)")
        weekly_metrics = week_df.groupby(['Category']).agg(
            Total_Volume=('Volume', 'sum'),
            Total_Reps=('Set_Reps', 'sum'),
            Total_Executed_Sets=('Set', 'count'),
            Max_Weight=('Set_Weight', 'max')
        ).reset_index()
        st.dataframe(weekly_metrics)
    with st.expander("Trends by Category (All Weeks)", expanded=False):
        # Use all prescribed categories for the selector (not just those with executed sets)
        prescribed_categories = sorted(df[df['Set'].notna() & df['Set_Reps'].notna()]['Category'].dropna().unique())
        selected_category = st.selectbox("Select a category:", prescribed_categories)
        # All unique weeks in the dataset
        all_weeks = sorted(df['Week'].dropna().astype(str).unique())
        # Prescribed sets: count unique (Day of the Week, Set) pairs for the selected category
        prescribed_mask = (df['Category'] == selected_category)
        prescribed_df = df[prescribed_mask]
        prescribed_df = prescribed_df[prescribed_df['Set'].notna() & prescribed_df['Set_Reps'].notna()]
        prescribed_df['Week'] = prescribed_df['Week'].astype(str)
        prescribed_sets = prescribed_df.groupby('Week').apply(lambda x: x.drop_duplicates(subset=['Day of the Week', 'Set']).shape[0]).reset_index(name='Total_Prescribed_Sets')
        prescribed_sets = prescribed_sets.set_index('Week').reindex(all_weeks, fill_value=0).reset_index()
        # Executed sets: only rows with Set, Set_Reps, Set_Weight not null
        executed_mask = (
            df['Category'] == selected_category
        ) & df['Set'].notna() & df['Set_Reps'].notna() & df['Set_Weight'].notna()
        cat_df = df[executed_mask]
        cat_df['Week'] = cat_df['Week'].astype(str)
        executed_sets = cat_df.groupby('Week').agg(
            Total_Executed_Sets=('Set', 'count'),
            Total_Lifted_Weight=('Volume', 'sum'),
            Total_Reps=('Set_Reps', 'sum'),
            Max_Weight=('Set_Weight', 'max')
        ).reset_index()
        executed_sets = executed_sets.set_index('Week').reindex(all_weeks, fill_value=0).reset_index()
        # Merge prescribed and executed sets
        week_group = pd.merge(prescribed_sets, executed_sets, on='Week', how='outer').sort_values('Week')
        week_group['Total_Executed_Sets'] = week_group['Total_Executed_Sets'].fillna(0)
        week_group['Total_Lifted_Weight'] = week_group['Total_Lifted_Weight'].fillna(0)
        week_group['Total_Reps'] = week_group['Total_Reps'].fillna(0)
        week_group['Max_Weight'] = week_group['Max_Weight'].fillna(0)
        week_group['Average_Load'] = week_group['Total_Lifted_Weight'] / week_group['Total_Reps']
        week_group['Average_Load'] = week_group['Average_Load'].fillna(0)
        fig = go.Figure()
        # Bars on primary y-axis
        fig.add_trace(go.Bar(x=week_group['Week'], y=week_group['Total_Prescribed_Sets'], name='Prescribed Sets', marker_color='grey', opacity=0.5))
        fig.add_trace(go.Bar(x=week_group['Week'], y=week_group['Total_Executed_Sets'], name='Executed Sets', marker_color='orange', opacity=0.6))
        # Lines on secondary y-axis
        fig.add_trace(go.Scatter(x=week_group['Week'], y=week_group['Average_Load'], mode='lines+markers', name='Average Load', line=dict(color='blue'), yaxis='y2'))
        fig.add_trace(go.Scatter(x=week_group['Week'], y=week_group['Max_Weight'], mode='markers', name='Weekly max', marker=dict(color='red', size=10), yaxis='y2'))
        fig.update_layout(
            title=f"Average Load, Executed vs Prescribed Sets, and Max Load for {selected_category} Over Time",
            xaxis=dict(title='Week'),
            yaxis=dict(title='Sets', tickfont=dict(color='orange'), showgrid=True),
            yaxis2=dict(title='Average Load / Max Weight', tickfont=dict(color='blue'), overlaying='y', side='right', showgrid=False),
            legend=dict(x=1.02, y=1),
            template='plotly_white',
            bargap=0.5
        )
        st.plotly_chart(fig, use_container_width=True)
    with st.expander("Personal Records (1RM)", expanded=False):
        # Only consider rows where Set_Reps == 1 and Set_Weight is not null and > 0
        pr_df = df[(df['Set_Reps'] == 1) & (df['Set_Weight'].notna()) & (df['Set_Weight'] > 0)]
        # Find PR for each category and get the corresponding week and exercise
        pr_table = (
            pr_df.loc[pr_df.groupby('Category')['Set_Weight'].idxmax()]
            .groupby('Category')
            .agg(Personal_Record_1RM_Weight=('Set_Weight', 'max'),
                 Week=('Week', 'first'),
                 Exercise=('Exercise', 'first'))
            .reset_index()
        )
        st.dataframe(pr_table)
