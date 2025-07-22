#!/usr/bin/env python3
"""
Script to manage secrets in Google Secret Manager.

Usage:
    python manage_secrets.py create --project PROJECT_ID
    python manage_secrets.py update --project PROJECT_ID --secret SECRET_ID
    python manage_secrets.py list --project PROJECT_ID
    python manage_secrets.py migrate --project PROJECT_ID --env-file .env.staging
"""

import os
import sys
import json
import argparse
import getpass
from typing import Dict, Any
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.secrets_manager import SecretsManager


def create_default_secrets(sm: SecretsManager, environment: str = "staging"):
    """Create default secrets for the environment."""
    print(f"\nCreating default secrets for {environment} environment...")
    
    secrets_to_create = {
        "database-password": {
            "prompt": "Enter database password",
            "is_password": True
        },
        "jwt-secret-key": {
            "prompt": "Enter JWT secret key (32+ chars)",
            "is_password": False,
            "default": None
        },
        "google-maps-api-key": {
            "prompt": "Enter Google Maps API key",
            "is_password": False
        },
        "first-superuser-password": {
            "prompt": "Enter first superuser password",
            "is_password": True
        },
        "redis-password": {
            "prompt": "Enter Redis password (if applicable)",
            "is_password": True,
            "optional": True
        },
        "smtp-credentials": {
            "prompt": "Enter SMTP credentials as JSON",
            "is_json": True,
            "optional": True,
            "example": '{"host": "smtp.gmail.com", "port": 587, "username": "user", "password": "pass"}'
        }
    }
    
    created_secrets = []
    
    for secret_id, config in secrets_to_create.items():
        print(f"\n{secret_id}:")
        
        if config.get("optional"):
            create = input(f"Create {secret_id}? (y/N): ").lower() == 'y'
            if not create:
                continue
        
        if config.get("is_json"):
            print(f"Example: {config.get('example', '{}')}")
            value = input(f"{config['prompt']}: ")
            try:
                # Validate JSON
                json.loads(value)
            except json.JSONDecodeError:
                print(f"Invalid JSON format for {secret_id}")
                continue
        elif config.get("is_password", False):
            value = getpass.getpass(f"{config['prompt']}: ")
        else:
            value = input(f"{config['prompt']}: ")
            
        if not value and not config.get("optional"):
            print(f"Skipping {secret_id} (no value provided)")
            continue
            
        if value:
            success = sm.create_secret(f"{environment}-{secret_id}", value)
            if success:
                created_secrets.append(secret_id)
                print(f"✓ Created {secret_id}")
            else:
                print(f"✗ Failed to create {secret_id}")
    
    return created_secrets


def migrate_from_env_file(sm: SecretsManager, env_file: str, environment: str = "staging"):
    """Migrate secrets from an environment file to Secret Manager."""
    print(f"\nMigrating secrets from {env_file} to Secret Manager...")
    
    if not os.path.exists(env_file):
        print(f"Error: Environment file {env_file} not found")
        return
    
    # Mapping of environment variables to secret IDs
    env_to_secret_mapping = {
        "POSTGRES_PASSWORD": "database-password",
        "SECRET_KEY": "jwt-secret-key",
        "GOOGLE_MAPS_API_KEY": "google-maps-api-key",
        "FIRST_SUPERUSER_PASSWORD": "first-superuser-password",
        "REDIS_PASSWORD": "redis-password",
    }
    
    migrated_secrets = []
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                
                if key in env_to_secret_mapping:
                    secret_id = f"{environment}-{env_to_secret_mapping[key]}"
                    success = sm.create_secret(secret_id, value)
                    if success:
                        migrated_secrets.append(key)
                        print(f"✓ Migrated {key} to {secret_id}")
                    else:
                        # Try updating if already exists
                        success = sm.update_secret(secret_id, value)
                        if success:
                            migrated_secrets.append(key)
                            print(f"✓ Updated {key} in {secret_id}")
                        else:
                            print(f"✗ Failed to migrate {key}")
    
    return migrated_secrets


def list_secrets(sm: SecretsManager):
    """List all secrets in the project."""
    print("\nListing all secrets...")
    secrets = sm.list_secrets()
    
    if not secrets:
        print("No secrets found")
        return
    
    print(f"\nFound {len(secrets)} secrets:")
    for secret in sorted(secrets):
        print(f"  - {secret}")


def update_secret_interactive(sm: SecretsManager, secret_id: str):
    """Update a secret interactively."""
    print(f"\nUpdating secret: {secret_id}")
    
    # Check if it's a JSON secret
    current_value = sm.get_secret_json(secret_id)
    if current_value is not None:
        print("Current value is JSON format")
        print(json.dumps(current_value, indent=2))
        new_value = input("Enter new JSON value: ")
        try:
            json.loads(new_value)
            success = sm.update_secret(secret_id, new_value)
        except json.JSONDecodeError:
            print("Invalid JSON format")
            return
    else:
        # Regular string secret
        if "password" in secret_id.lower() or "key" in secret_id.lower():
            new_value = getpass.getpass("Enter new value: ")
        else:
            new_value = input("Enter new value: ")
        success = sm.update_secret(secret_id, new_value)
    
    if success:
        print(f"✓ Updated {secret_id}")
    else:
        print(f"✗ Failed to update {secret_id}")


def main():
    parser = argparse.ArgumentParser(description="Manage Google Secret Manager secrets")
    parser.add_argument("action", choices=["create", "update", "list", "migrate"],
                        help="Action to perform")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--secret", help="Secret ID (for update action)")
    parser.add_argument("--env-file", help="Environment file to migrate from")
    parser.add_argument("--environment", default="staging",
                        help="Environment name (staging, production)")
    
    args = parser.parse_args()
    
    # Set project ID environment variable
    os.environ["GCP_PROJECT_ID"] = args.project
    
    # Initialize secrets manager
    sm = SecretsManager(project_id=args.project)
    
    if args.action == "create":
        created = create_default_secrets(sm, args.environment)
        print(f"\nCreated {len(created)} secrets")
        
    elif args.action == "update":
        if not args.secret:
            print("Error: --secret is required for update action")
            sys.exit(1)
        update_secret_interactive(sm, args.secret)
        
    elif args.action == "list":
        list_secrets(sm)
        
    elif args.action == "migrate":
        if not args.env_file:
            print("Error: --env-file is required for migrate action")
            sys.exit(1)
        migrated = migrate_from_env_file(sm, args.env_file, args.environment)
        print(f"\nMigrated {len(migrated)} secrets")


if __name__ == "__main__":
    main()