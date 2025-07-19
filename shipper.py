#!/usr/bin/env python3
"""
NFC Logistics System - Shipper Backend
Blue Ships Sync Middleware Bridge - Shipper Component

This module handles the shipper side of the NFC logistics system,
integrating with Infor SyteLine ERP and communicating with the carrier bridge.

Author: NFC Logistics System
Version: 1.0.0
"""

import json
import socket
import logging
import hashlib
import base64
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('shipper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ShipperConfig:
    """Configuration for the shipper system"""
    bridge_host: str = "localhost"
    bridge_port: int = 65432
    erp_base_url: str = "https://api.infor.syteline.com/v1"
    erp_api_key: str = "your_infor_api_key_here"
    erp_tenant: str = "your_tenant_id"
    company_id: str = "SHIPPER001"
    private_key_path: str = "shipper_private_key.pem"
    certificate_path: str = "shipper_certificate.pem"


class ERPIntegration:
    """Integration layer for Infor SyteLine ERP system"""
    
    def __init__(self, config: ShipperConfig):
        self.config = config
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'Authorization': f'Bearer {config.erp_api_key}',
            'Content-Type': 'application/json',
            'X-Tenant-ID': config.erp_tenant
        })
    
    def get_order_details(self, order_number: str) -> Optional[Dict[str, Any]]:
        """Retrieve order details from Infor SyteLine"""
        try:
            url = f"{self.config.erp_base_url}/orders/{order_number}"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully retrieved order {order_number} from ERP")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve order {order_number}: {e}")
            return None
    
    def get_inventory_details(self, item_ids: List[str]) -> Dict[str, Any]:
        """Retrieve inventory details for multiple items"""
        try:
            url = f"{self.config.erp_base_url}/inventory/batch"
            payload = {"item_ids": item_ids}
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully retrieved inventory for {len(item_ids)} items")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve inventory details: {e}")
            return {}
    
    def update_order_status(self, order_number: str, status: str) -> bool:
        """Update order status in ERP system"""
        try:
            url = f"{self.config.erp_base_url}/orders/{order_number}/status"
            payload = {
                "status": status,
                "updated_by": "NFC_LOGISTICS_SYSTEM",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            response = self.session.put(url, json=payload)
            response.raise_for_status()
            
            logger.info(f"Successfully updated order {order_number} status to {status}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update order status: {e}")
            return False


class DigitalSigner:
    """Handle digital signature operations"""
    
    def __init__(self, private_key_path: str, certificate_path: str):
        self.private_key_path = private_key_path
        self.certificate_path = certificate_path
        self._private_key = None
        self._certificate = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Load private key and certificate"""
        try:
            # Load private key
            with open(self.private_key_path, 'rb') as f:
                self._private_key = load_pem_private_key(
                    f.read(),
                    password=None  # Add password if key is encrypted
                )
            
            # Load certificate
            with open(self.certificate_path, 'rb') as f:
                self._certificate = f.read()
            
            logger.info("Successfully loaded signing credentials")
            
        except FileNotFoundError as e:
            logger.warning(f"Credential file not found: {e}")
            self._generate_test_credentials()
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            raise
    
    def _generate_test_credentials(self):
        """Generate test credentials for development"""
        logger.info("Generating test credentials for development")
        
        # Generate private key
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Save private key
        with open(self.private_key_path, 'wb') as f:
            f.write(self._private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Create a simple certificate (in production, use proper CA)
        self._certificate = b"-----BEGIN CERTIFICATE-----\nTEST_CERTIFICATE_FOR_DEVELOPMENT\n-----END CERTIFICATE-----"
        
        with open(self.certificate_path, 'wb') as f:
            f.write(self._certificate)
    
    def sign_payload(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Create digital signature for payload"""
        try:
            # Convert payload to canonical JSON string
            payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
            payload_bytes = payload_str.encode('utf-8')
            
            # Create signature
            signature = self._private_key.sign(
                payload_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return {
                "signature": base64.b64encode(signature).decode('utf-8'),
                "algorithm": "RSA-SHA256",
                "certificate": base64.b64encode(self._certificate).decode('utf-8'),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to sign payload: {e}")
            raise


class PayloadGenerator:
    """Generate NFC payload from ERP data"""
    
    def __init__(self, config: ShipperConfig):
        self.config = config
        self.erp = ERPIntegration(config)
        self.signer = DigitalSigner(config.private_key_path, config.certificate_path)
    
    def generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        return f"TXN-{uuid.uuid4().hex[:10].upper()}"
    
    def create_payload(self, order_number: str, carrier_info: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Create complete NFC payload from order data"""
        try:
            # Get order details from ERP
            order_data = self.erp.get_order_details(order_number)
            if not order_data:
                logger.error(f"Failed to retrieve order data for {order_number}")
                return None
            
            # Extract item IDs for inventory lookup
            item_ids = [item['sku'] for item in order_data.get('items', [])]
            inventory_data = self.erp.get_inventory_details(item_ids)
            
            # Generate transaction ID
            transaction_id = self.generate_transaction_id()
            
            # Build payload structure
            payload = {
                "transaction_id": transaction_id,
                "status": "initiated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "location": {
                    "latitude": order_data.get('ship_from_lat', 40.1262),  # Westerville, OH default
                    "longitude": order_data.get('ship_from_lng', -82.9291),
                    "address": order_data.get('ship_from_address', ''),
                    "city": order_data.get('ship_from_city', 'Westerville'),
                    "state": order_data.get('ship_from_state', 'OH'),
                    "zip_code": order_data.get('ship_from_zip', '43081')
                },
                "packing_slip": self._build_packing_slip(order_data, inventory_data),
                "bol": self._build_bol(order_data, carrier_info),
                "batch_details": self._build_batch_details(inventory_data),
                "commercial_invoice": self._build_commercial_invoice(order_data),
                "pallet_count": order_data.get('pallet_count', 1),
                "transit_type": carrier_info.get('transit_type', 'truck'),
                "shipper_erp": {
                    "system": "infor_syteline",
                    "id": self.config.company_id,
                    "order_number": order_number,
                    "customer_id": order_data.get('customer_id', '')
                },
                "receiver_erp": {
                    "system": order_data.get('receiver_erp_system', 'sap'),
                    "id": order_data.get('receiver_id', ''),
                    "purchase_order": order_data.get('po_number', ''),
                    "vendor_id": order_data.get('vendor_id', '')
                },
                "audit_trail": [{
                    "action": "payload_created",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "actor": f"shipper_{self.config.company_id}",
                    "location": "Westerville, OH",
                    "notes": f"Payload created for order {order_number}"
                }]
            }
            
            # Add digital signature
            payload["digital_signature"] = self.signer.sign_payload(payload)
            
            logger.info(f"Successfully created payload for transaction {transaction_id}")
            return payload
            
        except Exception as e:
            logger.error(f"Failed to create payload: {e}")
            return None
    
    def _build_packing_slip(self, order_data: Dict, inventory_data: Dict) -> Dict[str, Any]:
        """Build packing slip section"""
        items = []
        total_weight = 0
        
        for item in order_data.get('items', []):
            inventory_item = inventory_data.get(item['sku'], {})
            weight = item.get('weight', inventory_item.get('weight', 0))
            
            items.append({
                "sku": item['sku'],
                "description": item.get('description', inventory_item.get('description', '')),
                "quantity": item['quantity'],
                "weight": weight,
                "unit": item.get('unit', 'lbs')
            })
            
            total_weight += weight * item['quantity']
        
        return {
            "slip_number": order_data.get('packing_slip_number', f"PS-{order_data['order_number']}"),
            "items": items,
            "total_weight": total_weight,
            "weight_unit": "lbs"
        }
    
    def _build_bol(self, order_data: Dict, carrier_info: Dict) -> Dict[str, Any]:
        """Build Bill of Lading section"""
        return {
            "number": f"BOL-{order_data['order_number']}-{datetime.now().strftime('%Y%m%d')}",
            "carrier": carrier_info.get('name', 'TBD'),
            "origin": order_data.get('ship_from_address', 'Westerville, OH'),
            "destination": order_data.get('ship_to_address', ''),
            "pickup_date": order_data.get('pickup_date', datetime.now().date().isoformat()),
            "delivery_date": order_data.get('delivery_date', '')
        }
    
    def _build_batch_details(self, inventory_data: Dict) -> Dict[str, Any]:
        """Build batch details section"""
        # Get batch information from inventory data
        batch_info = {}
        serial_numbers = []
        
        for item_id, item_data in inventory_data.items():
            if 'batch_id' in item_data:
                batch_info.update({
                    "batch_id": item_data['batch_id'],
                    "manufacture_date": item_data.get('manufacture_date', ''),
                    "expiry_date": item_data.get('expiry_date', ''),
                    "lot_number": item_data.get('lot_number', '')
                })
            
            if 'serial_numbers' in item_data:
                serial_numbers.extend(item_data['serial_numbers'])
        
        if not batch_info:
            batch_info["batch_id"] = f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        if serial_numbers:
            batch_info["serial_numbers"] = serial_numbers
        
        return batch_info
    
    def _build_commercial_invoice(self, order_data: Dict) -> Dict[str, Any]:
        """Build commercial invoice section"""
        return {
            "number": order_data.get('invoice_number', f"INV-{order_data['order_number']}"),
            "total_value": order_data.get('total_value', 0),
            "currency": order_data.get('currency', 'USD'),
            "tax_amount": order_data.get('tax_amount', 0),
            "payment_terms": order_data.get('payment_terms', 'Net 30')
        }


class ShipperBridge:
    """Main bridge component for shipper operations"""
    
    def __init__(self, config: ShipperConfig):
        self.config = config
        self.payload_generator = PayloadGenerator(config)
        self.erp = ERPIntegration(config)
    
    def send_to_carrier(self, payload: Dict[str, Any]) -> bool:
        """Send payload to carrier bridge via socket"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(30)  # 30 second timeout
                sock.connect((self.config.bridge_host, self.config.bridge_port))
                
                # Send payload as JSON
                payload_json = json.dumps(payload)
                payload_bytes = payload_json.encode('utf-8')
                
                # Send length first, then payload
                sock.sendall(len(payload_bytes).to_bytes(4, byteorder='big'))
                sock.sendall(payload_bytes)
                
                # Wait for acknowledgment
                response = sock.recv(1024).decode('utf-8')
                
                if response == "ACK":
                    logger.info(f"Successfully sent payload {payload['transaction_id']} to carrier")
                    return True
                else:
                    logger.error(f"Unexpected response from carrier bridge: {response}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send payload to carrier: {e}")
            return False
    
    def process_shipment(self, order_number: str, carrier_info: Dict[str, str]) -> bool:
        """Process a complete shipment from order to carrier"""
        try:
            logger.info(f"Processing shipment for order {order_number}")
            
            # Generate payload
            payload = self.payload_generator.create_payload(order_number, carrier_info)
            if not payload:
                return False
            
            # Update ERP status
            if not self.erp.update_order_status(order_number, "in_transit"):
                logger.warning(f"Failed to update ERP status for order {order_number}")
            
            # Send to carrier
            if self.send_to_carrier(payload):
                logger.info(f"Successfully processed shipment for order {order_number}")
                return True
            else:
                # Rollback ERP status if send failed
                self.erp.update_order_status(order_number, "pending_shipment")
                return False
                
        except Exception as e:
            logger.error(f"Failed to process shipment: {e}")
            return False
    
    def start_completion_listener(self):
        """Start listening for completion notifications from carrier"""
        completion_port = 65433
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('localhost', completion_port))
            sock.listen(5)
            
            logger.info(f"Completion listener started on port {completion_port}")
            
            while True:
                try:
                    conn, addr = sock.accept()
                    logger.info(f"Completion notification from {addr}")
                    
                    with conn:
                        # Receive completion data
                        data = conn.recv(4096)
                        completion_data = json.loads(data.decode('utf-8'))
                        
                        # Process completion
                        self._handle_completion(completion_data)
                        
                        # Send acknowledgment
                        conn.sendall(b"ACK")
                        
                except Exception as e:
                    logger.error(f"Error handling completion notification: {e}")
    
    def _handle_completion(self, completion_data: Dict[str, Any]):
        """Handle shipment completion notification"""
        try:
            transaction_id = completion_data.get('transaction_id')
            order_number = completion_data.get('order_number')
            status = completion_data.get('status', 'delivered')
            
            logger.info(f"Handling completion for transaction {transaction_id}")
            
            # Update ERP status
            if order_number:
                self.erp.update_order_status(order_number, status)
            
            # Log completion
            logger.info(f"Completed processing for transaction {transaction_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle completion: {e}")


def main():
    """Main entry point for shipper system"""
    config = ShipperConfig()
    bridge = ShipperBridge(config)
    
    # Example usage
    carrier_info = {
        "name": "Westerville Logistics",
        "transit_type": "truck"
    }
    
    # Process a test shipment
    success = bridge.process_shipment("SO-2024-001", carrier_info)
    if success:
        print("Shipment processed successfully")
    else:
        print("Failed to process shipment")
    
    # Start completion listener (this will run indefinitely)
    # bridge.start_completion_listener()


if __name__ == "__main__":
    main()