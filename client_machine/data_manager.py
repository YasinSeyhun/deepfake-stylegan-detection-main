import os
from torch.utils.data import DataLoader, TensorDataset
from torchvision import datasets, transforms
from src.common.transforms import get_robust_transforms
import torch
import logging

class DataManager:
    """
    Manages data loading for the Federated Client.
    Supports both REAL dataset (ImageFolder) and SYNTHETIC simulation.
    """
    def __init__(self, batch_size: int = 32, data_root: str = "data"):
        self.batch_size = batch_size
        self.data_root = data_root
        
        # Initialize robust transforms
        self.transform = get_robust_transforms(img_size=380)
        
    def load_data(self):
        """Loads real data from disk, or falls back to synthetic if not found."""
        
        # Check if real data exists
        train_dir = os.path.join(self.data_root, "train")
        val_dir = os.path.join(self.data_root, "val")
        
        if os.path.exists(train_dir) and os.path.exists(val_dir):
            print(f"DataManager: ✅ Real dataset found at {self.data_root}")
            
            train_ds = datasets.ImageFolder(root=train_dir, transform=self.transform)
            val_ds = datasets.ImageFolder(root=val_dir, transform=self.transform)
            
            print(f"DataManager: Loaded {len(train_ds)} training images and {len(val_ds)} validation images.")
            
            # Configure loaders
            # num_workers=0 ensures compatibility across Windows/Linux without spawn issues
            train_loader = DataLoader(train_ds, batch_size=self.batch_size, shuffle=True, num_workers=2, pin_memory=True)
            val_loader = DataLoader(val_ds, batch_size=self.batch_size, shuffle=False)
            
            return train_loader, val_loader
        else:
            print(f"DataManager: ⚠️ Real dataset NOT found at {self.data_root}. Using SYNTHETIC data.")
            return self._generate_synthetic_data()

    def _generate_synthetic_data(self):
        print("DataManager: Generating synthetic dataset...")
        # Train: 32 samples (3 channels, 380x380 for EfficientNet)
        train_x = torch.randn(32, 3, 380, 380)
        train_y = torch.randint(0, 2, (32,))
        
        # Val: 16 samples
        val_x = torch.randn(16, 3, 380, 380)
        val_y = torch.randint(0, 2, (16,))
        
        train_ds = TensorDataset(train_x, train_y)
        val_ds = TensorDataset(val_x, val_y)
        
        train_loader = DataLoader(train_ds, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=self.batch_size)
        
        return train_loader, val_loader
