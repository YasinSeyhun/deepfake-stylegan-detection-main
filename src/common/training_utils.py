import torch
import torch.nn as nn

def apply_dp_privacy(model: nn.Module, max_norm: float, noise_multiplier: float, device: torch.device):
    """
    Applies Differential Privacy to the model's gradients.
    1. Clips gradients to max_norm.
    2. Adds Gaussian noise.
    """
    total_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm)
    
    for param in model.parameters():
        if param.grad is not None:
            noise = torch.normal(0, noise_multiplier * max_norm, param.grad.shape, device=device)
            param.grad += noise

def generate_adversarial_example(model: nn.Module, images: torch.Tensor, labels: torch.Tensor, criterion, epsilon: float):
    """
    Generates adversarial examples using Fast Gradient Sign Method (FGSM).
    Returns the perturbed images.
    """
    images.requires_grad = True
    
    # Forward pass to get gradients w.r.t input
    outputs = model(images)
    loss = criterion(outputs, labels)
    model.zero_grad()
    loss.backward()
    
    # Collect data_grad
    data_grad = images.grad.data
    
    # Create perturbed image
    sign_data_grad = data_grad.sign()
    perturbed_image = images + epsilon * sign_data_grad
    
    # Clamp to ensure valid pixel range (based on normalization used)
    # Using roughly -1 to 1 range due to standard normalization
    perturbed_image = torch.clamp(perturbed_image, -1, 1)
    
    return perturbed_image
