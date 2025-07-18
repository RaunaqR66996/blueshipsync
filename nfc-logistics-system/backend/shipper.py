#!/usr/bin/env python3
"""
Shipper Backend Module for NFC Logistics System
Handles ERP integration, payload generation, and socket communication
"""

import json
import socket
import threading
import logging
import datetime
import hashlib
import base64
import uuid
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SHIPPER_HOST = '0.0.0.0'
SHIPPER_PORT = 65432
BRIDGE_HOST = 'localhost'
BRIDGE_PORT = 65433
BUFFER_SIZE = 4096

# Mock ERP Configuration
INFOR_SYTELINE_API = {
    'base_url': 'https://api.infor-syteline.mock',
    'auth_token': 'mock-token-syteline',
    'company_id': 'SHIP-001'
}

@dataclass
class ShipmentPayload:
    """Data structure for shipment payload"""
    transaction_id: str
    status: str
    timestamp: str
    location: Dict[str, Any]
    packing_slip: Dict[str, Any]
    bol: Dict[str, Any]
    batch_details: Dict[str, Any]
    commercial_invoice: Dict[str, Any]
    logistics: Dict[str, Any]
    erp_identifiers: Dict[str, Any]
    security: Dict[str, Any]

class ERPIntegration:
    """Mock Infor SyteLine ERP integration"""
    
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config["auth_token"]}',
            'Content-Type': 'application/json'
        })
    
    def fetch_order_data(self, order_id: str) -> Dict[str, Any]:
        """Fetch order data from ERP system"""
        # Mock ERP response
        logger.info(f"Fetching order data for: {order_id}")
        
        # In production, this would be an actual API call
        # response = self.session.get(f"{self.config['base_url']}/orders/{order_id}")
        
        # Mock data for demonstration
        return {
            'order_id': order_id,
            'customer': {
                'id': 'REC-001',
                'name': 'Receiver Company LLC',
                'po_number': f'PO-{datetime.datetime.now().year}-{uuid.uuid4().hex[:4].upper()}'
            },
            'items': [
                {
                    'sku': 'PART-001',
                    'description': 'Industrial Component A',
                    'quantity': 100,
                    'weight': 50.5,
                    'unit': 'kg',
                    'batch_id': f'BATCH-{datetime.datetime.now().year}-Q1-001',
                    'manufacture_date': '2024-01-01T00:00:00Z',
                    'expiry_date': '2025-01-01T00:00:00Z'
                },
                {
                    'sku': 'PART-002',
                    'description': 'Industrial Component B',
                    'quantity': 50,
                    'weight': 25.0,
                    'unit': 'kg',
                    'batch_id': f'BATCH-{datetime.datetime.now().year}-Q1-002',
                    'manufacture_date': '2024-01-01T00:00:00Z',
                    'expiry_date': '2025-01-01T00:00:00Z'
                }
            ],
            'invoice': {
                'number': f'INV-{datetime.datetime.now().year}-{uuid.uuid4().hex[:6].upper()}',
                'total_value': 15000.00,
                'currency': 'USD',
                'terms': 'NET30'
            },
            'logistics': {
                'pallet_count': 2,
                'transit_type': 'truck',
                'carrier': {
                    'name': 'Express Logistics LLC',
                    'id': 'CARR-OH-123'
                }
            }
        }
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """Update order status in ERP"""
        logger.info(f"Updating order {order_id} status to: {status}")
        
        # Mock API call
        # response = self.session.put(
        #     f"{self.config['base_url']}/orders/{order_id}/status",
        #     json={'status': status}
        # )
        
        return True

