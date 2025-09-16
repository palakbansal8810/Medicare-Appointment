#!/usr/bin/env python3
"""
Test script for Calendly integration functionality
"""

import os
import sys
from datetime import datetime, timedelta

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_calendly_config():
    """Test Calendly configuration"""
    print("🧪 Testing Calendly Configuration")
    print("=" * 40)
    
    try:
        from src.calendly_config import validate_calendly_config, get_calendly_token
        
        # Check API token
        token = get_calendly_token()
        if token:
            print("✅ Calendly API token found")
        else:
            print("❌ Calendly API token not found")
            print("   Add CALENDLY_API_TOKEN to your .env file")
        
        # Validate configuration
        issues = validate_calendly_config()
        if issues:
            print("❌ Configuration issues found:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print("✅ Calendly configuration is valid")
            
    except ImportError as e:
        print(f"❌ Error importing calendly_config: {e}")

def test_calendly_functions():
    """Test Calendly integration functions"""
    print("\n🧪 Testing Calendly Functions")
    print("=" * 40)
    
    try:
        from app import (
            get_calendly_token, 
            create_calendly_event, 
            get_calendly_availability,
            create_calendly_booking_link,
            sync_calendly_to_excel
        )
        from src.calendly_config import (
            setup_calendly_webhooks,
            list_existing_webhooks,
            handle_webhook_event
        )
        
        # Test token retrieval
        token = get_calendly_token()
        print(f"API Token Status: {'✅ Configured' if token else '❌ Not configured'}")
        
        # Test booking link creation
        test_doctor = "Dr. Smith"
        booking_link = create_calendly_booking_link(test_doctor)
        if booking_link:
            print(f"✅ Booking link for {test_doctor}: {booking_link}")
        else:
            print(f"❌ No booking link configured for {test_doctor}")
        
        # Test event creation (mock data)
        if token:
            print("\n🔄 Testing event creation (mock data)...")
            event_result = create_calendly_event(
                patient_name="Test Patient",
                patient_email="test@example.com",
                doctor_name=test_doctor,
                appointment_date="2024-01-15",
                start_time="10:00",
                end_time="11:00",
                location="Test Clinic"
            )
            
            if event_result["success"]:
                print("✅ Event creation successful")
                print(f"   Event URL: {event_result.get('event_url', 'N/A')}")
            else:
                print(f"❌ Event creation failed: {event_result.get('error', 'Unknown error')}")
        else:
            print("⚠️ Skipping event creation test (no API token)")
        
        # Test availability sync
        print("\n🔄 Testing availability sync...")
        sync_result = sync_calendly_to_excel()
        if sync_result["success"]:
            print(f"✅ Sync successful: {sync_result['updated_slots']} slots updated")
        else:
            print(f"❌ Sync failed: {sync_result.get('error', 'Unknown error')}")
        
        # Test webhook functions
        print("\n🔗 Testing webhook functions...")
        
        # Test webhook setup
        webhook_setup_result = setup_calendly_webhooks()
        if webhook_setup_result["success"]:
            print(f"✅ Webhook setup: {webhook_setup_result['successful_webhooks']}/{webhook_setup_result['total_doctors']} doctors")
        else:
            print(f"❌ Webhook setup failed: {webhook_setup_result.get('error', 'Unknown error')}")
        
        # Test webhook listing
        webhooks_list_result = list_existing_webhooks()
        if webhooks_list_result["success"]:
            print(f"✅ Found {webhooks_list_result['count']} existing webhooks")
        else:
            print(f"❌ Failed to list webhooks: {webhooks_list_result.get('error', 'Unknown error')}")
        
        # Test webhook event handling
        sample_webhook_event = {
            "event": "invitee.created",
            "payload": {
                "event": {
                    "uri": "https://api.calendly.com/scheduled_events/test123",
                    "start_time": "2024-01-15T10:00:00.000000Z",
                    "end_time": "2024-01-15T11:00:00.000000Z"
                },
                "invitee": {
                    "name": "Test Patient",
                    "email": "test@example.com"
                }
            }
        }
        
        webhook_handle_result = handle_webhook_event(sample_webhook_event)
        if webhook_handle_result["success"]:
            print("✅ Webhook event handling successful")
        else:
            print(f"❌ Webhook event handling failed: {webhook_handle_result.get('error', 'Unknown error')}")
            
    except ImportError as e:
        print(f"❌ Error importing app functions: {e}")
    except Exception as e:
        print(f"❌ Error testing functions: {e}")

def test_calendly_api_connection():
    """Test connection to Calendly API"""
    print("\n🧪 Testing Calendly API Connection")
    print("=" * 40)
    
    try:
        import requests
        from app import get_calendly_token
        
        token = get_calendly_token()
        if not token:
            print("❌ No API token available for testing")
            return
        
        # Test API connection
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Test with a simple API call
        response = requests.get(
            "https://api.calendly.com/users/me",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            user_data = response.json()
            print("✅ Calendly API connection successful")
            print(f"   User: {user_data.get('resource', {}).get('name', 'Unknown')}")
            print(f"   Email: {user_data.get('resource', {}).get('email', 'Unknown')}")
        else:
            print(f"❌ Calendly API connection failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Error testing API connection: {e}")

def show_calendly_setup_guide():
    """Show Calendly setup guide"""
    print("\n📋 Calendly Setup Guide")
    print("=" * 40)
    print("""
1. Get Calendly API Token:
   • Go to https://calendly.com/integrations/api_webhooks
   • Click "Personal Access Tokens"
   • Generate a new token
   • Add to .env file: CALENDLY_API_TOKEN=your_token_here

2. Configure Doctor Calendly Accounts:
   • Each doctor needs a Calendly account
   • Create event types for medical appointments
   • Update calendly_config.py with actual URIs

3. Test Integration:
   • Run this test script
   • Use "Sync with Calendly" in the app
   • Create a test appointment

4. Webhook Setup (Optional):
   • Set up webhooks for real-time updates
   • Configure webhook URLs in calendly_config.py
   • Handle appointment.created, appointment.cancelled events
""")

def main():
    """Main test function"""
    print("🏥 MediCare Calendly Integration Test")
    print("=" * 50)
    
    # Run tests
    test_calendly_config()
    test_calendly_functions()
    test_calendly_api_connection()
    show_calendly_setup_guide()
    
    print("\n✅ Calendly integration test completed!")
    print("\n💡 Next Steps:")
    print("   1. Configure your Calendly API token")
    print("   2. Set up doctor Calendly accounts")
    print("   3. Update calendly_config.py with real URIs")
    print("   4. Test the integration in the Streamlit app")

if __name__ == "__main__":
    main()
