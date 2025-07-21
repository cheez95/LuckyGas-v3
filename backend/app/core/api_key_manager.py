"""
Secure API Key Management System
"""
from cryptography.fernet import Fernet
from abc import ABC, abstractmethod
import os
import json
from typing import Optional, Dict
import logging
from pathlib import Path
from datetime import datetime

try:
    from google.cloud import secretmanager
    HAS_GCP_SECRET_MANAGER = True
except ImportError:
    HAS_GCP_SECRET_MANAGER = False
    
logger = logging.getLogger(__name__)


class APIKeyManager(ABC):
    """Abstract base class for API key management"""
    
    @abstractmethod
    async def get_key(self, key_name: str) -> Optional[str]:
        """Retrieve an API key securely"""
        pass
    
    @abstractmethod
    async def set_key(self, key_name: str, value: str) -> bool:
        """Set an API key securely"""
        pass
    
    @abstractmethod
    async def rotate_key(self, key_name: str, new_value: str) -> bool:
        """Rotate an API key"""
        pass
    
    @abstractmethod
    async def delete_key(self, key_name: str) -> bool:
        """Delete an API key"""
        pass


class LocalEncryptedKeyManager(APIKeyManager):
    """Local development key manager with encryption"""
    
    def __init__(self, master_key_path: str = ".keys/master.key"):
        self.master_key_path = Path(master_key_path)
        self.keys_file = Path(".keys/encrypted_keys.json")
        self.master_key = self._load_or_create_master_key()
        self.fernet = Fernet(self.master_key)
    
    def _load_or_create_master_key(self) -> bytes:
        """Load existing master key or create a new one"""
        self.master_key_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.master_key_path.exists():
            logger.info("Loading existing master key")
            with open(self.master_key_path, 'rb') as f:
                return f.read()
        else:
            logger.info("Creating new master key")
            key = Fernet.generate_key()
            with open(self.master_key_path, 'wb') as f:
                f.write(key)
            # Restrict access to owner only
            os.chmod(self.master_key_path, 0o600)
            logger.warning(f"New master key created at {self.master_key_path}. Keep this secure!")
            return key
    
    async def get_key(self, key_name: str) -> Optional[str]:
        """Get an encrypted key with audit logging"""
        if not self.keys_file.exists():
            logger.warning(f"No encrypted keys file found at {self.keys_file}")
            logger.info(
                f"API_KEY_ACCESS: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"key_exists=False, reason=no_keys_file"
            )
            return None
        
        try:
            with open(self.keys_file, 'r') as f:
                encrypted_keys = json.load(f)
            
            if key_name in encrypted_keys:
                encrypted_value = encrypted_keys[key_name].encode()
                decrypted = self.fernet.decrypt(encrypted_value).decode()
                
                # Audit log - log key access without exposing the actual key
                logger.info(
                    f"API_KEY_ACCESS: key_name={key_name}, "
                    f"access_time={datetime.now().isoformat()}, "
                    f"key_exists=True, key_length={len(decrypted)}, "
                    f"operation=get_key, status=success"
                )
                
                return decrypted
            else:
                logger.warning(f"Key not found: {key_name}")
                logger.info(
                    f"API_KEY_ACCESS: key_name={key_name}, "
                    f"access_time={datetime.now().isoformat()}, "
                    f"key_exists=False, operation=get_key, status=not_found"
                )
                return None
        except Exception as e:
            logger.error(f"Error retrieving key {key_name}: {e}")
            logger.info(
                f"API_KEY_ACCESS: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=get_key, status=error, error_type={type(e).__name__}"
            )
            return None
    
    async def set_key(self, key_name: str, value: str) -> bool:
        """Set an encrypted key with audit logging"""
        try:
            encrypted_keys = {}
            key_existed = False
            
            if self.keys_file.exists():
                with open(self.keys_file, 'r') as f:
                    encrypted_keys = json.load(f)
                    key_existed = key_name in encrypted_keys
            
            encrypted_value = self.fernet.encrypt(value.encode()).decode()
            encrypted_keys[key_name] = encrypted_value
            
            # Ensure directory exists
            self.keys_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.keys_file, 'w') as f:
                json.dump(encrypted_keys, f, indent=2)
            
            # Restrict access
            os.chmod(self.keys_file, 0o600)
            
            # Audit log - log key modification without exposing the actual key
            logger.info(
                f"API_KEY_MODIFY: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=set_key, status=success, "
                f"key_existed={key_existed}, key_length={len(value)}"
            )
            
            return True
        except Exception as e:
            logger.error(f"Error setting key {key_name}: {e}")
            logger.info(
                f"API_KEY_MODIFY: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=set_key, status=error, error_type={type(e).__name__}"
            )
            return False
    
    async def rotate_key(self, key_name: str, new_value: str) -> bool:
        """Rotate a key with audit logging"""
        # Check if key exists before rotation
        old_key = await self.get_key(key_name)
        key_existed = old_key is not None
        
        result = await self.set_key(key_name, new_value)
        
        if result:
            # Audit log specifically for rotation
            logger.info(
                f"API_KEY_ROTATE: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=rotate_key, status=success, "
                f"key_existed={key_existed}, new_key_length={len(new_value)}"
            )
        else:
            logger.info(
                f"API_KEY_ROTATE: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=rotate_key, status=failed"
            )
        
        return result
    
    async def delete_key(self, key_name: str) -> bool:
        """Delete a key with audit logging"""
        if not self.keys_file.exists():
            logger.info(
                f"API_KEY_DELETE: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=delete_key, status=success, key_existed=False"
            )
            return True
        
        try:
            with open(self.keys_file, 'r') as f:
                encrypted_keys = json.load(f)
            
            key_existed = key_name in encrypted_keys
            
            if key_existed:
                del encrypted_keys[key_name]
                
                with open(self.keys_file, 'w') as f:
                    json.dump(encrypted_keys, f, indent=2)
                
                # Audit log for successful deletion
                logger.info(
                    f"API_KEY_DELETE: key_name={key_name}, "
                    f"access_time={datetime.now().isoformat()}, "
                    f"operation=delete_key, status=success, key_existed=True"
                )
            else:
                # Audit log when key didn't exist
                logger.info(
                    f"API_KEY_DELETE: key_name={key_name}, "
                    f"access_time={datetime.now().isoformat()}, "
                    f"operation=delete_key, status=success, key_existed=False"
                )
            
            return True
        except Exception as e:
            logger.error(f"Error deleting key {key_name}: {e}")
            logger.info(
                f"API_KEY_DELETE: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=delete_key, status=error, error_type={type(e).__name__}"
            )
            return False


