import sys
import os
import logging
import flwr as fl
import torch
import torch.nn as nn
import torch.optim as optim
from dotenv import load_dotenv
import time

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.common.model import FederatedDeepfakeDetector
from src.common.config import FederatedConfig
from src.common.security import SecurityManager
from src.common.training_utils import apply_dp_privacy, generate_adversarial_example
from client_machine.data_manager import DataManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepFakeClient(fl.client.NumPyClient):
    def __init__(self, client_id: str, secret_key: str):
        self.config = FederatedConfig()
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        logger.info(f"Client {client_id} initializing on {self.device}...")
        # Initialize model
        self.model = FederatedDeepfakeDetector().to(self.device).eval()
        self.criterion = nn.CrossEntropyLoss()
        self.data_manager = DataManager(batch_size=self.config.BATCH_SIZE)
        self.train_loader, self.val_loader = self.data_manager.load_data()
        
        # Security
        self.security_manager = SecurityManager(secret_key)
        self.token = self.security_manager.generate_token(client_id)
        logger.info(f"Client {client_id} ready.")

    def get_parameters(self, config):
        return self.model.get_parameters()

    def fit(self, parameters, config):
        logger.info("Starting training round...")
        self.model.set_parameters(parameters)
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.SGD(
            self.model.parameters(), 
            lr=self.config.LEARNING_RATE, 
            momentum=self.config.MOMENTUM
        )
        
        # Local training
        self.model.train()
        for epoch in range(self.config.EPOCHS_PER_ROUND):
            total_loss = 0
            for images, labels in self.train_loader:
                images, labels = images.to(self.device), labels.to(self.device)
                
                # --- Adversarial Training (FGSM) ---
                if self.config.ADVERSARIAL_TRAINING:
                    # Generate adversarial examples
                    adv_images = generate_adversarial_example(
                        self.model, images, labels, criterion, self.config.FGSM_EPSILON
                    )
                    # Concat original and adversarial images for robust training
                    # Or train on them separately. Concatenating doubled the batch size.
                    # Let's do a combined forward pass if memory allows, or two steps.
                    # Combining is cleaner for BatchNorm.
                    combined_images = torch.cat([images, adv_images], dim=0)
                    combined_labels = torch.cat([labels, labels], dim=0)
                    
                    optimizer.zero_grad()
                    outputs = self.model(combined_images)
                    loss = criterion(outputs, combined_labels)
                else:
                    optimizer.zero_grad()
                    outputs = self.model(images)
                    loss = criterion(outputs, labels)
                # -----------------------------------

                loss.backward()
                
                # --- Differential Privacy ---
                if self.config.USE_DIFFERENTIAL_PRIVACY:
                    apply_dp_privacy(
                        self.model, 
                        max_norm=self.config.DP_MAX_NORM, 
                        noise_multiplier=self.config.DP_NOISE_MULTIPLIER,
                        device=self.device
                    )
                # ----------------------------

                optimizer.step()
                total_loss += loss.item()
            logger.info(f"Epoch {epoch+1} loss: {total_loss}")
                
        return self.model.get_parameters(), len(self.train_loader.dataset), {"token": self.token}

    def evaluate(self, parameters, config):
        logger.info("Evaluating...")
        self.model.set_parameters(parameters)
        self.model.eval()
        loss = 0.0
        correct = 0
        total = 0
        
        criterion = nn.CrossEntropyLoss()
        
        with torch.no_grad():
            for images, labels in self.val_loader:
                images, labels = images.to(self.device), labels.to(self.device)
                outputs = self.model(images)
                loss += criterion(outputs, labels).item()
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        
        accuracy = correct / total
        logger.info(f"Evaluation accuracy: {accuracy}")
        return float(loss), len(self.val_loader.dataset), {"accuracy": float(accuracy), "token": self.token}

def start_client(client_id: str):
    load_dotenv()
    secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
    # Use 'server' hostname for Docker, fallback to localhost for local test
    server_address = os.getenv('SERVER_ADDRESS', 'server:8081') 
    
    client = DeepFakeClient(client_id, secret_key)
    
    # Retry logic for connecting to the server
    max_retries = 20
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"Attempting to connect to server at {server_address} (Attempt {attempt + 1}/{max_retries})...")
            fl.client.start_client(
                server_address=server_address,
                client=client.to_client()
            )
            break  # If successful, exit the loop
        except Exception as e:
            print(f"Connection failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Exiting.")
                sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        client_id = sys.argv[1]
    else:
        client_id = "client_1"
    start_client(client_id)
