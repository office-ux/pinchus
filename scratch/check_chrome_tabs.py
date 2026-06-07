import urllib.request
import urllib.error
import json

req = urllib.request.Request("http://localhost:9222/json/list")
req.add_header('Host', 'localhost:9222')

try:
    with urllib.request.urlopen(req) as response:
        print("Success:", response.read().decode())
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code, e.reason)
    print("Body:", e.read().decode())
except Exception as e:
    print("Other Error:", e)
