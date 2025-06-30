# Dishwasher Start/Stop Switch Implementation

This modified version of the `ha_gehome` integration includes additional functionality to start and stop your Fisher & Paykel DD60SCW9 dishwasher (and potentially other GE/compatible dishwashers) using ERD 0x0050.

## What's Added

### New Switch Entity: "Start/Stop"
- **Entity ID**: `switch.{dishwasher_serial}_start_stop`
- **Function**: Allows remote start/stop control of the dishwasher
- **ERD Used**: 0x0050 (decimal 80)

## Files Modified/Added

1. **New File**: `custom_components/ge_home/entities/dishwasher/ge_dishwasher_start_stop_switch.py`
   - Complete implementation of the start/stop switch
   - Includes safety checks for remote start capability
   - Provides detailed logging and error handling

2. **Modified**: `custom_components/ge_home/devices/dishwasher.py`
   - Added import for the new switch class
   - Added switch to the list of entities

3. **Modified**: `custom_components/ge_home/entities/dishwasher/__init__.py`
   - Added import for the new switch class

## How It Works

### Switch State Logic
The switch shows as "on" when:
- The dishwasher is currently running (checked via `DISHWASHER_CYCLE_STATE`)
- OR remote start is enabled (checked via `DISHWASHER_REMOTE_START_ENABLE`)

### Turn On (Start Dishwasher)
1. Checks if remote start is enabled on the dishwasher
2. If enabled, sends value `1` to ERD 0x0050
3. Logs the action and any errors

### Turn Off (Stop Dishwasher)
1. Sends value `0` to ERD 0x0050
2. Logs the action and any errors

### Availability
The switch is only available when remote start is enabled on the dishwasher itself.

## Prerequisites

### Dishwasher Settings
1. **Enable Remote Start**: This must be enabled on your dishwasher's control panel
   - Look for "Remote Enable" or "WiFi Remote Start" in your dishwasher settings
   - This setting allows the dishwasher to accept remote commands

2. **Load Dishwasher**: Make sure dishes are loaded and door is closed
3. **Select Cycle**: Choose your desired wash cycle on the dishwasher panel

### Home Assistant Setup
1. Have the original `ha_gehome` integration working
2. Your dishwasher should already be discovered and functioning
3. Replace the integration files with these modified versions

## Installation

1. **Backup Current Integration**:
   ```bash
   cp -r /config/custom_components/ge_home /config/custom_components/ge_home_backup
   ```

2. **Replace Files**:
   - Copy the entire `ha_gehome/custom_components/ge_home` folder to your Home Assistant `custom_components` directory
   - Overwrite existing files

3. **Restart Home Assistant**:
   - Go to Settings > System > Restart
   - Wait for restart to complete

4. **Check for New Entity**:
   - Go to Settings > Devices & Services
   - Find your dishwasher device
   - Look for the new "Start/Stop" switch entity

## Usage

### Via Home Assistant UI
1. Go to your dishwasher device page
2. Find the "Start/Stop" switch
3. Toggle it on to start, off to stop

### Via Automations
```yaml
# Example automation to start dishwasher at 10 PM
automation:
  - alias: "Start Dishwasher at Night"
    trigger:
      platform: time
      at: "22:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.dishwasher_door_status
        state: "off"  # Door closed
      - condition: state
        entity_id: binary_sensor.dishwasher_remote_start_enable
        state: "on"   # Remote start enabled
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.dishwasher_start_stop
```

### Via Scripts/Services
```yaml
# Start dishwasher
service: switch.turn_on
target:
  entity_id: switch.{your_dishwasher_serial}_start_stop

# Stop dishwasher  
service: switch.turn_off
target:
  entity_id: switch.{your_dishwasher_serial}_start_stop
```

## Additional State Attributes

The switch provides extra state attributes:
- `cycle_state`: Current cycle state (idle, running, paused, etc.)
- `operating_mode`: Current operating mode

## Troubleshooting

### Switch Not Appearing
1. Check Home Assistant logs for errors
2. Verify integration is working (other dishwasher entities present)
3. Restart Home Assistant
4. Check that files were copied correctly

### Switch Shows as Unavailable
1. Ensure "Remote Start" is enabled on your dishwasher
2. Check that dishwasher is connected to WiFi
3. Verify the dishwasher is responding to other commands

### Commands Not Working
1. Check Home Assistant logs for error messages
2. Verify ERD 0x0050 is the correct command ERD for your dishwasher model
3. Ensure dishwasher door is closed and cycle is selected
4. Try enabling debug logging:
   ```yaml
   logger:
     logs:
       custom_components.ge_home.entities.dishwasher.ge_dishwasher_start_stop_switch: debug
   ```

### Wrong ERD Code
If ERD 0x0050 doesn't work for your dishwasher model:
1. Check the dishwasher manual or service documentation
2. Try common alternatives: 0x0051, 0x0052, 0x1000, etc.
3. Modify the ERD code in `devices/dishwasher.py` line 37

## Safety Notes

- Always ensure the dishwasher is properly loaded before starting
- The dishwasher door must be closed for remote start to work
- Remote start must be enabled on the dishwasher itself
- This modification may void warranties - use at your own risk

## Support

This is a community modification. For issues:
1. Check the Home Assistant logs first
2. Verify your dishwasher model supports remote start/stop
3. Test with the original ha_gehome integration to ensure basic functionality

## License

This modification follows the same license as the original `ha_gehome` project.
