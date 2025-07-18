#!/usr/bin/env python3
"""
Receiver Backend and Blue Ships Sync Bridge Module
Handles NFC data reception, validation, and SAP ERP integration
"""

import json
import socket
import threading
import logging
import datetime
import base64
import uuid
import requests
import asyncio
import websockets
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from queue import Queue
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BRIDGE_HOST = '0.0.0.0'
BRIDGE_PORT = 65433
RECEIVER_HOST = '0.0.0.0'
RECEIVER_PORT = 65434
NFC_RECEIVER_PORT = 65435
WEBSOCKET_PORT = 8765
BUFFER_SIZE = 4096

# Mock SAP Configuration
SAP_API = {
    'base_url': 'https://api.sap.mock',
    'auth_token': 'mock-token-sap',
    'company_id': 'REC-001'
}

class BlueShipsSyncBridge:
    """Blue Ships Sync middleware bridge for multi-stakeholder communication"""
    
    def __init__(self):
        self.active_transactions = {}
        self.carrier_connections = {}
        self.message_queue = Queue()
        self.websocket_clients = set()
        
    async def handle_websocket(self, websocket, path):
        """Handle WebSocket connections from carrier apps"""
        carrier_id = None
        try:
            # Register carrier
            await websocket.send(json.dumps({
                'type': 'connection_established',
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
            }))
            
            self.websocket_clients.add(websocket)
            
            async for message in websocket:
                data = json.loads(message)
                
                if data['type'] == 'carrier_register':
                    carrier_id = data['carrier_id']
                    self.carrier_connections[carrier_id] = websocket
                    logger.info(f"Carrier registered: {carrier_id}")
                    
                    # Send acknowledgment
                    await websocket.send(json.dumps({
                        'type': 'registration_success',
                        'carrier_id': carrier_id
                    }))
                
                elif data['type'] == 'payload_received':
                    # Carrier acknowledges payload receipt
                    transaction_id = data['transaction_id']
                    if transaction_id in self.active_transactions:
                        self.active_transactions[transaction_id]['status'] = 'in_transit'
                        self.active_transactions[transaction_id]['carrier_id'] = carrier_id
                        logger.info(f"Payload {transaction_id} acknowledged by carrier {carrier_id}")
                
                elif data['type'] == 'delivery_completed':
                    # Carrier reports delivery completion
                    transaction_id = data['transaction_id']
                    if transaction_id in self.active_transactions:
                        self.active_transactions[transaction_id]['status'] = 'delivered'
                        self.active_transactions[transaction_id]['delivery_timestamp'] = data['timestamp']
                        logger.info(f"Delivery completed for {transaction_id}")
                        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Carrier {carrier_id} disconnected")
        finally:
            self.websocket_clients.discard(websocket)
            if carrier_id and carrier_id in self.carrier_connections:
                del self.carrier_connections[carrier_id]
    
    async def broadcast_to_carriers(self, message: Dict[str, Any]):
        """Broadcast message to all connected carriers"""
        if self.websocket_clients:
            disconnected = set()
            for client in self.websocket_clients:
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)
            
            # Clean up disconnected clients
            self.websocket_clients -= disconnected
    
    def start_websocket_server(self):
        """Start WebSocket server for carrier connections"""
        async def serve():
            async with websockets.serve(self.handle_websocket, BRIDGE_HOST, WEBSOCKET_PORT):
                logger.info(f"WebSocket server started on ws://{BRIDGE_HOST}:{WEBSOCKET_PORT}")
                await asyncio.Future()  # Run forever
        
        asyncio.new_event_loop().run_until_complete(serve())

