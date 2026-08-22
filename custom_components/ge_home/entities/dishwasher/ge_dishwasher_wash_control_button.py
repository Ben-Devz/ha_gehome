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

    # Bits 10-11 of the user-setting register hold the run-state field
    # (the SDK's "dry_option" position).
    _RUN_STATE_MASK = 0xC00
    _RUN_STATE_SHIFT = 10

    async def async_press(self) -> None:
        """Raw read-modify-write of the run-state field.

        We deliberately bypass ErdUserSettingConverter.erd_encode: it packs the
        register through erd_encode_int() with the default 2-byte length, which
        raises OverflowError for this 3-byte register (upstream never writes
        it, so the bug was never hit). Editing the raw hex also guarantees
        every other settings bit is left byte-identical.
        """
        raw = self.appliance.get_raw_erd_value(self.erd_code)
        if not raw:
            _LOGGER.error("Wash control '%s': no raw value cached for %s; cannot write",
                          self._command, self.erd_code)
            return
        target = self.COMMANDS[self._command][0]
        i = int(raw, 16)
        new_i = (i & ~self._RUN_STATE_MASK) | (target.value << self._RUN_STATE_SHIFT)
        new_raw = format(new_i, "0{}x".format(len(raw)))
        _LOGGER.info("Wash control '%s': %s raw %s -> %s", self._command,
                     self.erd_code, raw, new_raw)
        await self.appliance.client.async_set_erd_value(self.appliance, self.erd_code, new_raw)

    def _get_icon(self) -> Optional[str]:
        return self.COMMANDS[self._command][1]
