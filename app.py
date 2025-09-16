import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from datetime import date
from main import (
    greeting, lookup, scheduling_new, scheduling_returning, confirmation, mailing, setup_reminder_system,
    validate_email, validate_phone
)
import logging
from logging.handlers import RotatingFileHandler
from src.synthetic_data_generator import DataGenerator
from src.google_calender import get_google_calendar_service,create_google_calendar_event

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Logger setup
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("appointment_app")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    file_handler = RotatingFileHandler("logs/app.log", maxBytes=1_000_000, backupCount=5)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def update_slot_availability(doctor_name, location, date, start_time, end_time, available=False):
    """Update the availability status of a specific slot in doctor_schedules.xlsx"""
    try:
        file_path = "data/doctor_schedules.xlsx"
        
        if not os.path.exists(file_path):
            return False
        
        # Read the current schedule
        df = pd.read_excel(file_path)
        
        if end_time != start_time:
            # Convert time strings to datetime for comparison
            start_dt = pd.to_datetime(start_time, format='%H:%M').time()
            end_dt = pd.to_datetime(end_time, format='%H:%M').time()
            
            # Find slots that match the criteria
            mask = (
                (df['doctor_name'] == doctor_name) &
                (df['location'] == location) &
                (df['date'] == date) &
                (pd.to_datetime(df['start_time'], format='%H:%M').dt.time >= start_dt) &
                (pd.to_datetime(df['end_time'], format='%H:%M').dt.time <= end_dt)
            )
            
            # Update availability
            df.loc[mask, 'available'] = available
            
            # Save back to Excel
            df.to_excel(file_path, index=False)
            return True
        else:
            # For 30-minute appointments, find exact match
            mask = (
                (df['doctor_name'] == doctor_name) &
                (df['location'] == location) &
                (df['date'] == date) &
                (df['start_time'] == start_time) &
                (df['end_time'] == end_time)
            )
            
            df.loc[mask, 'available'] = available
            df.to_excel(file_path, index=False)
            return True
            
    except Exception as e:
        print(f"Error updating slot availability: {e}")
        return False

def restore_slot_availability(doctor_name, location, date, start_time, end_time):
    """Restore the availability status of a specific slot in doctor_schedules.xlsx (set to TRUE)"""
    return update_slot_availability(doctor_name, location, date, start_time, end_time, available=True)

# Calendly Integration Functions
# def get_calendly_token():
#     """Get Calendly API token from environment variables"""
#     return os.getenv('CALENDLY_API_TOKEN')

# def create_calendly_event(patient_name, patient_email, doctor_name, appointment_date, start_time, end_time, location):
#     """Create a Calendly event for the appointment"""
#     try:
#         token = get_calendly_token()
#         if not token:
#             return {"success": False, "error": "Calendly API token not configured"}
        
#         # Calendly API endpoint for creating events
#         url = "https://api.calendly.com/scheduled_events"
        
#         headers = {
#             "Authorization": f"Bearer {token}",
#             "Content-Type": "application/json"
#         }
        
#         # Convert appointment details to Calendly format
#         start_datetime = f"{appointment_date}T{start_time}:00"
#         end_datetime = f"{appointment_date}T{end_time}:00"
        
#         # Create event data
#         event_data = {
#             "name": f"Medical Appointment - {patient_name}",
#             "start_time": start_datetime,
#             "end_time": end_datetime,
#             "location": {
#                 "type": "physical",
#                 "location": location
#             },
#             "attendees": [
#                 {
#                     "email": patient_email,
#                     "name": patient_name
#                 }
#             ],
#             "description": f"Medical appointment with {doctor_name} at {location}",
#             "status": "confirmed"
#         }
        
#         # Make API request
#         response = requests.post(url, headers=headers, json=event_data)
        
#         if response.status_code == 201:
#             event_info = response.json()
#             return {
#                 "success": True, 
#                 "event_id": event_info.get("resource", {}).get("uri", ""),
#                 "event_url": event_info.get("resource", {}).get("event_url", "")
#             }
#         else:
#             return {
#                 "success": False, 
#                 "error": f"Calendly API error: {response.status_code} - {response.text}"
#             }
            
#     except Exception as e:
#         return {"success": False, "error": f"Error creating Calendly event: {str(e)}"}

