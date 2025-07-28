"""
Secure Banking Service with Enhanced Credential Protection

This module provides secure banking operations with:
- Encrypted credential storage using Fernet encryption
- Secure SFTP connection management with connection pooling
- Transaction signing and verification
- Comprehensive audit trails
- Zero-trust security model
"""

import os
import io
import re
import json
import time
import base64
import hashlib
import logging
import threading
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from contextlib import contextmanager
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import paramiko
from sqlalchemy.orm import Session
from sqlalchemy import func
import csv

from app.models.banking import (
    PaymentBatch, PaymentTransaction, ReconciliationLog, BankConfiguration,
    PaymentBatchStatus, ReconciliationStatus, TransactionStatus
)
from app.models.audit import BankingAuditLog, AuditAction
from app.core.enhanced_secrets_manager import get_secret_secure, rotate_secret_secure
from app.core.config import settings
from app.core.notifications import send_security_alert

logger = logging.getLogger(__name__)


class SecureCredentialStore:
    """Secure storage for banking credentials with encryption."""
    
    def __init__(self):
        self._encryption_key = self._get_or_create_master_key()
        self._cipher_suite = Fernet(self._encryption_key)
        self._credential_cache = {}
        self._cache_lock = threading.Lock()
        
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key."""
        # Get from secure storage
        master_key = get_secret_secure(
            "banking_master_encryption_key",
            user_id=0,  # System user
            purpose="banking_credential_encryption"
        )
        
        if not master_key:
            # Generate new master key
            master_key = Fernet.generate_key().decode('utf-8')
            
            # Store in secret manager
            from app.core.enhanced_secrets_manager import create_secret
            create_secret("banking_master_encryption_key", master_key)
            
            logger.info("Generated new banking master encryption key")
        
        return master_key.encode('utf-8')
    
    def encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential."""
        encrypted = self._cipher_suite.encrypt(credential.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    
    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential."""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_credential.encode('utf-8'))
            decrypted = self._cipher_suite.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            raise ValueError("Invalid encrypted credential")
    
    def store_bank_credentials(
        self,
        bank_code: str,
        credentials: Dict[str, str],
        user_id: int
    ) -> bool:
        """
        Store bank credentials securely.
        
        Args:
            bank_code: Bank identifier
            credentials: Dictionary of credentials to store
            user_id: User storing the credentials
            
        Returns:
            True if successful
        """
        try:
            encrypted_creds = {}
            
            # Encrypt each credential
            for key, value in credentials.items():
                if value:  # Only encrypt non-empty values
                    encrypted_creds[key] = self.encrypt_credential(value)
            
            # Store in secret manager as JSON
            secret_id = f"banking_{bank_code}_credentials"
            success = create_secret(secret_id, encrypted_creds)
            
            if success:
                # Log audit entry
                self._log_credential_access(
                    bank_code=bank_code,
                    action="store",
                    user_id=user_id,
                    details="Credentials stored securely"
                )
                
                # Clear cache
                with self._cache_lock:
                    self._credential_cache.pop(bank_code, None)
                
                logger.info(f"Stored credentials for bank {bank_code}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to store bank credentials: {e}")
            self._log_credential_access(
                bank_code=bank_code,
                action="store_failed",
                user_id=user_id,
                details=str(e)
            )
            return False
    
    def get_bank_credentials(
        self,
        bank_code: str,
        user_id: int,
        purpose: str
    ) -> Optional[Dict[str, str]]:
        """
        Retrieve and decrypt bank credentials.
        
        Args:
            bank_code: Bank identifier
            user_id: User requesting credentials
            purpose: Purpose of credential access
            
        Returns:
            Decrypted credentials or None
        """
        try:
            # Check cache first
            with self._cache_lock:
                if bank_code in self._credential_cache:
                    cache_entry = self._credential_cache[bank_code]
                    if datetime.utcnow() - cache_entry['timestamp'] < timedelta(minutes=5):
                        return cache_entry['credentials']
            
            # Get from secret manager
            secret_id = f"banking_{bank_code}_credentials"
            encrypted_creds = get_secret_secure(
                secret_id,
                user_id=user_id,
                purpose=purpose
            )
            
            if not encrypted_creds:
                logger.warning(f"No credentials found for bank {bank_code}")
                return None
            
            # Parse JSON if string
            if isinstance(encrypted_creds, str):
                encrypted_creds = json.loads(encrypted_creds)
            
            # Decrypt credentials
            decrypted_creds = {}
            for key, encrypted_value in encrypted_creds.items():
                if encrypted_value:
                    decrypted_creds[key] = self.decrypt_credential(encrypted_value)
            
            # Cache decrypted credentials
            with self._cache_lock:
                self._credential_cache[bank_code] = {
                    'credentials': decrypted_creds,
                    'timestamp': datetime.utcnow()
                }
            
            # Log access
            self._log_credential_access(
                bank_code=bank_code,
                action="retrieve",
                user_id=user_id,
                details=purpose
            )
            
            return decrypted_creds
            
        except Exception as e:
            logger.error(f"Failed to retrieve bank credentials: {e}")
            self._log_credential_access(
                bank_code=bank_code,
                action="retrieve_failed",
                user_id=user_id,
                details=str(e)
            )
            return None
    
    def rotate_bank_credentials(
        self,
        bank_code: str,
        new_credentials: Dict[str, str],
        user_id: int,
        reason: str
    ) -> bool:
        """
        Rotate bank credentials.
        
        Args:
            bank_code: Bank identifier
            new_credentials: New credentials
            user_id: User rotating credentials
            reason: Reason for rotation
            
        Returns:
            True if successful
        """
        try:
            # Encrypt new credentials
            encrypted_creds = {}
            for key, value in new_credentials.items():
                if value:
                    encrypted_creds[key] = self.encrypt_credential(value)
            
            # Rotate in secret manager
            secret_id = f"banking_{bank_code}_credentials"
            success = rotate_secret_secure(
                secret_id,
                encrypted_creds,
                reason=f"banking_rotation: {reason}"
            )
            
            if success:
                # Clear cache
                with self._cache_lock:
                    self._credential_cache.pop(bank_code, None)
                
                # Log rotation
                self._log_credential_access(
                    bank_code=bank_code,
                    action="rotate",
                    user_id=user_id,
                    details=reason
                )
                
                # Send notification
                await send_security_alert(
                    title="Banking Credentials Rotated",
                    message=f"Credentials for bank {bank_code} were rotated. Reason: {reason}",
                    severity="info"
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to rotate bank credentials: {e}")
            self._log_credential_access(
                bank_code=bank_code,
                action="rotate_failed",
                user_id=user_id,
                details=str(e)
            )
            return False
    
    def _log_credential_access(
        self,
        bank_code: str,
        action: str,
        user_id: int,
        details: str
    ):
        """Log credential access for audit trail."""
        try:
            # This would write to audit log table
            logger.info(
                f"Banking credential access: bank={bank_code}, "
                f"action={action}, user={user_id}, details={details}"
            )
        except Exception as e:
            logger.error(f"Failed to log credential access: {e}")


class SecureSFTPManager:
    """Secure SFTP connection manager with enhanced security."""
    
    def __init__(self, credential_store: SecureCredentialStore):
        self._credential_store = credential_store
        self._connection_pool = {}
        self._pool_lock = threading.Lock()
        self._connection_timeout = 300  # 5 minutes
        self._max_pool_size = 5
        
    @contextmanager
    def get_secure_sftp_client(
        self,
        bank_config: BankConfiguration,
        user_id: int
    ):
        """
        Get secure SFTP client with credential protection.
        
        Args:
            bank_config: Bank configuration
            user_id: User requesting connection
            
        Yields:
            paramiko.SFTPClient: Connected SFTP client
        """
        bank_code = bank_config.bank_code
        connection_key = f"{bank_code}_{user_id}"
        
        try:
            # Try to get from pool
            with self._pool_lock:
                if connection_key in self._connection_pool:
                    pool_entry = self._connection_pool[connection_key]
                    if self._is_connection_alive(pool_entry):
                        yield pool_entry['sftp']
                        return
            
            # Get credentials from secure store
            credentials = self._credential_store.get_bank_credentials(
                bank_code=bank_code,
                user_id=user_id,
                purpose="sftp_connection"
            )
            
            if not credentials:
                raise ValueError(f"No credentials available for bank {bank_code}")
            
            # Create new secure connection
            transport = self._create_secure_transport(bank_config, credentials)
            sftp = paramiko.SFTPClient.from_transport(transport)
            
            # Configure security settings
            sftp.get_channel().settimeout(30.0)
            
            # Add to pool
            with self._pool_lock:
                if len(self._connection_pool) >= self._max_pool_size:
                    # Remove oldest connection
                    oldest_key = min(
                        self._connection_pool.keys(),
                        key=lambda k: self._connection_pool[k]['created']
                    )
                    self._close_connection(self._connection_pool.pop(oldest_key))
                
                self._connection_pool[connection_key] = {
                    'transport': transport,
                    'sftp': sftp,
                    'created': datetime.utcnow(),
                    'last_used': datetime.utcnow()
                }
            
            logger.info(f"Established secure SFTP connection to {bank_code}")
            yield sftp
            
        except Exception as e:
            logger.error(f"Secure SFTP connection failed: {e}")
            
            # Log security event
            await send_security_alert(
                title="SFTP Connection Failed",
                message=f"Failed to connect to bank {bank_code}: {str(e)}",
                severity="warning"
            )
            
            raise
    
    def _create_secure_transport(
        self,
        bank_config: BankConfiguration,
        credentials: Dict[str, str]
    ) -> paramiko.Transport:
        """Create secure transport with proper authentication."""
        transport = paramiko.Transport((bank_config.sftp_host, bank_config.sftp_port))
        
        # Set security options
        transport.set_keepalive(30)
        transport.use_compression(True)
        
        # Get authentication details
        username = credentials.get('sftp_username', bank_config.sftp_username)
        password = credentials.get('sftp_password')
        private_key_data = credentials.get('sftp_private_key')
        passphrase = credentials.get('sftp_passphrase')
        
        # Use key-based authentication if available
        if private_key_data:
            try:
                # Try different key types
                key = None
                for key_class in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey]:
                    try:
                        key = key_class.from_private_key(
                            io.StringIO(private_key_data),
                            password=passphrase
                        )
                        break
                    except:
                        continue
                
                if key:
                    transport.connect(username=username, pkey=key)
                    logger.info(f"Connected using key-based authentication")
                    return transport
            except Exception as e:
                logger.warning(f"Key authentication failed: {e}")
        
        # Fall back to password authentication
        if password:
            transport.connect(username=username, password=password)
            logger.info(f"Connected using password authentication")
            return transport
        
        raise ValueError("No valid authentication method available")
    
    def _is_connection_alive(self, pool_entry: Dict) -> bool:
        """Check if pooled connection is still alive."""
        try:
            # Check timeout
            if datetime.utcnow() - pool_entry['last_used'] > timedelta(seconds=self._connection_timeout):
                return False
            
            # Test connection
            pool_entry['sftp'].stat('.')
            pool_entry['last_used'] = datetime.utcnow()
            return True
        except:
            return False
    
    def _close_connection(self, pool_entry: Dict):
        """Close pooled connection."""
        try:
            pool_entry['sftp'].close()
            pool_entry['transport'].close()
        except:
            pass
    
    def cleanup_connections(self):
        """Clean up idle connections."""
        with self._pool_lock:
            expired_keys = []
            for key, entry in self._connection_pool.items():
                if not self._is_connection_alive(entry):
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._close_connection(self._connection_pool.pop(key))


class TransactionSigner:
    """Sign and verify banking transactions."""
    
    def __init__(self):
        self._signing_key = self._get_signing_key()
    
    def _get_signing_key(self) -> bytes:
        """Get transaction signing key."""
        key = get_secret_secure(
            "banking_transaction_signing_key",
            user_id=0,
            purpose="transaction_signing"
        )
        
        if not key:
            # Generate new signing key
            key = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
            from app.core.enhanced_secrets_manager import create_secret
            create_secret("banking_transaction_signing_key", key)
        
        return key.encode('utf-8')
    
    def sign_transaction(
        self,
        transaction: PaymentTransaction,
        user_id: int
    ) -> str:
        """
        Sign a transaction for integrity verification.
        
        Args:
            transaction: Transaction to sign
            user_id: User initiating transaction
            
        Returns:
            Transaction signature
        """
        # Create signing data
        signing_data = {
            'transaction_id': transaction.transaction_id,
            'customer_id': transaction.customer_id,
            'amount': str(transaction.amount),
            'account_number': transaction.account_number,
            'scheduled_date': transaction.scheduled_date.isoformat(),
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Create canonical string
        canonical = json.dumps(signing_data, sort_keys=True)
        
        # Generate signature
        signature = hashlib.pbkdf2_hmac(
            'sha256',
            canonical.encode('utf-8'),
            self._signing_key,
            100000  # iterations
        )
        
        return base64.urlsafe_b64encode(signature).decode('utf-8')
    
    def verify_transaction(
        self,
        transaction: PaymentTransaction,
        signature: str,
        user_id: int
    ) -> bool:
        """
        Verify transaction signature.
        
        Args:
            transaction: Transaction to verify
            signature: Signature to verify
            user_id: User who signed
            
        Returns:
            True if valid
        """
        try:
            # Recreate signature
            expected_signature = self.sign_transaction(transaction, user_id)
            
            # Compare signatures
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Transaction verification failed: {e}")
            return False


class SecureBankingService:
    """Enhanced banking service with security features."""
    
    def __init__(self, db: Session):
        self.db = db
        self.credential_store = SecureCredentialStore()
        self.sftp_manager = SecureSFTPManager(self.credential_store)
        self.transaction_signer = TransactionSigner()
        self._audit_buffer = []
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background thread for connection cleanup."""
        def cleanup_worker():
            while True:
                try:
                    self.sftp_manager.cleanup_connections()
                    self._flush_audit_buffer()
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
                time.sleep(60)  # Run every minute
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()
    
    async def create_secure_payment_batch(
        self,
        bank_code: str,
        processing_date: datetime,
        invoice_ids: List[int],
        created_by: int
    ) -> PaymentBatch:
        """
        Create payment batch with security measures.
        
        Args:
            bank_code: Bank code
            processing_date: Processing date
            invoice_ids: Invoice IDs to include
            created_by: User creating batch
            
        Returns:
            Created payment batch
        """
        try:
            # Verify user permissions
            if not await self._verify_user_permission(created_by, "create_payment_batch"):
                raise PermissionError("User not authorized to create payment batches")
            
            # Create batch (implementation from original service)
            batch = await self._create_batch_internal(
                bank_code, processing_date, invoice_ids
            )
            
            # Sign all transactions
            for transaction in batch.transactions:
                transaction.signature = self.transaction_signer.sign_transaction(
                    transaction, created_by
                )
            
            # Audit log
            self._log_banking_action(
                action="create_batch",
                batch_id=batch.id,
                user_id=created_by,
                details=f"Created batch {batch.batch_number} with {len(batch.transactions)} transactions"
            )
            
            self.db.commit()
            
            logger.info(f"Created secure payment batch {batch.batch_number}")
            return batch
            
        except Exception as e:
            logger.error(f"Failed to create secure payment batch: {e}")
            self.db.rollback()
            raise
    
    async def upload_payment_file_secure(
        self,
        batch_id: int,
        uploaded_by: int
    ) -> bool:
        """
        Upload payment file with secure SFTP.
        
        Args:
            batch_id: Batch ID
            uploaded_by: User uploading file
            
        Returns:
            True if successful
        """
        batch = self.db.query(PaymentBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        # Verify all transactions are signed
        for transaction in batch.transactions:
            if not transaction.signature:
                raise ValueError("All transactions must be signed before upload")
            
            if not self.transaction_signer.verify_transaction(
                transaction, transaction.signature, uploaded_by
            ):
                raise ValueError(f"Invalid signature for transaction {transaction.transaction_id}")
        
        # Get bank configuration
        bank_config = self.db.query(BankConfiguration).filter_by(
            bank_code=batch.bank_code,
            is_active=True
        ).first()
        
        if not bank_config:
            raise ValueError(f"No active configuration for bank {batch.bank_code}")
        
        try:
            # Generate file content
            file_content = self._generate_payment_file(batch, bank_config)
            
            # Calculate file hash
            file_hash = hashlib.sha256(file_content.encode()).hexdigest()
            
            # Upload via secure SFTP
            with self.sftp_manager.get_secure_sftp_client(bank_config, uploaded_by) as sftp:
                # Generate file name
                file_name = self._generate_file_name(
                    bank_config.payment_file_pattern,
                    batch.batch_number,
                    batch.processing_date
                )
                
                remote_path = os.path.join(bank_config.upload_path, file_name)
                
                # Upload with integrity check
                with sftp.file(remote_path, 'w') as remote_file:
                    remote_file.write(file_content)
                
                # Verify upload
                remote_stat = sftp.stat(remote_path)
                if remote_stat.st_size != len(file_content.encode()):
                    raise ValueError("File size mismatch after upload")
                
                # Set secure permissions
                sftp.chmod(remote_path, 0o400)  # Read-only for owner
            
            # Update batch
            batch.status = PaymentBatchStatus.UPLOADED
            batch.uploaded_at = datetime.utcnow()
            batch.uploaded_by = uploaded_by
            batch.file_hash = file_hash
            batch.sftp_upload_path = remote_path
            
            # Audit log
            self._log_banking_action(
                action="upload_file",
                batch_id=batch.id,
                user_id=uploaded_by,
                details=f"Uploaded file {file_name} with hash {file_hash[:8]}..."
            )
            
            self.db.commit()
            
            logger.info(f"Successfully uploaded secure payment file for batch {batch.id}")
            return True
            
        except Exception as e:
            logger.error(f"Secure upload failed: {e}")
            
            # Security alert
            await send_security_alert(
                title="Payment File Upload Failed",
                message=f"Failed to upload payment file for batch {batch.batch_number}: {str(e)}",
                severity="high"
            )
            
            self.db.rollback()
            return False
    
    def _log_banking_action(
        self,
        action: str,
        batch_id: Optional[int] = None,
        user_id: Optional[int] = None,
        details: Optional[str] = None
    ):
        """Log banking action for audit trail."""
        audit_entry = {
            'timestamp': datetime.utcnow(),
            'action': action,
            'batch_id': batch_id,
            'user_id': user_id,
            'details': details,
            'ip_address': self._get_client_ip(),
            'session_id': self._get_session_id()
        }
        
        self._audit_buffer.append(audit_entry)
        
        # Flush if buffer is large
        if len(self._audit_buffer) >= 50:
            self._flush_audit_buffer()
    
    def _flush_audit_buffer(self):
        """Flush audit buffer to database."""
        if not self._audit_buffer:
            return
        
        try:
            # Write to audit log table
            # Implementation depends on your audit model
            logger.info(f"Flushing {len(self._audit_buffer)} banking audit entries")
            self._audit_buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush audit buffer: {e}")
    
    async def _verify_user_permission(self, user_id: int, permission: str) -> bool:
        """Verify user has required permission."""
        # Implementation depends on your permission system
        # For now, return True for demonstration
        return True
    
    def _get_client_ip(self) -> Optional[str]:
        """Get client IP from request context."""
        # Implementation depends on your framework
        return None
    
    def _get_session_id(self) -> Optional[str]:
        """Get session ID from request context."""
        # Implementation depends on your framework
        return None
    
    # Additional methods would include all the original banking service methods
    # with enhanced security features...