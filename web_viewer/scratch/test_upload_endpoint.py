import os
import sys
import io
import json

# Add parent directory of scratch to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, BASE_DIR

def run_test():
    # Make sure we use a clean test global_stamp_config.json or back up the current one
    config_path = os.path.join(BASE_DIR, "global_stamp_config.json")
    backup_path = config_path + ".bak"
    
    backup_exists = os.path.exists(config_path)
    if backup_exists:
        print("Backing up global_stamp_config.json...")
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.rename(config_path, backup_path)
        
    try:
        # Write an initial config to test merging
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"uploadedStamps": ["existing_stamp_abc"]}, f)
            
        app.config['TESTING'] = True
        with app.test_client() as client:
            # 1. Test upload of multiple images
            print("Uploading multiple images...")
            data = {
                'files[]': [
                    (io.BytesIO(b"dummy image data 1"), "new_stamp_foo.png"),
                    (io.BytesIO(b"dummy image data 2"), "new_stamp_bar.jpg"),
                ],
                'project': 'test_project'
            }
            response = client.post('/api/manage_tags/upload', data=data, content_type='multipart/form-data')
            print("Response status:", response.status_code)
            res_data = response.get_json()
            print("Response JSON:", res_data)
            
            # Check the saved config
            with open(config_path, "r", encoding="utf-8") as f:
                saved_config = json.load(f)
            print("Saved config:", saved_config)
            
            assert res_data.get("success") is True
            assert "newstampfoo" in saved_config["uploadedStamps"]
            assert "newstampbar" in saved_config["uploadedStamps"]
            assert "existing_stamp_abc" in saved_config["uploadedStamps"]
            print("Test 1 passed successfully!")
            
    finally:
        # Restore configuration
        if os.path.exists(config_path):
            os.remove(config_path)
        if backup_exists:
            print("Restoring global_stamp_config.json...")
            os.rename(backup_path, config_path)

if __name__ == "__main__":
    run_test()
