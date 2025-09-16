from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from typing import Dict, List, Optional, TypedDict, Literal
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain.prompts import PromptTemplate
import re 
import json
import pandas as pd
from datetime import datetime, timedelta
import os
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import smtplib
from src.helpers import clean_llm_response, get_available_slots
from src.synthetic_data_generator import DataGenerator
load_dotenv()

try:
    llm = ChatGroq(model='gemma2-9b-it')
except Exception as e:
    print(f"Warning: Could not initialize ChatGroq: {e}")
    llm = None

EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

class AgentState(TypedDict):
    # Patient Information
    patient_name: str
    date_of_birth: str
    doctor: str
    location: str
    patient_type: Literal['new', 'existing']
    appointment_duration: Literal['30 minutes', '60 minutes']
    selected_time_start: str
    selected_time_end: str
    selected_time_date: str
    selected_slot: Optional[Dict]
    appointment_id: str
    insurance_carrier: str
    insurance_member_id: str
    insurance_group: str
    patient_email: str
    patient_contact: str
    appointment_confirmed: bool
    patient_id: Optional[int]
    message: str
    response: str
    available_slots: List[Dict]
    user_input: bool
    mail_sent: bool
    errors: List[str]
    retry_count: int
    current_step: str

def validate_email(email: str) -> bool:
 
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    
    digits_only = re.sub(r'\D', '', phone)
    return len(digits_only) >= 10

def validate_date_format(date_str: str) -> bool:

    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def safe_llm_call(prompt_template: PromptTemplate, input_data: dict, max_retries: int = 3):
    """Safely call LLM with retry logic"""
    if not llm:
        return {"error": "LLM not initialized"}
    
    for attempt in range(max_retries):
        try:
            chain = prompt_template | llm
            response = chain.invoke(input_data)
            extracted_text = response.content if hasattr(response, 'content') else response.text
            return clean_llm_response(extracted_text)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"LLM call failed after {max_retries} attempts: {e}")
                return {"error": str(e)}
            print(f"LLM call attempt {attempt + 1} failed, retrying...")

def greeting(state: AgentState) -> AgentState:
    """Process greeting information - pure logic function"""
    state.setdefault('errors', [])
    state.setdefault('retry_count', 0)
    state['current_step'] = 'greeting'
    
    # Check if we've already exceeded retry limit
    if state['retry_count'] >= 3:
        return {**state, "errors": ["Maximum retry attempts exceeded"]}
    
    # Get user input from state (provided by main function)
    message = state.get('user_input', '')
    
    if not message.strip():
        return {**state, "errors": ["Empty input provided"], "retry_count": state['retry_count'] + 1}
        
    extract_info_prompt = PromptTemplate(
        input_variables=["message"],
        template="""
        Extract the following information from the user's message. Be very careful about date formats.
        
        User Message: {message}
        
        Extract:
        1. Full Name (first and last name)
        2. Date of Birth (must be in YYYY-MM-DD format, convert if necessary)
        3. Preferred Doctor (should include "Dr." title if not present)
        4. Location (clinic location)
        
        Return JSON format:
        {{
            "Full Name": "<name or Not Provided>",
            "Date of Birth": "<YYYY-MM-DD or Not Provided>", 
            "Preferred Doctor": "<Dr. Name or Not Provided>",
            "Location": "<location or Not Provided>"
        }}
        
        JSON:"""
    )
    
    result = safe_llm_call(extract_info_prompt, {"message": message})
    
    if "error" in result:
        return {**state, "errors": ["Failed to process information"], "retry_count": state['retry_count'] + 1}
        
    full_name = result.get("Full Name", "Not Provided")
    dob = result.get("Date of Birth", "Not Provided") 
    doctor = result.get("Preferred Doctor", "Not Provided")
    location = result.get("Location", "Not Provided")
    
    current_errors = []
    
    if full_name == "Not Provided" or len(full_name.strip()) < 2:
        current_errors.append("Valid full name required")
        
    if dob == "Not Provided" or not validate_date_format(dob):
        current_errors.append("Date of birth in YYYY-MM-DD format required")
        
    if doctor == "Not Provided":
        current_errors.append("Preferred doctor required")
    elif not doctor.startswith("Dr."):
        doctor = f"Dr. {doctor}"
        
    if location == "Not Provided":
        current_errors.append("Location required")
        
    if current_errors:
        return {**state, "errors": current_errors, "retry_count": state['retry_count'] + 1}
    
    return {
        **state,
        "patient_name": full_name,
        "date_of_birth": dob,
        "doctor": doctor,
        "location": location,
        "errors": [],
        "retry_count": 0
    }

