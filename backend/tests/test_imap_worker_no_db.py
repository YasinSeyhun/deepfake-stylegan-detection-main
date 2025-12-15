import os
import json
import tempfile
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_imap_worker_adds_json_and_pubsub():
    # Geçici dosya ve ortam değişkenleri
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = os.path.join(tmpdir, "inbox_cache.jsonl")
        tmp_dir = os.path.join(tmpdir, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        os.environ["INBOX_CACHE"] = jsonl_path
        os.environ["TMP_DIR"] = tmp_dir
        os.environ["IMAP_HOST"] = "mockhost"
        os.environ["IMAP_PORT"] = "993"
        os.environ["IMAP_USER"] = "user"
        os.environ["IMAP_PASS"] = "pass"
        os.environ["ANALYZE_URL"] = "http://mock/analyze"
        os.environ["REDIS_URL"] = "redis://localhost:6379/0"

        # Mock IMAP ve analiz
        with patch("imaplib.IMAP4_SSL") as mock_imap, \
             patch("aiohttp.ClientSession.post", new_callable=AsyncMock) as mock_post, \
             patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_redis:
            # IMAP davranışı
            instance = mock_imap.return_value
            instance.login.return_value = None
            instance.select.return_value = ("OK", [b"1"])
            instance.uid.side_effect = [
                ("OK", [b"123"]),  # search
                ("OK", [(None, b"rawmail")]),  # fetch
            ]
            # E-posta mocku
            with patch("email.message_from_bytes") as mock_msg:
                msg = MagicMock()
                msg.walk.return_value = []
                msg.get.side_effect = lambda k: {"From": "a@b.com", "To": "me@c.com", "Subject": "Test", "Date": "2024-05-27T12:00:00"}.get(k)
                mock_msg.return_value = msg
                # Analyze mocku
                mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={"result": "fake", "score": 0.9})
                # Redis mocku
                mock_pub = AsyncMock()
                mock_redis.return_value = mock_pub
                # Worker'ı bir kez çalıştır
                from backend.services.imap_worker import imap_worker
                await asyncio.wait_for(imap_worker(), timeout=2)
                # Dosya yazıldı mı?
                with open(jsonl_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    assert len(lines) > 0
                    obj = json.loads(lines[0])
                    assert obj["from"] == "a@b.com"
                    assert obj["phishing"] is True
                # Redis publish çağrıldı mı?
                assert mock_pub.publish.called 