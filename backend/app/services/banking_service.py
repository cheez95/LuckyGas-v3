"""Banking service for payment processing and reconciliation with production SFTP support."""

import io
import os
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from decimal import Decimal
import paramiko
from sqlalchemy.orm import Session
from sqlalchemy import func
import csv
from contextlib import contextmanager
import time
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
import json

from app.models.banking import (
    PaymentBatch, PaymentTransaction, ReconciliationLog, BankConfiguration,
    PaymentBatchStatus, ReconciliationStatus, TransactionStatus
)
from app.models.invoice import Invoice, InvoicePaymentStatus
from app.models.customer import Customer
from app.core.config import settings
from app.core.secrets_manager import get_secrets_manager

logger = logging.getLogger(__name__)


class BankingFormatError(Exception):
    """Raised when there's an error in banking file format."""
    pass


class SFTPConnectionError(Exception):
    """Raised when SFTP connection fails."""
    pass


class BankingService:
    """Service for handling banking operations including SFTP file exchange."""
    
    def __init__(self, db: Session):
        self.db = db
        self._sftp_clients = {}
        self._circuit_breaker_states = {}
        self._connection_pool = {}
        self._pool_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._init_metrics()
        self._load_production_credentials()
        
    def _init_metrics(self):
        """Initialize Prometheus metrics for monitoring"""
        try:
            from prometheus_client import Counter, Histogram, Gauge
            
            self.metrics = {
                "sftp_connections": Gauge(
                    'banking_sftp_connections',
                    'Active SFTP connections',
                    ['bank_code']
                ),
                "sftp_failures": Counter(
                    'banking_sftp_failures_total',
                    'SFTP connection failures',
                    ['bank_code', 'error_type']
                ),
                "file_transfers": Counter(
                    'banking_file_transfers_total',
                    'File transfer operations',
                    ['bank_code', 'direction', 'status']
                ),
                "transfer_duration": Histogram(
                    'banking_transfer_duration_seconds',
                    'File transfer duration',
                    ['bank_code', 'direction']
                ),
                "reconciliation_accuracy": Gauge(
                    'banking_reconciliation_accuracy',
                    'Reconciliation match rate',
                    ['bank_code']
                )
            }
        except ImportError:
            logger.warning("Prometheus client not available, metrics disabled")
            self.metrics = None
    
    def _load_production_credentials(self):
        """Load bank credentials from Secret Manager"""
        if settings.ENVIRONMENT != "production":
            return
            
        try:
            sm = get_secrets_manager()
            
            # Load bank-specific credentials
            banks = ["mega", "ctbc", "esun", "first", "taishin"]
            for bank in banks:
                credentials = sm.get_secret_json(f"banking-{bank}-credentials")
                if credentials:
                    # Store in secure memory (not logged)
                    self._store_credentials(bank, credentials)
                    logger.info(f"Loaded credentials for {bank} from Secret Manager")
                    
        except Exception as e:
            logger.error(f"Failed to load banking credentials: {e}")
    
    def _store_credentials(self, bank_code: str, credentials: Dict[str, Any]):
        """Securely store bank credentials in memory"""
        # Create secure storage if not exists
        if not hasattr(self, '_secure_credentials'):
            self._secure_credentials = {}
            
        self._secure_credentials[bank_code] = {
            'username': credentials.get('sftp_username'),
            'password': credentials.get('sftp_password'),
            'private_key': credentials.get('sftp_private_key'),
            'passphrase': credentials.get('sftp_passphrase'),
            'api_key': credentials.get('api_key'),
            'api_secret': credentials.get('api_secret')
        }
    
    def _get_credentials(self, bank_code: str) -> Dict[str, Any]:
        """Get bank credentials from secure storage"""
        if hasattr(self, '_secure_credentials') and bank_code in self._secure_credentials:
            return self._secure_credentials[bank_code]
        return {}
        
    @contextmanager
    def get_sftp_client(self, bank_config: BankConfiguration):
        """
        Get SFTP client with connection pooling and circuit breaker.
        
        Args:
            bank_config: Bank configuration with SFTP details
            
        Yields:
            paramiko.SFTPClient: Connected SFTP client
            
        Raises:
            SFTPConnectionError: If connection fails
        """
        bank_code = bank_config.bank_code
        
        # Check circuit breaker
        if self._is_circuit_open(bank_code):
            raise SFTPConnectionError(f"Circuit breaker open for {bank_code}")
        
        try:
            # Try to get from connection pool
            with self._pool_lock:
                if bank_code in self._connection_pool:
                    pool = self._connection_pool[bank_code]
                    if pool and len(pool) > 0:
                        transport, sftp = pool.pop()
                        # Test if connection is still alive
                        try:
                            sftp.stat('.')
                            if self.metrics:
                                self.metrics["sftp_connections"].labels(bank_code=bank_code).inc()
                            yield sftp
                            # Return to pool
                            with self._pool_lock:
                                pool.append((transport, sftp))
                            return
                        except:
                            # Connection dead, close it
                            try:
                                transport.close()
                            except:
                                pass
            
            # Create new connection with production settings
            transport = paramiko.Transport((bank_config.sftp_host, bank_config.sftp_port))
            transport.set_keepalive(30)  # Send keepalive every 30 seconds
            
            # Get production credentials
            creds = self._get_credentials(bank_config.bank_code)
            username = creds.get('username') or bank_config.sftp_username
            password = creds.get('password') or bank_config.sftp_password
            private_key_data = creds.get('private_key') or bank_config.sftp_private_key
            
            # Use password or private key authentication
            if private_key_data:
                # Key-based authentication (preferred for production)
                try:
                    # Try different key types
                    key = None
                    key_types = [
                        (paramiko.RSAKey, "RSA"),
                        (paramiko.Ed25519Key, "Ed25519"),
                        (paramiko.ECDSAKey, "ECDSA")
                    ]
                    
                    for key_class, key_type in key_types:
                        try:
                            key = key_class.from_private_key(
                                io.StringIO(private_key_data),
                                password=creds.get('passphrase')
                            )
                            logger.info(f"Using {key_type} key for {bank_code}")
                            break
                        except:
                            continue
                    
                    if not key:
                        raise ValueError("Could not parse private key")
                        
                    transport.connect(username=username, pkey=key)
                except Exception as e:
                    logger.error(f"Key authentication failed for {bank_code}: {e}")
                    raise
            else:
                # Password authentication (fallback)
                transport.connect(username=username, password=password)
            
            # Configure SFTP client
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.get_channel().settimeout(30.0)  # 30 second timeout
            
            # Add to connection pool
            with self._pool_lock:
                if bank_code not in self._connection_pool:
                    self._connection_pool[bank_code] = []
                # Keep max 5 connections per bank
                if len(self._connection_pool[bank_code]) < 5:
                    self._connection_pool[bank_code].append((transport, sftp))
            
            # Reset circuit breaker on successful connection
            self._reset_circuit_breaker(bank_code)
            
            # Update metrics
            if self.metrics:
                self.metrics["sftp_connections"].labels(bank_code=bank_code).inc()
            
            logger.info(f"Established SFTP connection to {bank_code}")
            
            yield sftp
            
        except Exception as e:
            logger.error(f"SFTP connection failed for {bank_code}: {str(e)}")
            self._record_circuit_failure(bank_code)
            
            # Update failure metrics
            if self.metrics:
                error_type = type(e).__name__
                self.metrics["sftp_failures"].labels(
                    bank_code=bank_code,
                    error_type=error_type
                ).inc()
                
            raise SFTPConnectionError(f"Failed to connect to {bank_code}: {str(e)}")
    
    def _is_circuit_open(self, bank_code: str) -> bool:
        """Check if circuit breaker is open for a bank."""
        if bank_code not in self._circuit_breaker_states:
            return False
        
        state = self._circuit_breaker_states[bank_code]
        if state['failures'] >= 3:
            # Check if cooldown period has passed (5 minutes)
            if datetime.utcnow() - state['last_failure'] < timedelta(minutes=5):
                return True
            else:
                # Reset after cooldown
                self._reset_circuit_breaker(bank_code)
        
        return False
    
    def _record_circuit_failure(self, bank_code: str):
        """Record a failure for circuit breaker."""
        if bank_code not in self._circuit_breaker_states:
            self._circuit_breaker_states[bank_code] = {'failures': 0, 'last_failure': None}
        
        self._circuit_breaker_states[bank_code]['failures'] += 1
        self._circuit_breaker_states[bank_code]['last_failure'] = datetime.utcnow()
    
    def _reset_circuit_breaker(self, bank_code: str):
        """Reset circuit breaker for a bank."""
        self._circuit_breaker_states[bank_code] = {'failures': 0, 'last_failure': None}
    
    def generate_payment_file(self, batch_id: int) -> str:
        """
        Generate payment collection file for a batch.
        
        Args:
            batch_id: Payment batch ID
            
        Returns:
            str: Generated file content
            
        Raises:
            BankingFormatError: If file generation fails
        """
        batch = self.db.query(PaymentBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Payment batch {batch_id} not found")
        
        bank_config = self.db.query(BankConfiguration).filter_by(
            bank_code=batch.bank_code,
            is_active=True
        ).first()
        
        if not bank_config:
            raise ValueError(f"No active configuration for bank {batch.bank_code}")
        
        if bank_config.file_format == 'fixed_width':
            return self._generate_fixed_width_file(batch, bank_config)
        elif bank_config.file_format == 'csv':
            return self._generate_csv_file(batch, bank_config)
        else:
            raise BankingFormatError(f"Unsupported file format: {bank_config.file_format}")
    
    def _generate_fixed_width_file(self, batch: PaymentBatch, bank_config: BankConfiguration) -> str:
        """Generate fixed-width format payment file (Taiwan banking standard)."""
        lines = []
        
        # Header record
        header = self._format_fixed_width([
            ('H', 1),  # Record type
            (batch.batch_number, 20),  # Batch number
            (datetime.now().strftime('%Y%m%d'), 8),  # File date
            (bank_config.bank_code, 3),  # Bank code
            ('001', 3),  # Version
            ('', 174),  # Filler
        ])
        lines.append(header)
        
        # Detail records
        total_amount = Decimal('0')
        for idx, transaction in enumerate(batch.transactions, 1):
            detail = self._format_fixed_width([
                ('D', 1),  # Record type
                (str(idx).zfill(6), 6),  # Sequence number
                (transaction.transaction_id, 20),  # Transaction ID
                (transaction.account_number, 14),  # Bank account
                (transaction.account_holder[:30], 30),  # Account holder name
                (self._format_amount(transaction.amount), 13),  # Amount (no decimals)
                (transaction.scheduled_date.strftime('%Y%m%d'), 8),  # Payment date
                ('', 108),  # Filler
            ])
            lines.append(detail)
            total_amount += transaction.amount
        
        # Trailer record
        trailer = self._format_fixed_width([
            ('T', 1),  # Record type
            (str(len(batch.transactions)).zfill(6), 6),  # Total count
            (self._format_amount(total_amount), 15),  # Total amount
            ('', 178),  # Filler
        ])
        lines.append(trailer)
        
        # Join with appropriate line ending for Taiwan banks
        content = '\r\n'.join(lines)
        
        # Handle encoding
        if bank_config.encoding.upper() == 'BIG5':
            content = content.encode('big5', errors='replace').decode('big5')
        
        return content
    
    def _generate_csv_file(self, batch: PaymentBatch, bank_config: BankConfiguration) -> str:
        """Generate CSV format payment file."""
        output = io.StringIO()
        
        # Define CSV headers based on Taiwan banking standards
        headers = [
            '交易序號',  # Transaction sequence
            '扣款帳號',  # Debit account
            '戶名',      # Account holder
            '扣款金額',  # Amount
            '扣款日期',  # Debit date
            '備註'       # Remarks
        ]
        
        writer = csv.DictWriter(
            output, 
            fieldnames=headers,
            delimiter=bank_config.delimiter or ','
        )
        writer.writeheader()
        
        for idx, transaction in enumerate(batch.transactions, 1):
            writer.writerow({
                '交易序號': str(idx).zfill(6),
                '扣款帳號': transaction.account_number,
                '戶名': transaction.account_holder,
                '扣款金額': str(transaction.amount),
                '扣款日期': transaction.scheduled_date.strftime('%Y/%m/%d'),
                '備註': f'Invoice: {transaction.invoice_id}' if transaction.invoice_id else ''
            })
        
        content = output.getvalue()
        
        # Handle encoding
        if bank_config.encoding.upper() == 'BIG5':
            content = content.encode('big5', errors='replace').decode('big5')
        
        return content
    
    def _format_fixed_width(self, fields: List[Tuple[str, int]]) -> str:
        """Format fields into fixed-width string."""
        result = ''
        for value, width in fields:
            # Convert to string and handle encoding
            str_value = str(value)
            # Pad or truncate to fit width
            if len(str_value) > width:
                result += str_value[:width]
            else:
                result += str_value.ljust(width)
        return result
    
    def _format_amount(self, amount: Decimal) -> str:
        """Format amount for banking files (no decimals, in cents)."""
        cents = int(amount * 100)
        return str(cents).zfill(13)
    
    def upload_payment_file(self, batch_id: int) -> bool:
        """
        Upload payment file to bank via SFTP with production reliability.
        
        Args:
            batch_id: Payment batch ID
            
        Returns:
            bool: True if successful
        """
        batch = self.db.query(PaymentBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Payment batch {batch_id} not found")
        
        if batch.status != PaymentBatchStatus.GENERATED:
            raise ValueError(f"Batch {batch_id} is not in GENERATED status")
        
        bank_config = self.db.query(BankConfiguration).filter_by(
            bank_code=batch.bank_code,
            is_active=True
        ).first()
        
        if not bank_config:
            raise ValueError(f"No active configuration for bank {batch.bank_code}")
        
        start_time = time.time()
        temp_file = None
        
        try:
            # Generate file name from pattern
            file_name = self._generate_file_name(
                bank_config.payment_file_pattern,
                batch.batch_number,
                batch.processing_date
            )
            
            # Get file content
            if not batch.file_content:
                batch.file_content = self.generate_payment_file(batch_id)
            
            # Calculate checksum for verification
            content_bytes = batch.file_content.encode(bank_config.encoding or 'UTF-8')
            checksum = hashlib.sha256(content_bytes).hexdigest()
            
            # Create temporary file for atomic upload
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.write(content_bytes)
            temp_file.close()
            
            # Upload via SFTP with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with self.get_sftp_client(bank_config) as sftp:
                        # Create remote paths
                        remote_path = os.path.join(bank_config.upload_path, file_name)
                        temp_remote_path = f"{remote_path}.tmp"
                        
                        # Ensure remote directory exists
                        try:
                            sftp.stat(bank_config.upload_path)
                        except FileNotFoundError:
                            # Create directory if it doesn't exist
                            sftp.makedirs(bank_config.upload_path)
                        
                        # Upload to temporary location first
                        sftp.put(temp_file.name, temp_remote_path)
                        
                        # Verify file size
                        local_size = os.path.getsize(temp_file.name)
                        remote_size = sftp.stat(temp_remote_path).st_size
                        
                        if local_size != remote_size:
                            raise ValueError(f"File size mismatch: local={local_size}, remote={remote_size}")
                        
                        # Atomic rename to final location
                        sftp.rename(temp_remote_path, remote_path)
                        
                        # Set file permissions (read-only for security)
                        sftp.chmod(remote_path, 0o444)
                        
                        logger.info(f"Successfully uploaded payment file {file_name} to {bank_config.bank_code}")
                        
                        # Update batch status
                        batch.status = PaymentBatchStatus.UPLOADED
                        batch.uploaded_at = datetime.utcnow()
                        batch.sftp_upload_path = remote_path
                        batch.file_name = file_name
                        batch.file_checksum = checksum
                        
                        # Update metrics
                        duration = time.time() - start_time
                        if self.metrics:
                            self.metrics["file_transfers"].labels(
                                bank_code=bank_config.bank_code,
                                direction="upload",
                                status="success"
                            ).inc()
                            self.metrics["transfer_duration"].labels(
                                bank_code=bank_config.bank_code,
                                direction="upload"
                            ).observe(duration)
                        
                        self.db.commit()
                        return True
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Upload attempt {attempt + 1} failed, retrying: {e}")
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise
                        
        except Exception as e:
            logger.error(f"Failed to upload payment file: {str(e)}")
            batch.status = PaymentBatchStatus.FAILED
            batch.error_message = str(e)
            batch.retry_count += 1
            
            # Update failure metrics
            if self.metrics:
                self.metrics["file_transfers"].labels(
                    bank_code=bank_config.bank_code,
                    direction="upload",
                    status="failure"
                ).inc()
                
            self.db.commit()
            return False
            
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    def check_reconciliation_files(self, bank_code: str) -> List[str]:
        """
        Check for new reconciliation files from bank.
        
        Args:
            bank_code: Bank code to check
            
        Returns:
            List[str]: List of new reconciliation file names
        """
        bank_config = self.db.query(BankConfiguration).filter_by(
            bank_code=bank_code,
            is_active=True
        ).first()
        
        if not bank_config:
            raise ValueError(f"No active configuration for bank {bank_code}")
        
        new_files = []
        
        try:
            with self.get_sftp_client(bank_config) as sftp:
                # List files in download directory
                files = sftp.listdir(bank_config.download_path)
                
                # Filter reconciliation files based on pattern
                pattern = self._compile_file_pattern(bank_config.reconciliation_file_pattern)
                
                for file_name in files:
                    if pattern.match(file_name):
                        # Check if already processed
                        existing = self.db.query(ReconciliationLog).filter_by(
                            file_name=file_name
                        ).first()
                        
                        if not existing:
                            new_files.append(file_name)
                
                logger.info(f"Found {len(new_files)} new reconciliation files for {bank_code}")
                
        except Exception as e:
            logger.error(f"Failed to check reconciliation files: {str(e)}")
            raise
        
        return new_files
    
    def process_reconciliation_file(self, bank_code: str, file_name: str) -> ReconciliationLog:
        """
        Download and process a reconciliation file.
        
        Args:
            bank_code: Bank code
            file_name: File name to process
            
        Returns:
            ReconciliationLog: Processing result
        """
        bank_config = self.db.query(BankConfiguration).filter_by(
            bank_code=bank_code,
            is_active=True
        ).first()
        
        if not bank_config:
            raise ValueError(f"No active configuration for bank {bank_code}")
        
        # Create reconciliation log
        log = ReconciliationLog(
            file_name=file_name,
            file_received_at=datetime.utcnow(),
            status=ReconciliationStatus.PENDING
        )
        
        try:
            # Download file
            with self.get_sftp_client(bank_config) as sftp:
                remote_path = os.path.join(bank_config.download_path, file_name)
                
                # Download to memory
                file_obj = io.BytesIO()
                sftp.getfo(remote_path, file_obj)
                file_obj.seek(0)
                
                # Decode content
                content = file_obj.read().decode(bank_config.encoding or 'UTF-8')
                log.file_content = content
                
                # Move to archive if configured
                if bank_config.archive_path:
                    archive_path = os.path.join(bank_config.archive_path, file_name)
                    sftp.rename(remote_path, archive_path)
            
            # Parse and process the file
            if bank_config.file_format == 'fixed_width':
                results = self._process_fixed_width_reconciliation(content, bank_config)
            elif bank_config.file_format == 'csv':
                results = self._process_csv_reconciliation(content, bank_config)
            else:
                raise BankingFormatError(f"Unsupported file format: {bank_config.file_format}")
            
            # Update transactions based on results
            matched = 0
            failed = 0
            
            for result in results:
                transaction = self.db.query(PaymentTransaction).filter_by(
                    transaction_id=result['transaction_id']
                ).first()
                
                if transaction:
                    transaction.bank_reference = result.get('bank_reference')
                    transaction.bank_response_code = result.get('response_code')
                    transaction.bank_response_message = result.get('response_message')
                    transaction.processed_date = result.get('processed_date')
                    
                    if result['success']:
                        transaction.status = TransactionStatus.SUCCESS
                        matched += 1
                        
                        # Update related invoice if exists
                        if transaction.invoice_id:
                            invoice = self.db.query(Invoice).filter_by(
                                id=transaction.invoice_id
                            ).first()
                            if invoice:
                                invoice.payment_status = InvoicePaymentStatus.PAID
                                invoice.paid_at = transaction.processed_date
                    else:
                        transaction.status = TransactionStatus.FAILED
                        failed += 1
                else:
                    logger.warning(f"Transaction {result['transaction_id']} not found")
            
            # Update log statistics
            log.total_records = len(results)
            log.matched_records = matched
            log.failed_records = failed
            log.unmatched_records = log.total_records - matched - failed
            log.status = ReconciliationStatus.MATCHED if log.unmatched_records == 0 else ReconciliationStatus.UNMATCHED
            log.processed_at = datetime.utcnow()
            
            # Find and update related batch
            if results:
                # Get batch from first transaction
                first_transaction = self.db.query(PaymentTransaction).filter_by(
                    transaction_id=results[0]['transaction_id']
                ).first()
                
                if first_transaction:
                    batch = first_transaction.batch
                    batch.status = PaymentBatchStatus.RECONCILED
                    batch.reconciled_at = datetime.utcnow()
                    batch.reconciliation_file_name = file_name
                    log.batch_id = batch.id
            
            self.db.add(log)
            self.db.commit()
            
            logger.info(f"Processed reconciliation file {file_name}: "
                       f"{matched} matched, {failed} failed, {log.unmatched_records} unmatched")
            
            return log
            
        except Exception as e:
            logger.error(f"Failed to process reconciliation file: {str(e)}")
            log.status = ReconciliationStatus.FAILED
            log.error_details = str(e)
            self.db.add(log)
            self.db.commit()
            raise
    
    def _process_fixed_width_reconciliation(self, content: str, bank_config: BankConfiguration) -> List[Dict]:
        """Parse fixed-width reconciliation file."""
        results = []
        lines = content.strip().split('\n')
        
        for line in lines:
            if not line or line[0] == 'H' or line[0] == 'T':  # Skip header/trailer
                continue
            
            if line[0] == 'D':  # Detail record
                result = {
                    'transaction_id': line[7:27].strip(),
                    'bank_reference': line[27:47].strip(),
                    'response_code': line[47:50].strip(),
                    'response_message': line[50:150].strip(),
                    'processed_date': datetime.strptime(line[150:158], '%Y%m%d'),
                    'success': line[47:50].strip() == '000'  # Success code
                }
                results.append(result)
        
        return results
    
    def _process_csv_reconciliation(self, content: str, bank_config: BankConfiguration) -> List[Dict]:
        """Parse CSV reconciliation file."""
        results = []
        
        reader = csv.DictReader(
            io.StringIO(content),
            delimiter=bank_config.delimiter or ','
        )
        
        for row in reader:
            result = {
                'transaction_id': row.get('交易序號', '').strip(),
                'bank_reference': row.get('銀行參考號', '').strip(),
                'response_code': row.get('回應代碼', '').strip(),
                'response_message': row.get('回應訊息', '').strip(),
                'processed_date': datetime.strptime(row.get('處理日期', ''), '%Y/%m/%d'),
                'success': row.get('回應代碼', '').strip() == '000'
            }
            results.append(result)
        
        return results
    
    def _generate_file_name(self, pattern: str, batch_number: str, date: datetime) -> str:
        """Generate file name from pattern."""
        replacements = {
            '{YYYY}': date.strftime('%Y'),
            '{MM}': date.strftime('%m'),
            '{DD}': date.strftime('%d'),
            '{YYYYMMDD}': date.strftime('%Y%m%d'),
            '{BATCH}': batch_number,
            '{TIMESTAMP}': str(int(time.time()))
        }
        
        file_name = pattern
        for key, value in replacements.items():
            file_name = file_name.replace(key, value)
        
        return file_name
    
    def _compile_file_pattern(self, pattern: str) -> re.Pattern:
        """Compile file name pattern to regex."""
        # Escape special regex characters except our placeholders
        pattern = re.escape(pattern)
        
        # Replace placeholders with regex patterns
        replacements = {
            r'\{YYYY\}': r'\d{4}',
            r'\{MM\}': r'\d{2}',
            r'\{DD\}': r'\d{2}',
            r'\{YYYYMMDD\}': r'\d{8}',
            r'\{BATCH\}': r'[A-Z0-9]+',
            r'\{TIMESTAMP\}': r'\d+'
        }
        
        for placeholder, regex in replacements.items():
            pattern = pattern.replace(placeholder, regex)
        
        return re.compile(pattern)
    
    def create_payment_batch(
        self,
        bank_code: str,
        processing_date: datetime,
        invoice_ids: Optional[List[int]] = None
    ) -> PaymentBatch:
        """
        Create a new payment batch for processing.
        
        Args:
            bank_code: Bank code for processing
            processing_date: Date to process payments
            invoice_ids: Optional list of specific invoice IDs to include
            
        Returns:
            PaymentBatch: Created batch
        """
        # Generate batch number
        batch_count = self.db.query(func.count(PaymentBatch.id)).filter(
            PaymentBatch.processing_date == processing_date,
            PaymentBatch.bank_code == bank_code
        ).scalar()
        
        batch_number = f"{bank_code}{processing_date.strftime('%Y%m%d')}{str(batch_count + 1).zfill(3)}"
        
        # Create batch
        batch = PaymentBatch(
            batch_number=batch_number,
            bank_code=bank_code,
            processing_date=processing_date,
            status=PaymentBatchStatus.DRAFT,
            file_format=self.db.query(BankConfiguration.file_format).filter_by(
                bank_code=bank_code
            ).scalar()
        )
        
        self.db.add(batch)
        self.db.flush()
        
        # Query invoices for payment
        query = self.db.query(Invoice).join(Customer).filter(
            Invoice.payment_status == InvoicePaymentStatus.PENDING,
            Customer.payment_method == 'bank_transfer',
            Customer.bank_code == bank_code
        )
        
        if invoice_ids:
            query = query.filter(Invoice.id.in_(invoice_ids))
        
        invoices = query.all()
        
        # Create transactions
        total_amount = Decimal('0')
        for invoice in invoices:
            transaction = PaymentTransaction(
                batch_id=batch.id,
                transaction_id=f"{batch_number}-{str(invoice.id).zfill(6)}",
                customer_id=invoice.customer_id,
                invoice_id=invoice.id,
                account_number=invoice.customer.bank_account_number,
                account_holder=invoice.customer.bank_account_holder or invoice.customer.name,
                amount=invoice.total_amount,
                scheduled_date=processing_date,
                status=TransactionStatus.PENDING
            )
            
            self.db.add(transaction)
            total_amount += invoice.total_amount
        
        # Update batch totals
        batch.total_transactions = len(invoices)
        batch.total_amount = total_amount
        
        self.db.commit()
        
        logger.info(f"Created payment batch {batch_number} with {len(invoices)} transactions")
        
        return batch
    
    def get_payment_status_report(self, batch_id: int) -> Dict[str, Any]:
        """
        Get detailed payment status report for a batch.
        
        Args:
            batch_id: Payment batch ID
            
        Returns:
            Dict containing status report
        """
        batch = self.db.query(PaymentBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Payment batch {batch_id} not found")
        
        # Get transaction statistics
        stats = self.db.query(
            PaymentTransaction.status,
            func.count(PaymentTransaction.id).label('count'),
            func.sum(PaymentTransaction.amount).label('total_amount')
        ).filter_by(
            batch_id=batch_id
        ).group_by(
            PaymentTransaction.status
        ).all()
        
        status_summary = {
            status.value: {
                'count': count,
                'amount': float(total_amount or 0)
            }
            for status, count, total_amount in stats
        }
        
        # Get failed transactions details
        failed_transactions = []
        if TransactionStatus.FAILED in status_summary:
            failed = self.db.query(PaymentTransaction).filter_by(
                batch_id=batch_id,
                status=TransactionStatus.FAILED
            ).all()
            
            failed_transactions = [
                {
                    'transaction_id': t.transaction_id,
                    'customer_id': t.customer_id,
                    'customer_name': t.customer.name if t.customer else None,
                    'amount': float(t.amount),
                    'error_code': t.bank_response_code,
                    'error_message': t.bank_response_message
                }
                for t in failed
            ]
        
        return {
            'batch_id': batch.id,
            'batch_number': batch.batch_number,
            'bank_code': batch.bank_code,
            'status': batch.status.value,
            'processing_date': batch.processing_date.isoformat(),
            'total_transactions': batch.total_transactions,
            'total_amount': float(batch.total_amount),
            'created_at': batch.created_at.isoformat(),
            'uploaded_at': batch.uploaded_at.isoformat() if batch.uploaded_at else None,
            'reconciled_at': batch.reconciled_at.isoformat() if batch.reconciled_at else None,
            'status_summary': status_summary,
            'failed_transactions': failed_transactions,
            'reconciliation_file': batch.reconciliation_file_name,
            'error_message': batch.error_message
        }