#!/usr/bin/env python3
"""
NFC Logistics System - Receiver Bridge Backend
Blue Ships Sync Middleware Bridge - Receiver Component

This module handles the receiver side of the NFC logistics system,
integrating with SAP ERP and processing delivery confirmations from carriers.

Author: NFC Logistics System
Version: 1.0.0
"""

import json
import socket
import logging
import threading
import base64
import hashlib
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sqlite3
from pathlib import Path


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('receiver_bridge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ReceiverConfig:
    """Configuration for the receiver bridge system"""
    # Bridge configuration
    bridge_port: int = 65432
    completion_port: int = 65433
    shipper_host: str = "localhost"
    
    # SAP ERP configuration
    sap_base_url: str = "https://api.sap.company.com/v1"
    sap_client: str = "100"
    sap_username: str = "NFC_LOGISTICS"
    sap_password: str = "your_sap_password"
    sap_language: str = "EN"
    
    # Company configuration
    company_id: str = "RECEIVER001"
    warehouse_location: str = "Westerville Distribution Center"
    
    # Security configuration
    certificate_path: str = "receiver_certificate.pem"
    trusted_shippers_path: str = "trusted_shippers.json"
    
    # Database configuration
    database_path: str = "receiver_transactions.db"


class DatabaseManager:
    """Manage SQLite database for transaction storage"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    received_timestamp TEXT NOT NULL,
                    processed_timestamp TEXT,
                    shipper_id TEXT,
                    order_number TEXT,
                    carrier_name TEXT,
                    total_value REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_transaction_status 
                ON transactions (status)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_audit_transaction 
                ON audit_log (transaction_id)
            ''')
    
    def store_transaction(self, payload: Dict[str, Any]) -> bool:
        """Store incoming transaction"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO transactions 
                    (transaction_id, payload, status, received_timestamp, 
                     shipper_id, order_number, carrier_name, total_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    payload['transaction_id'],
                    json.dumps(payload),
                    payload['status'],
                    datetime.now(timezone.utc).isoformat(),
                    payload.get('shipper_erp', {}).get('id'),
                    payload.get('shipper_erp', {}).get('order_number'),
                    payload.get('bol', {}).get('carrier'),
                    payload.get('commercial_invoice', {}).get('total_value', 0)
                ))
                
                self.log_audit(payload['transaction_id'], 'transaction_stored', 
                             'receiver_bridge', 'Transaction stored in database')
                return True
                
        except Exception as e:
            logger.error(f"Failed to store transaction: {e}")
            return False
    
    def update_transaction_status(self, transaction_id: str, status: str) -> bool:
        """Update transaction status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    UPDATE transactions 
                    SET status = ?, processed_timestamp = ?
                    WHERE transaction_id = ?
                ''', (status, datetime.now(timezone.utc).isoformat(), transaction_id))
                
                if cursor.rowcount > 0:
                    self.log_audit(transaction_id, 'status_updated', 
                                 'receiver_bridge', f'Status updated to {status}')
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Failed to update transaction status: {e}")
            return False
    
    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve transaction by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT payload FROM transactions WHERE transaction_id = ?
                ''', (transaction_id,))
                
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve transaction: {e}")
            return None
    
    def log_audit(self, transaction_id: str, action: str, actor: str, details: str = ""):
        """Log audit entry"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO audit_log (transaction_id, action, actor, timestamp, details)
                    VALUES (?, ?, ?, ?, ?)
                ''', (transaction_id, action, actor, 
                      datetime.now(timezone.utc).isoformat(), details))
                
        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")
    
    def get_pending_transactions(self) -> List[Dict[str, Any]]:
        """Get all pending transactions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT payload FROM transactions 
                    WHERE status IN ('delivered', 'in_transit')
                    ORDER BY received_timestamp
                ''')
                
                return [json.loads(row[0]) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to retrieve pending transactions: {e}")
            return []


class SignatureValidator:
    """Validate digital signatures from trusted shippers"""
    
    def __init__(self, trusted_shippers_path: str):
        self.trusted_shippers_path = trusted_shippers_path
        self.trusted_certificates = self._load_trusted_certificates()
    
    def _load_trusted_certificates(self) -> Dict[str, Any]:
        """Load trusted shipper certificates"""
        try:
            if Path(self.trusted_shippers_path).exists():
                with open(self.trusted_shippers_path, 'r') as f:
                    return json.load(f)
            else:
                # Create default trusted shippers file
                default_trusted = {
                    "SHIPPER001": {
                        "name": "Test Shipper",
                        "certificate": "TEST_CERTIFICATE_FOR_DEVELOPMENT",
                        "added_date": datetime.now(timezone.utc).isoformat()
                    }
                }
                with open(self.trusted_shippers_path, 'w') as f:
                    json.dump(default_trusted, f, indent=2)
                return default_trusted
                
        except Exception as e:
            logger.error(f"Failed to load trusted certificates: {e}")
            return {}
    
    def validate_signature(self, payload: Dict[str, Any]) -> bool:
        """Validate digital signature on payload"""
        try:
            # Extract signature info
            signature_info = payload.get('digital_signature', {})
            shipper_id = payload.get('shipper_erp', {}).get('id')
            
            if not signature_info or not shipper_id:
                logger.error("Missing signature or shipper information")
                return False
            
            # Check if shipper is trusted
            if shipper_id not in self.trusted_certificates:
                logger.error(f"Untrusted shipper: {shipper_id}")
                return False
            
            # For development/testing, we'll do a simple validation
            # In production, you would validate the actual cryptographic signature
            algorithm = signature_info.get('algorithm')
            signature_data = signature_info.get('signature')
            
            if algorithm and signature_data:
                logger.info(f"Signature validation passed for shipper {shipper_id}")
                return True
            
            logger.error("Invalid signature format")
            return False
            
        except Exception as e:
            logger.error(f"Signature validation failed: {e}")
            return False


class SAPIntegration:
    """Integration layer for SAP ERP system"""
    
    def __init__(self, config: ReceiverConfig):
        self.config = config
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Setup SAP session with authentication and retry logic"""
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "POST", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers for SAP
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CSRF-Token': 'Fetch'
        })
        
        # Authenticate with SAP
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with SAP system"""
        try:
            auth_url = f"{self.config.sap_base_url}/auth"
            auth_data = {
                "client": self.config.sap_client,
                "username": self.config.sap_username,
                "password": self.config.sap_password,
                "language": self.config.sap_language
            }
            
            response = self.session.post(auth_url, json=auth_data)
            
            if response.status_code == 200:
                auth_result = response.json()
                token = auth_result.get('access_token')
                if token:
                    self.session.headers['Authorization'] = f'Bearer {token}'
                    logger.info("Successfully authenticated with SAP")
                else:
                    logger.error("No access token received from SAP")
            else:
                logger.error(f"SAP authentication failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"SAP authentication error: {e}")
    
    def create_goods_receipt(self, payload: Dict[str, Any]) -> Optional[str]:
        """Create goods receipt in SAP"""
        try:
            # Map NFC payload to SAP goods receipt format
            receipt_data = {
                "DocumentDate": datetime.now().strftime('%Y-%m-%d'),
                "PostingDate": datetime.now().strftime('%Y-%m-%d'),
                "Reference": payload['transaction_id'],
                "DocumentHeaderText": f"NFC Receipt - {payload['bol']['number']}",
                "GoodsReceiptItems": []
            }
            
            # Add items from packing slip
            for item in payload['packing_slip']['items']:
                receipt_item = {
                    "Material": item['sku'],
                    "Plant": "1000",  # Default plant
                    "StorageLocation": "0001",  # Default storage location
                    "Quantity": item['quantity'],
                    "UnitOfEntry": item.get('unit', 'EA'),
                    "PurchaseOrder": payload.get('receiver_erp', {}).get('purchase_order', ''),
                    "Reference": payload['transaction_id']
                }
                receipt_data["GoodsReceiptItems"].append(receipt_item)
            
            # Post to SAP
            url = f"{self.config.sap_base_url}/GoodsReceipts"
            response = self.session.post(url, json=receipt_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                document_number = result.get('MaterialDocument')
                logger.info(f"Created SAP goods receipt: {document_number}")
                return document_number
            else:
                logger.error(f"Failed to create goods receipt: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating goods receipt: {e}")
            return None
    
    def update_purchase_order(self, po_number: str, status: str) -> bool:
        """Update purchase order status"""
        try:
            if not po_number:
                return True  # No PO to update
            
            url = f"{self.config.sap_base_url}/PurchaseOrders('{po_number}')"
            update_data = {
                "OverallStatus": status,
                "LastChangeDate": datetime.now().strftime('%Y-%m-%d'),
                "LastChangeTime": datetime.now().strftime('%H:%M:%S')
            }
            
            response = self.session.patch(url, json=update_data)
            
            if response.status_code in [200, 204]:
                logger.info(f"Updated PO {po_number} status to {status}")
                return True
            else:
                logger.error(f"Failed to update PO: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating purchase order: {e}")
            return False
    
    def release_payment(self, payload: Dict[str, Any]) -> bool:
        """Release payment for received goods"""
        try:
            invoice_info = payload.get('commercial_invoice', {})
            
            payment_data = {
                "CompanyCode": "1000",
                "DocumentType": "KR",  # Vendor invoice
                "Reference": payload['transaction_id'],
                "InvoiceReference": invoice_info.get('number', ''),
                "Vendor": payload.get('shipper_erp', {}).get('id', ''),
                "Amount": invoice_info.get('total_value', 0),
                "Currency": invoice_info.get('currency', 'USD'),
                "PaymentTerms": invoice_info.get('payment_terms', 'Z001'),
                "PostingDate": datetime.now().strftime('%Y-%m-%d')
            }
            
            url = f"{self.config.sap_base_url}/VendorInvoices"
            response = self.session.post(url, json=payment_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                document_number = result.get('AccountingDocument')
                logger.info(f"Released payment document: {document_number}")
                return True
            else:
                logger.error(f"Failed to release payment: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error releasing payment: {e}")
            return False


class CarrierBridge:
    """Bridge component to communicate with carriers"""
    
    def __init__(self, config: ReceiverConfig):
        self.config = config
        self.db = DatabaseManager(config.database_path)
        self.validator = SignatureValidator(config.trusted_shippers_path)
        self.sap = SAPIntegration(config)
        self.running = False
    
    def start_bridge(self):
        """Start the bridge server"""
        self.running = True
        bridge_thread = threading.Thread(target=self._run_bridge_server)
        bridge_thread.daemon = True
        bridge_thread.start()
        
        logger.info(f"Carrier bridge started on port {self.config.bridge_port}")
        return bridge_thread
    
    def _run_bridge_server(self):
        """Run the main bridge server"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('localhost', self.config.bridge_port))
            sock.listen(5)
            
            while self.running:
                try:
                    conn, addr = sock.accept()
                    logger.info(f"Connection from carrier at {addr}")
                    
                    # Handle connection in separate thread
                    handler_thread = threading.Thread(
                        target=self._handle_carrier_connection,
                        args=(conn, addr)
                    )
                    handler_thread.daemon = True
                    handler_thread.start()
                    
                except Exception as e:
                    if self.running:
                        logger.error(f"Error accepting connection: {e}")
    
    def _handle_carrier_connection(self, conn: socket.socket, addr: Tuple[str, int]):
        """Handle individual carrier connection"""
        try:
            with conn:
                # Receive payload size
                size_bytes = conn.recv(4)
                if len(size_bytes) != 4:
                    logger.error("Failed to receive payload size")
                    return
                
                payload_size = int.from_bytes(size_bytes, byteorder='big')
                
                # Receive payload
                payload_data = b''
                while len(payload_data) < payload_size:
                    chunk = conn.recv(min(4096, payload_size - len(payload_data)))
                    if not chunk:
                        break
                    payload_data += chunk
                
                if len(payload_data) != payload_size:
                    logger.error("Incomplete payload received")
                    conn.sendall(b"NACK")
                    return
                
                # Parse payload
                try:
                    payload = json.loads(payload_data.decode('utf-8'))
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON payload: {e}")
                    conn.sendall(b"NACK")
                    return
                
                # Process the delivery
                success = self.process_delivery(payload)
                
                # Send response
                if success:
                    conn.sendall(b"ACK")
                    logger.info(f"Successfully processed delivery {payload.get('transaction_id')}")
                else:
                    conn.sendall(b"NACK")
                    logger.error(f"Failed to process delivery {payload.get('transaction_id')}")
                
        except Exception as e:
            logger.error(f"Error handling carrier connection: {e}")
    
    def process_delivery(self, payload: Dict[str, Any]) -> bool:
        """Process incoming delivery from carrier"""
        try:
            transaction_id = payload.get('transaction_id')
            if not transaction_id:
                logger.error("Missing transaction ID")
                return False
            
            logger.info(f"Processing delivery for transaction {transaction_id}")
            
            # Validate digital signature
            if not self.validator.validate_signature(payload):
                logger.error(f"Signature validation failed for {transaction_id}")
                return False
            
            # Store transaction
            if not self.db.store_transaction(payload):
                logger.error(f"Failed to store transaction {transaction_id}")
                return False
            
            # Update payload status
            payload['status'] = 'delivered'
            payload['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            # Add audit trail entry
            if 'audit_trail' not in payload:
                payload['audit_trail'] = []
            
            payload['audit_trail'].append({
                "action": "delivery_received",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": f"receiver_{self.config.company_id}",
                "location": self.config.warehouse_location,
                "notes": "Delivery received via NFC"
            })
            
            # Process in SAP
            goods_receipt_number = self.sap.create_goods_receipt(payload)
            if goods_receipt_number:
                payload['sap_goods_receipt'] = goods_receipt_number
                
                # Update purchase order status
                po_number = payload.get('receiver_erp', {}).get('purchase_order')
                self.sap.update_purchase_order(po_number, 'delivered')
                
                # Release payment
                self.sap.release_payment(payload)
                
                # Update transaction status
                self.db.update_transaction_status(transaction_id, 'confirmed')
                
                # Notify shipper of completion
                self._notify_shipper_completion(payload)
                
                return True
            else:
                logger.error(f"Failed to create goods receipt for {transaction_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing delivery: {e}")
            return False
    
    def _notify_shipper_completion(self, payload: Dict[str, Any]):
        """Notify shipper that delivery is complete"""
        try:
            completion_data = {
                "transaction_id": payload['transaction_id'],
                "order_number": payload.get('shipper_erp', {}).get('order_number'),
                "status": "confirmed",
                "completion_timestamp": datetime.now(timezone.utc).isoformat(),
                "goods_receipt": payload.get('sap_goods_receipt'),
                "receiver_id": self.config.company_id
            }
            
            # Send completion notification to shipper
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((self.config.shipper_host, self.config.completion_port))
                
                completion_json = json.dumps(completion_data)
                sock.sendall(completion_json.encode('utf-8'))
                
                response = sock.recv(1024).decode('utf-8')
                if response == "ACK":
                    logger.info(f"Notified shipper of completion for {payload['transaction_id']}")
                else:
                    logger.warning(f"Unexpected response from shipper: {response}")
                    
        except Exception as e:
            logger.error(f"Failed to notify shipper of completion: {e}")
    
    def stop_bridge(self):
        """Stop the bridge server"""
        self.running = False
        logger.info("Carrier bridge stopped")


def main():
    """Main entry point for receiver bridge"""
    config = ReceiverConfig()
    bridge = CarrierBridge(config)
    
    try:
        # Start the bridge
        bridge_thread = bridge.start_bridge()
        
        print(f"NFC Receiver Bridge started on port {config.bridge_port}")
        print("Press Ctrl+C to stop...")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down receiver bridge...")
        bridge.stop_bridge()
        print("Receiver bridge stopped.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        bridge.stop_bridge()


if __name__ == "__main__":
    main()