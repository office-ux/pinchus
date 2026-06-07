import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'web_viewer'))

from app import app
import stamp_db

def test_flask_endpoints():
    app.config['TESTING'] = True
    # Bypass login decorator in testing by mock-injecting session or mocking wrap
    # Since our flask app requires login, let's see how session is configured.
    # We can write to session using test_client context manager!
    
    client = app.test_client()
    
    # Enable session key
    with client.session_transaction() as sess:
        sess['username'] = 'testuser' # Set session username to bypass @api_login_required
        sess['logged_in'] = True
        
    project = "PomonaTest"
    pdf_name = "Care365.pdf"
    pdf_path = f"Projects/{project}/pdfs/{pdf_name}"
    
    # Ensure PDF directory exists and has a dummy file
    os.makedirs(f"Projects/{project}/pdfs", exist_ok=True)
    import shutil
    shutil.copy("test.pdf", f"Projects/{project}/pdfs/{pdf_name}")
    
    # 1. Create a dummy stamp so there is data to render
    print("Pre-populating database with test stamp...")
    stamp_db.init_db()
    stamp_id = stamp_db.get_or_create_stamp(project, pdf_path, 1, 9999)
    stamp_db.upsert_fields(stamp_id, [
        {"name": "DWG #", "value": "M-101", "type": "string"},
        {"name": "#", "value": "99", "type": "string"},
        {"name": "TYPE", "value": "LSD", "type": "string"},
        {"name": "SIZE", "value": "24x6", "type": "string"},
        {"name": "K-factor", "value": "1.02", "type": "string"},
        {"name": "DESIGN CFM", "value": "120", "type": "string"},
        {"name": "FINAL VEL", "value": "350", "type": "string"},
        {"name": "FINAL CFM", "value": "115", "type": "string"},
        {"name": "FINAL %", "value": "96%", "type": "string"}
    ])
    
    # 2. Test template upload endpoint
    print("Testing template upload route...")
    template_file_path = r"c:\pinchus\report word samples\FCU Report.docx"
    with open(template_file_path, "rb") as f:
        response = client.post(
            f"/api/projects/{project}/templates/upload",
            data={"file": (f, "FCU Report.docx")},
            content_type="multipart/form-data"
        )
    print(f"  Upload response status: {response.status_code}")
    print(f"  Upload response body: {response.data.decode('utf-8')}")
    assert response.status_code == 201, "Template upload endpoint failed!"
    
    # 3. Test list templates endpoint
    print("Testing list templates route...")
    list_response = client.get(f"/api/projects/{project}/templates")
    print(f"  List response body: {list_response.data.decode('utf-8')}")
    assert list_response.status_code == 200
    
    # 4. Test render endpoint
    print("Testing render PDF report route...")
    render_payload = {
        "template_name": "FCU Report.docx"
    }
    render_response = client.post(
        f"/api/projects/{project}/pdf/{pdf_path}/render",
        data=json.dumps(render_payload),
        content_type="application/json"
    )
    print(f"  Render response status: {render_response.status_code}")
    assert render_response.status_code == 200, f"Render failed: {render_response.data}"
    print(f"  Rendered docx byte size: {len(render_response.data)} bytes")
    print("Flask endpoints integration test PASSED successfully!")

    # Cleanup test entry
    conn = stamp_db._get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM stamp_fields WHERE stamp_id=?", (stamp_id,))
        cur.execute("DELETE FROM stamps WHERE id=?", (stamp_id,))
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    test_flask_endpoints()
