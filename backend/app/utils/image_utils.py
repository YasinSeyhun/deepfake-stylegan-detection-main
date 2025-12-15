from PIL import Image, UnidentifiedImageError
from fastapi import UploadFile, HTTPException

def read_imagefile(file: UploadFile) -> Image.Image:
    try:
        image = Image.open(file.file)
        image = image.convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Geçersiz veya desteklenmeyen görsel dosyası.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Görsel işlenemedi: {str(e)}")
    return image 