"""Quick test for /api/manage_tags/apply_rules endpoint."""
import json, os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

def run():
    app.config['TESTING'] = True
    with app.test_client() as c:
        # 1. No project specified → 400
        r = c.post('/api/manage_tags/apply_rules', json={})
        assert r.status_code == 400, f"Expected 400, got {r.status_code}"

        # 2. Project with no config file → success with 0 updates
        config_path = r'c:\pinchus\global_stamp_config.json'
        backup = config_path + '.bak'
        if os.path.exists(config_path):
            os.rename(config_path, backup)
        try:
            r = c.post('/api/manage_tags/apply_rules', json={'project': 'TestProject'})
            data = r.get_json()
            assert data.get('success'), f"Unexpected: {data}"
            print(f"No-config case OK: {data}")
        finally:
            if os.path.exists(backup):
                os.rename(backup, config_path)

        # 3. With real config and a bogus project (no stamps) → success with 0 updates
        r = c.post('/api/manage_tags/apply_rules', json={'project': 'NonExistentProject12345'})
        data = r.get_json()
        assert data.get('success'), f"Unexpected: {data}"
        print(f"No-stamps case OK: {data}")

    print("All apply_rules tests passed!")

if __name__ == '__main__':
    run()
