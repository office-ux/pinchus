import re

app_js_path = r"C:\pinchus\web_viewer\static\js\app.js"
index_html_path = r"C:\pinchus\web_viewer\templates\index.html"

with open(app_js_path, "r", encoding="utf-8") as f:
    js_content = f.read()

with open(index_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

ids_in_js = re.findall(r"getElementById\('([^']+)'\)", js_content)
missing_ids = []

for html_id in set(ids_in_js):
    # Check if id="html_id" is in html_content
    # allow for quotes id="xyz" or id='xyz'
    if f'id="{html_id}"' not in html_content and f"id='{html_id}'" not in html_content:
        missing_ids.append(html_id)

print("Missing IDs in index.html:", missing_ids)
