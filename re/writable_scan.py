"""Find which valid ERDs the Brillion cloud lets us write, using a deliberately
wrong-length value (10 zero bytes) that the appliance rejects (status: timeout).

Usage: writable_scan.py MAC scan.tsv OUT
"""
import json, os, sys, time, urllib.request, pathlib

mac, scan, out = sys.argv[1:4]
token = pathlib.Path.home().joinpath(".config/home-assistant/token").read_text().strip()
url = "http://127.0.0.1:8123/api/services/ge_home/debug_api_request?return_response"
codes = [l.split("\t")[0] for l in open(scan) if l.startswith("0x") and l.split("\t")[1] == "200"]
codes = [c for c in codes if c[:4].upper() in ("0X30", "0X32", "0XD0", "0XD2")]
with open(out, "w") as f:
    for erd in codes:
        body = {"path": f"/v1/appliance/{mac}/erd/{erd}", "method": "POST",
                "body": {"kind": "appliance#erdListEntry", "userId": os.environ["GE_USER_ID"],
                         "applianceId": mac, "erd": erd, "value": "00" * 10,
                         "ackTimeout": 10, "delay": 0}}
        req = urllib.request.Request(url, json.dumps(body).encode(),
                                     {"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=60))["service_response"]
        j = r.get("json") or {}
        f.write(f"{erd}\t{r['status']}\t{j.get('reason') or j.get('status') or json.dumps(j)[:120]}\n"); f.flush()
        time.sleep(0.3)
