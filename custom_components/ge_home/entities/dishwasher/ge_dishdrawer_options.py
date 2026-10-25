"""Program select and Sanitize switch for F&P-firmware DishDrawers (e.g. GE DDS192AA).

Both registers take remote writes, and the drawer echoes the new value
(verified 2026-10-26):

- Program: "Selected Cycle" field of DISHWASHER_USER_SETTING (0x3007, bits
  1-4 -- four bits per the GE ERD definitions; the SDK's cycle_mode decode
  only reads three). The program indexes come from the idle time estimate
  the drawer publishes after each change (0xD004): 1 = 130 min, 2 = 115 min
  (131 with Sanitize), 6 = 202 min, 7 = 15 min, 8 = 110 min, 9 = 46 min.
  Indexes 0, 3-5 and 10-11 left the estimate unchanged and are not offered.
- Sanitize: bit 2 ("Sani") of ENABLE_FEATURES (0x3086). Changing the program
  clears it, so set the program first.

Writes are refused while a cycle is running or paused.
"""
import logging
from propcache.api import cached_property
from typing import List, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError
from gehomesdk import ErdCode

from ...devices import ApplianceApi
from ..common import GeErdEntity, GeErdSelect, OptionsConverter

_LOGGER = logging.getLogger(__name__)

PROGRAMS = {"Heavy": 1, "Medium": 2, "Eco": 6, "Rinse": 7, "Delicate": 8, "Fast": 9}
_PROGRAM_MASK = 0x1E
_RUN_STATE_MASK = 0xC00
_SANI_BIT = 0x04


def _raw_int(appliance, erd) -> Optional[int]:
    raw = appliance.get_raw_erd_value(erd)
    return int(raw, 16) if raw else None


def _ensure_idle(appliance) -> None:
    setting = _raw_int(appliance, ErdCode.DISHWASHER_USER_SETTING)
    if setting is None:
        raise HomeAssistantError("No user-setting value cached yet")
    if (setting & _RUN_STATE_MASK) >> 10 in (1, 2):
        raise HomeAssistantError("Can't change the DishDrawer program during a cycle")


class GeDishDrawerProgramSelect(GeErdSelect):
    """Wash program, via the Selected Cycle field of 0x3007."""

    def __init__(self, api: ApplianceApi, erd_override: str):
        # The select platform only adds GeErdSelect entities; the options
        # logic below works on the raw register, so the converter is unused.
        super().__init__(api, ErdCode.DISHWASHER_USER_SETTING, OptionsConverter(),
                         erd_override=erd_override, icon_override="mdi:dishwasher")

    @cached_property
    def unique_id(self) -> Optional[str]:
        return f"{super().unique_id}_program"

    @cached_property
    def options(self) -> List[str]:
        return list(PROGRAMS)

    @property
    def current_option(self) -> str | None:  # type: ignore
        setting = _raw_int(self.appliance, self.erd_code)
        if setting is None:
            return None
        idx = (setting & _PROGRAM_MASK) >> 1
        return next((name for name, i in PROGRAMS.items() if i == idx), None)

    async def async_select_option(self, option: str) -> None:
        _ensure_idle(self.appliance)
        raw = self.appliance.get_raw_erd_value(self.erd_code)
        new_i = (int(raw, 16) & ~_PROGRAM_MASK) | (PROGRAMS[option] << 1)
        new_raw = format(new_i, "0{}x".format(len(raw)))
        _LOGGER.info("DishDrawer program %s: 0x3007 %s -> %s", option, raw, new_raw)
        await self.appliance.client.async_set_erd_value(self.appliance, self.erd_code, new_raw)


class GeDishDrawerSanitizeSwitch(GeErdEntity, SwitchEntity):
    """Sanitize option, via the Sani bit of 0x3086."""

    def __init__(self, api: ApplianceApi, erd_override: str):
        super().__init__(api, ErdCode.DISHWASHER_UNKNOWN_3086, erd_override=erd_override,
                         icon_override="mdi:shield-check-outline")

    @cached_property
    def unique_id(self) -> Optional[str]:
        return f"{super().unique_id}_sanitize"

    @property
    def is_on(self) -> bool | None:  # type: ignore
        value = _raw_int(self.appliance, self.erd_code)
        return None if value is None else bool(value & _SANI_BIT)

    async def _set(self, on: bool) -> None:
        _ensure_idle(self.appliance)
        raw = self.appliance.get_raw_erd_value(self.erd_code) or "00"
        i = int(raw, 16)
        new_raw = format(i | _SANI_BIT if on else i & ~_SANI_BIT, "0{}x".format(len(raw)))
        _LOGGER.info("DishDrawer sanitize %s: 0x3086 %s -> %s", "on" if on else "off", raw, new_raw)
        await self.appliance.client.async_set_erd_value(self.appliance, self.erd_code, new_raw)

    async def async_turn_on(self, **kwargs) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set(False)
