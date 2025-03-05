#!/usr/bin/env python3
"""
Environment Variable Management Script

This script provides utilities for managing environment variables for the GPU Fleet Manager.
It helps with creating .env files from templates, validating required variables,
and generating secure random values for secrets.

Usage:
    python manage_env.py create              # Create .env file from template
    python manage_env.py validate            # Validate existing .env file
    python manage_env.py generate-secrets    # Generate secure random values for secret fields
    python manage_env.py encrypt --key KEY   # Encrypt .env file to .env.encrypted using key
    python manage_env.py decrypt --key KEY   # Decrypt .env.encrypted to .env using key
"""

import os
import sys
import re
import argparse
import secrets
import string
import logging
from typing import Dict, List, Set, Optional
from dotenv import load_dotenv
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import project modules
from src.config.secrets import SecretManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Constants
ENV_TEMPLATE_PATH = '.env.template'
ENV_PATH = '.env'
ENV_ENCRYPTED_PATH = '.env.encrypted'
SECRET_FIELDS = [
    'POSTGRES_PASSWORD',
    'SUPABASE_KEY',
    'SUPABASE_JWT_SECRET',
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
    'WEBHOOK_SIGNING_SECRET',
    'SECRET_KEY',
    'MASTER_KEY'
]


def create_env_file() -> None:
    """Create .env file from template"""
    if os.path.exists(ENV_PATH):
        logger.warning(f"{ENV_PATH} already exists. Do you want to overwrite it? (y/n)")
        if input().lower() != 'y':
            logger.info("Operation cancelled.")
            return

    if not os.path.exists(ENV_TEMPLATE_PATH):
        logger.error(f"{ENV_TEMPLATE_PATH} not found. Cannot create {ENV_PATH}.")
        return

    # Read template file
    with open(ENV_TEMPLATE_PATH, 'r') as f:
        template_content = f.read()
    
    # Create .env file with interactive input
    env_content = []
    
    for line in template_content.splitlines():
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith('#'):
            env_content.append(line)
            continue
            
        # Handle variable lines
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Handle commented-out variables
            if key.startswith('#'):
                env_content.append(line)
                continue
                
            # For secret fields, offer to generate random values
            if key in SECRET_FIELDS and not value:
                logger.info(f"Do you want to generate a secure random value for {key}? (y/n)")
                if input().lower() == 'y':
                    value = generate_secure_string(32)
                    logger.info(f"Generated value for {key}")
                else:
                    logger.info(f"Enter value for {key}:")
                    value = input()
                    
            # For non-secret fields with empty values, prompt for input
            elif not value or value == '""' or value == "''":
                logger.info(f"Enter value for {key}:")
                value = input()
                
            env_content.append(f"{key}={value}")
        else:
            env_content.append(line)
    
    # Write .env file
    with open(ENV_PATH, 'w') as f:
        f.write('\n'.join(env_content))
        
    logger.info(f"{ENV_PATH} file created successfully.")


