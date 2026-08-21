"""Wash-control buttons for Fisher & Paykel-firmware DishDrawers (e.g. GE DDS192AA).

On these models the appliance does NOT honor writes to the
DISHWASHER_REMOTE_START_COMMAND ERDs (0x3204/0x3604) -- those registers belong
to a tub that doesn't exist on single-drawer units, and commands sent there are
silently ignored. Live SmartHQ traffic captured on a DDS192AA (2026-08-22)
shows the app controls the cycle through a two-bit field inside
DISHWASHER_USER_SETTING (0x3007) -- the field the SDK models as `dry_option`:

    0 = stop/cancel        (observed raw 0x300082)
    1 = start/resume       (observed raw 0x300482)
    2 = pause              (observed raw 0x300882)

Remote mode must be physically armed first (the `wifi_enabled` bit of the same
register; hold the WiFi button 4s and close the drawer while it flashes -- the
arm lasts 72h and clears when the drawer opens).

These buttons read the appliance's current user-setting tuple, replace only
that field, and write the whole register back.
"""
import logging
from propcache.api import cached_property
from typing import Optional

from gehomesdk import ErdCode
from gehomesdk.erd.values.dishwasher.erd_user_setting import UserDryOptionSetting

from ...devices import ApplianceApi
from ..common import GeErdButton

_LOGGER = logging.getLogger(__name__)


class GeDishwasherWashControlButton(GeErdButton):
    """Start/pause/cancel via the run-state field of DISHWASHER_USER_SETTING."""

    COMMANDS = {
        "start_resume": (UserDryOptionSetting(1), "mdi:play"),
        "pause": (UserDryOptionSetting(2), "mdi:pause"),
        "cancel": (UserDryOptionSetting(0), "mdi:stop"),
    }

    def __init__(self, api: ApplianceApi, erd_code: ErdCode, command: str,
                 erd_override: Optional[str] = None):
        if command not in self.COMMANDS:
            raise ValueError(f"unknown wash control command: {command}")
        super().__init__(api, erd_code=erd_code, erd_override=erd_override)
        self._command = command

    @cached_property
    def unique_id(self) -> Optional[str]:
        return f"{super().unique_id}_{self._command}"

    @cached_property
    def name(self) -> Optional[str]:
        return f"{super().name} {self._command.replace('_', ' ').title()}"

    async def async_press(self) -> None:
        current = self.appliance.get_erd_value(self.erd_code)
        target = self.COMMANDS[self._command][0]
        new_value = current._replace(dry_option=target)
        _LOGGER.info(
            "Wash control '%s': writing %s run-state field %s (was %s)",
            self._command, self.erd_code, target, current.dry_option,
        )
        await self.appliance.async_set_erd_value(self.erd_code, new_value)

    def _get_icon(self) -> Optional[str]:
        return self.COMMANDS[self._command][1]
