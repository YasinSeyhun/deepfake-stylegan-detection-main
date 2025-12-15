from fastapi import APIRouter, Query, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import status
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import Security
from fastapi import Header
from fastapi import Body
from fastapi import Path
from fastapi import UploadFile, File
from sse_starlette.sse import EventSourceResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import os
import json
import aiofiles
import redis.asyncio as aioredis
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.config import settings

router = APIRouter()

JSONL_PATH = settings.INBOX_CACHE
REDIS_URL = settings.REDIS_URL
TMP_DIR = settings.TMP_DIR

limiter = Limiter(key_func=get_remote_address)

# Helper: Read all mails from JSONL
async def read_mails():
    print("INBOX_CACHE path:", JSONL_PATH)
    if not os.path.exists(JSONL_PATH):
        print("Dosya bulunamadı:", JSONL_PATH)
        return []
    else:
        print("Dosya bulundu, içerik okunuyor:", JSONL_PATH)
    mails = []
    async with aiofiles.open(JSONL_PATH, mode="r", encoding="utf-8") as f:
        async for line in f:
            try:
                mail = json.loads(line)
                mails.append(mail)
            except Exception:
                continue
    return mails

# GET /mails
@router.get("/mails")
@limiter.limit("5/second")
async def get_mails(request: Request, phishing: Optional[bool] = None, skip: int = 0, limit: int = 20):
    mails = await read_mails()
    mails = [m for m in mails if not m.get("deleted", False)]
    if phishing is not None:
        mails = [m for m in mails if m.get("phishing") == phishing]
    def parse_date(mail):
        date_str = mail.get("date", "")
        for fmt in ("%a, %d %b %Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(date_str[:19], fmt)
            except Exception:
                continue
        try:
            return datetime.fromisoformat(date_str)
        except Exception:
            return datetime.min
    mails = sorted(mails, key=parse_date, reverse=False)
    return mails[skip:skip+limit]

# SSE /mails/stream
@router.get("/mails/stream")
async def mails_stream():
    redis_conn = await aioredis.from_url(REDIS_URL)
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe("mail:new")
    async def event_generator():
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=10.0)
                if message and message["type"] == "message":
                    yield {
                        "event": "mail:new",
                        "data": message["data"].decode()
                    }
        finally:
            await pubsub.unsubscribe("mail:new")
            await pubsub.close()
    return EventSourceResponse(event_generator())

# GET /mails/{id}
@router.get("/mails/{mail_id}")
async def get_mail(mail_id: str):
    mails = await read_mails()
    for mail in mails:
        if mail["id"] == mail_id:
            return mail
    raise HTTPException(status_code=404, detail="Mail not found")

# GET /mails/{id}/attachment/{filename}
@router.get("/mails/{mail_id}/attachment/{filename}")
async def get_attachment(mail_id: str, filename: str):
    mails = await read_mails()
    mail = next((m for m in mails if m["id"] == mail_id), None)
    if not mail:
        raise HTTPException(status_code=404, detail="Mail not found")
    # Ekler listesinden tam dosya yolunu bul
    file_path = next((att for att in mail.get("attachments", []) if os.path.basename(att) == filename), None)
    if file_path and os.path.exists(file_path):
        async def file_stream():
            async with aiofiles.open(file_path, mode="rb") as f:
                chunk = await f.read(8192)
                while chunk:
                    yield chunk
                    chunk = await f.read(8192)
        return StreamingResponse(file_stream(), media_type="application/octet-stream")
    raise HTTPException(status_code=404, detail="Attachment not found")

# DELETE /mails/{id}
@router.delete("/mails/{mail_id}")
async def delete_mail(mail_id: str):
    mails = await read_mails()
    found = False
    for mail in mails:
        if mail["id"] == mail_id:
            mail["deleted"] = True
            found = True
    if not found:
        raise HTTPException(status_code=404, detail="Mail not found")
    # Yeniden yaz
    async with aiofiles.open(JSONL_PATH, mode="w", encoding="utf-8") as f:
        for mail in mails:
            await f.write(json.dumps(mail, ensure_ascii=False) + "\n")
    return {"ok": True} 