# def get_calendly_availability(doctor_name, date_range_days=14):
#     """Get available time slots from Calendly for a specific doctor"""
#     try:
#         token = get_calendly_token()
#         if not token:
#             return {"success": False, "error": "Calendly API token not configured"}
        
#         # Get doctor's Calendly user URI (this would be configured per doctor)
#         doctor_calendly_uri = get_doctor_calendly_uri(doctor_name)
#         if not doctor_calendly_uri:
#             return {"success": False, "error": f"No Calendly URI configured for {doctor_name}"}
        
#         # Calendly API endpoint for availability
#         url = "https://api.calendly.com/event_types/availability"
        
#         headers = {
#             "Authorization": f"Bearer {token}",
#             "Content-Type": "application/json"
#         }
        
#         # Calculate date range
#         start_date = datetime.now().date()
#         end_date = start_date + timedelta(days=date_range_days)
        
#         params = {
#             "event_type": doctor_calendly_uri,
#             "start_time": start_date.isoformat(),
#             "end_time": end_date.isoformat()
#         }
        
#         response = requests.get(url, headers=headers, params=params)
        
#         if response.status_code == 200:
#             availability_data = response.json()
#             return {
#                 "success": True,
#                 "availability": availability_data.get("collection", [])
#             }
#         else:
#             return {
#                 "success": False,
#                 "error": f"Calendly API error: {response.status_code} - {response.text}"
#             }
            
#     except Exception as e:
#         return {"success": False, "error": f"Error getting Calendly availability: {str(e)}"}

# def get_doctor_calendly_uri(doctor_name):
#     """Get Calendly URI for a specific doctor (configured mapping)"""
#     # This would typically be stored in a database or config file
#     doctor_calendly_mapping = {
#         "Dr. Smith": "https://calendly.com/dr-smith/medical-appointment",
#         "Dr. Johnson": "https://calendly.com/dr-johnson/medical-appointment", 
#         "Dr. Williams": "https://calendly.com/dr-williams/medical-appointment",
#         "Dr. John": "https://calendly.com/dr-john/medical-appointment",
#         "Dr. Robin": "https://calendly.com/dr-robin/medical-appointment"
#     }
#     return doctor_calendly_mapping.get(doctor_name)

# def sync_calendly_to_excel():
#     """Sync Calendly availability to local Excel schedule"""
#     try:
#         # Get all doctors
#         df = pd.read_excel("data/doctor_schedules.xlsx")
#         doctors = df['doctor_name'].unique()
        
#         updated_slots = []
        
#         for doctor in doctors:
#             # Get Calendly availability for this doctor
#             availability_result = get_calendly_availability(doctor)
            
#             if availability_result["success"]:
#                 # Process availability data and update Excel
#                 for slot in availability_result["availability"]:
#                     updated_slots.append({
#                         "doctor_name": doctor,
#                         "location": "Calendly Sync",
#                         "date": slot.get("start_time", "").split("T")[0],
#                         "start_time": slot.get("start_time", "").split("T")[1][:5],
#                         "end_time": slot.get("end_time", "").split("T")[1][:5],
#                         "available": True,
#                         "source": "calendly"
#                     })
        
#         # Update Excel file with Calendly data
#         if updated_slots:
#             calendly_df = pd.DataFrame(updated_slots)
#             # Merge with existing data or replace
#             df = pd.concat([df, calendly_df], ignore_index=True)
#             df.to_excel("data/doctor_schedules.xlsx", index=False)
            
#         return {"success": True, "updated_slots": len(updated_slots)}
        
#     except Exception as e:
#         return {"success": False, "error": f"Error syncing Calendly: {str(e)}"}

# def create_calendly_booking_link(doctor_name, appointment_type="medical"):
#     """Generate a Calendly booking link for a doctor"""
#     doctor_calendly_mapping = {
#         "Dr. Smith": "dr-smith",
#         "Dr. Johnson": "dr-johnson", 
#         "Dr. Williams": "dr-williams",
#         "Dr. John": "dr-john",
#         "Dr. Robin": "dr-robin"
#     }
    
#     doctor_slug = doctor_calendly_mapping.get(doctor_name)
#     if doctor_slug:
#         return f"https://calendly.com/{doctor_slug}/{appointment_type}"
#     return None

