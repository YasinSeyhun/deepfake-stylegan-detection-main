import torch
import random
import numpy as np
from PIL import Image, ImageFilter
from torchvision import transforms
import io

class RandomJPEGCompression(object):
    """
    Randomly applies JPEG compression to an image.
    Simulates compression artifacts common in web images.
    """
    def __init__(self, quality_min=60, quality_max=100, p=0.5):
        self.quality_min = quality_min
        self.quality_max = quality_max
        self.p = p

    def __call__(self, img):
        if random.random() < self.p:
            output = io.BytesIO()
            quality = random.randint(self.quality_min, self.quality_max)
            img.save(output, 'JPEG', quality=quality)
            output.seek(0)
            return Image.open(output)
        return img

class RandomGaussianBlur(object):
    """
    Applies random Gaussian Blur.
    Forces the model to focus on structural anomalies rather than pixel-perfect high-freq artifacts.
    """
    def __init__(self, radius_min=0.1, radius_max=2.0, p=0.5):
        self.radius_min = radius_min
        self.radius_max = radius_max
        self.p = p

    def __call__(self, img):
        if random.random() < self.p:
            radius = random.uniform(self.radius_min, self.radius_max)
            return img.filter(ImageFilter.GaussianBlur(radius))
        return img

class RandomGaussianNoise(object):
    """
    Adds random Gaussian noise to the image tensor.
    Simulates sensor noise.
    """
    def __init__(self, mean=0.0, std_min=0.01, std_max=0.05, p=0.5):
        self.mean = mean
        self.std_min = std_min
        self.std_max = std_max
        self.p = p

    def __call__(self, tensor):
        if random.random() < self.p:
            std = random.uniform(self.std_min, self.std_max)
            noise = torch.randn(tensor.size()) * std + self.mean
            return tensor + noise
        return tensor

def get_robust_transforms(img_size=380):
    """
    Returns a composition of robust transforms.
    Note: EfficientNet-B4 uses 380x380.
    """
    return transforms.Compose([
        RandomJPEGCompression(quality_min=60, quality_max=95, p=0.5),
        RandomGaussianBlur(radius_min=0.1, radius_max=2.0, p=0.3),
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        RandomGaussianNoise(p=0.3),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
