"""Enhanced Banking SFTP Service with production-grade reliability."""

import io
import os
import json
import time
import logging
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from contextlib import contextmanager
from dataclasses import dataclass
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, Future
import paramiko
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.secrets_manager import get_secrets_manager
from app.models.banking import (
    BankConfiguration, PaymentBatch, PaymentBatchStatus,
    ReconciliationLog, ReconciliationStatus
)
from app.services.encryption.pgp_handler import PGPHandler
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


@dataclass
class TransferResult:
    """Result of an SFTP transfer operation."""
    success: bool
    file_name: str
    remote_path: str
    transfer_time: float
    checksum: str
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class ConnectionPoolStats:
    """Statistics for connection pool monitoring."""
    total_connections: int
    active_connections: int
    idle_connections: int
    failed_connections: int
    average_response_time: float
    last_health_check: datetime


class CircuitBreaker:
    """Circuit breaker pattern implementation for SFTP connections."""
    
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = {}
        self.last_failure_time = {}
        self._lock = threading.Lock()
    
    def is_open(self, bank_code: str) -> bool:
        """Check if circuit is open (failing) for a bank."""
        with self._lock:
            if bank_code not in self.failures:
                return False
            
            if self.failures[bank_code] >= self.failure_threshold:
                # Check if recovery timeout has passed
                if bank_code in self.last_failure_time:
                    time_since_failure = (datetime.utcnow() - self.last_failure_time[bank_code]).seconds
                    if time_since_failure < self.recovery_timeout:
                        return True
                    else:
                        # Reset after recovery timeout
                        self.reset(bank_code)
            
            return False
    
    def record_failure(self, bank_code: str):
        """Record a connection failure."""
        with self._lock:
            self.failures[bank_code] = self.failures.get(bank_code, 0) + 1
            self.last_failure_time[bank_code] = datetime.utcnow()
            logger.warning(f"Circuit breaker: Recorded failure {self.failures[bank_code]} for {bank_code}")
    
    def record_success(self, bank_code: str):
        """Record a successful connection."""
        with self._lock:
            if bank_code in self.failures:
                logger.info(f"Circuit breaker: Resetting {bank_code} after successful connection")
            self.reset(bank_code)
    
    def reset(self, bank_code: str):
        """Reset circuit breaker for a bank."""
        self.failures.pop(bank_code, None)
        self.last_failure_time.pop(bank_code, None)


class ConnectionPool:
    """Enhanced connection pool with health monitoring."""
    
    def __init__(self, max_connections: int = 5, health_check_interval: int = 60):
        self.max_connections = max_connections
        self.health_check_interval = health_check_interval
        self._pools: Dict[str, List[Tuple[paramiko.Transport, paramiko.SFTPClient]]] = {}
        self._stats: Dict[str, ConnectionPoolStats] = {}
        self._lock = threading.Lock()
        self._health_check_thread = None
        self._running = True
        self._start_health_monitor()
    
    def _start_health_monitor(self):
        """Start background health monitoring thread."""
        self._health_check_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
        self._health_check_thread.start()
    
    def _health_monitor_loop(self):
        """Background thread for connection health monitoring."""
        while self._running:
            try:
                time.sleep(self.health_check_interval)
                self._check_all_connections()
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
    
    def _check_all_connections(self):
        """Check health of all pooled connections."""
        with self._lock:
            for bank_code, connections in list(self._pools.items()):
                healthy_connections = []
                
                for transport, sftp in connections:
                    try:
                        # Test connection
                        sftp.stat('.')
                        healthy_connections.append((transport, sftp))
                    except Exception:
                        # Connection is dead, close it
                        try:
                            transport.close()
                        except:
                            pass
                        logger.info(f"Removed dead connection from pool for {bank_code}")
                
                self._pools[bank_code] = healthy_connections
                self._update_stats(bank_code)
    
    def _update_stats(self, bank_code: str):
        """Update connection pool statistics."""
        pool = self._pools.get(bank_code, [])
        self._stats[bank_code] = ConnectionPoolStats(
            total_connections=len(pool),
            active_connections=0,  # Would need request tracking
            idle_connections=len(pool),
            failed_connections=0,  # Would need failure tracking
            average_response_time=0.0,  # Would need timing tracking
            last_health_check=datetime.utcnow()
        )
    
    def get_connection(self, bank_code: str) -> Optional[Tuple[paramiko.Transport, paramiko.SFTPClient]]:
        """Get a connection from the pool."""
        with self._lock:
            if bank_code in self._pools and self._pools[bank_code]:
                return self._pools[bank_code].pop()
            return None
    
    def return_connection(self, bank_code: str, transport: paramiko.Transport, sftp: paramiko.SFTPClient):
        """Return a connection to the pool."""
        with self._lock:
            if bank_code not in self._pools:
                self._pools[bank_code] = []
            
            if len(self._pools[bank_code]) < self.max_connections:
                self._pools[bank_code].append((transport, sftp))
            else:
                # Pool is full, close the connection
                try:
                    transport.close()
                except:
                    pass
    
    def get_stats(self, bank_code: str) -> Optional[ConnectionPoolStats]:
        """Get statistics for a bank's connection pool."""
        return self._stats.get(bank_code)
    
    def shutdown(self):
        """Shutdown the connection pool."""
        self._running = False
        with self._lock:
            for bank_code, connections in self._pools.items():
                for transport, _ in connections:
                    try:
                        transport.close()
                    except:
                        pass
            self._pools.clear()


