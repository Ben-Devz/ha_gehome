"""Snapshot the cloud's stored value/time of every valid ERD (read-only).

Usage: snapshot.py MAC scan.tsv OUT
"""
import json, sys, time, urllib.request, pathlib

mac, scan, out = sys.argv[1:4]
token = pathlib.Path.home().joinpath(".config/home-assistant/token").read_text().strip()
url = "http://127.0.0.1:8123/api/services/ge_home/debug_api_request?return_response"
codes = [l.split("\t")[0] for l in open(scan) if l.startswith("0x") and l.split("\t")[1] == "200"]
with open(out, "w") as f:
    for erd in codes:
        req = urllib.request.Request(url, json.dumps({"path": f"/v1/appliance/{mac}/erd/{erd}"}).encode(),
                                     {"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        j = json.load(urllib.request.urlopen(req, timeout=60))["service_response"].get("json") or {}
        f.write(f"{erd}\t{j.get('value', '-')}\t{j.get('time', '-')}\n")
        time.sleep(0.08)