def lookup(state: AgentState) -> AgentState:
    """Look up patient in database - pure logic function"""
    state['current_step'] = 'lookup'
    
    # Validate required fields
    if not state.get('patient_name') or not state.get('date_of_birth'):
        return {**state, "patient_id": None, "patient_type": "new", 
                "appointment_duration": "60 minutes", 
                "errors": ["Insufficient patient information"]}
    
    try:
        # Load patient database
        file_path = "data/patients.csv"
        
        if not os.path.exists(file_path):
            # Create empty database
            df = pd.DataFrame(columns=[
                "id", "full_name", "last_name", "date_of_birth", 
                "email", "phone", "insurance_carrier", "insurance_member_id", 
                "insurance_group", "created_date"
            ])
            os.makedirs("data", exist_ok=True)
            df.to_csv(file_path, index=False)
        else:
            df = pd.read_csv(file_path)
        
        # Search for patient (case-insensitive)
        match = df[
            (df['full_name'].str.lower() == state['patient_name'].lower()) & 
            (df['date_of_birth'] == state['date_of_birth'])
        ]
        
        if not match.empty:
            patient_row = match.iloc[0]
            
            return {
                **state,
                "patient_id": int(patient_row['id']),
                "patient_type": "existing",
                "appointment_duration": "30 minutes",
                "insurance_carrier": patient_row.get('insurance_carrier', ''),
                "insurance_member_id": patient_row.get('insurance_member_id', ''),
                "insurance_group": patient_row.get('insurance_group', ''),
                "patient_contact": patient_row.get('phone', ''),
                "patient_email": patient_row.get('email', '')
            }
        else:
            return {
                **state,
                "patient_id": None,
                "patient_type": "new", 
                "appointment_duration": "60 minutes"
            }
            
    except Exception as e:
        return {
            **state, 
            "patient_id": None, 
            "patient_type": "new", 
            "appointment_duration": "60 minutes",
            "errors": [f"Database error: {str(e)}"]
        }

def scheduling_new(state: AgentState) -> AgentState:
    return _scheduling_logic(state, "new", "60 minutes")

def scheduling_returning(state: AgentState) -> AgentState:
    
    return _scheduling_logic(state, "existing", "30 minutes")

