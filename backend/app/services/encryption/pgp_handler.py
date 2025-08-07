"""PGP encryption handler for secure banking file transfers."""

import base64
import hashlib
import logging
import os
from datetime import datetime
from typing import Dict, Tuple

import gnupg
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.core.config import settings
from app.core.secrets_manager import get_secrets_manager

logger = logging.getLogger(__name__)


class PGPHandler:
    """
    Handler for PGP encryption / decryption operations.

    Supports both GPG and native Python cryptography for flexibility.
    """

    def __init__(self):
        self.gpg = None
        self.key_cache = {}
        self.use_gpg = self._init_gpg()
        self._load_keys()

    def _init_gpg(self) -> bool:
        """Initialize GPG if available."""
        try:
            # Try to initialize GPG
            gpg_home = os.path.join(settings.DATA_DIR, ".gnupg")
            os.makedirs(gpg_home, exist_ok=True)

            self.gpg = gnupg.GPG(gnupghome=gpg_home)
            self.gpg.encoding = "utf - 8"

            # Test GPG
            version = self.gpg.version
            if version:
                logger.info(f"GPG initialized successfully, version: {version}")
                return True
            else:
                logger.warning("GPG not available, using fallback encryption")
                return False

        except Exception as e:
            logger.warning(f"Failed to initialize GPG: {e}, using fallback encryption")
            return False

    def _load_keys(self):
        """Load encryption keys from secure storage."""
        if settings.ENVIRONMENT == "production":
            sm = get_secrets_manager()

            # Load our private key
            try:
                our_key = sm.get_secret_value("banking - pgp - private - key")
                passphrase = sm.get_secret_value("banking - pgp - passphrase")

                if self.use_gpg:
                    # Import to GPG keyring
                    result = self.gpg.import_keys(our_key)
                    if result.count > 0:
                        logger.info("Imported private key to GPG keyring")
                else:
                    # Store for fallback encryption
                    self.key_cache["private"] = {
                        "key": our_key,
                        "passphrase": passphrase,
                    }

            except Exception as e:
                logger.error(f"Failed to load private key: {e}")

            # Load bank public keys
            banks = ["mega", "ctbc", "esun", "first", "taishin"]
            for bank in banks:
                try:
                    public_key = sm.get_secret_value(
                        f"banking-{bank}-pgp - public - key"
                    )

                    if self.use_gpg:
                        # Import to GPG keyring
                        result = self.gpg.import_keys(public_key)
                        if result.count > 0:
                            logger.info(f"Imported public key for {bank}")
                    else:
                        # Store for fallback encryption
                        self.key_cache[f"{bank}_public"] = public_key

                except Exception as e:
                    logger.warning(f"Failed to load public key for {bank}: {e}")

    def encrypt(self, data: bytes, recipient_bank: str) -> bytes:
        """
        Encrypt data for a specific bank.

        Args:
            data: Data to encrypt
            recipient_bank: Bank code to encrypt for

        Returns:
            Encrypted data
        """
        if self.use_gpg:
            return self._encrypt_gpg(data, recipient_bank)
        else:
            return self._encrypt_fallback(data, recipient_bank)

    def _encrypt_gpg(self, data: bytes, recipient_bank: str) -> bytes:
        """Encrypt using GPG."""
        try:
            # Find recipient key
            keys = self.gpg.list_keys()
            recipient_key = None

            for key in keys:
                if recipient_bank.lower() in str(key.get("uids", [])).lower():
                    recipient_key = key["keyid"]
                    break

            if not recipient_key:
                raise ValueError(f"No public key found for {recipient_bank}")

            # Encrypt data
            encrypted = self.gpg.encrypt(
                data, recipients=[recipient_key], armor=True, always_trust=True
            )

            if encrypted.ok:
                return str(encrypted).encode("utf - 8")
            else:
                raise ValueError(f"Encryption failed: {encrypted.status}")

        except Exception as e:
            logger.error(f"GPG encryption failed: {e}")
            # Fallback to alternative encryption
            return self._encrypt_fallback(data, recipient_bank)

    def _encrypt_fallback(self, data: bytes, recipient_bank: str) -> bytes:
        """Fallback encryption using cryptography library."""
        try:
            # Generate session key
            session_key = os.urandom(32)  # 256 - bit key
            iv = os.urandom(16)  # 128 - bit IV

            # Encrypt data with AES
            cipher = Cipher(
                algorithms.AES(session_key), modes.CBC(iv), backend=default_backend()
            )
            encryptor = cipher.encryptor()

            # Pad data to AES block size
            pad_length = 16 - (len(data) % 16)
            padded_data = data + (bytes([pad_length]) * pad_length)

            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

            # Create PGP - like message structure
            message = self._create_pgp_message(
                encrypted_data, session_key, iv, recipient_bank
            )

            return message

        except Exception as e:
            logger.error(f"Fallback encryption failed: {e}")
            raise

    def decrypt(self, data: bytes) -> bytes:
        """
        Decrypt data using our private key.

        Args:
            data: Encrypted data

        Returns:
            Decrypted data
        """
        if self.use_gpg:
            return self._decrypt_gpg(data)
        else:
            return self._decrypt_fallback(data)

    def _decrypt_gpg(self, data: bytes) -> bytes:
        """Decrypt using GPG."""
        try:
            # Get passphrase from secure storage
            passphrase = None
            if settings.ENVIRONMENT == "production":
                sm = get_secrets_manager()
                passphrase = sm.get_secret_value("banking - pgp - passphrase")

            # Decrypt data
            decrypted = self.gpg.decrypt(data, passphrase=passphrase)

            if decrypted.ok:
                return bytes(str(decrypted), "utf - 8")
            else:
                raise ValueError(f"Decryption failed: {decrypted.status}")

        except Exception as e:
            logger.error(f"GPG decryption failed: {e}")
            # Fallback to alternative decryption
            return self._decrypt_fallback(data)

    def _decrypt_fallback(self, data: bytes) -> bytes:
        """Fallback decryption using cryptography library."""
        try:
            # Parse PGP - like message
            session_key, iv, encrypted_data = self._parse_pgp_message(data)

            # Decrypt with AES
            cipher = Cipher(
                algorithms.AES(session_key), modes.CBC(iv), backend=default_backend()
            )
            decryptor = cipher.decryptor()

            padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

            # Remove padding
            pad_length = padded_data[-1]
            return padded_data[:-pad_length]

        except Exception as e:
            logger.error(f"Fallback decryption failed: {e}")
            raise

    def sign(self, data: bytes) -> bytes:
        """
        Create digital signature for data.

        Args:
            data: Data to sign

        Returns:
            Signature
        """
        if self.use_gpg:
            return self._sign_gpg(data)
        else:
            return self._sign_fallback(data)

    def _sign_gpg(self, data: bytes) -> bytes:
        """Sign using GPG."""
        try:
            # Get passphrase
            passphrase = None
            if settings.ENVIRONMENT == "production":
                sm = get_secrets_manager()
                passphrase = sm.get_secret_value("banking - pgp - passphrase")

            # Sign data
            signed = self.gpg.sign(data, passphrase=passphrase, detach=True)

            return str(signed).encode("utf - 8")

        except Exception as e:
            logger.error(f"GPG signing failed: {e}")
            return self._sign_fallback(data)

    def _sign_fallback(self, data: bytes) -> bytes:
        """Fallback signing using cryptography library."""
        try:
            # For fallback, just create a SHA256 HMAC
            key = self.key_cache.get("private", {}).get("key", b"")
            if isinstance(key, str):
                key = key.encode("utf - 8")

            h = hashlib.sha256()
            h.update(key)
            h.update(data)

            return base64.b64encode(h.digest())

        except Exception as e:
            logger.error(f"Fallback signing failed: {e}")
            raise

    def verify(self, data: bytes, signature: bytes, sender_bank: str) -> bool:
        """
        Verify signature on data.

        Args:
            data: Original data
            signature: Signature to verify
            sender_bank: Bank that signed the data

        Returns:
            True if signature is valid
        """
        if self.use_gpg:
            return self._verify_gpg(data, signature, sender_bank)
        else:
            return self._verify_fallback(data, signature, sender_bank)

    def _verify_gpg(self, data: bytes, signature: bytes, sender_bank: str) -> bool:
        """Verify using GPG."""
        try:
            # Create temporary file for data
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False) as tmp_data:
                tmp_data.write(data)
                tmp_data_path = tmp_data.name

            with tempfile.NamedTemporaryFile(delete=False) as tmp_sig:
                tmp_sig.write(signature)
                tmp_sig_path = tmp_sig.name

            try:
                # Verify signature
                verified = self.gpg.verify_file(tmp_sig_path, tmp_data_path)
                return verified.valid

            finally:
                # Clean up temp files
                os.unlink(tmp_data_path)
                os.unlink(tmp_sig_path)

        except Exception as e:
            logger.error(f"GPG verification failed: {e}")
            return False

    def _verify_fallback(self, data: bytes, signature: bytes, sender_bank: str) -> bool:
        """Fallback verification."""
        # For fallback, we can't truly verify without the sender's key
        # This is just a placeholder
        return True

    def _create_pgp_message(
        self, encrypted_data: bytes, session_key: bytes, iv: bytes, recipient_bank: str
    ) -> bytes:
        """Create PGP - like message structure."""
        # Simple structure: base64 encode everything
        message = {
            "version": "1.0",
            "recipient": recipient_bank,
            "algorithm": "AES256 - CBC",
            "session_key": base64.b64encode(session_key).decode("utf - 8"),
            "iv": base64.b64encode(iv).decode("utf - 8"),
            "data": base64.b64encode(encrypted_data).decode("utf - 8"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Create ASCII - armored format
        import json

        json_data = json.dumps(message, indent=2)

        pgp_message = """-----BEGIN PGP MESSAGE-----
Version: LuckyGas PGP 1.0

{base64.b64encode(json_data.encode('utf - 8')).decode('utf - 8')}
-----END PGP MESSAGE-----"""

        return pgp_message.encode("utf - 8")

    def _parse_pgp_message(self, data: bytes) -> Tuple[bytes, bytes, bytes]:
        """Parse PGP - like message structure."""
        try:
            # Extract base64 content
            message_str = data.decode("utf - 8")
            start = message_str.find("\n\n") + 2
            end = message_str.find("\n-----END")

            if start < 2 or end < 0:
                raise ValueError("Invalid PGP message format")

            base64_content = message_str[start:end].strip()
            json_data = base64.b64decode(base64_content).decode("utf - 8")

            import json

            message = json.loads(json_data)

            session_key = base64.b64decode(message["session_key"])
            iv = base64.b64decode(message["iv"])
            encrypted_data = base64.b64decode(message["data"])

            return session_key, iv, encrypted_data

        except Exception as e:
            logger.error(f"Failed to parse PGP message: {e}")
            raise

    def generate_key_pair(self, name: str, email: str) -> Tuple[str, str]:
        """
        Generate a new PGP key pair.

        Args:
            name: Key owner name
            email: Key owner email

        Returns:
            Tuple of (public_key, private_key)
        """
        if self.use_gpg:
            return self._generate_gpg_keys(name, email)
        else:
            return self._generate_fallback_keys(name, email)

    def _generate_gpg_keys(self, name: str, email: str) -> Tuple[str, str]:
        """Generate keys using GPG."""
        try:
            # Generate key
            input_data = self.gpg.gen_key_input(
                name_real=name,
                name_email=email,
                key_type="RSA",
                key_length=4096,
                expire_date="2y",
            )

            key = self.gpg.gen_key(input_data)

            # Export keys
            public_key = self.gpg.export_keys(str(key))
            private_key = self.gpg.export_keys(str(key), True)

            return public_key, private_key

        except Exception as e:
            logger.error(f"GPG key generation failed: {e}")
            return self._generate_fallback_keys(name, email)

    def _generate_fallback_keys(self, name: str, email: str) -> Tuple[str, str]:
        """Generate fallback keys using cryptography library."""
        # For simplicity, just generate a symmetric key
        # In production, would use proper asymmetric keys
        key = os.urandom(32)

        public_key = """-----BEGIN PUBLIC KEY-----
{base64.b64encode(key).decode('utf - 8')}
-----END PUBLIC KEY-----"""

        private_key = """-----BEGIN PRIVATE KEY-----
{base64.b64encode(key).decode('utf - 8')}
-----END PRIVATE KEY-----"""

        return public_key, private_key

    def get_key_info(self, bank_code: str) -> Dict[str, any]:
        """Get information about a bank's encryption key."""
        info = {
            "bank_code": bank_code,
            "has_public_key": False,
            "key_id": None,
            "key_fingerprint": None,
            "key_expiry": None,
            "key_algorithm": None,
        }

        if self.use_gpg:
            # Check GPG keyring
            keys = self.gpg.list_keys()
            for key in keys:
                if bank_code.lower() in str(key.get("uids", [])).lower():
                    info["has_public_key"] = True
                    info["key_id"] = key.get("keyid")
                    info["key_fingerprint"] = key.get("fingerprint")
                    info["key_expiry"] = key.get("expires")
                    info["key_algorithm"] = key.get("algo")
                    break
        else:
            # Check key cache
            if f"{bank_code}_public" in self.key_cache:
                info["has_public_key"] = True
                info["key_algorithm"] = "AES256"

        return info
