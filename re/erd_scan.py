"""Read-only scan of which ERD codes the Brillion cloud accepts for an appliance.

Uses HA's ge_home.debug_api_request service. Usage: erd_scan.py MAC START END OUT
"""
import json, sys, time, urllib.request, pathlib

mac, start, end, out = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16), sys.argv[4]
token = pathlib.Path.home().joinpath(".config/home-assistant/token").read_text().strip()
url = "http://127.0.0.1:8123/api/services/ge_home/debug_api_request?return_response"

with open(out, "a") as f:
    for code in range(start, end + 1):
        erd = f"0x{code:04X}"
        body = json.dumps({"path": f"/v1/appliance/{mac}/erd/{erd}"}).encode()
        req = urllib.request.Request(url, body, {"Authorization": f"Bearer {token}",
                                                 "Content-Type": "application/json"})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=30))["service_response"]
        except Exception as ex:
            f.write(f"{erd}\tERR\t{ex}\n"); f.flush(); time.sleep(2); continue
        j = r.get("json") or {}
        if r["status"] == 400 and j.get("reason") == "invalid erd":
            pass
        else:
            f.write(f"{erd}\t{r['status']}\t{json.dumps(j)[:300]}\n"); f.flush()
        time.sleep(0.08)
