from dataclasses import dataclass
from typing import Optional

@dataclass
class FederatedConfig:
    # Server configuration
    MIN_CLIENTS: int = 2
    MAX_CLIENTS: int = 10
    ROUNDS: int = 10
    EPOCHS_PER_ROUND: int = 5
    
    # Model configuration
    MODEL_NAME: str = "resnet18"
    NUM_CLASSES: int = 2
    
    # Training configuration
    BATCH_SIZE: int = 32
    LEARNING_RATE: float = 0.001
    MOMENTUM: float = 0.9
    WEIGHT_DECAY: float = 0.0001
    
    # Data configuration
    TRAIN_SPLIT: float = 0.8
    VAL_SPLIT: float = 0.2
    
    # Security configuration
    TOKEN_EXPIRY: int = 3600  # 1 hour in seconds 