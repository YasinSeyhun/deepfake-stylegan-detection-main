import argparse
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import cv2
import os

# Grad-CAM helper
class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self.hook_handles = []
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output.detach()
        def backward_hook(module, grad_in, grad_out):
            self.gradients = grad_out[0].detach()
        self.hook_handles.append(self.target_layer.register_forward_hook(forward_hook))
        self.hook_handles.append(self.target_layer.register_backward_hook(backward_hook))

    def remove_hooks(self):
        for handle in self.hook_handles:
            handle.remove()

    def __call__(self, input_tensor, class_idx=None):
        self.model.zero_grad()
        output = self.model(input_tensor)
        if class_idx is None:
            class_idx = output.argmax(dim=1).item()
        target = output[0, class_idx]
        target.backward()
        gradients = self.gradients[0]  # [C, H, W]
        activations = self.activations[0]  # [C, H, W]
        weights = gradients.mean(dim=(1, 2))  # [C]
        cam = (weights[:, None, None] * activations).sum(dim=0)
        cam = torch.relu(cam)
        cam = cam - cam.min()
        cam = cam / (cam.max() + 1e-8)
        cam = cam.cpu().numpy()
        return cam

def get_last_conv_layer(model):
    # For ResNet18, last conv layer is model.layer4[1].conv2
    return model.layer4[1].conv2

def load_model(model_path, num_classes=2):
    model = models.resnet50(pretrained=False)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    checkpoint = torch.load(model_path, map_location=torch.device('cpu'))
    # Anahtar ismi 'model_state_dict' veya 'state_dict' olabilir, kontrol et
    if 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
    elif 'state_dict' in checkpoint:
        state_dict = checkpoint['state_dict']
    else:
        state_dict = checkpoint  # Eğer doğrudan state_dict ise
    model.load_state_dict(state_dict)
    model.eval()
    return model

def preprocess_image(image_path):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    image = Image.open(image_path).convert('RGB')
    input_tensor = transform(image).unsqueeze(0)
    return input_tensor, image

def overlay_cam_on_image(img: Image.Image, cam: np.ndarray, alpha=0.4):
    img = np.array(img.resize((224, 224)))
    cam_resized = cv2.resize(cam, (224, 224))  # Grad-CAM çıktısını yeniden boyutlandır
    heatmap = cv2.applyColorMap(np.uint8(255 * cam_resized), cv2.COLORMAP_JET)
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
    overlayed = np.float32(heatmap) * alpha + np.float32(img) * (1 - alpha)
    overlayed = overlayed / np.max(overlayed)
    overlayed = np.uint8(255 * overlayed)
    return overlayed

def main():
    parser = argparse.ArgumentParser(description="Grad-CAM ile ısı haritası üretir.")
    parser.add_argument('--image_path', type=str, required=True, help='Test görselinin yolu')
    parser.add_argument('--output_path', type=str, required=True, help='Çıktı PNG dosya yolu')
    parser.add_argument('--model_path', type=str, required=True, help='Eğitilmiş modelin yolu')
    parser.add_argument('--class_idx', type=int, default=None, help='İsteğe bağlı: Sınıf indexi (0/1)')
    args = parser.parse_args()

    model = load_model(args.model_path)
    target_layer = get_last_conv_layer(model)
    gradcam = GradCAM(model, target_layer)

    input_tensor, orig_img = preprocess_image(args.image_path)
    cam = gradcam(input_tensor, class_idx=args.class_idx)
    gradcam.remove_hooks()

    overlayed = overlay_cam_on_image(orig_img, cam)
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    Image.fromarray(overlayed).save(args.output_path)
    print(f"Grad-CAM ısı haritası kaydedildi: {args.output_path}")

if __name__ == "__main__":
    main() 