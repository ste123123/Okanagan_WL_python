import os
import pandas as pd

RAW_DATA_DIR = "C:\\Users\\stefa\\OneDrive\\Documents\\Okanagan_WL\\Okanagan_WL\\Training_data_raw"
OUTPUT_DIR = "C:\\Users\\stefa\\OneDrive\\Documents\\Okanagan_WL\\Okanagan_WL\\aggregated_athletes"
SET_COUNT = 8  # Number of sets per row

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Find all Excel files in the raw data directory
excel_files = [f for f in os.listdir(RAW_DATA_DIR) if f.endswith('.xlsx') and (f.startswith('2025_') or f.startswith('2024_'))]

athlete_data = {}

for file in excel_files:
    week_name = file.split('.')[0]
    file_path = os.path.join(RAW_DATA_DIR, file)
    xls = pd.ExcelFile(file_path)
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        if df.empty:
            continue
        df['Week'] = week_name
        df['Athlete'] = sheet_name
        # Skip rows where both Category and Exercise are empty or missing
        df = df[~((df['Category'].isna() | (df['Category'].astype(str).str.strip() == '')) & (df['Exercise'].isna() | (df['Exercise'].astype(str).str.strip() == '')))]
        # Melt sets to long format: always output a row for each prescribed set
        set_rows = []
        for i in range(1, SET_COUNT + 1):
            reps_col = f'Set {i} Reps'
            weight_col = f'Set {i} Weight'
            temp = df.copy()
            temp['Set'] = i
            temp['Set_Reps'] = temp[reps_col] if reps_col in df.columns else None
            temp['Set_Weight'] = temp[weight_col] if weight_col in df.columns else None
            set_rows.append(temp)
        long_df = pd.concat(set_rows, ignore_index=True)
        # Drop original set columns
        drop_cols = [f'Set {i} Reps' for i in range(1, SET_COUNT+1)] + [f'Set {i} Weight' for i in range(1, SET_COUNT+1)]
        long_df = long_df.drop(columns=[c for c in drop_cols if c in long_df.columns])
        # Reorder columns
        cols = ['Athlete', 'Week', 'Day of the Week', 'Category', 'Exercise', 'Reps', 'Sets', 'Set', 'Set_Reps', 'Set_Weight']
        cols = [c for c in cols if c in long_df.columns] + [c for c in long_df.columns if c not in cols]
        long_df = long_df[cols]
        athlete_data.setdefault(sheet_name, []).append(long_df)

# Save each athlete's aggregated data as CSV
for athlete, dfs in athlete_data.items():
    agg_df = pd.concat(dfs, ignore_index=True)
    out_path = os.path.join(OUTPUT_DIR, f"{athlete.replace(' ', '_')}.csv")
    agg_df.to_csv(out_path, index=False)
    print(f"Saved: {out_path} ({len(agg_df)} rows)")

print("Aggregation complete.")
