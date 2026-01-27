import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend_core.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
try:
    resp = client.post("/auth/login", json={"username":"admin","password":"Admin@123"})
    print('STATUS', resp.status_code)
    print('HEADERS', resp.headers)
    print('BODY')
    print(resp.text)
except Exception as e:
    import traceback
    traceback.print_exc()
    print('Exception during test:', e)