def _scheduling_logic(state: AgentState, patient_type: str, duration: str) -> AgentState:
    """Scheduling logic - pure function"""
    state['current_step'] = f'scheduling_{patient_type}'
    
    try:
        file_path = "data/doctor_schedules.xlsx"
        
        if not os.path.exists(file_path):
            return {**state, "errors": ["Schedule database not available"]}
            
        df = pd.read_excel(file_path)
        
        # Validate doctor
        if not state.get('doctor') or state['doctor'] == "Not Provided":
            available_doctors = df['doctor_name'].unique().tolist()
            return {**state, "errors": ["Doctor selection required"], 
                    "available_doctors": available_doctors}
        
        if state['doctor'] not in df['doctor_name'].values:
            available_doctors = df['doctor_name'].unique().tolist()
            return {**state, "errors": [f"Doctor {state['doctor']} not available"], 
                    "available_doctors": available_doctors}
        
        # Validate location
        doctor_locations = df[df['doctor_name'] == state['doctor']]['location'].unique().tolist()
        
        if not state.get('location') or state['location'] == "Not Provided":
            return {**state, "errors": ["Location selection required"], 
                    "available_locations": doctor_locations}
            
        if state['location'] not in doctor_locations:
            return {**state, "errors": [f"Location {state['location']} not available"], 
                    "available_locations": doctor_locations}
        
        # Get available slots
        duration_minutes = 60 if duration == "60 minutes" else 30
        available_slots = get_available_slots(file_path, duration_minutes, state['doctor'], state['location'])
        
        if not available_slots:
            return {**state, "errors": ["No available appointment slots"], 
                    "available_slots": []}
        
        # Get user selection from state
        slot_selection = state.get('slot_selection')
        if slot_selection is None:
            return {**state, "available_slots": available_slots, "errors": []}
        
        try:
            slot_index = int(slot_selection) - 1
            if 0 <= slot_index < len(available_slots):
                selected_slot = available_slots[slot_index]
                
                return {
                    **state,
                    "selected_time_start": selected_slot['start_time'],
                    "selected_time_end": selected_slot['end_time'], 
                    "selected_time_date": selected_slot['date'],
                    "selected_slot": selected_slot,
                    "available_slots": available_slots,
                    "errors": []
                }
            else:
                return {**state, "errors": [f"Invalid slot selection. Please choose 1-{len(available_slots)}"], 
                        "available_slots": available_slots}
        except ValueError:
            return {**state, "errors": ["Invalid slot selection. Please enter a number"], 
                    "available_slots": available_slots}
        
    except Exception as e:
        return {**state, "errors": [f"Scheduling system error: {str(e)}"]}

def insurance(state: AgentState) -> AgentState:
    """Insurance information processing - pure logic function"""
    state['current_step'] = 'insurance'
    
    if state.get('patient_type') == 'existing':
        return state
    
    # Check retry count
    retry_count = state.get('retry_count', 0)
    if retry_count >= 3:
        return {**state, "errors": ["Failed to collect insurance information"]}
    
    # Get user input from state
    message = state.get('insurance_input', '')
    
    if not message.strip():
        return {**state, "errors": ["Insurance information cannot be empty"], "retry_count": retry_count + 1}
        
    # Extract insurance info
    extract_info_prompt = PromptTemplate(
        input_variables=["message"],
        template="""
        Extract insurance information from the user's message:
        
        User Message: {message}
        
        Extract:
        1. Insurance Carrier (company name)
        2. Member ID (ID number)  
        3. Group (group number/name)
        
        JSON format:
        {{
            "Insurance Carrier": "<carrier or Not Provided>",
            "Member ID": "<id or Not Provided>", 
            "Group": "<group or Not Provided>"
        }}
        
        JSON:"""
    )
    
    result = safe_llm_call(extract_info_prompt, {"message": message})
    
    if "error" in result:
        return {**state, "errors": ["Failed to process insurance information"], "retry_count": retry_count + 1}
        
    carrier = result.get("Insurance Carrier", "Not Provided")
    member_id = result.get("Member ID", "Not Provided")
    group = result.get("Group", "Not Provided")
    
    # Validation
    errors = []
    if carrier == "Not Provided" or len(carrier.strip()) < 2:
        errors.append("Insurance carrier required")
    if member_id == "Not Provided" or len(member_id.strip()) < 3:
        errors.append("Member ID required")
    if group == "Not Provided" or len(group.strip()) < 1:
        errors.append("Group information required")
        
    if errors:
        return {**state, "errors": errors, "retry_count": retry_count + 1}
        
    # Get contact information from state
    contact_info = {
        "patient_email": state.get('patient_email', ''),
        "patient_contact": state.get('patient_contact', '')
    }
    
    return {
        **state,
        "insurance_carrier": carrier,
        "insurance_member_id": member_id,
        "insurance_group": group,
        **contact_info,
        "errors": []
    }


