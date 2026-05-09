
from fastapi.testclient import TestClient
from app.main import app
from tests.fakes import FakeLLM

client = TestClient(app)

def test_specify_minimal(monkeypatch):
    import agents.nodes as nodes

    monkeypatch.setattr(nodes, "llm", FakeLLM())
    data = {"specscript": "#spec\nTitle: Demo\nType: PRD\naccept:\n- GWT: As a user, when I click X, I see Y."}
    r = client.post("/specify", data=data)
    assert r.status_code == 200
    js = r.json()
    assert "spec" in js
    assert "trace" in js
