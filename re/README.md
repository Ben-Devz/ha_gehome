# Sadie (F&P DishDrawer DDS192AA) reverse-engineering notes

Tools (they need the fork's debug services running in HA):
- `erd_scan.py MAC START END OUT`: read-only probe of which ERDs the Brillion cloud accepts ("invalid erd" means not in this appliance's schema).
- `writable_scan.py MAC scan.tsv OUT`: writability map. It POSTs a 10-byte zero value. Read-only ERDs answer "erd is not writable" before reaching the appliance. Writable ones reach the appliance, which rejects the bad length (`{"status":"timeout"}`).
- `snapshot.py MAC scan.tsv OUT`: the cloud's stored value and time for every valid ERD.
- `/config/ge_erd_trace.log` (in HA): every ERD change the appliance publishes, as raw hex with a UTC timestamp.

Findings (2026-10-26):
- 107 valid ERDs (scan.tsv). Values are known for 32 (baseline-2026-10-26.tsv).
- Writable: 0x3007, 0x301F, 0x3086, 0x3207, 0x321A-0x3222, 0x322B, 0xD006, 0xD010. 0x3087 (REMOTE_START_ENABLE) is valid but read-only. 0x3204 (GE remote start command) is not valid for this appliance.
- Writing 0x3007 bit 7 (the "wifi_enabled"/arm bit) sticks (the drawer reports 300084), but a start (300484) after it is ignored. The real arm is internal.
- The cloud checks the request in this order: JSON format, then hex value, then writability, then length (left to the appliance).
- The SmartHQ v2 API (client.mysmarthq.com) shows only firmware and RSSI services for this drawer, so the app must control it over the ERD API.

Next: capture while Ben uses the SmartHQ app's remote toggle and does a physical arm. Diff the trace log and a fresh snapshot against the baseline.

## 2026-10-26 (late): vendor SmartHQ v2 command path — dead end for this unit

Added `smarthq.debug_request` to the official smarthq integration (working copy
~/dev/smarthq_src, deployed live, backup of the original in
~/ha-backups/2026-10-26-dishwasher-autostart/smarthq-live.tar).

- `GET /v2/device/<id>`: deviceType `cloud.smarthq.device.dishdrawer`, model DDS192AA.
  Services: firmware.v1 (wifi), firmware.v1 (appliance), integer/rssi. No state or mode service.
- `POST /v2/command` validates domainType/serviceDeviceType against enums.
  `cloud.smarthq.domain.dishdrawer` + `cloud.smarthq.device.dishdrawer[.lower|.upper]`
  and `cloud.smarthq.device.appliance` pass validation. Every start
  (dishdrawer.state.legacy.start, dishwasher.state.v1.start) returns
  403 `cloud.smarthq.outcome.notfound`: the cloud only routes commands to
  services the device registered, and Sadie registered none.
- Drawer unaffected (0x3007=300004, 0x300e=11).

Conclusion: the SmartHQ app must drive Sadie through the same Brillion ERD path
ge_home uses. So the app's remote toggle is most likely the same 0x3007 bit-7
write we already tried. The capture of Ben using the app is still the decider.

Also: the ERD trace hook now logs only changed values (the SDK re-publishes
all 32 ERDs on every 30 s poll). The first update after start is the baseline.

## 2026-10-26 ~01:17 local: REMOTE START WITHOUT PANEL ARM — WORKS

- Control endpoint: `POST /v1/appliance/<mac>/control/<cmd>` with
  `{"kind":"appliance#control","userId":...,"applianceId":<mac>,"command":<cmd>,"data":[],"ackTimeout":10,"delay":0}`.
- How the replies tell commands apart (ctl_scan.py, ctl.tsv): "invalid command specified" = no such command;
  "user error incorrect appliance type" = real command, other appliance type.
- `dishdrawer-start|pause|stop` reply "appliance remote enabled required" until 0x3007 bit 7 is set
  (remotely writable). `dishdrawer-set-cycle` replies 500 "error missing appliance state".
- Sequence: write 0x3007 = current|0x80 (300004 -> 300084), wait for the cloud to show it, then dishdrawer-start → success.
  The drawer went 0x300e 11→03 (Main Wash), 0xD004=0x83 (131 min), 0x3007 300484, heater ~800 W.
- dishdrawer-stop → success. The drawer went 0x300e→11, 0x3007 300084. Bit 7 was then reset to 300004.
- Not yet tested: dishdrawer-pause / resume.
- The fork's Wash buttons are rewritten to use this (entities/dishwasher/ge_dishwasher_wash_control_button.py), NOT deployed yet.

## Extended scan (2026-10-26, scan2.tsv)

Read-only, same oracle. Ranges 0x3100-31FF, 0x3300-37FF, 0xD100-D4FF.
Valid: 0x3100, 0x3101, 0x3109-0x310B, 0x3300, 0x3401, 0x340D, 0x3487 (GE's
upper-drawer REMOTE_START_ENABLE), 0x348A, 0x3596-0x35A3, 0x3600, 0x3610-0x361D.
Nothing valid in 0xD100-D4FF. Not needed now that the control command works.

## Running the tools

The scripts read the appliance MAC and the Brillion user id from the
environment: `GE_MAC=<mac> GE_USER_ID=<user id> python3 ctl_scan.py ...`.
The data files have both replaced with `<GE_MAC>` / `<GE_USER_ID>`.

## 2026-10-26 (later): program, Sanitize, pause/resume, LAN

GE's ERD definitions (geappliances/public-appliance-api-documentation,
appliance_api_erd_definitions.json) name Sadie's registers:
- 0x3007 User Settings: Selected Cycle is bits 1-4 (the SDK reads 3), Wash Temperature bits 12-14.
- 0x3086 Enable Features: bit 2 = Sani. Sadie normally reads 04 = Sanitize on.
- 0x3250 Cycle Modifier Actual (½ Load, Quiet, Sanitize, Dry+, ...) is valid but not published.
  0x3251 (Requested) is not valid on this drawer.

Writes to both 0x3007 (program) and 0x3086 (Sanitize) are accepted on an idle drawer, and the
drawer echoes the new value. Changing the program clears Sanitize. After each change the idle
estimate 0xD004 updates; cycle_index_map.txt has the estimates.
- Program indexes: 1 = 130 min (Heavy), 2 = 115 min (Medium; 131 with Sanitize), 6 = 202 min (Eco),
  7 = 15 min (Rinse), 8 = 110 min (Delicate), 9 = 46 min (Fast). 0, 3-5, 10, 11 left the estimate unchanged.
  The names are inferred from the durations.
- Medium + Sanitize = 0x3007 cycle 2 + 0x3086 04 → 131 min, which matches Ben's usual loads and tonight's remote start.

Pause/resume through the deployed HA buttons, on the real drawer:
start → run field 1 (300484); pause → run field 2 (300884, the same as a door-open pause;
0x300e stays 03); resume → 300484; cancel → 300084 and 0x300e 11.

LAN: Sadie has no open TCP ports (full 1-65535 connect scan) and no mDNS
or SSDP replies. The WiFi module is outbound-only, so there is no local network route like localtuya.
Local control would mean hardware on the appliance bus (see ESPHome-gea).