def confirmation(state: AgentState) -> AgentState:
    """Appointment confirmation - pure logic function"""
    state['current_step'] = 'confirmation'
    
    # Check for missing required information
    required_fields = [
        ('patient_name', 'Patient Name'),
        ('date_of_birth', 'Date of Birth'),
        ('doctor', 'Doctor'),
        ('location', 'Location'),
        ('selected_time_date', 'Appointment Date'),
        ('selected_time_start', 'Start Time'),
        ('insurance_carrier', 'Insurance Carrier'),
        ('patient_email', 'Email'),
        ('patient_contact', 'Phone')
    ]
    
    missing_fields = []
    for field, display_name in required_fields:
        if not state.get(field) or state.get(field) == 'Not provided':
            missing_fields.append(display_name)
    
    if missing_fields:
        return {**state, "errors": [f"Missing: {', '.join(missing_fields)}"]}
    
    # Get confirmation from state
    confirm = state.get('confirmation_input', '').strip().lower()
    
    if confirm in ['yes', 'y', 'confirm', 'ok', 'correct']:
        # Generate appointment ID
        appointment_id = f"APT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Save patient if new
        if state.get('patient_type') == 'new':
            patient_id = _save_new_patient(state)
            state['patient_id'] = patient_id
        
        return {
            **state,
            "appointment_confirmed": True,
            "appointment_id": appointment_id,
            "errors": []
        }
        
    elif confirm in ['no', 'n', 'cancel', 'abort']:
        return {**state, "appointment_confirmed": False, "errors": ["Cancelled by user"]}
        
    else:
        return {**state, "errors": ["Please answer 'yes' or 'no'"]}

def _save_new_patient(state: AgentState) -> int:
    """Save new patient to database"""
    try:
        file_path = "data/patients.csv"
        
        # Load existing data or create new
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
        else:
            df = pd.DataFrame(columns=[
                "id", "full_name",  "date_of_birth",
                "email", "phone", "insurance_carrier", "insurance_member_id",
                "insurance_group", "created_date"
            ])
        
        # Generate new ID
        new_id = len(df) + 1 if not df.empty else 1
        
        # Create patient record
        new_patient = {
            "id": new_id,
            "full_name": state['patient_name'],
            "date_of_birth": state['date_of_birth'],
            "email": state['patient_email'],
            "phone": state['patient_contact'],
            "insurance_carrier": state['insurance_carrier'],
            "insurance_member_id": state['insurance_member_id'],
            "insurance_group": state['insurance_group'],
            "created_date": datetime.now().isoformat()
        }
        
        df = pd.concat([df, pd.DataFrame([new_patient])], ignore_index=True)
        df.to_csv(file_path, index=False)
        
        return new_id
        
    except Exception as e:
        return None

def send_email(to_email: str, subject: str, body: str, attachment_path: Optional[str] = None) -> bool:

    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Add attachment if provided
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition", 
                    f"attachment; filename={os.path.basename(attachment_path)}"
                )
                msg.attach(part)
        
        # Send email if credentials available
        if EMAIL_SENDER and EMAIL_PASSWORD:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)
            return True
        else:
            print("📧 Email credentials not configured - email content prepared")
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print(f"Body:\n{body}")
            return True
            
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def mailing(state: AgentState) -> AgentState:
    """Send confirmation email - pure logic function"""
    state['current_step'] = 'mailing'
    
    if not state.get("appointment_confirmed"):
        return {**state, "mail_sent": False}
    
    # Create email body
    body = f"""Dear {state['patient_name']},

Your appointment has been successfully confirmed!

APPOINTMENT DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Appointment ID: {state['appointment_id']}
Patient Type: {state['patient_type'].title()}
Doctor: {state['doctor']}
Date: {state['selected_time_date']}
Time: {state['selected_time_start']} - {state['selected_time_end']}
Duration: {state['appointment_duration']}
Location: {state['location']}

INSURANCE INFORMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Carrier: {state['insurance_carrier']}
Member ID: {state['insurance_member_id']}
Group: {state['insurance_group']}

IMPORTANT REMINDERS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Please arrive 15 minutes before your appointment time
• Bring a valid photo ID and insurance card
• Bring any relevant medical records or test results
{f'• Complete the attached intake forms within 24 hours' if state['patient_type'] == 'new' else ''}

If you need to reschedule or cancel, please contact us at least 24 hours in advance.

Thank you for choosing us!

Best regards,
MediCare Appointment System
"""

    attachment_path = None
    if state['patient_type'] == "new":
        attachment_path = "forms/New Patient Intake Form.pdf"
        if not os.path.exists(attachment_path):
            attachment_path = None

    subject = f"Appointment Confirmation - {state['appointment_id']}"
    success = send_email(state['patient_email'], subject, body, attachment_path)
    
    if success:
        # Export to Excel for admin review
        _export_appointment_to_excel(state)
        return {**state, "mail_sent": True}
    else:
        return {**state, "mail_sent": False}

