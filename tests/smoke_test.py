
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_specify_minimal():
    data = {"specscript": "#spec\nTitle: Demo\nType: PRD\naccept:\n- GWT: As a user, when I click X, I see Y."}
    r = client.post("/specify", data=data)
    assert r.status_code == 200
    js = r.json()
    assert "spec" in js
