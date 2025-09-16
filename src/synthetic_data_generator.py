# synthetic_data_generation.py
from faker import Faker
import pandas as pd
import os
import random
from datetime import datetime, timedelta

class DataGenerator:
    def __init__(self):
        self.fake = Faker()
        self.patient_csv = "data/patients.csv"
        self.schedule_excel = "data/doctor_schedules.xlsx"
        self.appointments_excel = "data/appointments.xlsx"

    def generate_synthetic_data(self):
        if not os.path.exists(self.patient_csv):
            patients = []
            for i in range(50):
                patients.append({
                    "id": i + 1,
                    "full_name": self.fake.name(),
                    "date_of_birth": self.fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%Y-%m-%d"),
                    "email": self.fake.email(),
                    "phone": self.fake.phone_number(),
                    "insurance_carrier": random.choice(["Blue Cross", "Aetna", "Cigna", "UnitedHealth"]),
                    "insurance_member_id": self.fake.bothify(text="??######"),
                    "insurance_group": self.fake.bothify(text="GRP###"),
                    "created_date": datetime.now().isoformat()
                })
            pd.DataFrame(patients).to_csv(self.patient_csv, index=False)
        print(f"Synthetic patient data generated at {self.patient_csv}")
        
        if not os.path.exists(self.schedule_excel):
            doctors = ["Dr. Smith", "Dr. Johnson", "Dr. Williams", "Dr. John", "Dr. Robin"]
            locations = ["Main Clinic", "Downtown Office", "Suburban Center", "Railway Clinic"]
            schedules = []
            base_date = datetime.now().date()
            
            for i in range(6):
                current_date = base_date + timedelta(days=i)
                if current_date.weekday() < 5:
                    for doctor in doctors:
                        for location in locations:
                            for hour in range(9, 12):
                                for minute in [0, 30]:
                                    start_time = f"{hour:02d}:{minute:02d}"
                                    end_time = f"{hour:02d}:{minute + 30:02d}" if minute == 0 else f"{hour + 1:02d}:00"
                                    schedules.append({
                                        "doctor_name": doctor,
                                        "location": location,
                                        "date": current_date.isoformat(),
                                        "start_time": start_time,
                                        "end_time": end_time,
                                        "available": random.choices([True, False],weights=[0.6, 0.4])[0]
                                    })
                            for hour in range(14, 17):
                                for minute in [0, 30]:
                                    start_time = f"{hour:02d}:{minute:02d}"
                                    end_time = f"{hour:02d}:{minute + 30:02d}" if minute == 0 else f"{hour + 1:02d}:00"
                                    schedules.append({
                                        "doctor_name": doctor,
                                        "location": location,
                                        "date": current_date.isoformat(),
                                        "start_time": start_time,
                                        "end_time": end_time,
                                        "available": random.choices([True, False], weights=[0.6, 0.4])[0]
                                    })
            
            pd.DataFrame(schedules).to_excel(self.schedule_excel, index=False)
        print
        
        if not os.path.exists(self.appointments_excel):
            pd.DataFrame(columns=["appointment_id", "patient_id", "doctor", "appointment_date", 
                                "appointment_time", "duration", "status", "location", "created_date"]).to_excel(self.appointments_excel, index=False)

data_generator = DataGenerator()
data_generator.generate_synthetic_data()