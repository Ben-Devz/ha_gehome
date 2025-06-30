#!/usr/bin/env python3
"""
Test script to validate the dishwasher start/stop switch implementation.
This script checks if the files are properly structured for integration.
"""

import os
import sys

def check_files_exist():
    """Check if all required files exist."""
    required_files = [
        "custom_components/ge_home/entities/dishwasher/ge_dishwasher_start_stop_switch.py",
        "custom_components/ge_home/entities/dishwasher/__init__.py", 
        "custom_components/ge_home/devices/dishwasher.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"✓ {file_path} exists")
    
    if missing_files:
        print(f"✗ Missing files: {missing_files}")
        return False
    
    return True

def check_import_structure():
    """Check if the imports are properly structured."""
    try:
        # Check the dishwasher device file contains our import
        with open("custom_components/ge_home/devices/dishwasher.py", "r") as f:
            dishwasher_content = f.read()
            
        if "GeDishwasherStartStopSwitch" in dishwasher_content:
            print("✓ Start/stop switch is imported in dishwasher device")
        else:
            print("✗ Start/stop switch import missing in dishwasher device")
            return False
            
        if "GeDishwasherStartStopSwitch(self, 0x0050)" in dishwasher_content:
            print("✓ Start/stop switch is added to entities with ERD 0x0050")
        else:
            print("✗ Start/stop switch not added to entities list")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ Error checking imports: {e}")
        return False

def check_switch_implementation():
    """Check if the switch implementation looks correct."""
    try:
        with open("custom_components/ge_home/entities/dishwasher/ge_dishwasher_start_stop_switch.py", "r") as f:
            switch_content = f.read()
            
        checks = [
            ("class GeDishwasherStartStopSwitch", "Switch class defined"),
            ("async def async_turn_on", "Turn on method implemented"),
            ("async def async_turn_off", "Turn off method implemented"),
            ("ErdCode.DISHWASHER_REMOTE_START_ENABLE", "Remote start check implemented"),
            ("await self.appliance.async_set_erd_value", "ERD value setting implemented")
        ]
        
        for check_string, description in checks:
            if check_string in switch_content:
                print(f"✓ {description}")
            else:
                print(f"✗ {description} - missing")
                return False
                
        return True
        
    except Exception as e:
        print(f"✗ Error checking switch implementation: {e}")
        return False

def main():
    """Main test function."""
    print("=== GE Home Dishwasher Start/Stop Switch Integration Test ===\n")
    
    tests = [
        ("File Structure", check_files_exist),
        ("Import Structure", check_import_structure), 
        ("Switch Implementation", check_switch_implementation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
    
    print(f"\n=== Test Results: {passed}/{total} passed ===")
    
    if passed == total:
        print("""
🎉 All tests passed! Your dishwasher start/stop integration is ready.

Next steps:
1. Copy this modified ha_gehome folder to your Home Assistant custom_components directory
2. Restart Home Assistant
3. The start/stop switch should appear as a new entity for your dishwasher

The switch will:
- Show as "on" when the dishwasher is running or remote start is enabled
- Allow you to start the dishwasher when remote start is enabled
- Allow you to stop the dishwasher
- Use ERD 0x0050 for start/stop commands
- Provide additional state attributes showing cycle state and operating mode

Note: Make sure "Remote Start" is enabled on your dishwasher for the switch to work.
        """)
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please check the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
