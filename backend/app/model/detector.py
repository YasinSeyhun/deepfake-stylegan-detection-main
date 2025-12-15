import torch
import torch.nn as nn
from torchvision import models
import numpy as np
import cv2
from PIL import Image

# Label mapping for inference
LABELS = {0: 'fake', 1: 'real'}

def get_resnet50_detector(pretrained=True):
    model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1 if pretrained else None)
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, 2)  # 2 sınıf: real/fake
    return model

def load_trained_detector(weights_path, device='cpu'):
    model = get_resnet50_detector(pretrained=False)
    checkpoint = torch.load(weights_path, map_location=device)
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    model.eval()
    model.to(device)
    return model

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
    # For ResNet50, last conv layer is model.layer4[2].conv3
    return model.layer4[2].conv3

def overlay_cam_on_image(img: Image.Image, cam: np.ndarray, alpha=0.4):
    img = np.array(img.resize((224, 224)))
    cam_resized = cv2.resize(cam, (224, 224))  # Grad-CAM çıktısını yeniden boyutlandır
    heatmap = cv2.applyColorMap(np.uint8(255 * cam_resized), cv2.COLORMAP_JET)
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
    overlayed = np.float32(heatmap) * alpha + np.float32(img) * (1 - alpha)
    overlayed = overlayed / np.max(overlayed)
    overlayed = np.uint8(255 * overlayed)
    return overlayed

if __name__ == "__main__":
    model = get_resnet50_detector()
    print(model) 