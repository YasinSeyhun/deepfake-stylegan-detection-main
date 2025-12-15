import torch
import torch.nn as nn
from torchvision import models
import numpy as np
from typing import List

class FederatedResNetDetector(nn.Module):
    def __init__(self, model_name: str = "resnet50", num_classes: int = 2):
        super().__init__()
        # Use newer weights API if available, else pretrained=True
        try:
            # Try to use the new weights API if possible
            weights = models.ResNet50_Weights.IMAGENET1K_V1
            self.base_model = models.resnet50(weights=weights)
        except (AttributeError, NameError):
             # Fallback for older torchvision versions
            self.base_model = models.resnet50(pretrained=True)
            
        # Modify the final layer for binary classification
        in_features = self.base_model.fc.in_features
        self.base_model.fc = nn.Linear(in_features, num_classes)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.base_model(x)
        
    def get_parameters(self) -> List[np.ndarray]:
        """Get model parameters as a list of NumPy arrays."""
        return [val.cpu().numpy() for _, val in self.state_dict().items()]
        
    def set_parameters(self, parameters: List[np.ndarray]) -> None:
        """Set model parameters from a list of NumPy arrays."""
        params_dict = zip(self.state_dict().keys(), parameters)
        state_dict = {}
        for k, v in params_dict:
            if not isinstance(v, np.ndarray):
                v = np.array(v)
            state_dict[k] = torch.from_numpy(v)
        self.load_state_dict(state_dict, strict=True)
