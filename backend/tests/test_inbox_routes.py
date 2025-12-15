import os
import json
import tempfile
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def setup_jsonl(tmp_path):
    jsonl_path = tmp_path / "inbox_cache.jsonl"
    mails = [
        {"id": "1", "from": "a@b.com", "to": ["me@c.com"], "subject": "Test1", "date": "2024-05-27T12:00:00", "html": "<b>hi</b>", "text": "hi", "phishing": True, "score": 0.9, "attachments": [], "deleted": False},
        {"id": "2", "from": "b@b.com", "to": ["me@c.com"], "subject": "Test2", "date": "2024-05-26T12:00:00", "html": "<b>hello</b>", "text": "hello", "phishing": False, "score": 0.1, "attachments": [], "deleted": False},
    ]
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for m in mails:
            f.write(json.dumps(m) + "\n")
    os.environ["INBOX_CACHE"] = str(jsonl_path)
    return mails

def test_get_mails(client, setup_jsonl):
    r = client.get("/mails")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    r2 = client.get("/mails?phishing=true")
    assert len(r2.json()) == 1
    assert r2.json()[0]["phishing"] is True

def test_get_mail_by_id(client, setup_jsonl):
    r = client.get("/mails/1")
    assert r.status_code == 200
    assert r.json()["id"] == "1"
    r2 = client.get("/mails/999")
    assert r2.status_code == 404

def test_delete_mail(client, setup_jsonl):
    r = client.delete("/mails/1")
    assert r.status_code == 200
    r2 = client.get("/mails/1")
    assert r2.json()["deleted"] is True

def test_sse_stream(client, setup_jsonl):
    # SSE endpoint test (yalnızca bağlantı kurulabiliyor mu kontrolü)
    with client.stream("GET", "/mails/stream") as r:
        assert r.status_code == 200
        # SSE header
        assert r.headers["content-type"].startswith("text/event-stream") 