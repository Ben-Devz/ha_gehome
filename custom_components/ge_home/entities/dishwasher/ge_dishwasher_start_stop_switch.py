import logging
from typing import Any, Dict

from gehomesdk import ErdCodeType
from gehomesdk.erd import ErdCode
from homeassistant.components.switch import SwitchEntity

from ...devices import ApplianceApi
from ..common.ge_erd_entity import GeErdEntity

_LOGGER = logging.getLogger(__name__)

class GeDishwasherStartStopSwitch(GeErdEntity, SwitchEntity):
    """Switch for dishwasher start/stop control."""

    def __init__(self, api: ApplianceApi, erd_code: ErdCodeType):
        super().__init__(api, erd_code)
        self._erd_code = erd_code  # 0x2149 - Remote Start Selected Cycle
        self._stop_erd_code = 0x2040  # Remote Stop Cycle Request

    @property
    def name(self) -> str:
        return f"{self.serial_or_mac} Start/Stop"

    @property
    def unique_id(self) -> str:
        return f"{self.serial_or_mac}-start-stop"

    @property
    def device_class(self) -> str:
        return "switch"

    @property
    def icon(self) -> str:
        if self.is_on:
            return "mdi:dishwasher"
        return "mdi:dishwasher-off"

    @property
    def is_on(self) -> bool:
        """Return True if dishwasher is running or can be started."""
        try:
            # Check cycle state to see if dishwasher is currently running
            cycle_state = self.appliance.get_erd_value(ErdCode.DISHWASHER_CYCLE_STATE)
            if cycle_state and "running" in str(cycle_state).lower():
                return True
                
            # Check if remote start is enabled (backup check)
            remote_start = self.appliance.get_erd_value(ErdCode.DISHWASHER_REMOTE_START_ENABLE)
            return bool(remote_start)
        except Exception as e:
            _LOGGER.warning(f"Error checking dishwasher state: {e}")
            return False

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        try:
            # Check if remote start is enabled - this determines if we can control the dishwasher
            remote_start = self.appliance.get_erd_value(ErdCode.DISHWASHER_REMOTE_START_ENABLE)
            return bool(remote_start)
        except:
            return True  # Default to available if we can't check

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the dishwasher."""
        _LOGGER.info(f"Starting dishwasher {self.unique_id}")
        try:
            # First ensure remote start is enabled
            remote_start = self.appliance.get_erd_value(ErdCode.DISHWASHER_REMOTE_START_ENABLE)
            if not remote_start:
                _LOGGER.error("Cannot start dishwasher - remote start is not enabled")
                return
                
            # Send start command using Remote Start Selected Cycle ERD (0 = Start Remote Cycle command)
            await self.appliance.async_set_erd_value(self._erd_code, 0)
            _LOGGER.info(f"Start command sent to dishwasher {self.unique_id}")
        except Exception as e:
            _LOGGER.error(f"Error starting dishwasher {self.unique_id}: {e}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the dishwasher.""" 
        _LOGGER.info(f"Stopping dishwasher {self.unique_id}")
        try:
            # Send stop command using Remote Stop Cycle Request ERD (0 = Stop current cycle)
            await self.appliance.async_set_erd_value(self._stop_erd_code, 0)
            _LOGGER.info(f"Stop command sent to dishwasher {self.unique_id}")
        except Exception as e:
            _LOGGER.error(f"Error stopping dishwasher {self.unique_id}: {e}")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        attributes = {}
        
        # Add cycle state if available
        try:
            from gehomesdk.erd import ErdCode
            cycle_state = self.appliance.get_erd_value(ErdCode.DISHWASHER_CYCLE_STATE)
            if cycle_state:
                attributes["cycle_state"] = str(cycle_state)
        except:
            pass
            
        # Add operating mode if available  
        try:
            from gehomesdk.erd import ErdCode
            operating_mode = self.appliance.get_erd_value(ErdCode.DISHWASHER_OPERATING_MODE)
            if operating_mode:
                attributes["operating_mode"] = str(operating_mode)
        except:
            pass
            
        return attributes
