#!/usr/bin/env python3
"""
Test script to verify slot availability update functionality
"""

import pandas as pd
import os
from datetime import datetime

def test_slot_update():
    """Test the slot availability update functionality"""
    print("Testing slot availability update functionality...")
    
    # Check if doctor_schedules.xlsx exists
    file_path = "data/doctor_schedules.xlsx"
    if not os.path.exists(file_path):
        print(" doctor_schedules.xlsx not found. Please run the app first to generate data.")
        return False
    
    # Read the current schedule
    df = pd.read_excel(file_path)
    print(f" Loaded schedule with {len(df)} total slots")
    
    # Show current availability status
    available_count = len(df[df['available'] == True])
    unavailable_count = len(df[df['available'] == False])
    print(f" Current status: {available_count} available, {unavailable_count} unavailable")
    
    # Show sample data structure
    print("\n Sample data structure:")
    print(df.head())
    
    # Show unique doctors and locations
    print(f"\n Available doctors: {df['doctor_name'].unique().tolist()}")
    print(f" Available locations: {df['location'].unique().tolist()}")
    
    # Test updating a slot (find first available slot)
    available_slots = df[df['available'] == True]
    if not available_slots.empty:
        test_slot = available_slots.iloc[0]
        print(f"\n Testing with slot: {test_slot['doctor_name']} at {test_slot['location']} on {test_slot['date']} from {test_slot['start_time']} to {test_slot['end_time']}")
        
        # Import the update function
        import sys
        sys.path.append('.')
        from app import update_slot_availability, restore_slot_availability
        
        # Test setting to unavailable
        print(" Setting slot to unavailable...")
        result1 = update_slot_availability(
            test_slot['doctor_name'],
            test_slot['location'], 
            test_slot['date'],
            test_slot['start_time'],
            test_slot['end_time'],
            available=False
        )
        
        if result1:
            print(" Successfully set slot to unavailable")
            
            # Verify the change
            df_updated = pd.read_excel(file_path)
            updated_slot = df_updated[
                (df_updated['doctor_name'] == test_slot['doctor_name']) &
                (df_updated['location'] == test_slot['location']) &
                (df_updated['date'] == test_slot['date']) &
                (df_updated['start_time'] == test_slot['start_time']) &
                (df_updated['end_time'] == test_slot['end_time'])
            ]
            
            if not updated_slot.empty and updated_slot.iloc[0]['available'] == False:
                print(" Verification: Slot is now marked as unavailable")
            else:
                print(" Verification failed: Slot availability not updated correctly")
                return False
            
            # Test restoring to available
            print("Restoring slot to available...")
            result2 = restore_slot_availability(
                test_slot['doctor_name'],
                test_slot['location'],
                test_slot['date'], 
                test_slot['start_time'],
                test_slot['end_time']
            )
            
            if result2:
                print(" Successfully restored slot to available")
                
                # Verify the restoration
                df_restored = pd.read_excel(file_path)
                restored_slot = df_restored[
                    (df_restored['doctor_name'] == test_slot['doctor_name']) &
                    (df_restored['location'] == test_slot['location']) &
                    (df_restored['date'] == test_slot['date']) &
                    (df_restored['start_time'] == test_slot['start_time']) &
                    (df_restored['end_time'] == test_slot['end_time'])
                ]
                
                if not restored_slot.empty and restored_slot.iloc[0]['available'] == True:
                    print(" Verification: Slot is now marked as available again")
                    print(" All tests passed! Slot availability update functionality is working correctly.")
                    return True
                else:
                    print(" Verification failed: Slot availability not restored correctly")
                    return False
            else:
                print(" Failed to restore slot availability")
                return False
        else:
            print(" Failed to set slot to unavailable")
            return False
    else:
        print(" No available slots found to test with")
        return False

if __name__ == "__main__":
    success = test_slot_update()
    if success:
        print("\n Test completed successfully!")
    else:
        print("\n Test failed!")

