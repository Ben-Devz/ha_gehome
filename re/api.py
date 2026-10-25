"""Call ge_home.debug_api_request. Usage: api.py METHOD PATH [JSON_BODY]"""
import json, sys, urllib.request, pathlib
token = pathlib.Path.home().joinpath(".config/home-assistant/token").read_text().strip()
url = "http://127.0.0.1:8123/api/services/ge_home/debug_api_request?return_response"
def call(method, path, body=None):
    d = {"path": path, "method": method}
    if body is not None:
        d["body"] = body
    req = urllib.request.Request(url, json.dumps(d).encode(),
                                 {"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=90))["service_response"]
if __name__ == "__main__":
    body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    print(json.dumps(call(sys.argv[1], sys.argv[2], body))[:3000])
