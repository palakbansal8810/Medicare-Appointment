#!/usr/bin/env python3
"""
Calendly Configuration and Setup Guide
"""

import os
from typing import Dict, Optional

# Calendly API Configuration
CALENDLY_API_BASE_URL = "https://api.calendly.com"
CALENDLY_WEBHOOK_BASE_URL = "https://hooks.calendly.com"

# Doctor Calendly URI Mapping
# Replace these with actual Calendly URIs for your doctors
DOCTOR_CALENDLY_MAPPING = {
    "Dr. Smith": {
        "user_uri": "https://api.calendly.com/users/AAAAAAAAAAAAAAAA",
        "event_type_uri": "https://api.calendly.com/event_types/AAAAAAAAAAAAAAAA",
        "booking_url": "https://calendly.com/dr-smith/medical-appointment",
        "webhook_url": "http://localhost:5000/webhook/calendly/dr-smith"
    },
    "Dr. Johnson": {
        "user_uri": "https://api.calendly.com/users/BBBBBBBBBBBBBBBB",
        "event_type_uri": "https://api.calendly.com/event_types/BBBBBBBBBBBBBBBB",
        "booking_url": "https://calendly.com/dr-johnson/medical-appointment",
        "webhook_url": "http://localhost:5000/webhook/calendly/dr-johnson"
    },
    "Dr. Williams": {
        "user_uri": "https://api.calendly.com/users/CCCCCCCCCCCCCCCC",
        "event_type_uri": "https://api.calendly.com/event_types/CCCCCCCCCCCCCCCC",
        "booking_url": "https://calendly.com/dr-williams/medical-appointment",
        "webhook_url": "http://localhost:5000/webhook/calendly/dr-williams"
    },
    "Dr. John": {
        "user_uri": "https://api.calendly.com/users/DDDDDDDDDDDDDDDD",
        "event_type_uri": "https://api.calendly.com/event_types/DDDDDDDDDDDDDDDD",
        "booking_url": "https://calendly.com/dr-john/medical-appointment",
        "webhook_url": "http://localhost:5000/webhook/calendly/dr-john"
    },
    "Dr. Robin": {
        "user_uri": "https://api.calendly.com/users/EEEEEEEEEEEEEEEE",
        "event_type_uri": "https://api.calendly.com/event_types/EEEEEEEEEEEEEEEE",
        "booking_url": "https://calendly.com/dr-robin/medical-appointment",
        "webhook_url": "http://localhost:5000/webhook/calendly/dr-robin"
    }
}

def get_doctor_calendly_config(doctor_name: str) -> Optional[Dict]:
    """Get Calendly configuration for a specific doctor"""
    return DOCTOR_CALENDLY_MAPPING.get(doctor_name)

def get_calendly_token() -> Optional[str]:
    """Get Calendly API token from environment variables"""
    return os.getenv('CALENDLY_API_TOKEN')

def setup_calendly_webhooks():
    """Setup Calendly webhooks for appointment events"""
    import requests
    import json
    
    try:
        token = get_calendly_token()
        if not token:
            return {"success": False, "error": "Calendly API token not configured"}
        
        # Calendly webhook setup endpoint
        url = "https://api.calendly.com/webhook_subscriptions"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        webhook_events = [
            "invitee.created",
            "invitee.canceled", 
            "invitee.no_show",
            "invitee.rescheduled"
        ]
        
        results = []
        
        for doctor, config in DOCTOR_CALENDLY_MAPPING.items():
            webhook_url = config.get("webhook_url")
            if not webhook_url:
                continue
                
            # Create webhook subscription for each doctor
            webhook_data = {
                "url": webhook_url,
                "events": webhook_events,
                "organization": config.get("user_uri"),
                "user": config.get("user_uri"),
                "scope": "user"
            }
            
            try:
                response = requests.post(url, headers=headers, json=webhook_data)
                
                if response.status_code == 201:
                    webhook_info = response.json()
                    results.append({
                        "doctor": doctor,
                        "success": True,
                        "webhook_id": webhook_info.get("resource", {}).get("uri", ""),
                        "events": webhook_events
                    })
                else:
                    results.append({
                        "doctor": doctor,
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    })
                    
            except requests.exceptions.RequestException as e:
                results.append({
                    "doctor": doctor,
                    "success": False,
                    "error": f"Request error: {str(e)}"
                })
        
        return {
            "success": True,
            "results": results,
            "total_doctors": len(DOCTOR_CALENDLY_MAPPING),
            "successful_webhooks": len([r for r in results if r["success"]])
        }
        
    except Exception as e:
        return {"success": False, "error": f"Error setting up webhooks: {str(e)}"}

