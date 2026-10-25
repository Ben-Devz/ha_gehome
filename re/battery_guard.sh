#!/bin/bash
# Pause Sadie if battery SOC <= 35% while a cycle runs; exit when cycle ends.
# Needs GE_MAC and GE_USER_ID in the environment; NOTIFY_SERVICE (e.g. mobile_app_x) is optional.
S=~/.claude/skills/home-assistant/scripts
st(){ $S/ha-api GET states/$1 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin)['state'])" 2>/dev/null; }
cd ~/dev/ha_gehome/re
while true; do
  soc=$(st sensor.deye_battery); cyc=$(st sensor.ulv664010_lower_cycle_state)
  case "$cyc" in "N/A"|Off|Idle|"Fp Unknown 17"|Clean|Finished|*leted*) echo "$(date -u +%T) cycle ended: $cyc soc=$soc"; exit 0;; esac
  if [ -n "$soc" ] && python3 -c "import sys;sys.exit(0 if float('$soc')<=35 else 1)" 2>/dev/null; then
    echo "$(date -u +%T) SOC $soc <= 35, pausing (cycle=$cyc)"
    python3 api.py POST /v1/appliance/$GE_MAC/control/dishdrawer-pause "{\"kind\":\"appliance#control\",\"userId\":\"$GE_USER_ID\",\"applianceId\":\"$GE_MAC\",\"command\":\"dishdrawer-pause\",\"data\":[],\"ackTimeout\":10,\"delay\":0}"
    $S/ha-api POST services/notify/${NOTIFY_SERVICE:-notify} "{\"message\":\"Sadie paused: battery at $soc%. Resume on solar.\"}" >/dev/null
    exit 0
  fi
  sleep 60
done
