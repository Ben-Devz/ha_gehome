"""Enumerate Brillion control command names. Usage: GE_MAC=.. GE_USER_ID=.. ctl_scan.py OUT names..."""
import sys, time, json
from api import call
import os
M, U = os.environ["GE_MAC"], os.environ["GE_USER_ID"]
out = open(sys.argv[1], "a")
for name in sys.argv[2:]:
    body = {"kind": "appliance#control", "userId": U, "applianceId": M, "command": name,
            "data": [], "ackTimeout": 10, "delay": 0}
    r = call("POST", f"/v1/appliance/{M}/control/{name}", body)
    reason = (r.get("json") or {}).get("reason") or json.dumps(r)[:200]
    out.write(f"{name}\t{r['status']}\t{reason}\n"); out.flush()
    if reason != "invalid command specified":
        print(name, r["status"], reason, flush=True)
    time.sleep(0.1)
