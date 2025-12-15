import torch
import torch.nn as nn
import torchvision.models as models
from typing import List, Dict, Any

class FederatedResNetDetector(nn.Module):
    def __init__(self, model_name: str = "resnet18", num_classes: int = 2):
        super().__init__()
        self.base_model = getattr(models, model_name)(pretrained=True)
        
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
        state_dict = {k: torch.from_numpy(v) for k, v in params_dict}
        self.load_state_dict(state_dict) 