import urllib.request
import urllib.parse
import json

def test_endpoint(url):
    print(f"Testing URL: {url}")
    req = urllib.request.Request(url, data=b"", method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode("utf-8")
            print(f"Status: {status}")
            print(f"Body: {body}\n")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}\n")
    except Exception as e:
        print(f"Error: {e}\n")
    return None

if __name__ == "__main__":
    pdf_path = "Projects/test/pdfs/mechanical2.pdf"
    encoded_path = urllib.parse.quote(pdf_path, safe="")
    
    # 1. Test run-matching-lines
    url_matching = f"http://127.0.0.1:5000/api/pdf/{encoded_path}/run-matching-lines"
    test_endpoint(url_matching)
    
    # 2. Test run-patterns
    url_patterns = f"http://127.0.0.1:5000/api/pdf/{encoded_path}/run-patterns"
    test_endpoint(url_patterns)
