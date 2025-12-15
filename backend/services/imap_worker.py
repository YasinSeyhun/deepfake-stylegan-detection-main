from dotenv import load_dotenv
load_dotenv()
import asyncio
import email
import imaplib
import os
import uuid
import json
import aiohttp
import redis.asyncio as aioredis
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
import traceback
import mimetypes

IMAP_HOST = os.getenv("IMAP_HOST")
IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")
ANALYZE_URL = os.getenv("ANALYZE_URL", "http://127.0.0.1:8000/analyze-a")
JSONL_PATH = os.getenv("INBOX_CACHE", "backend/app/inbox_cache.jsonl")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(PROJECT_ROOT, os.getenv("TMP_DIR", "tmp/"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LAST_UID_PATH = "app/last_seen_uid.txt"

os.makedirs(TMP_DIR, exist_ok=True)

async def analyze_image(session, image_path):
    data = aiohttp.FormData()
    ext = os.path.splitext(image_path)[-1].lower()
    if ext in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif ext == ".png":
        mime = "image/png"
    else:
        mime = "application/octet-stream"
    with open(image_path, "rb") as f:
        file_bytes = f.read()
    data.add_field(
        "file",
        file_bytes,
        filename=os.path.basename(image_path),
        content_type=mime
    )
    async with session.post(ANALYZE_URL, data=data) as resp:
        text = await resp.text()
        print("ANALYZE RESPONSE:", resp.status, text)
        try:
            return json.loads(text)
        except Exception:
            return {"result": "error", "score": 0.0}

def sanitize_html(html):
    # Basit temizlik, daha güvenli için bleach/dompurify önerilir
    return html.replace('<script', '&lt;script')

def parse_email(msg):
    html = None
    text = None
    attachments = []
    skipped_attachments = []
    for part in msg.walk():
        ctype = part.get_content_type()
        fname = part.get_filename()
        if fname:
            fname = decode_mime_words(fname)
        if ctype in ["image/jpeg", "image/png"] and fname:
            payload = part.get_payload(decode=True)
            if payload:
                if len(payload) > 2 * 1024 * 1024:
                    skipped_attachments.append(fname)
                    continue
                path = os.path.join(TMP_DIR, f"att_{uuid.uuid4().hex}_{fname}")
                with open(path, "wb") as f:
                    f.write(payload)
                basename = os.path.basename(path)
                full_path = os.path.join(TMP_DIR, basename)
                if full_path not in attachments:
                    attachments.append(full_path)
        elif ctype == "text/html" and not html:
            html = part.get_payload(decode=True)
            if html:
                html = html.decode(errors="ignore")
        elif ctype == "text/plain" and not text:
            text = part.get_payload(decode=True)
            if text:
                text = text.decode(errors="ignore")
    return html, text, attachments, skipped_attachments

def decode_mime_words(s):
    if not s:
        return ""
    decoded = decode_header(s)
    result = []
    for part, encoding in decoded:
        if isinstance(part, bytes):
            try:
                if encoding and encoding.lower() not in ["unknown-8bit", "x-unknown", "unknown"]:
                    result.append(part.decode(encoding))
                else:
                    result.append(part.decode("utf-8", errors="replace"))
            except Exception:
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(part)
    return ''.join(result)

def load_last_seen_uid():
    try:
        with open(LAST_UID_PATH, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None

def save_last_seen_uid(uid):
    os.makedirs(os.path.dirname(LAST_UID_PATH), exist_ok=True)
    with open(LAST_UID_PATH, "w") as f:
        f.write(str(uid))

async def imap_worker():
    print("IMAP_HOST:", IMAP_HOST)
    print("IMAP_PORT:", IMAP_PORT)
    print("IMAP_USER:", IMAP_USER)
    redis_conn = await aioredis.from_url(REDIS_URL)
    last_seen_uid = load_last_seen_uid()
    while True:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(IMAP_USER, IMAP_PASS)
            # Klasör seç (INBOX veya All Mail)
            # mail.select('"[Gmail]/All Mail"')  # Gmail için tüm mailler
            typ, mailbox_info = mail.select("INBOX")
            print("IMAP select typ:", typ, "mailbox_info:", mailbox_info)
            typ, data = mail.uid('search', None, "ALL")
            uids = [int(x) for x in data[0].split()]
            uids.sort()
            print("last_seen_uid (from file):", last_seen_uid)
            # Sadece en yeni 50 maili işle
            new_uids = [uid for uid in uids if last_seen_uid is None or uid > last_seen_uid]
            new_uids = new_uids[-50:]
            print("New UIDs to process (limited to 50):", new_uids)
            if new_uids:
                last_seen_uid = max(new_uids)
                save_last_seen_uid(last_seen_uid)
            for uid in new_uids:
                typ, msg_data = mail.uid('fetch', str(uid), '(RFC822)')
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                html, text, attachments, skipped_attachments = parse_email(msg)
                print(f"[IMAP WORKER] UID: {uid} | Attachments: {attachments} | Skipped: {skipped_attachments}")
                if len(attachments) > 5:
                    skipped_attachments += attachments[5:]
                    attachments = attachments[:5]
                results = []
                async with aiohttp.ClientSession() as session:
                    for att in attachments:
                        if not os.path.exists(att):
                            print(f"[IMAP WORKER] File does not exist: {att}")
                        print(f"[IMAP WORKER] Analyzing attachment: {att}")
                        try:
                            res = await analyze_image(session, att)
                        except Exception as e:
                            print(f"[IMAP WORKER] Analyze error for {att}: {e}")
                            res = {"result": "error", "score": 0.0}
                        results.append(res)
                print(f"[IMAP WORKER] ANALYZE RESULTS for UID {uid}: {results}")
                phishing = any(r.get("result") == "fake" and r.get("score", 0) >= 0.8 for r in results)
                score = max([r.get("score", 0) for r in results], default=0)
                obj = {
                    "id": str(uuid.uuid4()),
                    "uid": uid,
                    "from": decode_mime_words(msg.get("From")),
                    "to": [decode_mime_words(msg.get("To"))],
                    "subject": decode_mime_words(msg.get("Subject")),
                    "date": msg.get("Date"),
                    "html": sanitize_html(html or ""),
                    "text": text or "",
                    "phishing": phishing,
                    "score": score,
                    "attachments": attachments,
                    "skipped_attachments": skipped_attachments,
                    "deleted": False
                }
                # Yeni maili eklemeden önce, dosyadaki satır sayısını kontrol et
                try:
                    with open(JSONL_PATH, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except FileNotFoundError:
                    lines = []
                lines.append(json.dumps(obj, ensure_ascii=False) + "\n")
                # Sadece son 20 maili tut
                if len(lines) > 20:
                    lines = lines[-20:]
                with open(JSONL_PATH, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                await redis_conn.publish("mail:new", json.dumps(obj))
            mail.logout()
        except Exception as e:
            print("IMAP worker error:", repr(e))
            traceback.print_exc()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(imap_worker()) 