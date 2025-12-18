import os
import logging
from typing import Dict, List, Optional, Tuple
import flwr as fl
from flwr.server.strategy.aggregate import aggregate
import torch
import numpy as np
from dotenv import load_dotenv

import sys
# Add parent directory to path to allow importing 'src'
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.common.model import FederatedDeepfakeDetector
from src.common.config import FederatedConfig
from src.common.security import SecurityManager

# Initialize model
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
global_model = FederatedDeepfakeDetector().to(device)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeepFakeServer(fl.server.strategy.FedAvg):
    def __init__(
        self,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.config = FederatedConfig()
        self.security_manager = SecurityManager(os.getenv('SECRET_KEY', 'default_secret_key'))
        self.global_model = FederatedDeepfakeDetector()
        self.client_weights: Dict[str, List[np.ndarray]] = {}
        self.client_metrics: Dict[str, Dict[str, float]] = {}
        
    def aggregate_fit(
        self,
        rnd: int,
        results: List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitRes]],
        failures: List[BaseException],
    ) -> Optional[fl.common.Parameters]:
        """Aggregate model weights using FedAvg."""
        if not results:
            return None
            
        # Verify client tokens and collect weights
        valid_results = []
        for client, fit_res in results:
            if not self.security_manager.is_token_valid(fit_res.metrics.get('token', '')):
                logger.warning(f"Invalid token from client {client.cid}")
                continue
                
            valid_results.append((client, fit_res))
            
        if not valid_results:
            return None
            
        # Aggregate weights
        # Aggregate weights
        weights_results = [
            (fl.common.parameters_to_ndarrays(fit_res.parameters), fit_res.num_examples)
            for _, fit_res in valid_results
        ]
        weights_aggregated = aggregate(weights_results)
        
        # Update global model
        self.global_model.set_parameters(weights_aggregated)
        
        return fl.common.ndarrays_to_parameters(weights_aggregated), {}
        
    def aggregate_evaluate(
        self,
        rnd: int,
        results: List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.EvaluateRes]],
        failures: List[BaseException],
    ) -> Optional[float]:
        """Aggregate evaluation metrics."""
        if not results:
            return None
            
        # Collect metrics from valid clients
        valid_metrics = []
        for client, eval_res in results:
            if not self.security_manager.is_token_valid(eval_res.metrics.get('token', '')):
                continue
                
            valid_metrics.append(eval_res.metrics)
            
        if not valid_metrics:
            return None
            
        # Calculate global metrics
        global_metrics = self.calculate_global_metrics(valid_metrics)
        logger.info(f"Round {rnd} - Global metrics: {global_metrics}")
        
        return global_metrics.get('loss', 0.0), global_metrics
        
    def calculate_global_metrics(self, client_metrics: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate global metrics from client metrics."""
        total_samples = sum(metrics.get('num_samples', 0) for metrics in client_metrics)
        if total_samples == 0:
            return {}
            
        global_metrics = {
            'accuracy': 0.0,
            'loss': 0.0,
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0
        }
        
        for metrics in client_metrics:
            weight = metrics.get('num_samples', 0) / total_samples
            for key in global_metrics:
                if key in metrics:
                    global_metrics[key] += metrics[key] * weight
                    
        return global_metrics

def start_server():
    """Start the Flower server."""
    # Load environment variables
    load_dotenv()
    
    # Initialize server
    # Initialize server
    strategy = DeepFakeServer(
        min_available_clients=int(os.getenv('MIN_CLIENTS', 2)),
        min_fit_clients=int(os.getenv('MIN_CLIENTS', 2)),
        min_evaluate_clients=int(os.getenv('MIN_CLIENTS', 2)),
        initial_parameters=fl.common.ndarrays_to_parameters(
            FederatedDeepfakeDetector().get_parameters()
        ),
    )
    
    # Start server
    fl.server.start_server(
        server_address="[::]:8081",
        config=fl.server.ServerConfig(num_rounds=int(os.getenv('ROUNDS', 10))),
        strategy=strategy
    )

if __name__ == "__main__":
    start_server() 