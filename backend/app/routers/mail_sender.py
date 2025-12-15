# -- coding: utf-8 --
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sse_starlette.sse import EventSourceResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any
import aiosmtplib
import jinja2
import os
from datetime import datetime
import json
import uuid
import asyncio
import email.message
import re

from app.core.config import settings

router = APIRouter()

MAIL_LOGS_PATH = settings.MAIL_LOGS_PATH

# Basit in-memory task store (production için Redis önerilir)
tasks: Dict[str, Dict[str, Any]] = {}

class SendPhishingRequest(BaseModel):
    subject: str
    html_body: str
    image_name: str
    targets: List[EmailStr]

@router.post("/send-phishing")
async def send_phishing(
    req: SendPhishingRequest,
    request: Request
):
    if len(req.targets) > 200:
        raise HTTPException(status_code=429, detail="En fazla 200 alıcıya izin verilir.")
    
    SMTP_HOST = settings.SMTP_HOST
    SMTP_PORT = settings.SMTP_PORT
    SMTP_USER = settings.SMTP_USER
    SMTP_PASS = settings.SMTP_PASS

    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS]):
        # Just warn in dev, or error? Let's error to be safe as per original logic
        pass 
        # Original code raised 500. We keep it but maybe we should allow it if we are just testing?
        # For now, let's keep logic but use settings.
    
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS]):
         raise HTTPException(status_code=500, detail="SMTP yapılandırması eksik.")

    # Görsel yolu oluşturma (uploads/, data/ ve uploaded_ ile başlayanlar için)
    # Use config paths
    if os.path.isabs(req.image_name):
        image_path = req.image_name
    elif req.image_name.startswith("uploads/"):
        # Strip uploads/ prefix and join with UPLOAD_DIR
        clean_name = req.image_name.replace("uploads/", "")
        image_path = str(settings.UPLOAD_DIR / clean_name)
    elif req.image_name.startswith("uploaded_"):
        image_path = str(settings.UPLOAD_DIR / req.image_name)
    else:
        # Assuming data/ is in project root? config doesn't have DATA_DIR yet.
        # Let's assume it is peer to uploads
        image_path = str(settings.BASE_DIR / "data" / req.image_name)

    print("Görsel yolu:", image_path)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=400, detail="Görsel bulunamadı.")
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "progress": 0,
        "total": len(req.targets),
        "sent": 0,
        "status": "pending",
        "error": None,
    }
    # Gönderim işlemini arka planda başlat
    asyncio.create_task(_send_mails_background(task_id, req, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, image_path))
    return {"task_id": task_id}

async def _send_mails_background(task_id, req, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, image_path):
    try:
        template = jinja2.Template(req.html_body)
        total = len(req.targets)
        sent = 0
        for target in req.targets:
            context = {"first_name": "Kullanıcı", "last_name": "", "email": target}
            html = template.render(**context)
            try:
                msg = email.message.EmailMessage()
                msg["From"] = SMTP_USER
                msg["To"] = target
                msg["Subject"] = req.subject
                msg.set_content("Bu mail HTML desteklemeyen istemciler için.")
                msg.add_alternative(html, subtype="html")
                # HTML içinden ilk cid:xxx ifadesini bul
                cid_match = re.search(r'cid:([\\w\\-]+)', html)
                cid = cid_match.group(1) if cid_match else "mailimage"
                with open(image_path, "rb") as imgf:
                    img_data = imgf.read()
                    img_name = os.path.basename(image_path)
                    maintype, subtype = "image", "png"
                    if "." in img_name:
                        ext = img_name.split(".")[-1].lower()
                        if ext in ["jpg", "jpeg"]:
                            subtype = "jpeg"
                        elif ext == "gif":
                            subtype = "gif"
                    msg.get_payload()[1].add_related(
                        img_data,
                        maintype=maintype,
                        subtype=subtype,
                        cid=f"<{cid}>"
                    )
                    msg.add_attachment(img_data, maintype=maintype, subtype=subtype, filename=img_name)
                await aiosmtplib.send(
                    msg,
                    hostname=SMTP_HOST,
                    port=SMTP_PORT,
                    username=SMTP_USER,
                    password=SMTP_PASS,
                    start_tls=True
                )
                status_ = "success"
            except Exception as e:
                status_ = "fail"
            log_entry = {
                "target": target,
                "status": status_,
                "timestamp": datetime.utcnow().isoformat(),
                "template": req.subject,
                "image_used": req.image_name
            }
            with open(MAIL_LOGS_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            sent += 1
            percent = int(sent / total * 100)
            tasks[task_id]["progress"] = percent
            tasks[task_id]["sent"] = sent
            await asyncio.sleep(0.1)  # Simülasyon için, gerçek gönderimde kaldırılabilir
        tasks[task_id]["progress"] = 100
        tasks[task_id]["status"] = "done"
    except Exception as e:
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["status"] = "error"

@router.get("/send-phishing/{task_id}")
async def phishing_progress(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task bulunamadı")
    async def event_stream():
        last_progress = -1
        while True:
            task = tasks.get(task_id)
            if not task:
                break
            progress = task["progress"]
            if progress != last_progress:
                yield f"data: {progress}\n\n"
                last_progress = progress
            if progress >= 100 or task["status"] in ("done", "error"):
                break
            await asyncio.sleep(0.5)
    return EventSourceResponse(event_stream()) 