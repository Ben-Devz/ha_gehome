"""Wash-control buttons for Fisher & Paykel-firmware DishDrawers (e.g. GE DDS192AA).

On these models the appliance does NOT honor writes to the
DISHWASHER_REMOTE_START_COMMAND ERDs (0x3204/0x3604) -- 0x3204 is not even a
valid ERD for a DDS192AA. Writing the run-state field of
DISHWASHER_USER_SETTING (0x3007 bits 10-11) is also ignored by the drawer.

What works (found 2026-10-26) is the Brillion cloud's control command:

    POST /v1/appliance/<mac>/control/dishdrawer-start   (also -pause, -stop)
    {"kind": "appliance#control", "userId": ..., "applianceId": <mac>,
     "command": "dishdrawer-start", "data": [], "ackTimeout": 10, "delay": 0}

The cloud refuses it with "appliance remote enabled required" unless remote
mode is on. It reads that from bit 7 (`wifi_enabled`) of 0x3007, and that bit
can be written remotely -- so no physical arm on the panel is needed. The
drawer still checks its own door switch.

These buttons set the bit if it is clear, wait for the cloud to see it, then
send the control command.
"""
import asyncio
import logging
from propcache.api import cached_property
from typing import Optional

from gehomesdk import ErdCode
from gehomesdk.clients.const import API_URL

from homeassistant.exceptions import HomeAssistantError

from ...devices import ApplianceApi
from ..common import GeErdButton

_LOGGER = logging.getLogger(__name__)

_REMOTE_ENABLE_BIT = 0x80
_USER_SETTING = "0x3007"


async def _rest(client, method: str, path: str, body=None):
    session, token = client._session, client._access_token
    if session is None or not token:
        raise HomeAssistantError("GE client has no session/token yet")
    async with session.request(method, API_URL + path, json=body,
                               headers={"Authorization": "Bearer " + token}) as resp:
        try:
            data = await resp.json(content_type=None)
        except Exception:
            data = {"text": (await resp.text())[:500]}
        return resp.status, data or {}


async def async_dishdrawer_command(appliance, command: str) -> None:
    """Enable remote mode if needed, then send a dishdrawer control command."""
    client = appliance.client
    mac = appliance.mac_addr
    erd_path = f"/v1/appliance/{mac}/erd/{_USER_SETTING}"

    raw = appliance.get_raw_erd_value(ErdCode.DISHWASHER_USER_SETTING)
    if not raw:
        raise HomeAssistantError(f"No user-setting value cached for {mac}")
    i = int(raw, 16)
    if not i & _REMOTE_ENABLE_BIT:
        new_raw = format(i | _REMOTE_ENABLE_BIT, "0{}x".format(len(raw)))
        _LOGGER.info("DishDrawer %s: enabling remote mode, 0x3007 %s -> %s", mac, raw, new_raw)
        await client.async_set_erd_value(appliance, ErdCode.DISHWASHER_USER_SETTING, new_raw)
        # The cloud only updates its copy once the drawer acks the write.
        for _ in range(20):
            await asyncio.sleep(1.5)
            _, data = await _rest(client, "GET", erd_path)
            value = data.get("value")
            if value and int(value, 16) & _REMOTE_ENABLE_BIT:
                break
        else:
            raise HomeAssistantError(f"DishDrawer {mac}: remote mode did not take")

    body = {"kind": "appliance#control", "userId": client.user_id, "applianceId": mac,
            "command": command, "data": [], "ackTimeout": 10, "delay": 0}
    status, data = None, {}
    for attempt in range(3):
        status, data = await _rest(client, "POST", f"/v1/appliance/{mac}/control/{command}", body)
        _LOGGER.info("DishDrawer %s: %s -> %s %s", mac, command, status, data)
        if status == 200 and data.get("status") == "success":
            return
        if data.get("reason") != "appliance remote enabled required":
            break
        await asyncio.sleep(3)
    raise HomeAssistantError(f"DishDrawer {mac}: {command} failed: {status} {data}")


class GeDishwasherWashControlButton(GeErdButton):
    """Start/pause/cancel a DishDrawer through the cloud control command."""

    COMMANDS = {
        "start_resume": ("dishdrawer-start", "mdi:play"),
        "pause": ("dishdrawer-pause", "mdi:pause"),
        "cancel": ("dishdrawer-stop", "mdi:stop"),
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
        await async_dishdrawer_command(self.appliance, self.COMMANDS[self._command][0])

    def _get_icon(self) -> Optional[str]:
        return self.COMMANDS[self._command][1]
