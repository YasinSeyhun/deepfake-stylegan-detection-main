import jwt
import time
from typing import Dict, Optional
from .config import FederatedConfig

class SecurityManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.config = FederatedConfig()
    
    def generate_token(self, client_id: str) -> str:
        """Generate JWT token for client authentication."""
        payload = {
            'client_id': client_id,
            'exp': int(time.time()) + self.config.TOKEN_EXPIRY
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return payload if valid."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def is_token_valid(self, token: str) -> bool:
        """Check if token is valid and not expired."""
        payload = self.verify_token(token)
        return payload is not None 