class GCPSecretManager(APIKeyManager):
    """Production key manager using Google Secret Manager"""
    
    def __init__(self, project_id: str):
        if not HAS_GCP_SECRET_MANAGER:
            raise ImportError("google-cloud-secret-manager is required for GCP Secret Manager")
        
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()
    
    def _get_secret_name(self, key_name: str) -> str:
        """Get the full secret resource name"""
        # Replace underscores with hyphens for GCP naming
        safe_key_name = key_name.replace('_', '-').lower()
        return f"projects/{self.project_id}/secrets/{safe_key_name}"
    
    async def get_key(self, key_name: str) -> Optional[str]:
        """Retrieve a secret from Google Secret Manager with audit logging"""
        try:
            name = f"{self._get_secret_name(key_name)}/versions/latest"
            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            
            # Audit log - log key access without exposing the actual key
            logger.info(
                f"API_KEY_ACCESS: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"key_exists=True, key_length={len(secret_value)}, "
                f"operation=get_key, status=success, provider=gcp_secret_manager"
            )
            
            return secret_value
        except Exception as e:
            logger.error(f"Failed to retrieve secret {key_name}: {e}")
            logger.info(
                f"API_KEY_ACCESS: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=get_key, status=error, provider=gcp_secret_manager, "
                f"error_type={type(e).__name__}"
            )
            return None
    
    async def set_key(self, key_name: str, value: str) -> bool:
        """Create a new secret in Google Secret Manager with audit logging"""
        try:
            parent = f"projects/{self.project_id}"
            secret_id = key_name.replace('_', '-').lower()
            secret_created = False
            
            # Try to create the secret
            try:
                secret = self.client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": {
                            "replication": {
                                "automatic": {}
                            }
                        }
                    }
                )
                secret_created = True
                logger.info(f"Created new secret: {key_name}")
            except Exception:
                # Secret might already exist
                pass
            
            # Add the secret version
            parent = self._get_secret_name(key_name)
            response = self.client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": value.encode("UTF-8")}
                }
            )
            
            # Audit log - log key modification without exposing the actual key
            logger.info(
                f"API_KEY_MODIFY: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=set_key, status=success, provider=gcp_secret_manager, "
                f"secret_created={secret_created}, key_length={len(value)}"
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to set secret {key_name}: {e}")
            logger.info(
                f"API_KEY_MODIFY: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=set_key, status=error, provider=gcp_secret_manager, "
                f"error_type={type(e).__name__}"
            )
            return False
    
    async def rotate_key(self, key_name: str, new_value: str) -> bool:
        """Rotate a secret by adding a new version with audit logging"""
        try:
            parent = self._get_secret_name(key_name)
            response = self.client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": new_value.encode("UTF-8")}
                }
            )
            
            # Audit log for key rotation
            logger.info(
                f"API_KEY_ROTATE: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=rotate_key, status=success, provider=gcp_secret_manager, "
                f"new_key_length={len(new_value)}"
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to rotate secret {key_name}: {e}")
            logger.info(
                f"API_KEY_ROTATE: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=rotate_key, status=error, provider=gcp_secret_manager, "
                f"error_type={type(e).__name__}"
            )
            return False
    
    async def delete_key(self, key_name: str) -> bool:
        """Delete a secret (actually disables it in GCP) with audit logging"""
        try:
            name = self._get_secret_name(key_name)
            # In production, we disable rather than delete for safety
            response = self.client.destroy_secret_version(
                request={
                    "name": f"{name}/versions/latest"
                }
            )
            
            # Audit log for key deletion/disabling
            logger.info(
                f"API_KEY_DELETE: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=delete_key, status=success, provider=gcp_secret_manager, "
                f"action=disabled_latest_version"
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {key_name}: {e}")
            logger.info(
                f"API_KEY_DELETE: key_name={key_name}, "
                f"access_time={datetime.now().isoformat()}, "
                f"operation=delete_key, status=error, provider=gcp_secret_manager, "
                f"error_type={type(e).__name__}"
            )
            return False


# Factory function to get appropriate key manager
def _get_api_key_manager_impl(environment: str, project_id: Optional[str] = None) -> APIKeyManager:
    """Get the appropriate API key manager based on environment"""
    if environment == "production" and project_id:
        logger.info("Using GCP Secret Manager for API keys")
        return GCPSecretManager(project_id)
    else:
        logger.info("Using local encrypted storage for API keys")
        return LocalEncryptedKeyManager()


async def get_api_key_manager() -> APIKeyManager:
    """Get the appropriate API key manager based on current environment"""
    import os
    from app.core.config import settings
    
    environment = os.getenv("ENVIRONMENT", "development")
    project_id = getattr(settings, "GCP_PROJECT_ID", None)
    
    # Use the existing factory function
    return _get_api_key_manager_impl(environment, project_id)