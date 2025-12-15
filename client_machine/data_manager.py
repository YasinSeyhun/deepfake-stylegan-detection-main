import torch
from torch.utils.data import DataLoader, TensorDataset

class DataManager:
    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
        
    def load_data(self):
        """Generates synthetic data for simulation."""
        # Generate random images (3 channels, 224x224) and labels (0 or 1)
        # Train: 32 samples (small for speed on local cpu)
        train_x = torch.randn(32, 3, 224, 224)
        train_y = torch.randint(0, 2, (32,))
        
        # Val: 16 samples
        val_x = torch.randn(16, 3, 224, 224)
        val_y = torch.randint(0, 2, (16,))
        
        train_ds = TensorDataset(train_x, train_y)
        val_ds = TensorDataset(val_x, val_y)
        
        train_loader = DataLoader(train_ds, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=self.batch_size)
        
        return train_loader, val_loader