def list_existing_webhooks():
    """List existing Calendly webhooks"""
    import requests
    
    try:
        token = get_calendly_token()
        if not token:
            return {"success": False, "error": "Calendly API token not configured"}
        
        url = "https://api.calendly.com/webhook_subscriptions"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            webhooks_data = response.json()
            return {
                "success": True,
                "webhooks": webhooks_data.get("collection", []),
                "count": len(webhooks_data.get("collection", []))
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
            
    except Exception as e:
        return {"success": False, "error": f"Error listing webhooks: {str(e)}"}

def delete_webhook(webhook_uri):
    """Delete a specific Calendly webhook"""
    import requests
    
    try:
        token = get_calendly_token()
        if not token:
            return {"success": False, "error": "Calendly API token not configured"}
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.delete(webhook_uri, headers=headers)
        
        if response.status_code == 204:
            return {"success": True, "message": "Webhook deleted successfully"}
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
            
    except Exception as e:
        return {"success": False, "error": f"Error deleting webhook: {str(e)}"}

def handle_webhook_event(event_data):
    """Handle incoming Calendly webhook events"""
    try:
        event_type = event_data.get("event")
        payload = event_data.get("payload", {})
        
        if event_type == "invitee.created":
            return handle_appointment_created(payload)
        elif event_type == "invitee.canceled":
            return handle_appointment_canceled(payload)
        elif event_type == "invitee.no_show":
            return handle_appointment_no_show(payload)
        elif event_type == "invitee.rescheduled":
            return handle_appointment_rescheduled(payload)
        else:
            return {"success": False, "error": f"Unknown event type: {event_type}"}
            
    except Exception as e:
        return {"success": False, "error": f"Error handling webhook event: {str(e)}"}

def handle_appointment_created(payload):
    """Handle appointment created webhook"""
    try:
        # Extract appointment details from Calendly payload
        event = payload.get("event", {})
        invitee = payload.get("invitee", {})
        
        appointment_details = {
            "calendly_event_uri": event.get("uri", ""),
            "patient_name": invitee.get("name", ""),
            "patient_email": invitee.get("email", ""),
            "appointment_time": event.get("start_time", ""),
            "appointment_end_time": event.get("end_time", ""),
            "status": "confirmed",
            "source": "calendly_webhook"
        }
        
        # Update local database/Excel with the appointment
        # This would integrate with your existing appointment system
        print(f"📅 New appointment created via Calendly: {appointment_details}")
        
        return {"success": True, "appointment": appointment_details}
        
    except Exception as e:
        return {"success": False, "error": f"Error handling appointment created: {str(e)}"}

def handle_appointment_canceled(payload):
    """Handle appointment canceled webhook"""
    try:
        event = payload.get("event", {})
        invitee = payload.get("invitee", {})
        
        appointment_details = {
            "calendly_event_uri": event.get("uri", ""),
            "patient_name": invitee.get("name", ""),
            "patient_email": invitee.get("email", ""),
            "status": "canceled",
            "source": "calendly_webhook"
        }
        
        # Update local database/Excel to mark appointment as canceled
        # Restore slot availability if needed
        print(f"❌ Appointment canceled via Calendly: {appointment_details}")
        
        return {"success": True, "appointment": appointment_details}
        
    except Exception as e:
        return {"success": False, "error": f"Error handling appointment canceled: {str(e)}"}

def handle_appointment_no_show(payload):
    """Handle appointment no-show webhook"""
    try:
        event = payload.get("event", {})
        invitee = payload.get("invitee", {})
        
        appointment_details = {
            "calendly_event_uri": event.get("uri", ""),
            "patient_name": invitee.get("name", ""),
            "patient_email": invitee.get("email", ""),
            "status": "no_show",
            "source": "calendly_webhook"
        }
        
        # Update local database/Excel to mark appointment as no-show
        print(f"🚫 No-show recorded via Calendly: {appointment_details}")
        
        return {"success": True, "appointment": appointment_details}
        
    except Exception as e:
        return {"success": False, "error": f"Error handling appointment no-show: {str(e)}"}

def handle_appointment_rescheduled(payload):
    """Handle appointment rescheduled webhook"""
    try:
        event = payload.get("event", {})
        invitee = payload.get("invitee", {})
        old_event = payload.get("old_invitee", {})
        
        appointment_details = {
            "calendly_event_uri": event.get("uri", ""),
            "patient_name": invitee.get("name", ""),
            "patient_email": invitee.get("email", ""),
            "new_appointment_time": event.get("start_time", ""),
            "old_appointment_time": old_event.get("start_time", ""),
            "status": "rescheduled",
            "source": "calendly_webhook"
        }
        
        # Update local database/Excel with new appointment time
        # Restore old slot availability and mark new slot as unavailable
        print(f"🔄 Appointment rescheduled via Calendly: {appointment_details}")
        
        return {"success": True, "appointment": appointment_details}
        
    except Exception as e:
        return {"success": False, "error": f"Error handling appointment rescheduled: {str(e)}"}

def verify_webhook_signature(payload, signature, secret):
    """Verify Calendly webhook signature for security"""
    import hmac
    import hashlib
    
    try:
        # Calendly uses HMAC-SHA256 for webhook signature verification
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        print(f"Error verifying webhook signature: {e}")
        return False.get("invitee", {})
        
        appointment_details = {
            "calendly_event_uri": event.get("uri", ""),
            "patient_name": invitee.get("name", ""),
            "patient_email": invitee.get("email", ""),
            "status": "no_show",
            "source": "calendly_webhook"
        }
        
        # Update local database/Excel to mark appointment as no-show
        print(f"🚫 No-show recorded via Calendly: {appointment_details}")
        
        return {"success": True, "appointment": appointment_details}
        
    except Exception as e:
        return {"success": False, "error": f"Error handling appointment no-show: {str(e)}"}

def handle_appointment_rescheduled(payload):
    """Handle appointment rescheduled webhook"""
    try:
        event = payload.get("event", {})
        invitee = payload.get("invitee", {})
        old_event = payload.get("old_invitee", {})
        
        appointment_details = {
            "calendly_event_uri": event.get("uri", ""),
            "patient_name": invitee.get("name", ""),
            "patient_email": invitee.get("email", ""),
            "new_appointment_time": event.get("start_time", ""),
            "old_appointment_time": old_event.get("start_time", ""),
            "status": "rescheduled",
            "source": "calendly_webhook"
        }
        
        # Update local database/Excel with new appointment time
        # Restore old slot availability and mark new slot as unavailable
        print(f"🔄 Appointment rescheduled via Calendly: {appointment_details}")
        
        return {"success": True, "appointment": appointment_details}
        
    except Exception as e:
        return {"success": False, "error": f"Error handling appointment rescheduled: {str(e)}"}

def verify_webhook_signature(payload, signature, secret):
    """Verify Calendly webhook signature for security"""
    import hmac
    import hashlib
    
    try:
        # Calendly uses HMAC-SHA256 for webhook signature verification
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        print(f"Error verifying webhook signature: {e}")
        return False

def validate_calendly_config():
    """Validate Calendly configuration"""
    issues = []
    
    # Check if API token is configured
    if not get_calendly_token():
        issues.append("CALENDLY_API_TOKEN not found in environment variables")
    
    # Check if doctor mappings are configured
    for doctor, config in DOCTOR_CALENDLY_MAPPING.items():
        if not config.get("user_uri") or not config.get("event_type_uri"):
            issues.append(f"Missing Calendly configuration for {doctor}")
    
    return issues

if __name__ == "__main__":
    print("Calendly Configuration Validation")
    print("=" * 40)
    
    issues = validate_calendly_config()
    if issues:
        print("❌ Configuration Issues Found:")
        for issue in issues:
            print(f"  • {issue}")
    else:
        print("✅ Calendly configuration is valid")
    
    print(f"\n📋 Configured Doctors: {len(DOCTOR_CALENDLY_MAPPING)}")
    for doctor in DOCTOR_CALENDLY_MAPPING.keys():
        print(f"  • {doctor}")