def _export_appointment_to_excel(state: AgentState):
    try:
        file_path = "data/appointments_export.xlsx"
        
        appointment_data = {
            "Appointment ID": [state['appointment_id']],
            "Date Created": [datetime.now().isoformat()],
            "Patient Name": [state['patient_name']],
            "Patient Type": [state['patient_type']],
            "Date of Birth": [state['date_of_birth']],
            "Doctor": [state['doctor']],
            "Location": [state['location']],
            "Appointment Date": [state['selected_time_date']],
            "Start Time": [state['selected_time_start']],
            "End Time": [state['selected_time_end']],
            "Duration": [state['appointment_duration']],
            "Insurance Carrier": [state['insurance_carrier']],
            "Member ID": [state['insurance_member_id']],
            "Group": [state['insurance_group']],
            "Email": [state['patient_email']],
            "Phone": [state['patient_contact']],
            "Email Sent": [state.get('mail_sent', False)]
        }
        
        new_df = pd.DataFrame(appointment_data)
        
        if os.path.exists(file_path):
            existing_df = pd.read_excel(file_path)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
            os.makedirs("data", exist_ok=True)
        
        combined_df.to_excel(file_path, index=False)
        
    except Exception as e:
        pass  # Silent failure

def setup_reminder_system(state: AgentState) -> AgentState:
    """Setup automated reminder system - pure logic function"""
    if not state.get("appointment_confirmed"):
        return state
    
    try:
        # Calculate reminder dates
        appointment_date_str = state['selected_time_date']
        appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d')
        
        reminders = [
            {
                "type": "initial",
                "date": appointment_date - timedelta(days=3),
                "message": "Reminder: You have an upcoming appointment in 3 days"
            },
            {
                "type": "forms_check", 
                "date": appointment_date - timedelta(days=1),
                "message": "Please confirm: Have you completed your intake forms?"
            },
            {
                "type": "final_confirmation",
                "date": appointment_date - timedelta(hours=2),
                "message": "Final reminder: Your appointment is in 2 hours. Please confirm attendance."
            }
        ]
        
        return {**state, "reminders_set": True, "reminders": reminders}
        
    except Exception as e:
        return {**state, "reminders_set": False}

def handle_errors(state: AgentState) -> str:
    """Route based on errors in state"""
    errors = state.get('errors', [])
    
    if not errors:
        return "END"
    
    current_step = state.get('current_step', '')
    
    # Route back to appropriate step based on error type
    error_routes = {
        'greeting': 'greeting',
        'lookup': 'lookup', 
        'scheduling_new': 'scheduling_new',
        'scheduling_returning': 'scheduling_returning',
        'insurance': 'insurance',
        'confirmation': 'confirmation'
    }
    
    return error_routes.get(current_step, 'END')

def create_workflow():
    """Create and configure the workflow - simplified for manual orchestration"""
    # Since we're handling the flow manually in main(), we don't need a complex workflow
    # This is kept for potential future use or if you want to switch back to automatic flow
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("greeting", greeting)
    workflow.add_node("lookup", lookup)
    workflow.add_node("scheduling_new", scheduling_new)
    workflow.add_node("scheduling_returning", scheduling_returning)
    workflow.add_node("insurance", insurance)
    workflow.add_node("confirmation", confirmation)
    workflow.add_node("mailing", mailing)
    workflow.add_node("setup_reminders", setup_reminder_system)
    
    # Simple linear flow
    workflow.set_entry_point("greeting")
    workflow.add_edge("greeting", "lookup")
    workflow.add_edge("lookup", "scheduling_new")
    workflow.add_edge("scheduling_new", "insurance")
    workflow.add_edge("insurance", "confirmation")
    workflow.add_edge("confirmation", "mailing")
    workflow.add_edge("mailing", "setup_reminders")
    workflow.add_edge("setup_reminders", END)
    
    return workflow.compile()

