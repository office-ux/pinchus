import sys
import os

# Adjust path to import web_viewer.app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from web_viewer.app import app, PROJECTS_DIR
import json
import shutil

# Enable testing mode
app.config['TESTING'] = True
client = app.test_client()

# Create a test project name
test_proj = "TestProjectAnnotations"
test_proj_dir = os.path.join(PROJECTS_DIR, test_proj)

try:
    # 1. Create the project
    res = client.post("/api/projects", json={"name": test_proj})
    print("Create Project:", res.status_code, res.get_json())
    assert res.status_code in (200, 201)

    # 2. Get annotations (should be empty initially)
    res = client.get(f"/api/projects/{test_proj}/annotations")
    print("List Annotations (Empty):", res.status_code, res.get_json())
    assert res.status_code == 200
    assert res.get_json() == []

    # 3. Add an annotation
    payload = {
        "name": "Grill Type A Test",
        "type": "grill",
        "pdf_path": "Projects/TestProjectAnnotations/pdfs/mechanical2.pdf",
        "page_num": 1,
        "vectors": [{"id": "123", "type": "Line", "start": [0,0], "end": [10,10]}]
    }
    res = client.post(f"/api/projects/{test_proj}/annotations", json=payload)
    print("Add Annotation:", res.status_code, res.get_json())
    assert res.status_code == 201
    assert res.get_json()["success"] is True

    # 4. Get annotations again (should contain the added one)
    res = client.get(f"/api/projects/{test_proj}/annotations")
    data = res.get_json()
    print("List Annotations (1 item):", res.status_code, len(data))
    assert res.status_code == 200
    assert len(data) == 1
    assert data[0]["name"] == "Grill Type A Test"
    assert data[0]["type"] == "grill"
    assert data[0]["page_num"] == 1

    print("ALL TESTS PASSED SUCCESSFULLY!")

finally:
    # Cleanup test project
    if os.path.exists(test_proj_dir):
        shutil.rmtree(test_proj_dir)
        print("Cleaned up test project directory.")