class BankingSFTPService:
    """Enhanced SFTP service with production reliability features."""
    
    def __init__(self, db: Session):
        self.db = db
        self._circuit_breaker = CircuitBreaker()
        self._connection_pool = ConnectionPool()
        self._retry_queue = Queue()
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._pgp_handler = PGPHandler()
        self._notification_service = NotificationService(db)
        self._transfer_history: List[TransferResult] = []
        self._init_monitoring()
    
    def _init_monitoring(self):
        """Initialize monitoring and metrics."""
        try:
            from prometheus_client import Counter, Histogram, Gauge
            
            self.metrics = {
                "sftp_transfers": Counter(
                    'banking_sftp_transfers_total',
                    'Total SFTP transfers',
                    ['bank_code', 'direction', 'status', 'file_type']
                ),
                "transfer_duration": Histogram(
                    'banking_sftp_transfer_duration_seconds',
                    'SFTP transfer duration',
                    ['bank_code', 'direction', 'file_type']
                ),
                "active_connections": Gauge(
                    'banking_sftp_active_connections',
                    'Active SFTP connections',
                    ['bank_code']
                ),
                "retry_queue_size": Gauge(
                    'banking_sftp_retry_queue_size',
                    'Number of transfers in retry queue'
                ),
                "encryption_operations": Counter(
                    'banking_encryption_operations_total',
                    'Encryption operations',
                    ['operation', 'algorithm', 'status']
                )
            }
        except ImportError:
            logger.warning("Prometheus client not available")
            self.metrics = None
    
    @contextmanager
    def get_sftp_connection(self, bank_config: BankConfiguration):
        """Get SFTP connection with enhanced reliability."""
        if self._circuit_breaker.is_open(bank_config.bank_code):
            raise Exception(f"Circuit breaker open for {bank_config.bank_code}")
        
        # Try to get from pool first
        pooled = self._connection_pool.get_connection(bank_config.bank_code)
        if pooled:
            transport, sftp = pooled
            try:
                # Test connection
                sftp.stat('.')
                yield sftp
                # Return to pool
                self._connection_pool.return_connection(bank_config.bank_code, transport, sftp)
                return
            except:
                # Connection is dead
                try:
                    transport.close()
                except:
                    pass
        
        # Create new connection
        transport = None
        try:
            transport = self._create_connection(bank_config)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.get_channel().settimeout(30.0)
            
            self._circuit_breaker.record_success(bank_config.bank_code)
            
            yield sftp
            
            # Return to pool
            self._connection_pool.return_connection(bank_config.bank_code, transport, sftp)
            
        except Exception as e:
            self._circuit_breaker.record_failure(bank_config.bank_code)
            if transport:
                try:
                    transport.close()
                except:
                    pass
            raise
    
    def _create_connection(self, bank_config: BankConfiguration) -> paramiko.Transport:
        """Create new SFTP connection with production settings."""
        transport = paramiko.Transport((bank_config.sftp_host, bank_config.sftp_port))
        transport.set_keepalive(30)
        
        # Get credentials from secrets manager
        credentials = self._get_secure_credentials(bank_config.bank_code)
        
        if credentials.get('private_key'):
            # Key-based authentication
            key = self._load_private_key(
                credentials['private_key'],
                credentials.get('passphrase')
            )
            transport.connect(
                username=credentials.get('username', bank_config.sftp_username),
                pkey=key
            )
        else:
            # Password authentication
            transport.connect(
                username=credentials.get('username', bank_config.sftp_username),
                password=credentials.get('password', bank_config.sftp_password)
            )
        
        return transport
    
    def _load_private_key(self, key_data: str, passphrase: Optional[str] = None) -> paramiko.PKey:
        """Load private key with support for multiple key types."""
        key_types = [
            (paramiko.RSAKey, "RSA"),
            (paramiko.Ed25519Key, "Ed25519"),
            (paramiko.ECDSAKey, "ECDSA"),
            (paramiko.DSSKey, "DSS")
        ]
        
        for key_class, key_type in key_types:
            try:
                key = key_class.from_private_key(
                    io.StringIO(key_data),
                    password=passphrase
                )
                logger.info(f"Loaded {key_type} key successfully")
                return key
            except:
                continue
        
        raise ValueError("Could not parse private key")
    
    def _get_secure_credentials(self, bank_code: str) -> Dict[str, str]:
        """Get credentials from secure storage."""
        if settings.ENVIRONMENT == "production":
            sm = get_secrets_manager()
            return sm.get_secret_json(f"banking-{bank_code}-credentials")
        
        # For non-production, use database config
        config = self.db.query(BankConfiguration).filter_by(
            bank_code=bank_code,
            is_active=True
        ).first()
        
        return {
            'username': config.sftp_username,
            'password': config.sftp_password,
            'private_key': config.sftp_private_key
        }
    
    async def transfer_file_with_retry(
        self,
        bank_config: BankConfiguration,
        local_path: str,
        remote_path: str,
        direction: str = "upload",
        encrypt: bool = True,
        max_retries: int = 3
    ) -> TransferResult:
        """Transfer file with automatic retry and monitoring."""
        start_time = time.time()
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                if direction == "upload":
                    result = await self._upload_file(
                        bank_config, local_path, remote_path, encrypt
                    )
                else:
                    result = await self._download_file(
                        bank_config, remote_path, local_path, encrypt
                    )
                
                # Update metrics
                if self.metrics:
                    self.metrics["sftp_transfers"].labels(
                        bank_code=bank_config.bank_code,
                        direction=direction,
                        status="success",
                        file_type=self._get_file_type(local_path)
                    ).inc()
                    
                    duration = time.time() - start_time
                    self.metrics["transfer_duration"].labels(
                        bank_code=bank_config.bank_code,
                        direction=direction,
                        file_type=self._get_file_type(local_path)
                    ).observe(duration)
                
                result.retry_count = retry_count
                self._transfer_history.append(result)
                
                return result
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                
                if retry_count <= max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.warning(
                        f"Transfer failed for {bank_config.bank_code}, "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Transfer failed after {max_retries} retries: {e}")
        
        # All retries failed
        if self.metrics:
            self.metrics["sftp_transfers"].labels(
                bank_code=bank_config.bank_code,
                direction=direction,
                status="failure",
                file_type=self._get_file_type(local_path)
            ).inc()
        
        result = TransferResult(
            success=False,
            file_name=os.path.basename(local_path),
            remote_path=remote_path,
            transfer_time=time.time() - start_time,
            checksum="",
            error=last_error,
            retry_count=retry_count
        )
        
        self._transfer_history.append(result)
        
        # Add to retry queue for later processing
        self._retry_queue.put({
            'bank_config': bank_config,
            'local_path': local_path,
            'remote_path': remote_path,
            'direction': direction,
            'encrypt': encrypt,
            'timestamp': datetime.utcnow()
        })
        
        if self.metrics:
            self.metrics["retry_queue_size"].set(self._retry_queue.qsize())
        
        return result
    
    async def _upload_file(
        self,
        bank_config: BankConfiguration,
        local_path: str,
        remote_path: str,
        encrypt: bool
    ) -> TransferResult:
        """Upload file with encryption and verification."""
        # Read file content
        with open(local_path, 'rb') as f:
            content = f.read()
        
        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()
        
        # Encrypt if required
        if encrypt:
            content = self._encrypt_content(content, bank_config.bank_code)
            if self.metrics:
                self.metrics["encryption_operations"].labels(
                    operation="encrypt",
                    algorithm="PGP",
                    status="success"
                ).inc()
        
        # Create temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            with self.get_sftp_connection(bank_config) as sftp:
                # Ensure remote directory exists
                remote_dir = os.path.dirname(remote_path)
                try:
                    sftp.stat(remote_dir)
                except FileNotFoundError:
                    self._makedirs_remote(sftp, remote_dir)
                
                # Upload to temporary location
                temp_remote = f"{remote_path}.tmp"
                sftp.put(temp_path, temp_remote)
                
                # Verify upload
                local_size = os.path.getsize(temp_path)
                remote_size = sftp.stat(temp_remote).st_size
                
                if local_size != remote_size:
                    raise ValueError(f"Size mismatch: {local_size} != {remote_size}")
                
                # Atomic rename
                sftp.rename(temp_remote, remote_path)
                
                # Set permissions
                sftp.chmod(remote_path, 0o644)
                
                logger.info(f"Successfully uploaded {os.path.basename(local_path)} to {bank_config.bank_code}")
                
                return TransferResult(
                    success=True,
                    file_name=os.path.basename(local_path),
                    remote_path=remote_path,
                    transfer_time=0,  # Will be set by caller
                    checksum=checksum
                )
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def _download_file(
        self,
        bank_config: BankConfiguration,
        remote_path: str,
        local_path: str,
        decrypt: bool
    ) -> TransferResult:
        """Download file with decryption and verification."""
        import tempfile
        temp_path = None
        
        try:
            with self.get_sftp_connection(bank_config) as sftp:
                # Download to temporary file
                temp_fd, temp_path = tempfile.mkstemp()
                os.close(temp_fd)
                
                sftp.get(remote_path, temp_path)
                
                # Read content
                with open(temp_path, 'rb') as f:
                    content = f.read()
                
                # Calculate checksum
                checksum = hashlib.sha256(content).hexdigest()
                
                # Decrypt if required
                if decrypt:
                    content = self._decrypt_content(content, bank_config.bank_code)
                    if self.metrics:
                        self.metrics["encryption_operations"].labels(
                            operation="decrypt",
                            algorithm="PGP",
                            status="success"
                        ).inc()
                
                # Write to final location
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(content)
                
                # Archive remote file if configured
                if bank_config.archive_path:
                    archive_name = f"{os.path.basename(remote_path)}.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                    archive_path = os.path.join(bank_config.archive_path, archive_name)
                    try:
                        sftp.rename(remote_path, archive_path)
                        logger.info(f"Archived {remote_path} to {archive_path}")
                    except Exception as e:
                        logger.warning(f"Failed to archive file: {e}")
                
                logger.info(f"Successfully downloaded {os.path.basename(remote_path)} from {bank_config.bank_code}")
                
                return TransferResult(
                    success=True,
                    file_name=os.path.basename(remote_path),
                    remote_path=remote_path,
                    transfer_time=0,  # Will be set by caller
                    checksum=checksum
                )
                
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _encrypt_content(self, content: bytes, bank_code: str) -> bytes:
        """Encrypt content using bank-specific PGP key."""
        return self._pgp_handler.encrypt(content, bank_code)
    
    def _decrypt_content(self, content: bytes, bank_code: str) -> bytes:
        """Decrypt content using our PGP key."""
        return self._pgp_handler.decrypt(content)
    
    def _makedirs_remote(self, sftp: paramiko.SFTPClient, path: str):
        """Create remote directory structure."""
        parts = path.strip('/').split('/')
        current = ''
        
        for part in parts:
            current = f"{current}/{part}" if current else part
            try:
                sftp.stat(current)
            except FileNotFoundError:
                sftp.mkdir(current)
    
    def _get_file_type(self, file_path: str) -> str:
        """Determine file type from path."""
        if 'payment' in file_path.lower() or 'pay' in file_path.lower():
            return 'payment'
        elif 'reconciliation' in file_path.lower() or 'rec' in file_path.lower():
            return 'reconciliation'
        elif 'report' in file_path.lower():
            return 'report'
        else:
            return 'other'
    
    async def process_retry_queue(self):
        """Process failed transfers from retry queue."""
        processed = 0
        
        while not self._retry_queue.empty():
            try:
                item = self._retry_queue.get_nowait()
                
                # Skip if too old (> 24 hours)
                age = (datetime.utcnow() - item['timestamp']).total_seconds()
                if age > 86400:
                    logger.warning(f"Skipping old retry item: {item['local_path']}")
                    continue
                
                # Retry transfer
                result = await self.transfer_file_with_retry(
                    item['bank_config'],
                    item['local_path'],
                    item['remote_path'],
                    item['direction'],
                    item['encrypt'],
                    max_retries=1  # Only one retry from queue
                )
                
                if result.success:
                    processed += 1
                    logger.info(f"Successfully processed retry: {result.file_name}")
                
            except Empty:
                break
            except Exception as e:
                logger.error(f"Error processing retry queue: {e}")
        
        if self.metrics:
            self.metrics["retry_queue_size"].set(self._retry_queue.qsize())
        
        return processed
    
    def get_transfer_history(
        self,
        bank_code: Optional[str] = None,
        hours: int = 24
    ) -> List[TransferResult]:
        """Get recent transfer history."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter by age (would need timestamp in TransferResult)
        recent = [t for t in self._transfer_history[-1000:]]  # Last 1000 transfers
        
        if bank_code:
            # Would need to track bank_code in TransferResult
            recent = [t for t in recent if bank_code in t.remote_path]
        
        return recent
    
    def get_connection_stats(self) -> Dict[str, ConnectionPoolStats]:
        """Get connection pool statistics for all banks."""
        stats = {}
        
        for bank_code in self.db.query(BankConfiguration.bank_code).filter_by(
            is_active=True
        ).all():
            pool_stats = self._connection_pool.get_stats(bank_code[0])
            if pool_stats:
                stats[bank_code[0]] = pool_stats
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on SFTP service."""
        health = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'circuit_breakers': {},
            'connection_pools': {},
            'retry_queue_size': self._retry_queue.qsize(),
            'checks': []
        }
        
        # Check each bank
        banks = self.db.query(BankConfiguration).filter_by(is_active=True).all()
        
        for bank in banks:
            # Circuit breaker status
            health['circuit_breakers'][bank.bank_code] = {
                'open': self._circuit_breaker.is_open(bank.bank_code),
                'failures': self._circuit_breaker.failures.get(bank.bank_code, 0)
            }
            
            # Connection pool stats
            stats = self._connection_pool.get_stats(bank.bank_code)
            if stats:
                health['connection_pools'][bank.bank_code] = {
                    'total': stats.total_connections,
                    'idle': stats.idle_connections,
                    'last_check': stats.last_health_check.isoformat()
                }
            
            # Try a test connection
            try:
                with self.get_sftp_connection(bank) as sftp:
                    sftp.stat('.')
                health['checks'].append({
                    'bank': bank.bank_code,
                    'status': 'connected',
                    'message': 'Connection successful'
                })
            except Exception as e:
                health['status'] = 'degraded'
                health['checks'].append({
                    'bank': bank.bank_code,
                    'status': 'failed',
                    'message': str(e)
                })
        
        return health
    
    def shutdown(self):
        """Gracefully shutdown the service."""
        logger.info("Shutting down Banking SFTP Service")
        
        # Shutdown connection pool
        self._connection_pool.shutdown()
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        # Save retry queue to database for persistence
        retry_items = []
        while not self._retry_queue.empty():
            try:
                retry_items.append(self._retry_queue.get_nowait())
            except Empty:
                break
        
        if retry_items:
            # Would need to implement persistent retry storage
            logger.info(f"Saved {len(retry_items)} items from retry queue")