class SAPIntegration:
    """Mock SAP ERP integration for receiver"""
    
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config["auth_token"]}',
            'Content-Type': 'application/json'
        })
    
    def validate_po(self, po_number: str) -> bool:
        """Validate purchase order exists in SAP"""
        logger.info(f"Validating PO: {po_number}")
        
        # Mock validation - in production would be actual API call
        # response = self.session.get(f"{self.config['base_url']}/purchase-orders/{po_number}")
        
        return True  # Mock always valid
    
    def create_goods_receipt(self, payload: Dict[str, Any]) -> str:
        """Create goods receipt in SAP"""
        logger.info("Creating goods receipt in SAP")
        
        # Extract relevant data
        gr_data = {
            'po_number': payload['erp_identifiers']['receiver']['po_number'],
            'delivery_date': datetime.datetime.utcnow().isoformat(),
            'items': [],
            'total_value': payload['commercial_invoice']['total_value'],
            'currency': payload['commercial_invoice']['currency']
        }
        
        # Process items
        for item in payload['packing_slip']['items']:
            gr_data['items'].append({
                'material': item['sku'],
                'quantity': item['quantity'],
                'unit': item['unit'],
                'batch': payload['batch_details']['batch_id']
            })
        
        # Mock API call
        # response = self.session.post(f"{self.config['base_url']}/goods-receipts", json=gr_data)
        
        # Return mock GR number
        gr_number = f"GR-{datetime.datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
        logger.info(f"Created goods receipt: {gr_number}")
        
        return gr_number
    
    def trigger_payment_release(self, invoice_number: str, gr_number: str) -> bool:
        """Trigger payment release in SAP"""
        logger.info(f"Triggering payment release for invoice: {invoice_number}")
        
        # Mock payment release
        # response = self.session.post(
        #     f"{self.config['base_url']}/payments/release",
        #     json={
        #         'invoice_number': invoice_number,
        #         'gr_number': gr_number,
        #         'release_type': 'automatic'
        #     }
        # )
        
        return True
    
    def update_inventory(self, items: List[Dict[str, Any]]) -> bool:
        """Update inventory levels in SAP"""
        logger.info("Updating inventory in SAP")
        
        # Mock inventory update
        for item in items:
            logger.info(f"Updated inventory for {item['sku']}: +{item['quantity']} {item['unit']}")
        
        return True

class SignatureValidator:
    """Validate digital signatures on payloads"""
    
    @staticmethod
    def validate_signature(payload: Dict[str, Any]) -> bool:
        """Validate the digital signature of a payload"""
        try:
            # Extract security data
            security = payload.get('security', {})
            signature_b64 = security.get('digital_signature')
            public_key_pem = security.get('public_key')
            
            if not signature_b64 or not public_key_pem:
                logger.error("Missing signature or public key")
                return False
            
            # Remove security field for validation
            payload_copy = payload.copy()
            del payload_copy['security']
            
            # Serialize payload
            payload_bytes = json.dumps(payload_copy, sort_keys=True).encode()
            
            # Decode signature
            signature = base64.b64decode(signature_b64)
            
            # Load public key
            public_key = serialization.load_pem_public_key(public_key_pem.encode())
            
            # Verify signature
            public_key.verify(
                signature,
                payload_bytes,
                ec.ECDSA(hashes.SHA256())
            )
            
            logger.info("Signature validation successful")
            return True
            
        except InvalidSignature:
            logger.error("Invalid signature")
            return False
        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return False

