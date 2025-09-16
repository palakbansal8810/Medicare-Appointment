import os
import sys
from datetime import datetime, timedelta

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import (
    greeting, lookup, scheduling_new, scheduling_returning,
    insurance, confirmation, mailing, setup_reminder_system
)
from src.synthetic_data_generator import DataGenerator

def demo_appointment_flow():
    """Demonstrate the appointment booking flow"""
    print(" MediCare Appointment System - Demo")
    print("=" * 50)
    
    # Ensure data exists
    if not os.path.exists("data/patients.csv"):
        print("Generating synthetic data...")
        data_generator = DataGenerator()
        data_generator.generate_synthetic_data()
        print("Data generated successfully\n")
    
    # Demo state
    state = {
        "errors": [],
        "retry_count": 0,
        "appointment_confirmed": False,
        "mail_sent": False,
        "current_step": "greeting"
    }
    
    print("📝 Demo: New Patient Appointment Booking")
    print("-" * 40)
    
    # Step 1: Greeting
    print("\n1️⃣ Patient Information Collection")
    demo_input = "Name: Rahul, DOB: 1985-06-15, Doctor: Johnson, Location: Main Clinic"
    print(f"Input: {demo_input}")
    
    state['user_input'] = demo_input
    state = greeting(state)
    
    if state.get('errors'):
        print(f"❌ Errors: {state['errors']}")
        return
    
    print(f"✅ Collected: {state['patient_name']}, DOB: {state['date_of_birth']}")
    print(f"   Doctor: {state['doctor']}, Location: {state['location']}")
    
    # Step 2: Lookup
    print("\n2️⃣ Patient Lookup")
    state = lookup(state)
    
    if state.get('patient_type') == 'existing':
        print(f"✅ Existing patient found! ID: {state.get('patient_id')}")
        print(f"   Duration: {state.get('appointment_duration')}")
    else:
        print("ℹ️ New patient - will need 60-minute appointment")
        print(f"   Duration: {state.get('appointment_duration')}")
    
    # Step 3: Scheduling
    print("\n3️⃣ Appointment Scheduling")
    if state.get('patient_type') == 'existing':
        state = scheduling_returning(state)
    else:
        state = scheduling_new(state)
    
    if state.get('errors'):
        print(f"❌ Scheduling errors: {state['errors']}")
        return
    
    available_slots = state.get('available_slots', [])
    print(f"✅ Found {len(available_slots)} available slots")
    
    if available_slots:
        # Select first available slot
        state['slot_selection'] = '1'
        if state.get('patient_type') == 'existing':
            state = scheduling_returning(state)
        else:
            state = scheduling_new(state)
        
        if not state.get('errors'):
            selected_slot = state.get('selected_slot')
            print(f"✅ Selected: {selected_slot['date']} at {selected_slot['start_time']}-{selected_slot['end_time']}")
    
    # Step 4: Insurance (for new patients)
    if state.get('patient_type') == 'new':
        print("\n4️⃣ Insurance Information")
        insurance_input = "Carrier: Blue Cross, Member ID: BC123456, Group: GRP001"
        print(f"Input: {insurance_input}")
        
        state['insurance_input'] = insurance_input
        state['patient_email'] = "john.smith@email.com"
        state['patient_contact'] = "(555) 123-4567"
        
        state = insurance(state)
        
        if state.get('errors'):
            print(f"❌ Insurance errors: {state['errors']}")
            return
        
        print("✅ Insurance information collected")
        print(f"   Carrier: {state['insurance_carrier']}")
        print(f"   Member ID: {state['insurance_member_id']}")
        print(f"   Group: {state['insurance_group']}")
    else:
        print("\n4️⃣ Using existing insurance information")
        state = insurance(state)
    
    # Step 5: Confirmation
    print("\n5️⃣ Appointment Confirmation")
    state['confirmation_input'] = 'yes'
    state = confirmation(state)
    
    if state.get('appointment_confirmed'):
        print(f"✅ Appointment confirmed! ID: {state.get('appointment_id')}")
    else:
        print("❌ Appointment not confirmed")
        return
    
    # Step 6: Email and Reminders
    print("\n6️⃣ Email and Reminder Setup")
    state = mailing(state)
    
    if state.get('mail_sent'):
        print("✅ Confirmation email sent")
    else:
        print("⚠️ Email not sent (credentials not configured)")
    
    state = setup_reminder_system(state)
    
    if state.get('reminders_set'):
        print("✅ Reminder system configured")
        for reminder in state.get('reminders', []):
            print(f"   • {reminder['type']}: {reminder['date'].strftime('%Y-%m-%d %H:%M')}")
    
    # Final Summary
    print("\n" + "="*50)
    print("🎉 DEMO COMPLETE!")
    print("="*50)
    print(f"Appointment ID: {state.get('appointment_id')}")
    print(f"Patient: {state.get('patient_name')}")
    print(f"Date: {state.get('selected_time_date')}")
    print(f"Time: {state.get('selected_time_start')}-{state.get('selected_time_end')}")
    print(f"Doctor: {state.get('doctor')}")
    print(f"Location: {state.get('location')}")
    print(f"Duration: {state.get('appointment_duration')}")
    print(f"Email sent: {'Yes' if state.get('mail_sent') else 'No'}")

def show_system_info():
    """Show system information and data"""
    print("\n📊 System Information")
    print("-" * 30)
    
    # Check data files
    data_files = [
        "data/patients.csv",
        "data/doctor_schedules.xlsx", 
        "data/appointments_export.xlsx"
    ]
    
    for file_path in data_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {file_path} ({size} bytes)")
        else:
            print(f"❌ {file_path} (not found)")
    
    # Show sample data
    if os.path.exists("data/patients.csv"):
        import pandas as pd
        df = pd.read_csv("data/patients.csv")
        print(f"\n📋 Patient Database: {len(df)} patients")
        if len(df) > 0:
            print("Sample patients:")
            for i, row in df.head(3).iterrows():
                print(f"   • {row['full_name']} (ID: {row['id']})")

if __name__ == "__main__":
    try:
        show_system_info()
        demo_appointment_flow()
        
        print("\n🚀 To run the full Streamlit application:")
        print("   streamlit run streamlit_app.py")
        print("   or")
        print("   python run_app.py")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