def validate_env_file() -> bool:
    """
    Validate existing .env file
    
    Returns:
        True if validation passed, False otherwise
    """
    if not os.path.exists(ENV_PATH):
        logger.error(f"{ENV_PATH} not found. Run 'python manage_env.py create' to create it.")
        return False
        
    if not os.path.exists(ENV_TEMPLATE_PATH):
        logger.error(f"{ENV_TEMPLATE_PATH} not found. Cannot validate {ENV_PATH}.")
        return False
        
    # Load template required variables
    required_vars = set()
    with open(ENV_TEMPLATE_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key = line.split('=', 1)[0].strip()
                # Skip commented-out variables
                if not key.startswith('#'):
                    required_vars.add(key)
    
    # Load existing variables
    load_dotenv(ENV_PATH)
    existing_vars = {}
    missing_vars = []
    empty_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if value is None:
            missing_vars.append(var)
        elif not value.strip():
            empty_vars.append(var)
        else:
            existing_vars[var] = value
    
    # Validate
    if missing_vars:
        logger.error(f"Missing variables in {ENV_PATH}: {', '.join(missing_vars)}")
        return False
        
    if empty_vars:
        logger.warning(f"Empty variables in {ENV_PATH}: {', '.join(empty_vars)}")
        
    # Check for sensitive variables that should be secret
    for secret_field in SECRET_FIELDS:
        if secret_field in existing_vars and len(existing_vars[secret_field]) < 16:
            logger.warning(f"{secret_field} may not be secure. Consider generating a stronger value.")
    
    logger.info(f"{ENV_PATH} validation completed. {len(existing_vars)} variables found.")
    return True


def generate_secure_string(length: int = 32) -> str:
    """
    Generate a secure random string
    
    Args:
        length: Length of the string to generate
        
    Returns:
        Secure random string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_secrets() -> None:
    """Generate secure random values for secret fields"""
    if not os.path.exists(ENV_PATH):
        logger.error(f"{ENV_PATH} not found. Run 'python manage_env.py create' to create it.")
        return
        
    # Load existing .env file
    with open(ENV_PATH, 'r') as f:
        env_content = f.read()
        
    # Generate new secrets for each secret field
    for secret_field in SECRET_FIELDS:
        pattern = f"^{secret_field}=.*$"
        
        # Check if the variable exists and has a value
        match = re.search(pattern, env_content, re.MULTILINE)
        if match:
            value = match.group(0).split('=', 1)[1]
            if not value.strip():
                # Generate a new value
                new_value = generate_secure_string(32)
                env_content = re.sub(
                    pattern,
                    f"{secret_field}={new_value}",
                    env_content,
                    flags=re.MULTILINE
                )
                logger.info(f"Generated new value for {secret_field}")
    
    # Write updated .env file
    with open(ENV_PATH, 'w') as f:
        f.write(env_content)
        
    logger.info("Secret values generated successfully.")


def encrypt_env_file(key: Optional[str] = None) -> None:
    """
    Encrypt .env file to .env.encrypted
    
    Args:
        key: Encryption key to use
    """
    if not os.path.exists(ENV_PATH):
        logger.error(f"{ENV_PATH} not found. Run 'python manage_env.py create' to create it.")
        return
        
    # Load .env file
    env_vars = {}
    with open(ENV_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key_val = line.split('=', 1)
                if len(key_val) == 2:
                    env_vars[key_val[0].strip()] = key_val[1].strip()
    
    # Encrypt
    manager = SecretManager(master_key=key)
    manager.save_to_file(env_vars, ENV_ENCRYPTED_PATH)
    
    logger.info(f"Environment variables encrypted to {ENV_ENCRYPTED_PATH}")


def decrypt_env_file(key: Optional[str] = None) -> None:
    """
    Decrypt .env.encrypted to .env
    
    Args:
        key: Decryption key to use
    """
    if not os.path.exists(ENV_ENCRYPTED_PATH):
        logger.error(f"{ENV_ENCRYPTED_PATH} not found.")
        return
        
    if os.path.exists(ENV_PATH):
        logger.warning(f"{ENV_PATH} already exists. Do you want to overwrite it? (y/n)")
        if input().lower() != 'y':
            logger.info("Operation cancelled.")
            return
    
    # Decrypt
    manager = SecretManager(master_key=key)
    env_vars = manager.load_from_file(ENV_ENCRYPTED_PATH)
    
    # Write .env file
    with open(ENV_PATH, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    logger.info(f"Environment variables decrypted to {ENV_PATH}")


def main():
    """Parse arguments and execute commands"""
    parser = argparse.ArgumentParser(description="Manage environment variables for GPU Fleet Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create .env file from template")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate existing .env file")
    
    # Generate secrets command
    generate_parser = subparsers.add_parser("generate-secrets", help="Generate secure random values for secret fields")
    
    # Encrypt command
    encrypt_parser = subparsers.add_parser("encrypt", help="Encrypt .env file to .env.encrypted")
    encrypt_parser.add_argument("--key", help="Encryption key to use")
    
    # Decrypt command
    decrypt_parser = subparsers.add_parser("decrypt", help="Decrypt .env.encrypted to .env")
    decrypt_parser.add_argument("--key", help="Decryption key to use")
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_env_file()
    elif args.command == "validate":
        validate_env_file()
    elif args.command == "generate-secrets":
        generate_secrets()
    elif args.command == "encrypt":
        encrypt_env_file(args.key)
    elif args.command == "decrypt":
        decrypt_env_file(args.key)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