class DigitalSigner:
    """Handle digital signature generation and verification"""
    
    def __init__(self):
        # Generate key pair for demonstration
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.public_key = self.private_key.public_key()
        self.key_id = f"KEY-SHIP-{uuid.uuid4().hex[:6].upper()}"
    
    def sign_payload(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Generate digital signature for payload"""
        # Serialize payload for signing
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        
        # Sign the payload
        signature = self.private_key.sign(
            payload_bytes,
            ec.ECDSA(hashes.SHA256())
        )
        
        # Encode signature and public key
        signature_b64 = base64.b64encode(signature).decode()
        public_key_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        return {
            'digital_signature': signature_b64,
            'signature_algorithm': 'ECDSA-SHA256',
            'signature_timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
            'public_key_id': self.key_id,
            'public_key': public_key_pem
        }

class ShipperServer:
    """Socket server for shipper operations"""
    
    def __init__(self, host: str = SHIPPER_HOST, port: int = SHIPPER_PORT):
        self.host = host
        self.port = port
        self.erp = ERPIntegration(INFOR_SYTELINE_API)
        self.signer = DigitalSigner()
        self.active_shipments = {}
        
    def generate_payload(self, order_id: str) -> ShipmentPayload:
        """Generate shipment payload from ERP data"""
        # Fetch data from ERP
        order_data = self.erp.fetch_order_data(order_id)
        
        # Generate transaction ID
        transaction_id = f"TRX-{datetime.datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
        
        # Build payload
        timestamp = datetime.datetime.utcnow().isoformat() + 'Z'
        
        # Process items for packing slip
        items = []
        total_weight = 0
        lot_numbers = []
        
        for item in order_data['items']:
            items.append({
                'sku': item['sku'],
                'description': item['description'],
                'quantity': item['quantity'],
                'weight': item['weight'],
                'unit': item['unit']
            })
            total_weight += item['weight']
            lot_numbers.append(f"LOT-{item['sku']}-{uuid.uuid4().hex[:4].upper()}")
        
        # Create payload structure
        payload_dict = {
            'transaction': {
                'id': transaction_id,
                'status': 'initiated',
                'timestamp': timestamp,
                'location': {
                    'latitude': 40.1263,
                    'longitude': -82.9290,
                    'address': '123 Logistics Way, Westerville, OH 43081'
                }
            },
            'packing_slip': {
                'items': items,
                'total_weight': total_weight,
                'weight_unit': 'kg'
            },
            'bol': {
                'number': f"BOL-{datetime.datetime.now().year}-{uuid.uuid4().hex[:4].upper()}",
                'date': timestamp,
                'carrier_name': order_data['logistics']['carrier']['name'],
                'carrier_id': order_data['logistics']['carrier']['id']
            },
            'batch_details': {
                'batch_id': order_data['items'][0]['batch_id'],
                'manufacture_date': order_data['items'][0]['manufacture_date'],
                'expiry_date': order_data['items'][0]['expiry_date'],
                'lot_numbers': lot_numbers
            },
            'commercial_invoice': {
                'number': order_data['invoice']['number'],
                'date': timestamp,
                'total_value': order_data['invoice']['total_value'],
                'currency': order_data['invoice']['currency'],
                'terms': order_data['invoice']['terms']
            },
            'logistics': {
                'pallet_count': order_data['logistics']['pallet_count'],
                'transit_type': order_data['logistics']['transit_type'],
                'vehicle_id': f"TRUCK-OH-{uuid.uuid4().hex[:3].upper()}",
                'driver_id': f"DRV-{uuid.uuid4().hex[:3].upper()}"
            },
            'erp_identifiers': {
                'shipper': {
                    'system': 'Infor SyteLine',
                    'company_id': self.erp.config['company_id'],
                    'order_id': order_id
                },
                'receiver': {
                    'system': 'SAP',
                    'company_id': order_data['customer']['id'],
                    'po_number': order_data['customer']['po_number']
                }
            }
        }
        
        # Add digital signature
        signature_data = self.signer.sign_payload(payload_dict)
        payload_dict['security'] = signature_data
        
        # Create payload object
        payload = ShipmentPayload(
            transaction_id=payload_dict['transaction']['id'],
            status=payload_dict['transaction']['status'],
            timestamp=payload_dict['transaction']['timestamp'],
            location=payload_dict['transaction']['location'],
            packing_slip=payload_dict['packing_slip'],
            bol=payload_dict['bol'],
            batch_details=payload_dict['batch_details'],
            commercial_invoice=payload_dict['commercial_invoice'],
            logistics=payload_dict['logistics'],
            erp_identifiers=payload_dict['erp_identifiers'],
            security=payload_dict['security']
        )
        
        return payload
    
    def send_to_bridge(self, payload: ShipmentPayload) -> bool:
        """Send payload to Blue Ships Sync bridge"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((BRIDGE_HOST, BRIDGE_PORT))
                
                # Prepare message
                message = {
                    'type': 'shipment_initiated',
                    'payload': asdict(payload)
                }
                
                # Send message
                sock.sendall(json.dumps(message).encode())
                
                # Wait for acknowledgment
                response = sock.recv(BUFFER_SIZE)
                result = json.loads(response.decode())
                
                if result.get('status') == 'success':
                    logger.info(f"Successfully sent payload to bridge: {payload.transaction_id}")
                    return True
                else:
                    logger.error(f"Bridge rejected payload: {result.get('error')}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send to bridge: {e}")
            return False
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Handle incoming client connections"""
        logger.info(f"New connection from {address}")
        
        try:
            # Receive request
            request = client_socket.recv(BUFFER_SIZE).decode()
            data = json.loads(request)
            
            if data['action'] == 'create_shipment':
                order_id = data['order_id']
                
                # Generate payload
                payload = self.generate_payload(order_id)
                
                # Store active shipment
                self.active_shipments[payload.transaction_id] = payload
                
                # Send to bridge
                if self.send_to_bridge(payload):
                    # Update ERP status
                    self.erp.update_order_status(order_id, 'shipped')
                    
                    response = {
                        'status': 'success',
                        'transaction_id': payload.transaction_id,
                        'message': 'Shipment initiated successfully'
                    }
                else:
                    response = {
                        'status': 'error',
                        'message': 'Failed to send to bridge'
                    }
            
            elif data['action'] == 'get_status':
                transaction_id = data['transaction_id']
                
                if transaction_id in self.active_shipments:
                    payload = self.active_shipments[transaction_id]
                    response = {
                        'status': 'success',
                        'shipment_status': payload.status,
                        'last_update': payload.timestamp
                    }
                else:
                    response = {
                        'status': 'error',
                        'message': 'Transaction not found'
                    }
            
            else:
                response = {
                    'status': 'error',
                    'message': 'Unknown action'
                }
            
            # Send response
            client_socket.sendall(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Error handling client: {e}")
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            client_socket.sendall(json.dumps(error_response).encode())
        
        finally:
            client_socket.close()
    
    def start(self):
        """Start the shipper server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        
        logger.info(f"Shipper server listening on {self.host}:{self.port}")
        
        try:
            while True:
                client_socket, address = server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.start()
                
        except KeyboardInterrupt:
            logger.info("Shutting down shipper server...")
        finally:
            server_socket.close()

def main():
    """Main entry point"""
    server = ShipperServer()
    server.start()

if __name__ == "__main__":
    main()