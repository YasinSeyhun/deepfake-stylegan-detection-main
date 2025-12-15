import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(SCRIPT_DIR, '..')))

from src.fake_detector_models.resnet50.detector import load_trained_detector, LABELS
import torch
from torchvision import transforms
from PIL import Image

# Model ve device ayarları
MODEL_PATH = os.path.join(SCRIPT_DIR, "..", "src", "models", "detector_best.pth")
DEVICE = torch.device("cpu")
model = load_trained_detector(MODEL_PATH, device=DEVICE)

# Preprocess
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])

def predict_image(image_path):
    image = Image.open(image_path).convert("RGB")
    input_tensor = preprocess(image).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        outputs = model(input_tensor)
        probs = torch.softmax(outputs, dim=1).cpu().numpy()[0]
        pred_idx = int(outputs.argmax(dim=1).cpu().numpy()[0])
        label = LABELS[pred_idx]
        confidence = float(probs[pred_idx])
    print(f"Image: {image_path}")
    print(f"Prediction: {label} ({confidence*100:.2f}%)")
    return label, confidence

# ÖRNEK KULLANIM
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Kullanım: python test_inference.py <gorsel_yolu>")
    else:
        predict_image(sys.argv[1])