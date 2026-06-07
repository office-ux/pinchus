import urllib.request
from urllib.error import HTTPError
import json

url = "http://127.0.0.1:5000/api/projects/PomonaTest/data"
print(f"Fetching: {url}")
try:
    with urllib.request.urlopen(url) as response:
        print("Status Code:", response.status)
        print("Headers:", dict(response.headers))
        body = response.read().decode('utf-8')
        print("Body preview:", body[:500])
except HTTPError as e:
    print("HTTPError Code:", e.code)
    print("HTTPError Headers:", dict(e.headers))
    print("HTTPError Body:", e.read().decode('utf-8')[:500])
except Exception as ex:
    print("General Exception:", ex)
