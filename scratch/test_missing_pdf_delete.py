import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'web_viewer'))

from app import app, get_pdf_path
import stamp_db

def test_missing_pdf_force_delete():
    app.config['TESTING'] = True
    client = app.test_client()
    
    # Bypass login
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'
        sess['logged_in'] = True
        
    project = "TestProj"
    pdf_name = "does_not_exist_file.pdf"
    pdf_path = f"Projects/{project}/pdfs/{pdf_name}"
    xref = 9999
    
    # Ensure database is initialized
    stamp_db.init_db()
    
    # Get the resolved path (absolute) to match real app database format
    resolved_path = get_pdf_path(pdf_path)
    print(f"Resolved absolute path: {resolved_path}")
    
    # Ensure file physically doesn't exist
    if os.path.exists(resolved_path):
        os.remove(resolved_path)
        
    # --- TEST CASE 1: Relative PDF route path ---
    # Pre-populate db with stamp for a missing PDF file
    stamp_id_1 = stamp_db.get_or_create_stamp(project, resolved_path, 1, xref)
    stamp_db.upsert_fields(stamp_id_1, [{"name": "TestField", "value": "TestVal", "type": "string"}])
    
    url_rel = f"/api/pdf/{pdf_path}/stamps/{xref}"
    print(f"\n1. Testing normal delete relative endpoint: {url_rel}")
    res = client.delete(url_rel)
    assert res.status_code == 404, f"Expected 404, got {res.status_code}"
    
    force_url_rel = f"{url_rel}?force=true"
    print(f"Testing force delete relative endpoint: {force_url_rel}")
    res_force = client.delete(force_url_rel)
    assert res_force.status_code == 200, f"Expected 200, got {res_force.status_code}"
    
    # --- TEST CASE 2: Absolute PDF route path ---
    # Pre-populate again
    xref_abs = 8888
    stamp_id_2 = stamp_db.get_or_create_stamp(project, resolved_path, 1, xref_abs)
    stamp_db.upsert_fields(stamp_id_2, [{"name": "TestField2", "value": "TestVal2", "type": "string"}])
    
    # Pass absolute path in the route directly
    url_abs = f"/api/pdf/{resolved_path}/stamps/{xref_abs}"
    print(f"\n2. Testing normal delete absolute endpoint: {url_abs}")
    res = client.delete(url_abs)
    print(f"  Response status: {res.status_code}")
    print(f"  Response body: {res.data.decode('utf-8')}")
    assert res.status_code == 404, f"Expected 404, got {res.status_code}"
    
    force_url_abs = f"{url_abs}?force=true"
    print(f"Testing force delete absolute endpoint: {force_url_abs}")
    res_force = client.delete(force_url_abs)
    print(f"  Response status: {res_force.status_code}")
    print(f"  Response body: {res_force.data.decode('utf-8')}")
    assert res_force.status_code == 200, f"Expected 200, got {res_force.status_code}"
    
    # Verify both records are deleted from DB
    conn = stamp_db._get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM stamps WHERE id IN (?,?)", (stamp_id_1, stamp_id_2))
        rows = cur.fetchall()
        assert len(rows) == 0, f"Expected both stamp records to be deleted, but found: {rows}"
        print("\nAll missing PDF force-delete tests (both relative and absolute) PASSED successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    test_missing_pdf_force_delete()
