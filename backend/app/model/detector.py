import torch
import os
import torch.nn as nn
from torchvision import models
import numpy as np
import cv2
from PIL import Image

# Label mapping for inference
LABELS = {0: 'fake', 1: 'real'}

def get_efficientnet_detector(pretrained=True):
    # This logic matches src/common/model.py
    try:
        weights = models.EfficientNet_B4_Weights.IMAGENET1K_V1
        model = models.efficientnet_b4(weights=weights if pretrained else None)
    except (AttributeError, NameError):
        model = models.efficientnet_b4(pretrained=pretrained)
        
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, 2)
    return model

def load_trained_detector(weights_path, device='cpu'):
    model = get_efficientnet_detector(pretrained=False)
    # Check if file exists, if not warn
    if not os.path.exists(weights_path):
        print(f"Warning: Model file {weights_path} not found. Using random weights.")
        model.to(device)
        return model

    checkpoint = torch.load(weights_path, map_location=device)
    
    # Handle both full state dict and direct model
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
    else:
        state_dict = checkpoint
        
    # The server might save 'base_model.' prefix if using wrapper, or not.
    # We need to handle key matching.
    # Our backend 'model' is the pure EfficientNet, but 'FederatedDeepfakeDetector' has 'base_model' attribute.
    # If the saved weights have 'base_model.' prefix, remove it.
    new_state_dict = {}
    for k, v in state_dict.items():
        if k.startswith('base_model.'):
            new_state_dict[k.replace('base_model.', '')] = v
        else:
            new_state_dict[k] = v
            
    try:
        model.load_state_dict(new_state_dict, strict=False)
    except Exception as e:
        print(f"Error loading state dict: {e}")
        
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
    # For EfficientNet-B4, the last convolutional layer is in 'features' block
    # Specifically usually the last module in features
    return model.features[-1]

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
    model = get_efficientnet_detector()
    print(model) 