def main():
    """Main application entry point with UI handling"""
    print(" AI Scheduling Agent")
    print("=" * 50)
    
    # Create sample data if not exists
    if not os.path.exists("data/patients.csv"):
        data_generator = DataGenerator()
        data_generator.generate_synthetic_data()
    
    try:
        # Create workflow
        workflow = create_workflow()
        
        print("\n🚀 Starting appointment booking process...")
        print("Press Ctrl+C at any time to cancel\n")
        
        # Initialize state
        state = {
            "errors": [],
            "retry_count": 0,
            "appointment_confirmed": False,
            "mail_sent": False
        }
        
        # Step 1: Greeting and basic info
        print("\n Welcome to Appointment Scheduling System!")
        print("Please provide the following information:")
        print("1. Full Name")
        print("2. Date of Birth (YYYY-MM-DD format)")
        print("3. Preferred Doctor")
        print("4. Location")
        
        while True:
            if state.get('errors'):
                print("\nPrevious errors:")
                for error in state['errors']:
                    print(f"   • {error}")
                print("Please provide the missing/corrected information.\n")
            
            message = input("Your information: ")
            state['user_input'] = message
            
            # Process greeting
            state = greeting(state)
            
            if not state.get('errors'):
                break
            elif state.get('retry_count', 0) >= 3:
                print("Maximum retry attempts reached. Please restart the system.")
                return
        
        # Step 2: Patient lookup
        print(f"\n Looking up patient: {state['patient_name']} (DOB: {state['date_of_birth']})")
        state = lookup(state)
        
        if state.get('patient_type') == 'existing':
            print(f"Existing patient found! ID: {state.get('patient_id')}")
        else:
            print("ℹNo existing patient found. Proceeding as new patient.")
        
        # Step 3: Scheduling
        patient_type = state.get('patient_type')
        duration = state.get('appointment_duration')
        
        print(f"    Scheduling appointment for {patient_type} patient")
        print(f"    Duration: {duration}")
        print(f"    Doctor: {state.get('doctor', 'Not specified')}")
        print(f"    Location: {state.get('location', 'Not specified')}")
        
        # Process scheduling
        if patient_type == 'existing':
            state = scheduling_returning(state)
        else:
            state = scheduling_new(state)
        
        if state.get('errors'):
            print(f"Error: {state['errors'][0]}")
            return
        
        # Show available slots and get selection
        available_slots = state.get('available_slots', [])
        if available_slots:
            print(f"\n Found {len(available_slots)} available slots:")
            print("=" * 50)
            
            for i, slot in enumerate(available_slots, 1):
                print(f"{i:2}. {slot['date']} | {slot['start_time']} - {slot['end_time']}")
            
            while True:
                try:
                    selection = input(f"\nSelect slot (1-{len(available_slots)}): ")
                    state['slot_selection'] = selection
                    
                    # Re-process scheduling with selection
                    if patient_type == 'existing':
                        state = scheduling_returning(state)
                    else:
                        state = scheduling_new(state)
                    
                    if not state.get('errors'):
                        selected_slot = state.get('selected_slot')
                        print(f"\n✅ Selected: {selected_slot['date']} at {selected_slot['start_time']}-{selected_slot['end_time']}")
                        break
                    else:
                        print(f" {state['errors'][0]}")
                        
                except ValueError:
                    print("  Please enter a valid number")
                except KeyboardInterrupt:
                    print("\n Appointment booking cancelled")
                    return
        
        # Step 4: Insurance (for new patients)
        if state.get('patient_type') == 'new':
            print("\n💳 Insurance Information Required")
            print("Please provide your insurance details:")
            
            while True:
                if state.get('errors'):
                    print("\n  Please provide complete insurance information:")
                
                message = input("Insurance Carrier, Member ID, and Group: ")
                state['insurance_input'] = message
                
                # Get contact information
                while True:
                    email = input("Email address: ").strip()
                    if validate_email(email):
                        state['patient_email'] = email
                        break
                    print(" Please enter a valid email address")
                
                while True:
                    phone = input("Phone number: ").strip()
                    if validate_phone(phone):
                        state['patient_contact'] = phone
                        break
                    print(" Please enter a valid phone number (at least 10 digits)")
                
                # Process insurance
                state = insurance(state)
                
                if not state.get('errors'):
                    break
                elif state.get('retry_count', 0) >= 3:
                    print(" Maximum retries for insurance information reached")
                    return
        else:
            print("\n Using existing insurance information on file")
            state = insurance(state)
        
        # Step 5: Confirmation
        print("\n" + "="*60)
        print(" APPOINTMENT SUMMARY")
        print("="*60)
        
        details = {
            "Patient Name": state.get('patient_name', 'Not provided'),
            "Date of Birth": state.get('date_of_birth', 'Not provided'),
            "Patient Type": state.get('patient_type', 'Not provided'),
            "Doctor": state.get('doctor', 'Not provided'),
            "Location": state.get('location', 'Not provided'),
            "Appointment Date": state.get('selected_time_date', 'Not provided'),
            "Appointment Time": f"{state.get('selected_time_start', 'Not provided')} - {state.get('selected_time_end', 'Not provided')}",
            "Duration": state.get('appointment_duration', 'Not provided'),
            "Insurance Carrier": state.get('insurance_carrier', 'Not provided'),
            "Member ID": state.get('insurance_member_id', 'Not provided'),
            "Group": state.get('insurance_group', 'Not provided'),
            "Email": state.get('patient_email', 'Not provided'),
            "Phone": state.get('patient_contact', 'Not provided')
        }
        
        for key, value in details.items():
            print(f"{key:20}: {value}")
        
        print("="*60)
        
        while True:
            confirm = input("\n✅ Confirm appointment? (yes/no): ").strip().lower()
            state['confirmation_input'] = confirm
            
            # Process confirmation
            state = confirmation(state)
            
            if state.get('errors'):
                if "Missing:" in state['errors'][0]:
                    print(f"\n Missing required information: {state['errors'][0]}")
                    return
                elif "Please answer" in state['errors'][0]:
                    print("Please answer 'yes' or 'no'")
                    continue
                else:
                    print(f" {state['errors'][0]}")
                    return
            else:
                break
        
        if state.get('appointment_confirmed'):
            print(f"\n Appointment confirmed!")
            print(f" Appointment ID: {state.get('appointment_id')}")
            
            # Step 6: Send email
            print("\n Preparing confirmation email...")
            state = mailing(state)
            
            if state.get('mail_sent'):
                print("Confirmation email sent successfully!")
                print(f" Appointment exported to data/appointments_export.xlsx")
            else:
                print(" Failed to send confirmation email")
            
            # Step 7: Setup reminders
            print("\n Setting up reminder system...")
            state = setup_reminder_system(state)
            
            if state.get('reminders_set'):
                print(" Reminder system configured:")
                for reminder in state.get('reminders', []):
                    print(f"   • {reminder['type']}: {reminder['date'].strftime('%Y-%m-%d %H:%M')}")
            else:
                print(" Reminder system setup completed")
            
            # Final summary
            print("\n BOOKING COMPLETE!")
            print("=" * 50)
            print(f"Appointment ID: {state.get('appointment_id', 'N/A')}")
            print(f"Patient: {state.get('patient_name', 'N/A')}")
            print(f"Date: {state.get('selected_time_date', 'N/A')}")
            print(f"Time: {state.get('selected_time_start', 'N/A')}-{state.get('selected_time_end', 'N/A')}")
            print(f"Doctor: {state.get('doctor', 'N/A')}")
            print(f"Email sent: {'Yes' if state.get('mail_sent') else 'No'}")
        else:
            print(" Appointment cancelled")
        
    except KeyboardInterrupt:
        print("\n\nBooking cancelled by user")
    except Exception as e:
        print(f"\nSystem error: {e}")
        print("Please contact system administrator")

if __name__ == "__main__":
    main()