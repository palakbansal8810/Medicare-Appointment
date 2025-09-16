# MediCare Appointment System 
An appointment booking system built with Streamlit. Patients can select a doctor and location, choose an available slot, confirm the appointment, receive an email confirmation, and optionally add the event to Google Calendar.

## Features

- Patient information collection (name, DOB, doctor, location)
- Patient lookup (new vs returning)
- Smart scheduling: 60 min for new, 30 min for returning
- Availability listing from `data/doctor_schedules.xlsx`
- Insurance collection and validation
- Appointment confirmation and export to Excel
- Email confirmation with optional intake form for new patients
- Optional Google Calendar event creation via OAuth
- Automated reminders (3 notifications)
- Rotating logs to `logs/app.log`

## Installation

1) Create a virtual environment and install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

2) Environment variables (email, LLM optional)

Create a `.env` file in the project root:

```
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
GROQ_API_KEY=your-groq-api-key
```

- Use a Gmail App Password (Google Account → Security → App passwords)

## Running

Start the Streamlit app:

```bash
streamlit run app.py
```

Open the browser URL printed in the terminal (usually `http://localhost:8501`).

## Using the App

1) Patient Info: Enter name, DOB, choose doctor and location
2) Lookup: System determines new vs returning
3) Scheduling: Select an available slot shown
4) Insurance: For new patients, enter carrier, member ID, group, email, phone
5) Confirmation: Review summary and click Confirm Appointment
6) Final Steps: Email confirmation is sent and reminders configured
7) Optional: In the sidebar, click “Sync with Calendar” to add the event to Google Calendar

## Google Calendar Integration

The app supports adding a confirmed appointment to Google Calendar using OAuth.

1) Create an OAuth client (Desktop app) in Google Cloud Console:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID → Application type: Desktop app
   - Download the JSON to `credentials/` (the code expects a file there). If you use a different filename, update the path in `src/google_calender.py`.

2) First-run OAuth flow:
   - When you confirm and add to calendar (or use the sidebar button), a browser window opens to grant permission
   - After consent, `token.pickle` is saved at the project root for reuse
   - The app auto-recovers if `token.pickle` is empty/corrupt (it will re-authenticate)

3) Troubleshooting 400 Bad Request:
   - Ensure the appointment is confirmed so date/start/end exist
   - Ensure end time is after start time
   - Delete `token.pickle` and try again if auth gets stuck

## Email Configuration

- Set `EMAIL_SENDER` and `EMAIL_PASSWORD` in `.env`
- Use a Gmail App Password
- Email is sent via SMTP (`smtp.gmail.com:587` with STARTTLS)

## Data and Exports

- `data/patients.csv`: patient records (auto-created with synthetic data if missing)
- `data/doctor_schedules.xlsx`: doctor availability
- `data/appointments_export.xlsx`: appended after successful email send
- `forms/New Patient Intake Form.pdf`: included for new patients if present

## Logging

- Logs are written to `logs/app.log` and the console
- Major steps logged: session init, step transitions, scheduling results, confirmation, email result, calendar API result

## File Structure

```
Automated Appointment/
├── app.py                          # Streamlit UI and flow
├── main.py                         # Core logic (also has CLI flow)
├── src/
│   ├── helpers.py                  # Helper functions
│   ├── synthetic_data_generator.py # Synthetic data for testing
│   ├── google_calender.py          # Google Calendar OAuth and event creation
│   └── test_slot_update.py         # Slot update tests
├── data/
│   ├── patients.csv
│   ├── doctor_schedules.xlsx
│   └── appointments_export.xlsx
├── forms/
│   └── New Patient Intake Form.pdf
├── credentials/
│   └── <oauth_client>.json         # Your Google OAuth client file
├── requirements.txt
└── README.md
```


