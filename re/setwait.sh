#!/bin/bash
# setwait.sh ERD VALUE : write via ge_home.debug_write_erd, then wait for the cloud copy (device ack)
S=~/.claude/skills/home-assistant/scripts; M=${GE_MAC:?}
$S/ha-api POST "services/ge_home/debug_write_erd" "{\"appliance\":\"$M\",\"erd\":\"$1\",\"value\":\"$2\"}" >/dev/null
for i in $(seq 1 20); do
  r=$(python3 ~/dev/ha_gehome/re/api.py GET /v1/appliance/$M/erd/$1 | python3 -c "import sys,json;j=json.load(sys.stdin)['json'];print(j.get('value','-'),j.get('time','-'))")
  [ "${r%% *}" = "$(echo $2 | tr a-f A-F)" ] || [ "${r%% *}" = "$2" ] && { echo "$1 -> $r (acked)"; exit 0; }
  sleep 1.5
done
echo "$1 -> $r (NOT acked as $2)"; exit 1
