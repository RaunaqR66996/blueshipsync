"""
Security module for NFC Logistics System
Handles digital signatures, encryption, and authentication
"""

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages security operations for the NFC logistics system"""
    
    def __init__(self, private_key_path: Optional[str] = None, public_key_path: Optional[str] = None):
        self.private_key = None
        self.public_key = None
        self.encryption_key = os.urandom(32)  # AES-256 key
        
        if private_key_path and os.path.exists(private_key_path):
            self.load_private_key(private_key_path)
        if public_key_path and os.path.exists(public_key_path):
            self.load_public_key(public_key_path)
    
    def generate_key_pair(self, key_size: int = 2048) -> tuple:
        """Generate RSA key pair for digital signatures"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        return private_key, public_key
    
    def save_key_pair(self, private_key, public_key, private_path: str, public_path: str):
        """Save RSA key pair to files"""
        # Save private key
        with open(private_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Save public key
        with open(public_path, 'wb') as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
    
    def load_private_key(self, key_path: str):
        """Load private key from file"""
        try:
            with open(key_path, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            logger.info(f"Private key loaded from {key_path}")
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
    
    def load_public_key(self, key_path: str):
        """Load public key from file"""
        try:
            with open(key_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            logger.info(f"Public key loaded from {key_path}")
        except Exception as e:
            logger.error(f"Failed to load public key: {e}")
    
    def create_digital_signature(self, data: Dict[str, Any]) -> str:
        """Create digital signature for payload data"""
        if not self.private_key:
            raise ValueError("Private key not loaded")
        
        # Convert data to canonical JSON string
        json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        data_bytes = json_str.encode('utf-8')
        
        # Create signature
        signature = self.private_key.sign(
            data_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_digital_signature(self, data: Dict[str, Any], signature: str) -> bool:
        """Verify digital signature of payload data"""
        if not self.public_key:
            raise ValueError("Public key not loaded")
        
        try:
            # Convert data to canonical JSON string
            json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
            data_bytes = json_str.encode('utf-8')
            
            # Decode signature
            signature_bytes = base64.b64decode(signature)
            
            # Verify signature
            self.public_key.verify(
                signature_bytes,
                data_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    def encrypt_payload(self, payload: Dict[str, Any]) -> str:
        """Encrypt payload data using AES-256"""
        json_str = json.dumps(payload)
        data_bytes = json_str.encode('utf-8')
        
        # Generate random IV
        iv = os.urandom(16)
        
        # Create cipher
        cipher = Cipher(algorithms.AES(self.encryption_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Pad data to block size
        padded_data = self._pad_data(data_bytes)
        
        # Encrypt
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Combine IV and encrypted data
        combined = iv + encrypted_data
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt_payload(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt payload data using AES-256"""
        combined = base64.b64decode(encrypted_data)
        
        # Extract IV and encrypted data
        iv = combined[:16]
        encrypted = combined[16:]
        
        # Create cipher
        cipher = Cipher(algorithms.AES(self.encryption_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        # Decrypt
        decrypted_data = decryptor.update(encrypted) + decryptor.finalize()
        
        # Remove padding
        unpadded_data = self._unpad_data(decrypted_data)
        
        # Parse JSON
        json_str = unpadded_data.decode('utf-8')
        return json.loads(json_str)
    
    def _pad_data(self, data: bytes) -> bytes:
        """Add PKCS7 padding to data"""
        block_size = 16
        padding_length = block_size - (len(data) % block_size)
        padding = bytes([padding_length] * padding_length)
        return data + padding
    
    def _unpad_data(self, data: bytes) -> bytes:
        """Remove PKCS7 padding from data"""
        padding_length = data[-1]
        return data[:-padding_length]
    
    def generate_checksum(self, data: Dict[str, Any]) -> str:
        """Generate MD5 checksum for data integrity"""
        json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.md5(json_str.encode('utf-8')).hexdigest()
    
    def verify_checksum(self, data: Dict[str, Any], checksum: str) -> bool:
        """Verify MD5 checksum for data integrity"""
        expected_checksum = self.generate_checksum(data)
        return hmac.compare_digest(expected_checksum, checksum)
    
    def generate_transaction_id(self, prefix: str = "TXN") -> str:
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        random_suffix = os.urandom(4).hex().upper()
        return f"{prefix}-{timestamp}-{random_suffix}"
    
    def create_secure_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a secure payload with digital signature and encryption"""
        # Add security metadata
        secure_payload = payload.copy()
        
        # Generate transaction ID if not present
        if 'transaction' not in secure_payload:
            secure_payload['transaction'] = {}
        if 'transaction_id' not in secure_payload['transaction']:
            secure_payload['transaction']['transaction_id'] = self.generate_transaction_id()
        
        # Add timestamp
        secure_payload['transaction']['timestamp'] = datetime.now().isoformat() + 'Z'
        
        # Create digital signature
        signature = self.create_digital_signature(secure_payload)
        
        # Generate checksum
        checksum = self.generate_checksum(secure_payload)
        
        # Add security information
        if 'security' not in secure_payload:
            secure_payload['security'] = {}
        
        secure_payload['security'].update({
            'digital_signature': signature,
            'signature_algorithm': 'SHA256withRSA',
            'signature_timestamp': datetime.now().isoformat() + 'Z',
            'encryption_key_id': 'KEY-' + datetime.now().strftime("%Y%m%d"),
            'checksum': checksum
        })
        
        return secure_payload
    
    def validate_secure_payload(self, payload: Dict[str, Any]) -> tuple[bool, str]:
        """Validate secure payload integrity and signature"""
        try:
            # Check if security section exists
            if 'security' not in payload:
                return False, "Missing security section"
            
            security = payload['security']
            
            # Verify checksum
            if 'checksum' not in security:
                return False, "Missing checksum"
            
            if not self.verify_checksum(payload, security['checksum']):
                return False, "Checksum verification failed"
            
            # Verify digital signature
            if 'digital_signature' not in security:
                return False, "Missing digital signature"
            
            if not self.verify_digital_signature(payload, security['digital_signature']):
                return False, "Digital signature verification failed"
            
            return True, "Payload validation successful"
            
        except Exception as e:
            logger.error(f"Payload validation error: {e}")
            return False, f"Validation error: {str(e)}"

# Global security manager instance
security_manager = SecurityManager()