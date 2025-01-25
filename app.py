import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import pandas as pd
import os

def load_data_from_folder(folder_path):
    """Load all Excel files from the specified folder as a dictionary of week-wise data."""
    excel_files = [f for f in os.listdir(folder_path) if f.endswith('.xlsx') and (f.startswith('2025_week_') or f.startswith('2024_week_'))]
    weeks_data = {}
    for file in excel_files:
        week_name = file.split('.')[0]
        try:
            weeks_data[week_name] = pd.read_excel(os.path.join(folder_path, file), sheet_name=None)
        except Exception as e:
            st.error(f"Error loading {file}: {e}")
    return weeks_data

def calculate_metrics(data):
    """Calculate adherence, total volume, and missed lifts."""
    adherence = []
    total_volume = []
    missed_lifts = []
    total_executed_sets = []


    for _, row in data.iterrows():
        planned_sets = row.get('Sets', 0)
        completed_sets = sum(pd.notna(row.get(f'Set {i} Reps')) for i in range(1, 9))
        adherence.append(completed_sets / planned_sets if planned_sets > 0 else 0)
        total_executed_sets.append(completed_sets)  # Count executed sets


        volume = sum(
            (row.get(f'Set {i} Reps', 0) or 0) * (row.get(f'Set {i} Weight', 0) or 0)
            for i in range(1, 9)
            if pd.notna(row.get(f'Set {i} Reps')) and pd.notna(row.get(f'Set {i} Weight'))
        )
        total_volume.append(volume)

        missed = sum(
            max(0, (row.get('Reps', 0) or 0) - (row.get(f'Set {i} Reps', 0) or 0))
            for i in range(1, 9)
            if pd.notna(row.get(f'Set {i} Reps'))
        )
        missed_lifts.append(missed)

    data['Adherence'] = adherence
    data['Total Volume'] = total_volume
    data['Missed Lifts'] = missed_lifts
    data['Total_Executed_Sets'] = total_executed_sets  # Add column here

    return data

# Function to calculate personal records (PRs)
def calculate_personal_records(data, week_name):
    """
    Calculate personal records (highest weight for 1 rep) for each category,
    including the exercise variation and the file name.
    """
    # Define categories of interest
    categories_of_interest = ["Snatch", "Clean", "Jerk", "Clean and Jerk", "Back Squat", "Front Squat"]

    # Map alternative names for Back Squat and Front Squat
    squat_mapping = {
        "Front Squat": ["Front squat", "Gambe avanti"],
        "Back Squat": ["Back squat", "Gambe dietro"]
    }

    pr_data = []

    for category in categories_of_interest:
        # Handle squats with alternative names
        if category in squat_mapping:
            category_data = data[data['Exercise'].isin(squat_mapping[category]) & (data['Reps'] == 1)]
        else:
            category_data = data[(data['Category'] == category) & (data['Reps'] == 1)]

        max_weight = 0  # Initialize max weight for the category
        exercise_name = None  # Initialize exercise name

        for _, row in category_data.iterrows():
            # Extract weights from the sets, skipping invalid or NaN values
            weights = [
                row.get(f'Set {i} Weight', 0)
                for i in range(1, 9)
                if pd.notna(row.get(f'Set {i} Weight'))
            ]
            if weights:  # Check if there are valid weights
                row_max_weight = max(weights)
                if row_max_weight > max_weight:
                    max_weight = row_max_weight
                    exercise_name = row['Exercise']  # Store the exercise name

        if max_weight > 0:  # Only add if a valid max weight exists
            pr_data.append({
                'Category': category,
                'Personal Record (1RM Weight)': max_weight,
                'Exercise': exercise_name,
                'File': week_name  # Add the week/file name
            })

    return pd.DataFrame(pr_data)


def calculate_training_sessions_per_week(weeks_data, athlete_name):
    """
    Calculate the number of training sessions performed by the athlete for each week.

    Args:
        weeks_data (dict): Dictionary containing weekly data with athlete sheets.
        athlete_name (str): Name of the athlete to process.

    Returns:
        pd.DataFrame: DataFrame with the week name and the number of training sessions performed.
    """
    sessions_per_week = []

    for week_name, week_data in weeks_data.items():
        if athlete_name in week_data:
            athlete_data = week_data[athlete_name]

            # Group by 'Day of the Week' to identify distinct training sessions
            if 'Day of the Week' in athlete_data.columns:
                performed_sessions = athlete_data.groupby('Day of the Week').apply(
                    lambda group: group['Sets'].sum() > 0
                ).sum()  # Count only sessions with prescribed sets > 0
                sessions_per_week.append({'Week': week_name, 'Performed Sessions': int(performed_sessions)})
            else:
                sessions_per_week.append({'Week': week_name, 'Performed Sessions': 0})

    return pd.DataFrame(sessions_per_week)


