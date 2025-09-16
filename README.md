# MediCare Appointment System - Streamlit Chatbot

A comprehensive appointment booking system built with Streamlit that provides a chatbot interface for patients to schedule medical appointments.

## Features

### Core Features (MVP-1)
- **Patient Greeting**: Collect name, DOB, doctor preference, and location
- **Patient Lookup**: Search EMR system, detect new vs returning patients
- **Smart Scheduling**: 60min for new patients, 30min for returning patients
- **Calendar Integration**: Show available slots with real-time availability
- **Insurance Collection**: Capture carrier, member ID, and group information
- **Appointment Confirmation**: Export to Excel and send email confirmations
- **Form Distribution**: Email patient intake forms after confirmation
- **Reminder System**: 3 automated reminders with confirmation tracking

### Technical Features
- **Chatbot Interface**: Interactive conversation flow with message history
- **Form Components**: Modern UI with select boxes and input validation
- **State Management**: Persistent session state throughout the booking process
- **Data Integration**: CSV patient database and Excel scheduling system
- **Email Integration**: Automated confirmation emails with attachments
- **Export Functionality**: Excel reports for admin review

## Installation

1. **Download the project files and create virtual env**
   ```bash
   python -m venv ragaenv
   ragaenv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (optional for email and Calendly functionality):
   Create a `.env` file in the project root:
   ```
   EMAIL_SENDER=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   GROQ_API_KEY=your-groq-api-key
   CALENDLY_API_TOKEN=your-calendly-api-token
   ```
Get the email app password from google security app specific passwords 
## Usage

### Running the Streamlit App

1. **Start the application**:
   ```bash
   streamlit run app.py
   ```

2. **Open your browser** to the URL shown in the terminal (usually `http://localhost:8501`)

### Running the chat based structure

1. **Run main.py file**
   ```bash
   python main.py
   ```
2. **Input all details**
eg:
   ```bash
   "My name is Palak Bansal, 23rd jan 2006, Dr. Smith at Suburban Center"
   ```
3. **Select the slot**
eg:
   ```bash
   4
   ```
4. **Insurance details**
eg:
   ```bash
   "Blue New is my carrier, 3234 is member id, Grp342"
   ```
5. **Input phone number and email**

6. **Confirm details**

Appointment Confirmed!

### Using the System

1. **Patient Information**: Enter your full name, date of birth, preferred doctor, and location
2. **Patient Lookup**: The system automatically checks if you're an existing patient
3. **Scheduling**: Choose from available appointment slots
4. **Insurance**: Provide insurance details (for new patients only)
5. **Confirmation**: Review and confirm your appointment details
6. **Final Steps**: Receive confirmation email and automated reminders

### Navigation

- **Sidebar**: Shows current step, progress, and patient information
- **Main Area**: Chat interface and form components
- **Quick Actions**: Reset session, view appointments, view patients

## File Structure

```
RagaAI/
├── app.py                                   # Main Streamlit application
├── main.py                                  # Core appointment logic and functions(A chat based structure)
├── demo.py                                  # Demo for the app
├── src/                                     
│   ├── synthetic_data_generator.py          # Data generation for testing
│   ├── helpers.py                           # Helper functions
│   ├── test_calendly_integration.py         # Calendly integratioh for testing
│   ├── test_slot_update.py                  # Slot updation for testing
│   └── calendly_config.py                   # For Calendly Configuration           
├── requirements.txt                         # Python dependencies
├── data/                                   
│   ├── patients.csv                         # Patient database
│   ├── doctor_schedules.xlsx                # Doctor availability
│   └── appointments_export.xlsx             # Exported appointments
└── forms/                                   
    └── New Patient Intake Form.pdf          # Patient intake forms
└── research/                                
    └── main.ipynb                           # For the initial logic
```

## Data Sources

### Mock Data (Automatically Generated)
- **Patient Database**: 50 synthetic patients with insurance information
- **Doctor Schedules**: Excel files with availability for multiple doctors and locations
- **Appointment Templates**: Form templates for new patients

### Supported Doctors
- Dr. Smith, Dr. Johnson, Dr. Williams, Dr. John, Dr. Robin

### Supported Locations

- Main Clinic
- Downtown Office
- Suburban Center
- Railway Clinic

## Technical Stack

- **Frontend**: Streamlit for UI
- **Backend**: Python with LangGraph + LangChain
- **LLM**: Groq (Gemma2-9b-it model)
- **Data Storage**: CSV and Excel files
- **Email**: SMTP integration for confirmations
- **Calendly API**: Calendly for syncing slots

## Features in Detail

### Form Components
- Patient information collection
- Doctor and location selection
- Time slot selection
- Insurance information forms
- Appointment confirmation

### State Management
- Session state persistence
- Step-by-step flow control
- Error handling and retry logic
- Progress tracking

### Integration Features
- Patient database lookup
- Real-time availability checking
- Email confirmation system
- Excel export functionality
- Automated reminder setup
- **Dynamic slot availability management** - Automatically marks slots as unavailable when booked and restores them when cancelled
- **Calendly Integration** - Full integration with Calendly for calendar management and event creation

### Slot Availability Management
The system now includes intelligent slot management:
- **Automatic Slot Booking**: When an appointment is confirmed, the selected time slot(s) are automatically marked as unavailable in the doctor_schedules.xlsx file
- **Slot Restoration**: If an appointment is cancelled, the slot availability is restored
- **Real-time Updates**: The schedule is updated immediately, preventing double-booking
- **Admin View**: Use the "View Schedule" button in the sidebar to see current availability status

### Calendly Integration
The system includes comprehensive Calendly integration:
- **Event Creation**: Automatically creates Calendly events when appointments are confirmed
- **Availability Sync**: Syncs available time slots from Calendly to the local Excel schedule
- **Direct Booking Links**: Provides direct Calendly booking links for each doctor
- **API Integration**: Full Calendly API integration for real-time calendar management
- **Webhook Support**: Complete webhook integration for real-time updates
- **Event Handling**: Processes appointment created, canceled, rescheduled, and no-show events
- **Security**: Webhook signature verification for secure event processing

#### Calendly Setup Instructions:
1. **Get Calendly API Token**: 
   - Go to Calendly Settings > Integrations > API & Webhooks
   - Generate a Personal Access Token
   - Add it to your `.env` file as `CALENDLY_API_TOKEN`

2. **Configure Doctor Calendly URIs**:
   - Each doctor needs a Calendly account
   - Update the doctor mappings in `calendly_config.py`
   - Replace placeholder URIs with actual Calendly URIs

3. **Test Integration**:
   - Use the "Sync with Calendly" button in the sidebar
   - Check the Calendly configuration status
   - Verify event creation during appointment confirmation