# Page configuration
st.set_page_config(
    page_title="MediCare Appointment System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .step-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
        border-left: 4px solid #3498db;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left-color: #2196f3;
    }
    .bot-message {
        background-color: #f3e5f5;
        border-left-color: #9c27b0;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'appointment_state' not in st.session_state:
        st.session_state.appointment_state = {
            "errors": [],
            "retry_count": 0,
            "appointment_confirmed": False,
            "mail_sent": False,
            "current_step": "greeting"
        }
        logger.info("Initialized appointment_state in session_state")
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
        logger.info("Initialized chat_history in session_state")
    
    if 'current_step' not in st.session_state:
        st.session_state.current_step = "greeting"
        logger.info("Set current_step to greeting")
    
    if 'show_form' not in st.session_state:
        st.session_state.show_form = False

# def display_chat_history():
#     """Display chat history"""
#     if st.session_state.chat_history:
#         st.markdown("###  Conversation History")
#         for message in st.session_state.chat_history:
#             if message['type'] == 'user':
#                 st.markdown(f"""
#                 <div class="chat-message user-message">
#                     <strong>You:</strong> {message['content']}
#                 </div>
#                 """, unsafe_allow_html=True)
#             else:
#                 st.markdown(f"""
#                 <div class="chat-message bot-message">
#                     <strong>Assistant:</strong> {message['content']}
#                 </div>
#                 """, unsafe_allow_html=True)

def add_to_chat_history(message_type: str, content: str):
    """Add message to chat history"""
    st.session_state.chat_history.append({
        'type': message_type,
        'content': content,
        'timestamp': datetime.now()
    })

def process_greeting_step():
    """Process the greeting step with form inputs"""
    logger.info("Entering process_greeting_step")
    st.markdown('<div class="step-header"> Patient Information</div>', unsafe_allow_html=True)
    
    with st.form("greeting_form"):
        col1, col2 = st.columns(2)
        df=pd.read_excel("data/doctor_schedules.xlsx")
        with col1:
            # Get unique doctors and locations from the schedule
            doctors = df["doctor_name"].unique().tolist()
            patient_name = st.text_input("Full Name", placeholder="Enter your full name")
            
            date_of_birth = st.date_input("Date of Birth",value=None,min_value=date(1900, 1, 1))
            doctor = st.selectbox(
                "Preferred Doctor",
                doctors
            )
        
        with col2:
            # Get unique locations from the schedule
            locations = df["location"].unique().tolist()
            location = st.selectbox(
                "Location",
                locations
            )
        
        submitted = st.form_submit_button("Continue", type="primary")
        
        if submitted:
            logger.info("Greeting form submitted")
            if not patient_name or not date_of_birth or not doctor or not location:
                st.error("Please fill in all required fields")
                logger.warning("Greeting validation failed: missing required fields")
                return False
            
            # Update state
            st.session_state.appointment_state.update({
                "patient_name": patient_name,
                "date_of_birth": date_of_birth.strftime('%Y-%m-%d'),
                "doctor": doctor,
                "location": location,
                "user_input": f"Name: {patient_name}, DOB: {date_of_birth.strftime('%Y-%m-%d')}, Doctor: {doctor}, Location: {location}"
            })
            
            add_to_chat_history('user', f"Name: {patient_name}, DOB: {date_of_birth.strftime('%Y-%m-%d')}, Doctor: {doctor}, Location: {location}")
            
            # Process greeting
            state = greeting(st.session_state.appointment_state)
            st.session_state.appointment_state.update(state)
            
            if state.get('errors'):
                for error in state['errors']:
                    st.error(error)
                    logger.error(f"Greeting step error: {error}")
                return False
            else:
                st.success(" Patient information collected successfully!")
                logger.info("Greeting processed successfully")
                add_to_chat_history('bot', f"Thank you {patient_name}! I've collected your information. Let me look you up in our system.")
                return True
    
    return False

def process_lookup_step():
    """Process patient lookup"""
    logger.info("Entering process_lookup_step")
    st.markdown('<div class="step-header"> Patient Lookup</div>', unsafe_allow_html=True)
    
    # Process lookup
    state = lookup(st.session_state.appointment_state)
    st.session_state.appointment_state.update(state)
    logger.info(f"Lookup result patient_type={state.get('patient_type')} patient_id={state.get('patient_id')}")
    
    if state.get('patient_type') == 'existing':
        st.success(f" Existing patient found! Patient ID: {state.get('patient_id')}")
        add_to_chat_history('bot', f"Great! I found you in our system as an existing patient. Your appointment will be 30 minutes.")
        
        # Display existing patient info
        with st.expander(" Existing Patient Information"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Insurance Carrier:** {state.get('insurance_carrier', 'N/A')}")
                st.write(f"**Member ID:** {state.get('insurance_member_id', 'N/A')}")
            with col2:
                st.write(f"**Group:** {state.get('insurance_group', 'N/A')}")
                st.write(f"**Phone:** {state.get('patient_contact', 'N/A')}")
    else:
        st.info(" No existing patient found. Proceeding as new patient.")
        add_to_chat_history('bot', "I don't see you in our system, so I'll set you up as a new patient. Your appointment will be 60 minutes.")
    
    return True

def process_scheduling_step():
    """Process appointment scheduling"""
    logger.info("Entering process_scheduling_step")
    st.markdown('<div class="step-header"> Appointment Scheduling</div>', unsafe_allow_html=True)
    
    patient_type = st.session_state.appointment_state.get('patient_type')
    duration = st.session_state.appointment_state.get('appointment_duration')
    
    st.info(f"**Patient Type:** {patient_type.title()} | **Duration:** {duration}")
    
    # Process scheduling
    if patient_type == 'existing':
        state = scheduling_returning(st.session_state.appointment_state)
    else:
        state = scheduling_new(st.session_state.appointment_state)
    
    st.session_state.appointment_state.update(state)
    
    if state.get('errors'):
        for error in state['errors']:
            st.error(error)
            logger.error(f"Scheduling error: {error}")
        return False
    
    available_slots = state.get('available_slots', [])
    
    if not available_slots:
        st.error("No available appointment slots found for the selected doctor and location.")
        logger.warning("No available slots found")
        return False
    
    st.success(f"Found {len(available_slots)} available appointment slots!")
    logger.info(f"Found {len(available_slots)} available slots")
    add_to_chat_history('bot', f"I found {len(available_slots)} available slots for {st.session_state.appointment_state.get('doctor')} at {st.session_state.appointment_state.get('location')}.")
    
    # Display available slots
    st.markdown("### Available Time Slots:")
    
    slot_options = []
    for i, slot in enumerate(available_slots, 1):
        slot_display = f"{slot['date']} | {slot['start_time']} - {slot['end_time']}"
        slot_options.append(slot_display)
    
    selected_slot_display = st.selectbox(
        "Choose your preferred time slot:",
        options=slot_options,
        index=None,
        placeholder="Select a time slot..."
    )
    
    if selected_slot_display:
        logger.info(f"Selected slot display: {selected_slot_display}")
        # Find the selected slot
        slot_index = slot_options.index(selected_slot_display)
        selected_slot = available_slots[slot_index]
        
        # Update state with selection
        st.session_state.appointment_state['slot_selection'] = str(slot_index + 1)
        
        # Re-process scheduling with selection
        if patient_type == 'existing':
            state = scheduling_returning(st.session_state.appointment_state)
        else:
            state = scheduling_new(st.session_state.appointment_state)
        
        st.session_state.appointment_state.update(state)
        
        if not state.get('errors'):
            st.success(f" Selected: {selected_slot['date']} at {selected_slot['start_time']}-{selected_slot['end_time']}")
            logger.info(f"Slot selected index={slot_index} date={selected_slot['date']} start={selected_slot['start_time']}")
            add_to_chat_history('bot', f"Perfect! I've selected {selected_slot['date']} at {selected_slot['start_time']}-{selected_slot['end_time']} for your appointment.")
            return True
        else:
            st.error(state['errors'][0])
            logger.error(f"Scheduling selection error: {state['errors'][0]}")
            return False
    
    return False

def process_insurance_step():
    """Process insurance information"""
    st.markdown('<div class="step-header">💳 Insurance Information</div>', unsafe_allow_html=True)
    
    patient_type = st.session_state.appointment_state.get('patient_type')
    
    if patient_type == 'existing':
        st.info("Using existing insurance information on file.")
        add_to_chat_history('bot', "I'll use your existing insurance information on file.")
        return True
    
    st.info("Please provide your insurance details:")
    
    with st.form("insurance_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            insurance_carrier = st.text_input("Insurance Carrier", placeholder="e.g., Blue Cross, Aetna")
            member_id = st.text_input("Member ID", placeholder="Your member ID")
        
        with col2:
            group = st.text_input("Group", placeholder="Group number/name")
            patient_email = st.text_input("Email Address", placeholder="your.email@example.com")
            patient_contact = st.text_input("Phone Number", placeholder="(555) 123-4567")
        
        submitted = st.form_submit_button("Continue", type="primary")
        
        if submitted:
            # Validate inputs
            errors = []
            if not insurance_carrier or len(insurance_carrier.strip()) < 2:
                errors.append("Insurance carrier is required")
            if not member_id or len(member_id.strip()) < 3:
                errors.append("Member ID is required")
            if not group or len(group.strip()) < 1:
                errors.append("Group information is required")
            if not validate_email(patient_email):
                errors.append("Valid email address is required")
            if not validate_phone(patient_contact):
                errors.append("Valid phone number is required (at least 10 digits)")
            
            if errors:
                for error in errors:
                    st.error(error)
                return False
            
            # Update state
            st.session_state.appointment_state.update({
                "insurance_carrier": insurance_carrier,
                "insurance_member_id": member_id,
                "insurance_group": group,
                "patient_email": patient_email,
                "patient_contact": patient_contact,
                "insurance_input": f"Carrier: {insurance_carrier}, Member ID: {member_id}, Group: {group}"
            })
            
            st.success(" Insurance information collected successfully!")
            add_to_chat_history('bot', "Thank you! I've collected your insurance information.")
            return True
    
    return False

def process_confirmation_step():
    """Process appointment confirmation"""
    logger.info("Entering process_confirmation_step")
    st.markdown('<div class="step-header"> Appointment Confirmation</div>', unsafe_allow_html=True)
    
    # Display appointment summary
    state = st.session_state.appointment_state
    
    st.markdown("###  Appointment Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Patient Information:**")
        st.write(f"• Name: {state.get('patient_name', 'N/A')}")
        st.write(f"• Date of Birth: {state.get('date_of_birth', 'N/A')}")
        st.write(f"• Patient Type: {state.get('patient_type', 'N/A').title()}")
        st.write(f"• Email: {state.get('patient_email', 'N/A')}")
        st.write(f"• Phone: {state.get('patient_contact', 'N/A')}")
    
    with col2:
        st.markdown("**Appointment Details:**")
        st.write(f"• Doctor: {state.get('doctor', 'N/A')}")
        st.write(f"• Location: {state.get('location', 'N/A')}")
        st.write(f"• Date: {state.get('selected_time_date', 'N/A')}")
        st.write(f"• Time: {state.get('selected_time_start', 'N/A')} - {state.get('selected_time_end', 'N/A')}")
        st.write(f"• Duration: {state.get('appointment_duration', 'N/A')}")
    
    st.markdown("**Insurance Information:**")
    col3, col4 = st.columns(2)
    with col3:
        st.write(f"• Carrier: {state.get('insurance_carrier', 'N/A')}")
    with col4:
        st.write(f"• Member ID: {state.get('insurance_member_id', 'N/A')}")
    st.write(f"• Group: {state.get('insurance_group', 'N/A')}")
    
    # Confirmation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button(" Confirm Appointment", type="primary", use_container_width=True):
            logger.info("Confirm Appointment clicked")
            st.session_state.appointment_state['confirmation_input'] = 'yes'
            
            # Process confirmation
            state = confirmation(st.session_state.appointment_state)
            st.session_state.appointment_state.update(state)
            
            if state.get('appointment_confirmed'):
                logger.info(f"Appointment confirmed id={state.get('appointment_id')}")
                # Update slot availability to FALSE
                doctor_name = st.session_state.appointment_state.get('doctor')
                location = st.session_state.appointment_state.get('location')
                date = st.session_state.appointment_state.get('selected_time_date')
                start_time = st.session_state.appointment_state.get('selected_time_start')
                end_time = st.session_state.appointment_state.get('selected_time_end')
                
                # Update the slot availability
                slot_updated = update_slot_availability(
                    doctor_name, location, date, start_time, end_time, available=False
                )
                logger.info(f"Slot availability update result: {slot_updated}")
                
                if slot_updated:
                    st.success(" Appointment confirmed successfully! Slot marked as unavailable.")
                else:
                    st.success(" Appointment confirmed successfully!")
                    st.warning(" Note: Could not update slot availability in schedule.")
                
                
                # Create Calendly event
                # calendly_result = create_calendly_event(
                #     patient_name=st.session_state.appointment_state.get('patient_name'),
                #     patient_email=st.session_state.appointment_state.get('patient_email'),
                #     doctor_name=st.session_state.appointment_state.get('doctor'),
                #     appointment_date=st.session_state.appointment_state.get('selected_time_date'),
                #     start_time=st.session_state.appointment_state.get('selected_time_start'),
                #     end_time=st.session_state.appointment_state.get('selected_time_end'),
                #     location=st.session_state.appointment_state.get('location')
                # )
                
                # if calendly_result["success"]:
                #     st.success(" Calendly event created successfully!")
                #     st.info(f"Event URL: {calendly_result.get('event_url', 'N/A')}")
                # else:
                #     st.warning(f"⚠️ Calendly integration: {calendly_result.get('error', 'Unknown error')}")
                
                
                return True
            else:
                st.error("Failed to confirm appointment. Please try again.")
                logger.error("Appointment confirmation failed")
                return False
    
    with col2:
        if st.button(" Cancel", use_container_width=True):
            st.session_state.appointment_state['confirmation_input'] = 'no'
            state = confirmation(st.session_state.appointment_state)
            st.session_state.appointment_state.update(state)
            
            # If there was a selected slot, restore its availability
            if st.session_state.appointment_state.get('selected_slot'):
                doctor_name = st.session_state.appointment_state.get('doctor')
                location = st.session_state.appointment_state.get('location')
                date = st.session_state.appointment_state.get('selected_time_date')
                start_time = st.session_state.appointment_state.get('selected_time_start')
                end_time = st.session_state.appointment_state.get('selected_time_end')
                
                # Restore slot availability
                slot_restored = restore_slot_availability(
                    doctor_name, location, date, start_time, end_time
                )
                
                if slot_restored:
                    st.warning("Appointment cancelled. Slot availability restored.")
                else:
                    st.warning("Appointment cancelled.")
            else:
                st.warning("Appointment cancelled.")
            
            add_to_chat_history('bot', "I understand you'd like to cancel. Please let me know if you need any assistance.")
            return False
    
    with col3:
        if st.button(" Start Over", use_container_width=True):
            # Reset session state
            st.session_state.appointment_state = {
                "errors": [],
                "retry_count": 0,
                "appointment_confirmed": False,
                "mail_sent": False,
                "current_step": "greeting"
            }
            st.session_state.chat_history = []
            st.session_state.current_step = "greeting"
            st.rerun()
    
    return False

def process_mailing_step():
    """Process email sending and final steps"""
    logger.info("Entering process_mailing_step")
    st.markdown('<div class="step-header"> Confirmation & Reminders</div>', unsafe_allow_html=True)
    
    if not st.session_state.appointment_state.get('appointment_confirmed'):
        st.error("Appointment not confirmed. Cannot proceed with email.")
        logger.warning("Attempted mailing without confirmed appointment")
        return False
    
    # Send email
    st.info("Sending confirmation email...")
    state = mailing(st.session_state.appointment_state)
    st.session_state.appointment_state.update(state)
    logger.info(f"Mailing result mail_sent={state.get('mail_sent')}")
    
    if state.get('mail_sent'):
        st.success(" Confirmation email sent successfully!")
        add_to_chat_history('bot', "I've sent you a confirmation email with all the details and any required forms.")
    else:
        st.warning(" Email could not be sent, but appointment is confirmed.")
        logger.error("Email sending failed or not configured")
        add_to_chat_history('bot', "Your appointment is confirmed, but I couldn't send the email. Please contact us for confirmation details.")
    
    # Setup reminders
    st.info("Setting up reminder system...")
    state = setup_reminder_system(st.session_state.appointment_state)
    st.session_state.appointment_state.update(state)
    logger.info(f"Reminder setup result reminders_set={state.get('reminders_set')}")
    
    if state.get('reminders_set'):
        st.success(" Reminder system configured!")
        add_to_chat_history('bot', "I've set up automated reminders for your appointment.")
        
        # Display reminders
        with st.expander(" Reminder Schedule"):
            for reminder in state.get('reminders', []):
                st.write(f"• **{reminder['type'].replace('_', ' ').title()}:** {reminder['date'].strftime('%Y-%m-%d %H:%M')}")
    
    # Final summary
    st.markdown("###  Booking Complete!")
    
    appointment_id = st.session_state.appointment_state.get('appointment_id', 'N/A')
    patient_name = st.session_state.appointment_state.get('patient_name', 'N/A')
    appointment_date = st.session_state.appointment_state.get('selected_time_date', 'N/A')
    appointment_time = f"{st.session_state.appointment_state.get('selected_time_start', 'N/A')} - {st.session_state.appointment_state.get('selected_time_end', 'N/A')}"
    doctor = st.session_state.appointment_state.get('doctor', 'N/A')
    email_sent = "Yes" if st.session_state.appointment_state.get('mail_sent') else "No"
    
    st.markdown(f"""
    <div class="success-box" style="color: green;">
    <h4 style="color: darkblue;">Final Summary</h4>
    <p><strong>Appointment ID:</strong> {appointment_id}</p>
    <p><strong>Patient:</strong> {patient_name}</p>
    <p><strong>Date:</strong> {appointment_date}</p>
    <p><strong>Time:</strong> {appointment_time}</p>
    <p><strong>Doctor:</strong> {doctor}</p>
    <p><strong>Email Sent:</strong> {email_sent}</p>
    </div>
    """, unsafe_allow_html=True)
    
    add_to_chat_history('bot', f"Your appointment booking is complete! Appointment ID: {appointment_id}. Thank you for choosing our services!")
    
    return True

def main():
    """Main Streamlit application"""
    logger.info("Starting Streamlit app main()")
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header"> MediCare Appointment System</h1>', unsafe_allow_html=True)
    
    # Create sample data if not exists
    if not os.path.exists("data/patients.csv"):
        with st.spinner("Setting up system data..."):
            data_generator = DataGenerator()
            data_generator.generate_synthetic_data()
    
    # Sidebar for navigation and info
    with st.sidebar:
        st.markdown("###  System Status")
        
        # Display current step
        step_names = {
            "greeting": " Patient Info",
            "lookup": " Patient Lookup", 
            "scheduling": " Scheduling",
            "insurance": " Insurance",
            "confirmation": "✅ Confirmation",
            "mailing": " Final Steps"
        }
        
        current_step_name = step_names.get(st.session_state.current_step, "Unknown")
        st.info(f"**Current Step:** {current_step_name}")
        
        # Progress indicator
        steps = ["greeting", "lookup", "scheduling", "insurance", "confirmation", "mailing"]
        current_index = steps.index(st.session_state.current_step) if st.session_state.current_step in steps else 0
        
        progress = (current_index + 1) / len(steps)
        st.progress(progress)
        
        # Quick stats
        if st.session_state.appointment_state.get('patient_name'):
            st.markdown("### 👤 Current Patient")
            st.write(f"**Name:** {st.session_state.appointment_state.get('patient_name')}")
            st.write(f"**Type:** {st.session_state.appointment_state.get('patient_type', 'Unknown').title()}")
            if st.session_state.appointment_state.get('appointment_id'):
                st.write(f"**Appointment ID:** {st.session_state.appointment_state.get('appointment_id')}")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Chat interface
        # Step processing
        if st.session_state.current_step == "greeting":
            if process_greeting_step():
                st.session_state.current_step = "lookup"
                logger.info("Transition: greeting -> lookup")
                st.rerun()
        
        elif st.session_state.current_step == "lookup":
            if process_lookup_step():
                st.session_state.current_step = "scheduling"
                logger.info("Transition: lookup -> scheduling")
                st.rerun()
        
        elif st.session_state.current_step == "scheduling":
            if process_scheduling_step():
                st.session_state.current_step = "insurance"
                logger.info("Transition: scheduling -> insurance")
                st.rerun()
        
        elif st.session_state.current_step == "insurance":
            if process_insurance_step():
                st.session_state.current_step = "confirmation"
                logger.info("Transition: insurance -> confirmation")
                st.rerun()
        
        elif st.session_state.current_step == "confirmation":
            if process_confirmation_step():
                st.session_state.current_step = "mailing"
                logger.info("Transition: confirmation -> mailing")
                st.rerun()
        
        elif st.session_state.current_step == "mailing":
            process_mailing_step()
    
    with col2:
        # Quick actions and info
        st.markdown("###  Quick Actions")
        
        if st.button(" Reset Session", use_container_width=True):
            # Reset everything
            st.session_state.appointment_state = {
                "errors": [],
                "retry_count": 0,
                "appointment_confirmed": False,
                "mail_sent": False,
                "current_step": "greeting"
            }
            st.session_state.chat_history = []
            st.session_state.current_step = "greeting"
            logger.info("Session reset to greeting")
            st.rerun()
        
        if st.button(" View Appointments", use_container_width=True):
            # Show appointments export
            if os.path.exists("data/appointments_export.xlsx"):
                df = pd.read_excel("data/appointments_export.xlsx")
                st.dataframe(df)
            else:
                st.info("No appointments exported yet.")
        
        if st.button("View Patients", use_container_width=True):
            # Show patient database
            if os.path.exists("data/patients.csv"):
                df = pd.read_csv("data/patients.csv")
                st.dataframe(df)
            else:
                st.info("No patient data available.")
        
        if st.button(" View Schedule", use_container_width=True):
            # Show doctor schedule with availability status
            if os.path.exists("data/doctor_schedules.xlsx"):
                df = pd.read_excel("data/doctor_schedules.xlsx")
                # Show only available slots
                available_slots = df[df['available'] == True]
                st.dataframe(available_slots)
                st.info(f"Showing {len(available_slots)} available slots out of {len(df)} total slots.")
            else:
                st.info("No schedule data available.")
        
        # Calendly Integration Section
        st.markdown("###  Calendar Integration")
        
        if st.button(" Sync with Calendar", use_container_width=True):
                # Use values from appointment_state
                appt = st.session_state.get('appointment_state', {})
                date_val = appt.get('selected_time_date')
                start_val = appt.get('selected_time_start')
                end_val = appt.get('selected_time_end')
                patient_name = appt.get('patient_name')
                doctor = appt.get('doctor')
                location_val = appt.get('location')

                # Validate required values
                if not all([date_val, start_val, end_val, patient_name, doctor, location_val]):
                    st.warning("Missing appointment details. Confirm the appointment first.")
                    logger.warning(f"Cannot create calendar event; missing values date={date_val} start={start_val} end={end_val} patient={patient_name} doctor={doctor} location={location_val}")
                else:
                    start_iso = f"{date_val}T{start_val}:00"
                    end_iso = f"{date_val}T{end_val}:00"
                    logger.info(f"Creating calendar event start={start_iso} end={end_iso} patient={patient_name} doctor={doctor}")
                    event_result = create_google_calendar_event(
                        summary=f"Medical Appointment - {patient_name}",
                        description=f"Appointment with {doctor} at {location_val}",
                        start_time=start_iso,
                        end_time=end_iso,
                        location=location_val
                    )
                    logger.info(f"Calendar event creation result: success={event_result.get('success')} id={event_result.get('event_id')}")
                    if event_result.get("success"):
                        st.write("Event added to Google Calendar!")
                        st.success("📅 Event added to Google Calendar!")
                        st.info(f"[View in Calendar]({event_result['event_url']})")
                    else:
                        st.warning(f"⚠️ Google Calendar error: {event_result.get('error')}")
                        logger.error(f"Google Calendar error: {event_result.get('error')}")
                
        # Show Calendly booking links
        # if st.session_state.appointment_state.get('doctor'):
        #     doctor = st.session_state.appointment_state.get('doctor')
        #     calendly_link = create_calendly_booking_link(doctor)
        #     if calendly_link:
        #         st.markdown(f"**Direct Calendly Booking:**")
        #         st.markdown(f"[Book with {doctor}]({calendly_link})")
        
        # Calendly configuration status
        # calendly_token = get_calendly_token()
        # if calendly_token:
        #     st.success(" Calendly API configured")
        # else:
        #     st.warning(" Calendly API not configured")
        #     st.info("Add CALENDLY_API_TOKEN to .env file")

if __name__ == "__main__":
    main()
