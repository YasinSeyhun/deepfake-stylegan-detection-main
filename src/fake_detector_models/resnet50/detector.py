import torch
import torch.nn as nn
from torchvision import models

# Label mapping for inference
LABELS = {0: 'real', 1: 'fake'}

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

if __name__ == "__main__":
    model = get_resnet50_detector()
    print(model) 