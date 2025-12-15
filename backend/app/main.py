from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import torch
import shutil
import json
from datetime import datetime
import io
import os
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
import os
import sys

# Add parent directory to path to allow importing src if needed in future
# and to be robust
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.append(project_root)

from app.core.config import settings
from app.model.detector import load_trained_detector, LABELS, GradCAM, get_last_conv_layer, overlay_cam_on_image
from app.routers import mail_sender_router, inbox_router
from torchvision import transforms

app = FastAPI(title=settings.PROJECT_NAME)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
try:
    model = load_trained_detector(str(settings.MODEL_PATH), device=device)
    print(f"Model loaded from {settings.MODEL_PATH}")
except Exception as e:
    print(f"Warning: Could not load model from {settings.MODEL_PATH}. Error: {e}")
    # Initialize a dummy model or fail? For now, let's keep it running but warn.
    # In a real fix, we might want to download weights or use a blank model.
    from app.model.detector import get_resnet50_detector
    model = get_resnet50_detector(pretrained=True)
    model.to(device)
    model.eval()

preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])

app.include_router(mail_sender_router)
app.include_router(inbox_router)

@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")
    
    try:
    # Convert to PIL Image
    try:
        contents = await file.read()
        image = Image.open(BytesIO(contents)).convert("RGB")
    except Exception as e:
        print(f"Analyze Error: {e}")
        raise HTTPException(status_code=400, detail="Could not process image.")
    
    # --- Face Guard: Check if a face is present ---
    # Convert PIL to OpenCV format (numpy array)
    open_cv_image = np.array(image)
    # Convert RGB to BGR
    open_cv_image = open_cv_image[:, :, ::-1].copy()
    
    # Load Haar Cascade
    face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(face_cascade_path)
    
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    if len(faces) == 0:
        raise HTTPException(
            status_code=400, 
            detail="No face detected in the image! Please upload a clear photo of a face for deepfake analysis."
        )
    # -----------------------------------------------

    # Preprocess for EfficientNet-B4 (Requires 380x380)
    # Re-define preprocess locally or update global if possible but modifying global here
    # to ensure it uses the correct size for this request
    custom_preprocess = transforms.Compose([
        transforms.Resize((380, 380)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]) # ImageNet Standards
    ])
    
    input_tensor = custom_preprocess(image).unsqueeze(0).to(device)
    
    # Inference
    with torch.no_grad():
        outputs = model(input_tensor)
        probs = torch.softmax(outputs, dim=1).cpu().numpy()[0]
        pred_idx = int(outputs.argmax(dim=1).cpu().numpy()[0])
        label = LABELS[pred_idx]
        confidence = float(probs[pred_idx])
        
    # Save Image (if not attachment)
    image_id = file.filename
    gradcam_filename = f"gradcam_{file.filename}.png" # Default fallback
    
    if not file.filename.startswith("att_"):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        ext = os.path.splitext(file.filename)[-1] or ".png"
        image_id = f"{timestamp}{ext}"
        image_path = settings.UPLOAD_DIR / image_id
        image.save(image_path)
        gradcam_filename = f"gradcam_{image_id}.png"
        
    # Grad-CAM
    try:
        target_layer = get_last_conv_layer(model)
        gradcam = GradCAM(model, target_layer)
        cam = gradcam(input_tensor, class_idx=pred_idx)
        gradcam.remove_hooks()
        
        overlayed = overlay_cam_on_image(image, cam)
        gradcam_path = settings.GRADCAM_DIR / gradcam_filename
        Image.fromarray(overlayed).save(gradcam_path)
        gradcam_url = f"/images/gradcam/{gradcam_filename}"
    except Exception as e:
        print(f"GradCAM Error: {e}")
        gradcam_url = None
        gradcam_filename = None

    # Save Result to JSON
    if not file.filename.startswith("att_"):
        result_obj = {
            "label": label,
            "score": round(confidence * 100, 2),
            "image_id": image_id,
            "file_name": file.filename,
            "date": datetime.now().isoformat(),
            "gradcam": gradcam_filename
        }
        save_result_to_json(result_obj)

    return {
        "result": label,
        "score": round(confidence * 100, 2),
        "image_id": image_id,
        "gradcam_url": gradcam_url
    }

def save_result_to_json(result_obj):
    results = []
    if settings.RESULTS_FILE.exists():
        try:
            with open(settings.RESULTS_FILE, "r", encoding="utf-8") as f:
                results = json.load(f)
        except Exception:
            results = []
    
    results.insert(0, result_obj)
    
    with open(settings.RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

@app.get("/images/{image_id}")
def get_image(image_id: str):
    image_path = settings.UPLOAD_DIR / image_id
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(image_path)

@app.get("/images/gradcam/{filename}")
def get_gradcam_image(filename: str):
    gradcam_path = settings.GRADCAM_DIR / filename
    if not gradcam_path.exists():
        raise HTTPException(status_code=404, detail="Grad-CAM image not found.")
    return FileResponse(gradcam_path)

@app.get("/results")
def get_results():
    if not settings.RESULTS_FILE.exists():
        return []
        
    try:
        with open(settings.RESULTS_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    except Exception:
        return []
        
    # Filter missing files
    filtered = []
    changed = False
    for r in results:
        image_id = r.get("image_id")
        if not image_id: continue
        
        # Check if file exists
        if (settings.UPLOAD_DIR / image_id).exists():
            filtered.append(r)
        else:
            changed = True
            
    if changed:
         with open(settings.RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
            
    return filtered

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")
        
    ext = os.path.splitext(file.filename)[-1] or ".png"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    filename = f"uploaded_{timestamp}{ext}"
    file_path = settings.UPLOAD_DIR / filename
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
    return {"filename": filename}