class ReceiverServer:
    """Receiver server with integrated bridge functionality"""
    
    def __init__(self):
        self.bridge = BlueShipsSyncBridge()
        self.sap = SAPIntegration(SAP_API)
        self.validator = SignatureValidator()
        self.processed_transactions = {}
        
    def handle_shipper_connection(self, client_socket: socket.socket, address: tuple):
        """Handle connections from shipper"""
        logger.info(f"Shipper connection from {address}")
        
        try:
            # Receive shipment data
            data = b''
            while True:
                chunk = client_socket.recv(BUFFER_SIZE)
                if not chunk:
                    break
                data += chunk
            
            message = json.loads(data.decode())
            
            if message['type'] == 'shipment_initiated':
                payload = message['payload']
                transaction_id = payload['transaction']['id']
                
                # Validate signature
                if not self.validator.validate_signature(payload):
                    response = {
                        'status': 'error',
                        'error': 'Invalid signature'
                    }
                else:
                    # Store in bridge
                    self.bridge.active_transactions[transaction_id] = {
                        'payload': payload,
                        'status': 'pending_carrier',
                        'received_at': datetime.datetime.utcnow().isoformat() + 'Z'
                    }
                    
                    # Broadcast to carriers
                    asyncio.run(self.bridge.broadcast_to_carriers({
                        'type': 'new_shipment',
                        'transaction_id': transaction_id,
                        'payload': payload
                    }))
                    
                    logger.info(f"Shipment {transaction_id} received and broadcasted")
                    
                    response = {
                        'status': 'success',
                        'transaction_id': transaction_id
                    }
                
                client_socket.sendall(json.dumps(response).encode())
                
        except Exception as e:
            logger.error(f"Error handling shipper connection: {e}")
            error_response = {
                'status': 'error',
                'error': str(e)
            }
            client_socket.sendall(json.dumps(error_response).encode())
        
        finally:
            client_socket.close()
    
    def handle_nfc_receiver(self, client_socket: socket.socket, address: tuple):
        """Handle NFC data reception from carrier"""
        logger.info(f"NFC receiver connection from {address}")
        
        try:
            # Receive NFC payload
            data = b''
            while True:
                chunk = client_socket.recv(BUFFER_SIZE)
                if not chunk:
                    break
                data += chunk
            
            nfc_data = json.loads(data.decode())
            
            if nfc_data['type'] == 'nfc_delivery':
                payload = nfc_data['payload']
                transaction_id = payload['transaction']['id']
                
                # Validate signature
                if not self.validator.validate_signature(payload):
                    response = {
                        'status': 'error',
                        'error': 'Invalid signature'
                    }
                else:
                    # Validate PO
                    po_number = payload['erp_identifiers']['receiver']['po_number']
                    if not self.sap.validate_po(po_number):
                        response = {
                            'status': 'error',
                            'error': 'Invalid PO number'
                        }
                    else:
                        # Process delivery
                        gr_number = self.sap.create_goods_receipt(payload)
                        
                        # Update inventory
                        self.sap.update_inventory(payload['packing_slip']['items'])
                        
                        # Trigger payment release
                        invoice_number = payload['commercial_invoice']['number']
                        payment_released = self.sap.trigger_payment_release(invoice_number, gr_number)
                        
                        # Update transaction status
                        if transaction_id in self.bridge.active_transactions:
                            self.bridge.active_transactions[transaction_id]['status'] = 'completed'
                            self.bridge.active_transactions[transaction_id]['gr_number'] = gr_number
                            self.bridge.active_transactions[transaction_id]['payment_released'] = payment_released
                        
                        # Store processed transaction
                        self.processed_transactions[transaction_id] = {
                            'payload': payload,
                            'gr_number': gr_number,
                            'processed_at': datetime.datetime.utcnow().isoformat() + 'Z',
                            'payment_released': payment_released
                        }
                        
                        logger.info(f"Transaction {transaction_id} completed successfully")
                        
                        response = {
                            'status': 'success',
                            'transaction_id': transaction_id,
                            'gr_number': gr_number,
                            'payment_released': payment_released
                        }
                
                client_socket.sendall(json.dumps(response).encode())
                
        except Exception as e:
            logger.error(f"Error handling NFC receiver: {e}")
            error_response = {
                'status': 'error',
                'error': str(e)
            }
            client_socket.sendall(json.dumps(error_response).encode())
        
        finally:
            client_socket.close()
    
    def start_bridge_server(self):
        """Start the bridge server for shipper connections"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((BRIDGE_HOST, BRIDGE_PORT))
        server_socket.listen(5)
        
        logger.info(f"Bridge server listening on {BRIDGE_HOST}:{BRIDGE_PORT}")
        
        while True:
            client_socket, address = server_socket.accept()
            client_thread = threading.Thread(
                target=self.handle_shipper_connection,
                args=(client_socket, address)
            )
            client_thread.start()
    
    def start_nfc_server(self):
        """Start the NFC receiver server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((RECEIVER_HOST, NFC_RECEIVER_PORT))
        server_socket.listen(5)
        
        logger.info(f"NFC receiver server listening on {RECEIVER_HOST}:{NFC_RECEIVER_PORT}")
        
        while True:
            client_socket, address = server_socket.accept()
            client_thread = threading.Thread(
                target=self.handle_nfc_receiver,
                args=(client_socket, address)
            )
            client_thread.start()
    
    def get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get status of a transaction"""
        if transaction_id in self.bridge.active_transactions:
            return self.bridge.active_transactions[transaction_id]
        elif transaction_id in self.processed_transactions:
            return self.processed_transactions[transaction_id]
        else:
            return {'status': 'not_found'}
    
    def start(self):
        """Start all server components"""
        # Start WebSocket server in separate thread
        ws_thread = threading.Thread(target=self.bridge.start_websocket_server)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Start NFC server in separate thread
        nfc_thread = threading.Thread(target=self.start_nfc_server)
        nfc_thread.daemon = True
        nfc_thread.start()
        
        # Start bridge server (main thread)
        try:
            self.start_bridge_server()
        except KeyboardInterrupt:
            logger.info("Shutting down receiver/bridge server...")

def main():
    """Main entry point"""
    server = ReceiverServer()
    server.start()

if __name__ == "__main__":
    main()