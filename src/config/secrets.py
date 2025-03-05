"""
Secrets management utilities for GPU Fleet Manager

This module provides utilities for securely handling sensitive configuration values,
including encryption, decryption, and secure storage of secrets.
"""

import os
import base64
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class SecretManager:
    """
    Manager for handling encrypted secrets
    
    This class provides functionality to securely store and retrieve sensitive
    configuration values using encryption.
    """
    
    def __init__(self, master_key: Optional[str] = None, salt: Optional[bytes] = None):
        """
        Initialize the secret manager
        
        Args:
            master_key: Optional master encryption key. If not provided, will attempt
                       to load from MASTER_KEY environment variable
            salt: Optional salt for key derivation. If not provided, will use a default salt
        """
        # Get master key
        self.master_key = master_key or os.environ.get("MASTER_KEY")
        if not self.master_key:
            logger.warning("No master key provided. Using insecure default key.")
            self.master_key = "default-insecure-key-do-not-use-in-production"
            
        # Set salt
        self.salt = salt or b'gpu-fleet-manager-salt'
        
        # Generate encryption key
        self._generate_key()
        
    def _generate_key(self) -> None:
        """Generate encryption key from master key and salt"""
        # Use PBKDF2 to derive a secure key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        derived_key = kdf.derive(self.master_key.encode())
        self.key = base64.urlsafe_b64encode(derived_key)
        self.cipher = Fernet(self.key)
        
    def encrypt(self, data: Union[str, Dict[str, Any]]) -> str:
        """
        Encrypt data
        
        Args:
            data: String or dictionary to encrypt
            
        Returns:
            Base64-encoded encrypted data
        """
        # Convert dict to JSON if needed
        if isinstance(data, dict):
            data = json.dumps(data)
            
        # Encrypt
        encrypted_data = self.cipher.encrypt(data.encode())
        
        # Return as base64 string
        return base64.urlsafe_b64encode(encrypted_data).decode()
        
    def decrypt(self, encrypted_data: str) -> Union[str, Dict[str, Any]]:
        """
        Decrypt data
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            Decrypted data, parsed as JSON if possible
        """
        try:
            # Decode base64
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            
            # Decrypt
            decrypted_data = self.cipher.decrypt(decoded_data).decode()
            
            # Try to parse as JSON
            try:
                return json.loads(decrypted_data)
            except json.JSONDecodeError:
                return decrypted_data
                
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise
            
    def save_to_file(self, data: Dict[str, Any], filename: Union[str, Path]) -> None:
        """
        Encrypt and save data to file
        
        Args:
            data: Dictionary of secrets to encrypt and save
            filename: Path to save the encrypted data
        """
        encrypted_data = self.encrypt(data)
        
        with open(filename, 'w') as f:
            f.write(encrypted_data)
        
        logger.info(f"Encrypted secrets saved to {filename}")
        
    def load_from_file(self, filename: Union[str, Path]) -> Dict[str, Any]:
        """
        Load and decrypt data from file
        
        Args:
            filename: Path to the encrypted data file
            
        Returns:
            Decrypted data as dictionary
        """
        try:
            with open(filename, 'r') as f:
                encrypted_data = f.read()
                
            decrypted_data = self.decrypt(encrypted_data)
            
            if not isinstance(decrypted_data, dict):
                raise ValueError("Decrypted data is not a dictionary")
                
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Error loading secrets from {filename}: {e}")
            raise

def create_secrets_file(output_file: str, secrets_dict: Dict[str, Any], master_key: Optional[str] = None):
    """
    Create an encrypted secrets file
    
    Args:
        output_file: Path to save the encrypted secrets
        secrets_dict: Dictionary of secrets to encrypt
        master_key: Optional master encryption key
    """
    manager = SecretManager(master_key=master_key)
    manager.save_to_file(secrets_dict, output_file)
    
def load_secrets(secrets_file: str, master_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Load secrets from an encrypted file
    
    Args:
        secrets_file: Path to the encrypted secrets file
        master_key: Optional master encryption key
        
    Returns:
        Dictionary of decrypted secrets
    """
    manager = SecretManager(master_key=master_key)
    return manager.load_from_file(secrets_file)