# Athlete Overview Tab
def athlete_overview(data):
    st.title("Athlete Overview")

    # Existing athlete metrics
    st.header("Weekly Training Metrics")
    # Example logic here...

    # New Personal Records Section
    st.header("Personal Records")
    
    # Calculate personal records
    pr_table = calculate_personal_records(data)
    
    # Display the table
    if not pr_table.empty:
        st.table(pr_table)
    else:
        st.warning("No personal records found for this athlete.")

# Main App
def main():

    # Load data (replace with your Excel files processing logic)
    data = pd.DataFrame({
        'Category': ['Snatch', 'Clean', 'Jerk', 'Clean', 'Snatch', 'Jerk', 'Clean and Jerk'],
        'Exercise': ['Power Snatch', 'Full Clean', 'Split Jerk', 'Hang Clean', 'Full Snatch', 'Push Jerk', 'Clean and Jerk'],
        'Reps': [1, 1, 1, 2, 1, 1, 1],
        'Load': [90, 120, 100, 110, 95, 105, 130]
    })  # Replace with actual data loading logic

# Run the app
if __name__ == "__main__":
    main()

def calculate_all_category_metrics(data):
    """
    Calculate metrics for all categories of exercises, 
    only including categories with prescribed sets > 0.
    """
    categories = ["Snatch", "Clean", "Jerk", "Clean and Jerk", "Squat", "Accessorize"]
    metrics = []

    for category in categories:
        category_data = data[data['Category'] == category]
        total_prescribed_sets = category_data['Sets'].sum()

        if total_prescribed_sets == 0:
            continue

        total_executed_sets = category_data['Total_Executed_Sets'].sum()
        total_missed_lifts = category_data['Missed Lifts'].sum()
        total_lifted_weight = sum(
            sum((row[f'Set {i} Reps'] or 0) * (row[f'Set {i} Weight'] or 0)
                for i in range(1, 9)
                if pd.notna(row[f'Set {i} Reps']) and pd.notna(row[f'Set {i} Weight']))
            for _, row in category_data.iterrows()
        )
        total_reps = sum(
            sum(row[f'Set {i} Reps'] or 0
                for i in range(1, 9)
                if pd.notna(row[f'Set {i} Reps']))
            for _, row in category_data.iterrows()
        )
        average_load = round(total_lifted_weight / total_reps, 2) if total_reps > 0 else 0

        metrics.append({
            'Category': category,
            'Total Prescribed Sets': round(total_prescribed_sets, 2),
            'Total Executed Sets': round(total_executed_sets, 2),
            'Total Missed Lifts': round(total_missed_lifts, 2),
            'Average Load Lifted': round(average_load, 2)
        })

    return pd.DataFrame(metrics)

def split_sessions(data):
    """
    Split data into training sessions based on 'Day of the Week'.
    Only return sessions with prescribed sets > 0.
    """
    sessions = []

    if 'Day of the Week' not in data.columns:
        raise ValueError("'Day of the Week' column is missing from the data.")

    # Group rows by 'Day of the Week'
    for day, session_data in data.groupby('Day of the Week'):
        # Filter out sessions with no prescribed sets
        if session_data['Sets'].sum() > 0:
            sessions.append(session_data.reset_index(drop=True))
    
    return sessions

def calculate_session_metrics(session):
    """Calculate metrics for a single training session grouped by category."""
    session = calculate_metrics(session)
    return calculate_all_category_metrics(session)

def cumulate_athlete_data(weeks_data, athlete_name):
    """Cumulate all weeks' data for a specific athlete."""
    cumulated_data = []

    for week_name, week_data in weeks_data.items():
        if athlete_name in week_data:
            athlete_data = week_data[athlete_name]
            athlete_data['Week'] = week_name  # Add week identifier
            cumulated_data.append(athlete_data)

    if cumulated_data:
        return pd.concat(cumulated_data, ignore_index=True)
    else:
        return pd.DataFrame()  # Return empty DataFrame if no data

# Streamlit app
st.title("Athlete Training Progress Viewer")

# Select folder containing Excel files
folder_path = st.text_input("Enter the folder path containing Excel files:")

