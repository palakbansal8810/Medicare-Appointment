
import pandas as pd
from datetime import datetime
import re
import json
import os 
from datetime import timedelta
def clean_llm_response(text: str):
    """Clean and parse LLM response to extract JSON"""
      
    text = text.strip()
    
    # Remove markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    
    # Find JSON object
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        # Fix common JSON issues
        json_str = re.sub(r"'", '"', json_str)  # Replace single quotes
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)  # Add quotes to keys
        
        parsed = json.loads(json_str)
        return {k: "" if v is None else str(v) for k, v in parsed.items()}
    
    return None


def get_available_slots(dataset_path: str, duration: int, doctor_name: str, location: str):
    try:
        # Load schedule
        df = pd.read_excel(dataset_path)

        # Normalize doctor + location input
        doctor_name = doctor_name.strip()
        location = location.strip()

        # Ensure datetime parsing
        df["start_time"] = pd.to_datetime(df["start_time"], format="%H:%M").dt.time
        df["end_time"] = pd.to_datetime(df["end_time"], format="%H:%M").dt.time

        # Force date column to datetime.date
        df["date"] = pd.to_datetime(df["date"]).dt.date

        # Filter for doctor/location/availability
        df = df[
            (df["doctor_name"].str.strip() == doctor_name) &
            (df["location"].str.strip() == location) &
            (df["available"] == True)
        ].copy()
        if df.empty:
            return []

        # Convert to datetime objects (merge with date column)
        df["start_dt"] = df.apply(lambda r: datetime.combine(r["date"], r["start_time"]), axis=1)
        df["end_dt"] = df.apply(lambda r: datetime.combine(r["date"], r["end_time"]), axis=1)

        available_slots = []

        if duration == 30:
            for _, row in df.iterrows():
                slot_duration = row["end_dt"] - row["start_dt"]
                available_slots.append({
                    "date": row["date"],
                    "start_time": row["start_time"].strftime("%H:%M"),
                    "end_time": row["end_time"].strftime("%H:%M"),
                    "location": row["location"],
                    "duration": str(slot_duration)
                })
                
        elif duration == 60:
            df_sorted = df.sort_values(["date", "start_dt"]).reset_index(drop=True)
            for i in range(len(df_sorted) - 1):
                row1, row2 = df_sorted.iloc[i], df_sorted.iloc[i+1]
                if (
                    row1["end_dt"] == row2["start_dt"] and
                    row1["date"] == row2["date"] and
                    row1["location"] == row2["location"]
                ):
                    slot_duration = row2["end_dt"] - row1["start_dt"]
                    available_slots.append({
                        "date": row1["date"].strftime("%Y-%m-%d"),
                        "start_time": row1["start_time"].strftime("%H:%M"),
                        "end_time": row2["end_time"].strftime("%H:%M"),
                        "location": row1["location"],
                        "duration": str(slot_duration)
                    })

        return available_slots

    except Exception as e:
        print(f"Error fetching slots: {e}")
        return []
def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email or ""))

def validate_phone(phone: str) -> bool:
    digits_only = re.sub(r'\D', '', phone or "")
    return len(digits_only) >= 10

def validate_date_format(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except Exception:
        return False
    
def init_doctor_schedule(path="data/doctor_schedules.xlsx"):
    """Create a 14-day schedule for a few doctors if file doesn't exist."""
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doctors = [
        ("Dr. Alice Gupta","Downtown Clinic"),
        ("Dr. Alice Gupta","Uptown Clinic"),
        ("Dr. Rahul Menon","Downtown Clinic"),
        ("Dr. Priya Shah","Uptown Clinic"),
        ("Dr. Omar Khan","Riverside Clinic"),
    ]
    start_date = datetime.today().date()
    rows = []
    for dname, loc in doctors:
        for day in range(0, 14):
            date = start_date + timedelta(days=day)
            # Working window 09:00 - 17:00
            rows.append({
                "doctor_name": dname,
                "location": loc,
                "date": date.strftime("%Y-%m-%d"),
                "start": "09:00",
                "end": "17:00"
            })
    pd.DataFrame(rows).to_excel(path, index=False)
    return path