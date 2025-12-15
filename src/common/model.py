import torch
import torch.nn as nn
from torchvision import models
import numpy as np
from typing import List

class FederatedDeepfakeDetector(nn.Module):
    def __init__(self, model_name: str = "efficientnet_b4", num_classes: int = 2):
        super().__init__()
        
        # Load EfficientNet-B4 with pretrained weights
        try:
            weights = models.EfficientNet_B4_Weights.IMAGENET1K_V1
            self.base_model = models.efficientnet_b4(weights=weights)
        except (AttributeError, NameError):
            # Fallback for older torchvision versions
            self.base_model = models.efficientnet_b4(pretrained=True)
            
        # EfficientNet has a 'classifier' block, not 'fc'.
        # The last layer in the classifier is usually the linear layer.
        # Structure: classifier = Sequential(Dropout, Linear)
        
        # Get in_features from the existing last linear layer
        # EfficientNet classifer structure: [Dropout, Linear]
        in_features = self.base_model.classifier[1].in_features
        
        # Replace the classifier head for binary classification
        self.base_model.classifier[1] = nn.Linear(in_features, num_classes)
        
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
