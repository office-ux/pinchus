import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'web_viewer'))

import stamp_db

def test_lifecycle():
    stamp_db.init_db()
    
    project = "LifecycleProj"
    pdf_path = "lifecycle_test.pdf"
    page = 2
    xref = 12345
    
    # 1. Create/Get Stamp
    print("Testing creation...")
    stamp_id = stamp_db.get_or_create_stamp(project, pdf_path, page, xref)
    print(f"  Created stamp row ID: {stamp_id}")
    
    # 2. Get Metadata (should auto-create default fields)
    print("Testing defaults population...")
    meta = stamp_db.get_stamp_metadata(stamp_id)
    fields = meta["fields"]
    print(f"  Defaults count: {len(fields)}")
    assert len(fields) == 12, f"Expected 12 default fields, got {len(fields)}"
    
    # 3. Verify specific fields
    names = [f["name"] for f in fields]
    assert "DWG #" in names, "Missing DWG #"
    assert "#" in names, "Missing pattern number field #"
    assert "DESIGN CFM" in names, "Missing DESIGN CFM"
    
    # 4. Test delete
    print("Testing delete synchronization...")
    stamp_db.delete_stamp_record(pdf_path, xref)
    
    # Verify both stamp and fields are gone (cascade deleted)
    conn = stamp_db._get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM stamps WHERE id=?", (stamp_id,))
        assert cur.fetchone() is None, "Stamp record was not deleted!"
        
        cur.execute("SELECT * FROM stamp_fields WHERE stamp_id=?", (stamp_id,))
        assert len(cur.fetchall()) == 0, "Stamp fields were not cascade-deleted!"
        print("  Delete synchronization verified (cascade delete works perfectly).")
    finally:
        conn.close()

if __name__ == "__main__":
    test_lifecycle()