if folder_path:
    try:
        # Load data
        weeks_data = load_data_from_folder(folder_path)

        # Tabs for different views
        tab1, tab2 = st.tabs(["Weekly View", "Athlete Overview"])

        with tab1:
            st.header("Weekly View")

            # Select week
            selected_week = st.selectbox("Select a week:", list(weeks_data.keys()))
            week_data = weeks_data[selected_week]

            # Select athlete (sheet)
            selected_athlete = st.selectbox("Select an athlete:", list(week_data.keys()))
            athlete_data = week_data[selected_athlete]

            # Display raw athlete data
            st.write("### Raw Athlete Data")
            st.dataframe(athlete_data.fillna(''))  # Replace None/NaN with empty cells

            # Display weekly metrics for all exercise categories
            try:
                athlete_data = calculate_metrics(athlete_data)  # Ensure metrics are calculated
                st.write("### Weekly Metrics by Exercise Category")
                weekly_metrics = calculate_all_category_metrics(athlete_data)

                if not weekly_metrics.empty:
                    # Format specific columns for display with 2 decimals
                    st.table(weekly_metrics.style.format({
                        "Total Prescribed Sets": "{:.2f}",
                        "Total Executed Sets": "{:.2f}",
                        "Total Missed Lifts": "{:.2f}",
                        "Average Load Lifted": "{:.2f}"
                    }))
                else:
                    st.warning("No prescribed sets found for any exercise category this week.")
            except Exception as e:
                st.error(f"Error calculating weekly metrics: {e}")

            # Split sessions and display data for each session
            try:
                sessions = split_sessions(athlete_data)

                if not sessions:
                    st.warning("No prescribed training sessions for this week.")
                else:
                    for i, session in enumerate(sessions):
                        st.write(f"### Session {i + 1}")
                        st.write("#### Training Data")
                        st.dataframe(session.fillna(''))  # Replace None/NaN with empty cells

                        # Calculate and display session metrics
                        if not session.empty:
                            session_metrics = calculate_session_metrics(session)
                            st.write("#### Metrics by Category")
                            st.table(session_metrics.style.format({
                                "Total Prescribed Sets": "{:.2f}",
                                "Total Executed Sets": "{:.2f}",
                                "Total Missed Lifts": "{:.2f}",
                                "Average Load Lifted": "{:.2f}"
                            }))
                        else:
                            st.warning("No data to display for this session.")
            except Exception as e:
                st.error(f"Error splitting or processing sessions: {e}")

        with tab2:
            st.header("Athlete Overview")

            # Select athlete
            athlete_names = list(set(sheet_name for week in weeks_data.values() for sheet_name in week.keys()))
            selected_athlete = st.selectbox("Select an athlete:", athlete_names)

            # Cumulate data
            cumulated_data = cumulate_athlete_data(weeks_data, selected_athlete)

            if not cumulated_data.empty:
                # Select category
                categories = ["Snatch", "Clean", "Jerk", "Clean and Jerk", "Combined C&J", "Squat", "Accessorize"]
                selected_category = st.selectbox("Select a category:", categories)

                # Filter data by category
                if selected_category == "Combined C&J":
                    filtered_data = cumulated_data[cumulated_data['Category'].isin(["Clean", "Jerk", "Clean and Jerk"])]
                else:
                    filtered_data = cumulated_data[cumulated_data['Category'] == selected_category]

                if not filtered_data.empty:
                    # Calculate total lifted weight, reps, and executed sets
                    filtered_data['Total Lifted Weight'] = filtered_data.apply(
                        lambda row: sum((row[f'Set {i} Reps'] or 0) * (row[f'Set {i} Weight'] or 0)
                                        for i in range(1, 9)
                                        if pd.notna(row[f'Set {i} Reps']) and pd.notna(row[f'Set {i} Weight'])),
                        axis=1
                    )
                    filtered_data['Total Reps'] = filtered_data.apply(
                        lambda row: sum((row[f'Set {i} Reps'] or 0)
                                        for i in range(1, 9)
                                        if pd.notna(row[f'Set {i} Reps'])),
                        axis=1
                    )
                    filtered_data['Total Executed Sets'] = filtered_data.apply(
                        lambda row: sum(pd.notna(row[f'Set {i} Reps']) for i in range(1, 9)),
                        axis=1
                    )
                    filtered_data['Average Load'] = filtered_data['Total Lifted Weight'] / filtered_data['Total Reps']
                    filtered_data['Average Load'] = filtered_data['Average Load'].fillna(0)

                    # Group by week
                    weekly_metrics = filtered_data.groupby('Week').agg(
                        Total_Lifted_Weight=('Total Lifted Weight', 'sum'),
                        Total_Reps=('Total Reps', 'sum'),
                        Total_Executed_Sets=('Total Executed Sets', 'sum')
                    ).reset_index()

                    # Calculate weighted average load
                    weekly_metrics['Average_Load'] = weekly_metrics['Total_Lifted_Weight'] / weekly_metrics['Total_Reps']
                    weekly_metrics['Average_Load'] = weekly_metrics['Average_Load'].fillna(0)  # Handle cases with 0 reps
                    # Plot using Plotly
                    fig = go.Figure()

                    # Add Average Load as a line (left y-axis)
                    fig.add_trace(
                        go.Scatter(
                            x=weekly_metrics['Week'],
                            y=weekly_metrics['Average_Load'],
                            mode='lines+markers',
                            name='Average Load',
                            line=dict(color='blue'),
                            yaxis='y'
                        )
                    )

                    # Add Total Executed Sets as a bar chart (right y-axis)
                    fig.add_trace(
                        go.Bar(
                            x=weekly_metrics['Week'],
                            y=weekly_metrics['Total_Executed_Sets'],
                            name='Total Executed Sets',
                            marker_color='orange',
                            opacity=0.6,
                            yaxis='y2'
                        )
                    )

                    # Update layout for dual y-axes
                    fig.update_layout(
                        title=f"Average Load and Total Executed Sets for {selected_category} Over Time",
                        xaxis=dict(title='Week'),
                        yaxis=dict(
                            title='Average Load',
                            titlefont=dict(color='blue'),
                            tickfont=dict(color='blue'),
                            showgrid=True
                        ),
                        yaxis2=dict(
                            title='Total Executed Sets',
                            titlefont=dict(color='orange'),
                            tickfont=dict(color='orange'),
                            overlaying='y',
                            side='right',
                            showgrid=False
                        ),
                        legend=dict(x=0.01, y=0.99),
                        template='plotly_white',
                        bargap=0.2
                    )

                    # Show the updated plot in Streamlit
                    st.plotly_chart(fig, use_container_width=True)
                #   Display Personal Records
                st.subheader("Personal Records")
                try:
                    pr_table = pd.DataFrame()
                    # Loop through all weeks to calculate PRs
                    for week_name, week_data in weeks_data.items():
                        if selected_athlete in week_data:
                            athlete_week_data = week_data[selected_athlete]
                            pr_week_table = calculate_personal_records(athlete_week_data, week_name)
                            pr_table = pd.concat([pr_table, pr_week_table], ignore_index=True)

                    # Drop duplicates to show only the highest PRs for each category
                    pr_table = pr_table.sort_values(by=["Category", "Personal Record (1RM Weight)"], ascending=False)
                    pr_table = pr_table.drop_duplicates(subset="Category", keep="first")

                    # Display the PR table
                    if not pr_table.empty:
                        st.table(pr_table)
                    else:
                        st.warning("No personal records found for this athlete.")
                except Exception as e:
                    st.error(f"Error calculating personal records: {e}")

                # Calculate the number of performed training sessions
                sessions_per_week = calculate_training_sessions_per_week(weeks_data, selected_athlete)
                # Add a subheader for the new plot
                st.subheader("Training Sessions Per Week")

                # Check if there is data to plot
                if not sessions_per_week.empty:
                    # Plot using Plotly
                    fig_sessions = go.Figure()

                    # Add a bar chart for performed training sessions
                    fig_sessions.add_trace(
                        go.Bar(
                            x=sessions_per_week['Week'],
                            y=sessions_per_week['Performed Sessions'],
                            name='Performed Training Sessions',
                            marker_color='green'
                        )
                    )

                    # Update layout
                    fig_sessions.update_layout(
                        title="Number of Performed Training Sessions per Week",
                        xaxis=dict(title="Week"),
                        yaxis=dict(title="Number of Training Sessions", 
                        range=[0, 7]), 
                        template="plotly_white",
                        bargap=0.2
                    )

                    # Display the plot
                    st.plotly_chart(fig_sessions, use_container_width=True)
                else:
                    st.warning("No training session data available for this athlete.")


            else:
                st.warning("No data available for the selected athlete.")


    except Exception as e:
        st.error(f"Error loading data: {e}")
