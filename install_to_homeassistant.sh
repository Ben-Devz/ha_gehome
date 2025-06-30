#!/bin/bash

# Installation script for modified ha_gehome with dishwasher start/stop functionality
# Usage: ./install_to_homeassistant.sh [HOME_ASSISTANT_CONFIG_PATH]

set -e

# Default Home Assistant config path (adjust as needed)
HA_CONFIG_PATH="${1:-/config}"
CUSTOM_COMPONENTS_PATH="$HA_CONFIG_PATH/custom_components"
TARGET_PATH="$CUSTOM_COMPONENTS_PATH/ge_home"
BACKUP_PATH="$CUSTOM_COMPONENTS_PATH/ge_home_backup_$(date +%Y%m%d_%H%M%S)"

echo "🏠 Installing modified ha_gehome with dishwasher start/stop functionality"
echo "📁 Home Assistant config path: $HA_CONFIG_PATH"
echo "🎯 Target installation path: $TARGET_PATH"

# Check if Home Assistant config directory exists
if [[ ! -d "$HA_CONFIG_PATH" ]]; then
    echo "❌ Home Assistant config directory not found: $HA_CONFIG_PATH"
    echo "💡 Usage: $0 [HOME_ASSISTANT_CONFIG_PATH]"
    echo "💡 Example: $0 /home/homeassistant/.homeassistant"
    exit 1
fi

# Create custom_components directory if it doesn't exist
mkdir -p "$CUSTOM_COMPONENTS_PATH"

# Backup existing installation if it exists
if [[ -d "$TARGET_PATH" ]]; then
    echo "📦 Backing up existing installation to: $BACKUP_PATH"
    cp -r "$TARGET_PATH" "$BACKUP_PATH"
    echo "✅ Backup created successfully"
fi

# Copy the modified integration
echo "📋 Installing modified ha_gehome integration..."
cp -r "custom_components/ge_home" "$TARGET_PATH"

# Verify installation
if [[ -f "$TARGET_PATH/entities/dishwasher/ge_dishwasher_start_stop_switch.py" ]]; then
    echo "✅ Installation successful!"
    echo ""
    echo "🔄 Next steps:"
    echo "1. Restart Home Assistant"
    echo "2. Enable 'Remote Start' on your dishwasher"
    echo "3. Look for the new 'Start/Stop' switch in your dishwasher device"
    echo ""
    echo "📖 For troubleshooting, see: DISHWASHER_START_STOP_README.md"
    echo ""
    if [[ -d "$BACKUP_PATH" ]]; then
        echo "🗂️  Backup location: $BACKUP_PATH"
        echo "💡 To restore: rm -rf '$TARGET_PATH' && mv '$BACKUP_PATH' '$TARGET_PATH'"
    fi
else
    echo "❌ Installation failed - start/stop switch file not found"
    exit 1
fi
