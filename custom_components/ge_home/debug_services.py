"""Raw ERD debug services, for reverse-engineering appliance behaviour.

ge_home.debug_read_erds   -> returns the raw cached hex value of ERDs (optionally
                             after forcing a full refresh from the cloud).
ge_home.debug_write_erd   -> writes a raw hex value to one ERD, bypassing the
                             SDK converters.
ge_home.debug_api_request -> raw REST call to the Brillion API with the live
                             client's session and token (path must start /v1/).

Note: gehomesdk optimistically caches a written value as soon as the cloud
acknowledges the request, so a read straight after a write can show the value
that was sent rather than what the appliance did. Use refresh: true (a full
GET of every ERD) and a short wait to see the appliance's real state.
"""
import asyncio
import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_READ = "debug_read_erds"
SERVICE_WRITE = "debug_write_erd"
SERVICE_API = "debug_api_request"

READ_SCHEMA = vol.Schema({
    vol.Optional("appliance"): cv.string,
    vol.Optional("erds", default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional("refresh", default=False): cv.boolean,
    vol.Optional("wait", default=5): vol.All(vol.Coerce(float), vol.Range(min=0, max=60)),
})

WRITE_SCHEMA = vol.Schema({
    vol.Optional("appliance"): cv.string,
    vol.Required("erd"): cv.string,
    vol.Required("value"): vol.All(cv.string, vol.Match(r"^[0-9a-fA-F]+$")),
})


API_SCHEMA = vol.Schema({
    vol.Required("path"): vol.All(cv.string, vol.Match(r"^/v1/")),
    vol.Optional("method", default="GET"): vol.In(["GET", "POST"]),
    vol.Optional("body"): dict,
})


def _norm_erd(code: str) -> str:
    code = code.strip().lower().replace("0x", "")
    return "0x" + code.zfill(4)


def _appliances(hass: HomeAssistant, match: str | None):
    found = []
    for coordinator in hass.data.get(DOMAIN, {}).values():
        client = getattr(coordinator, "_client", None)
        if client is None:
            continue
        for appliance in client.appliances.values():
            if match is None or match.upper() in appliance.mac_addr.upper():
                found.append((client, appliance))
    if not found:
        raise HomeAssistantError(f"No GE appliance matching {match!r}")
    return found


def _raw_cache(appliance) -> dict:
    out = {}
    for code, value in appliance._raw_property_cache.items():
        key = code.value if hasattr(code, "value") else str(code)
        out[str(key).lower()] = value
    return out


TRACE_FILE = "/config/ge_erd_trace.log"
_TRACE_LAST: dict[str, dict[str, str]] = {}


def _append_trace(line: str) -> None:
    with open(TRACE_FILE, "a") as f:
        f.write(line)


def trace_erd_update(hass: HomeAssistant, appliance, update_data) -> None:
    """Append every changed ERD (raw hex) to /config/ge_erd_trace.log.

    Records what the appliance publishes when it is armed or driven from the
    SmartHQ app, so the change can be diffed afterwards.
    """
    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    # The SDK re-publishes every ERD on each 30 s poll, so keep the last value
    # seen and only log real changes (the first update after start is the baseline).
    last = _TRACE_LAST.setdefault(appliance.mac_addr, {})
    lines = []
    for code in update_data:
        key = str(code.value if hasattr(code, "value") else code).lower()
        value = appliance.get_raw_erd_value(code)
        if last.get(key) == value:
            continue
        last[key] = value
        lines.append(f"{stamp}\t{appliance.mac_addr}\t{key}\t{value}\n")
    if lines:
        hass.async_add_executor_job(_append_trace, "".join(lines))


def async_register_debug_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_READ):
        return

    async def handle_read(call: ServiceCall):
        targets = _appliances(hass, call.data.get("appliance"))
        if call.data["refresh"]:
            for client, appliance in targets:
                await client.async_request_update(appliance)
            await asyncio.sleep(call.data["wait"])
        wanted = [_norm_erd(e) for e in call.data["erds"]]
        result = {}
        for _, appliance in targets:
            raw = _raw_cache(appliance)
            if wanted:
                raw = {k: raw.get(k) for k in wanted}
            result[appliance.mac_addr] = raw
        return {"appliances": result}

    async def handle_write(call: ServiceCall):
        targets = _appliances(hass, call.data.get("appliance"))
        if len(targets) != 1:
            raise HomeAssistantError("debug_write_erd needs 'appliance' to match exactly one appliance")
        client, appliance = targets[0]
        erd = _norm_erd(call.data["erd"])
        value = call.data["value"].lower()
        before = appliance.get_raw_erd_value(erd)
        _LOGGER.warning("DEBUG raw ERD write %s %s: %s -> %s", appliance.mac_addr, erd, before, value)
        await client.async_set_erd_value(appliance, erd, value)
        return {"appliance": appliance.mac_addr, "erd": erd, "before": before, "sent": value}

    async def handle_api(call: ServiceCall):
        client, _ = _appliances(hass, None)[0]
        session, token = client._session, client._access_token
        if session is None or not token:
            raise HomeAssistantError("GE client has no session/token yet")
        from gehomesdk.clients.const import API_URL
        url = API_URL + call.data["path"]
        method = call.data["method"]
        if method != "GET":
            _LOGGER.warning("DEBUG raw API %s %s %s", method, url, call.data.get("body"))
        async with session.request(method, url, json=call.data.get("body"),
                                   headers={"Authorization": "Bearer " + token}) as resp:
            text = await resp.text()
            try:
                data = await resp.json(content_type=None)
            except Exception:
                data = None
            return {"status": resp.status, "json": data, "text": None if data is not None else text[:4000]}

    hass.services.async_register(DOMAIN, SERVICE_API, handle_api, schema=API_SCHEMA,
                                 supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, SERVICE_READ, handle_read, schema=READ_SCHEMA,
                                 supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, SERVICE_WRITE, handle_write, schema=WRITE_SCHEMA,
                                 supports_response=SupportsResponse.OPTIONAL)
