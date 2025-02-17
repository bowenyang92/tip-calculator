import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# Define storage file for staff tip rates and calculation history
TIP_RATES_FILE = "staff_tip_rates.json"
HISTORY_FILE = "tip_history.json"

# Load existing staff tip rates if available
def load_staff_tip_rates():
    if not os.path.exists(TIP_RATES_FILE) or os.stat(TIP_RATES_FILE).st_size == 0:
        return {}  # Return empty dict if file doesn't exist or is empty
    try:
        with open(TIP_RATES_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:  # Handle invalid JSON
        return {}

# Save staff tip rates persistently
def save_staff_tip_rates(tip_rates):
    with open(TIP_RATES_FILE, "w") as file:
        json.dump(tip_rates, file)

# Load past tip history
def load_tip_history():
    if not os.path.exists(HISTORY_FILE) or os.stat(HISTORY_FILE).st_size == 0:
        return []  # Return empty list if file doesn't exist or is empty
    try:
        with open(HISTORY_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:  # Handle invalid JSON
        return []

# Save tip history
def save_tip_history(record):
    history = load_tip_history()
    history.append(record)
    with open(HISTORY_FILE, "w") as file:
        json.dump(history, file)

# Hardcoded staff list (to be updated in future versions)
staff_list = ["Alice", "Bob", "Charlie", "David", "Emma", "Frank", "Grace", "Helen"]

# Load saved tip rates
saved_tip_rates = load_staff_tip_rates()
default_tip_rates = {name: saved_tip_rates.get(name, 1.0) for name in staff_list}

# UI Elements
st.title("Restaurant Tip Calculator")

# Merchant Take Rate Input
merchant_take_rate = st.number_input("Merchant Take Rate (e.g., 0.2 for 20%)", min_value=0.0, max_value=1.0, value=0.0)

# Sales & Tip Inputs
total_sales = st.number_input("Total Sales", min_value=0.0)
day_sales = st.number_input("Day Sales", min_value=0.0)
night_sales = st.number_input("Night Sales", min_value=0.0)
total_tips = st.number_input("Total Tips", min_value=0.0)

# Staff Selection
st.subheader("Select Staff for Each Shift")
day_shift_staff = st.multiselect("Daytime Shift Staff", staff_list)
night_shift_staff = st.multiselect("Nighttime Shift Staff", staff_list)

# Tip Earning Rate Adjustments
st.subheader("Adjust Tip Earning Rate")
custom_tip_rates = {}

for name in staff_list:
    custom_tip_rates[name] = st.number_input(f"{name}'s Tip Earning Rate", min_value=0.5, max_value=2.0, value=default_tip_rates[name])

# "Set All to X" Button
new_global_rate = st.number_input("Set all staff tip earning rate to:", min_value=0.5, max_value=2.0, value=1.0)
if st.button("Apply to All"):
    for name in staff_list:
        custom_tip_rates[name] = new_global_rate

# Calculate Tips
if st.button("Calculate Tips"):
    # Apply Merchant Take Rate
    total_tips_to_distribute = total_tips * (1 - merchant_take_rate)

    # Calculate Tip Rate
    tip_rate = total_tips_to_distribute / total_sales if total_sales else 0
    day_tips = day_sales * tip_rate
    night_tips = night_sales * tip_rate

    # Distribute Tips
    day_count = len(day_shift_staff)
    night_count = len(night_shift_staff)

    tips_distribution = {}

    for staff in day_shift_staff:
        tips_distribution[staff] = round((day_tips / day_count) * custom_tip_rates[staff], 2) if day_count else 0

    for staff in night_shift_staff:
        tips_distribution[staff] = tips_distribution.get(staff, 0) + round((night_tips / night_count) * custom_tip_rates[staff], 2) if night_count else 0

    # Save updated tip rates
    save_staff_tip_rates(custom_tip_rates)

    # Save calculation result with timestamp
    calculation_record = {
        "timestamp": datetime.now().isoformat(),
        "merchant_take_rate": merchant_take_rate,
        "total_tips_distributed": total_tips_to_distribute,
        "tips_distribution": tips_distribution
    }
    save_tip_history(calculation_record)

    # Display Results
    st.subheader("Final Tip Distribution")
    df = pd.DataFrame(list(tips_distribution.items()), columns=["Staff", "Final Tips Earned"])
    st.dataframe(df)

    # Download Options
    st.subheader("Download Results")

    # Create Excel File
    def create_excel(history):
        output_file = "tip_distribution.xlsx"
        all_data = []

        for record in history:
            for staff, tips in record["tips_distribution"].items():
                all_data.append({
                    "Date": datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d"),
                    "Time": datetime.fromisoformat(record["timestamp"]).strftime("%H:%M:%S"),
                    "Merchant Take Rate": record["merchant_take_rate"],
                    "Staff": staff,
                    "Final Tips Earned": tips
                })

        df = pd.DataFrame(all_data)
        df.to_excel(output_file, index=False)
        return output_file

    # Filter history based on time range
    history = load_tip_history()
    now = datetime.now()

    time_filters = {
        "Current Calculation": [history[-1]] if history else [],
        "Last 1 Day": [r for r in history if now - datetime.fromisoformat(r["timestamp"]) <= timedelta(days=1)],
        "Last 1 Week": [r for r in history if now - datetime.fromisoformat(r["timestamp"]) <= timedelta(weeks=1)],
        "Last 1 Month": [r for r in history if now - datetime.fromisoformat(r["timestamp"]) <= timedelta(days=30)],
        "Last 1 Year": [r for r in history if now - datetime.fromisoformat(r["timestamp"]) <= timedelta(days=365)]
    }

    for label, filtered_history in time_filters.items():
        if filtered_history:
            file_path = create_excel(filtered_history)
            with open(file_path, "rb") as f:
                st.download_button(f"Download {label} Report", f, file_name=f"{label.replace(' ', '_')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
