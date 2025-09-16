from __future__ import print_function
import datetime
import os.path
import pickle

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import socket
from contextlib import closing
# Google Calendar API Scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

def find_available_port():
    """Find an available port for OAuth callback."""
    # Try common ports that are usually free
    # Prefer 8080 because it's already authorized in the OAuth client
    preferred_ports = [8080, 8081, 8082, 8083, 9000, 9001, 9002]
    
    for port in preferred_ports:
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                sock.bind(('localhost', port))
                return port
        except OSError:
            continue
    
    # If no preferred port is available, find any free port
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('localhost', 0))
        return sock.getsockname()[1]

def get_google_calendar_service():
    """Authenticate and return a Google Calendar API service object with port handling."""
    creds = None
    if os.path.exists('token.pickle'):
        try:
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        except Exception:
            # Handle corrupt/empty token files gracefully by deleting and re-authenticating
            try:
                os.remove('token.pickle')
            except Exception:
                pass
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                # If refresh fails, delete token and re-authenticate
                if os.path.exists('token.pickle'):
                    os.remove('token.pickle')
                creds = None
        
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials/client_secret_2_734803652945-4rqqq0bjrd1mruqa7a4l2pftj3crhmah.apps.googleusercontent.com.json', 
                SCOPES
            )
            
            # Find available port
            available_port = find_available_port()
            print(f"Using port {available_port} for OAuth callback")
            
            try:
                creds = flow.run_local_server(port=available_port, open_browser=True)
            except Exception as e:
                if "redirect_uri_mismatch" in str(e):
                    print(f"\n❌ Redirect URI mismatch for port {available_port}")
                    print("🔧 SOLUTION:")
                    print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
                    print("2. Navigate to: APIs & Services > Credentials")
                    print("3. Edit your OAuth 2.0 Client ID")
                    print(f"4. Add this URI: http://localhost:{available_port}/")
                    print("5. Save and try again")
                    raise e
                else:
                    # Try manual authentication as fallback
                    print("Falling back to manual authentication...")
                    creds = flow.run_console()
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service


def create_google_calendar_event(summary, description, start_time, end_time, location):
    """Create a Google Calendar event."""
    try:
        service = get_google_calendar_service()

        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Kolkata',  # Change if needed
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Asia/Kolkata',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 30},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"✅ Event created: {event.get('htmlLink')}")
        return {
            "success": True,
            "event_url": event.get('htmlLink'),
            "event_id": event.get('id')
        }
    
    except Exception as e:
        print(f"❌ Error creating Google Calendar event: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# Alternative method using manual authorization (no local server)
def get_google_calendar_service_manual():
    """Alternative authentication method that doesn't require a local server."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials/client_secret_2_734803652945-4rqqq0bjrd1mruqa7a4l2pftj3crhmah.apps.googleusercontent.com.json', 
                SCOPES
            )
            # Use manual authorization flow instead of local server
            creds = flow.run_console()
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service