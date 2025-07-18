"""
Receiver Bridge Backend for NFC Logistics System
Handles shipment completion and ERP integration with SAP
"""

import asyncio
import json
import logging
import socket
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
import threading
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.security import SecurityManager
from common.erp_integration import ERPIntegrationFactory, MOCK_ERP_CONFIGS, ERPConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('receiver_bridge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ReceiverBridge:
    """Receiver bridge server for NFC logistics system"""
    
    def __init__(self, host: str = 'localhost', port: int = 65433):
        self.host = host
        self.port = port
        self.security_manager = SecurityManager()
        self.erp_integration = None
        self.server_socket = None
        self.running = False
        self.active_connections = []
        self.pending_shipments = {}  # Track pending shipments
        
        # Initialize ERP integration
        self._initialize_erp()
    
    def _initialize_erp(self):
        """Initialize ERP integration with SAP"""
        try:
            config = MOCK_ERP_CONFIGS['sap']
            self.erp_integration = ERPIntegrationFactory.create_integration('sap', config)
            
            # Authenticate with ERP
            if self.erp_integration.authenticate():
                logger.info("Successfully connected to SAP ERP")
            else:
                logger.error("Failed to authenticate with SAP ERP")
                
        except Exception as e:
            logger.error(f"Failed to initialize ERP integration: {e}")
    
    def validate_payload(self, payload: Dict[str, Any]) -> tuple[bool, str]:
        """Validate received payload integrity and signature"""
        try:
            # Validate security
            is_valid, message = self.security_manager.validate_secure_payload(payload)
            if not is_valid:
                return False, f"Security validation failed: {message}"
            
            # Validate required fields
            required_sections = ['transaction', 'packing_slip', 'bill_of_lading', 'erp_identifiers']
            for section in required_sections:
                if section not in payload:
                    return False, f"Missing required section: {section}"
            
            # Validate transaction data
            transaction = payload.get('transaction', {})
            if not transaction.get('transaction_id'):
                return False, "Missing transaction ID"
            
            # Validate ERP identifiers
            erp_ids = payload.get('erp_identifiers', {})
            if not erp_ids.get('receiver_erp_id'):
                return False, "Missing receiver ERP ID"
            
            logger.info(f"Payload validation successful for transaction {transaction.get('transaction_id')}")
            return True, "Payload validation successful"
            
        except Exception as e:
            logger.error(f"Payload validation error: {e}")
            return False, f"Validation error: {str(e)}"
    
    def process_shipment_completion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process shipment completion and update ERP systems"""
        try:
            transaction_id = payload['transaction']['transaction_id']
            bol_number = payload['bill_of_lading']['bol_number']
            
            logger.info(f"Processing shipment completion for BOL: {bol_number}")
            
            # Update shipment status in SAP
            if self.erp_integration:
                success = self.erp_integration.update_shipment_status(bol_number, 'delivered')
                if not success:
                    raise Exception("Failed to update shipment status in SAP")
            
            # Update inventory in SAP
            packing_slip = payload.get('packing_slip', {})
            items = packing_slip.get('items', [])
            
            for item in items:
                success = self.erp_integration.update_inventory(
                    item['item_id'],
                    item['quantity'],
                    'add'  # Add to receiver inventory
                )
                if not success:
                    logger.warning(f"Failed to update inventory for item {item['item_id']}")
            
            # Release payment if commercial invoice exists
            commercial_invoice = payload.get('commercial_invoice', {})
            if commercial_invoice.get('invoice_number') and commercial_invoice.get('total_value'):
                payment_success = self.erp_integration.release_payment(
                    commercial_invoice['invoice_number'],
                    commercial_invoice['total_value']
                )
                if payment_success:
                    logger.info(f"Payment released for invoice {commercial_invoice['invoice_number']}")
                else:
                    logger.warning(f"Failed to release payment for invoice {commercial_invoice['invoice_number']}")
            
            # Create completion response
            completion_response = {
                'transaction': {
                    'transaction_id': transaction_id,
                    'status': 'completed',
                    'timestamp': datetime.now().isoformat() + 'Z',
                    'location': {
                        'latitude': 39.9612,  # Columbus, OH coordinates
                        'longitude': -82.9988,
                        'address': '456 Distribution Center Blvd',
                        'city': 'Columbus',
                        'state': 'OH',
                        'zip_code': '43215'
                    }
                },
                'shipment_details': {
                    'bol_number': bol_number,
                    'delivery_timestamp': datetime.now().isoformat() + 'Z',
                    'items_received': len(items),
                    'total_weight_received': packing_slip.get('total_weight', 0.0),
                    'pallet_count_received': packing_slip.get('pallet_count', 0)
                },
                'erp_identifiers': {
                    'receiver_erp_id': payload['erp_identifiers']['receiver_erp_id'],
                    'receiver_erp_type': payload['erp_identifiers']['receiver_erp_type']
                },
                'metadata': {
                    'version': '1.0',
                    'processed_by': 'receiver_bridge',
                    'processing_timestamp': datetime.now().isoformat() + 'Z'
                }
            }
            
            # Add security to completion response
            secure_completion = self.security_manager.create_secure_payload(completion_response)
            
            logger.info(f"Shipment completion processed successfully for BOL: {bol_number}")
            return secure_completion
            
        except Exception as e:
            logger.error(f"Failed to process shipment completion: {e}")
            raise
    
    async def handle_client(self, client_socket: socket.socket, address: tuple):
        """Handle individual client connections"""
        try:
            logger.info(f"Client connected from {address}")
            self.active_connections.append(client_socket)
            
            while self.running:
                # Receive data from client
                data = await asyncio.get_event_loop().run_in_executor(
                    None, client_socket.recv, 4096
                )
                
                if not data:
                    break
                
                # Parse received data
                try:
                    request = json.loads(data.decode('utf-8'))
                    response = await self.process_request(request)
                    
                    # Send response back to client
                    await asyncio.get_event_loop().run_in_executor(
                        None, client_socket.send, json.dumps(response).encode('utf-8')
                    )
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    error_response = {
                        'status': 'error',
                        'message': 'Invalid JSON format',
                        'timestamp': datetime.now().isoformat() + 'Z'
                    }
                    await asyncio.get_event_loop().run_in_executor(
                        None, client_socket.send, json.dumps(error_response).encode('utf-8')
                    )
                    
        except Exception as e:
            logger.error(f"Error handling client {address}: {e}")
        finally:
            if client_socket in self.active_connections:
                self.active_connections.remove(client_socket)
            client_socket.close()
            logger.info(f"Client {address} disconnected")
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests from clients"""
        try:
            request_type = request.get('type')
            
            if request_type == 'deliver_shipment':
                return await self._handle_deliver_shipment(request)
            elif request_type == 'validate_payload':
                return await self._handle_validate_payload(request)
            elif request_type == 'get_completion_status':
                return await self._handle_get_completion_status(request)
            else:
                return {
                    'status': 'error',
                    'message': f'Unknown request type: {request_type}',
                    'timestamp': datetime.now().isoformat() + 'Z'
                }
                
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat() + 'Z'
            }
    
    async def _handle_deliver_shipment(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shipment delivery request"""
        try:
            payload = request.get('payload', {})
            
            # Validate payload
            is_valid, message = self.validate_payload(payload)
            if not is_valid:
                return {
                    'status': 'error',
                    'message': f'Payload validation failed: {message}',
                    'timestamp': datetime.now().isoformat() + 'Z'
                }
            
            # Process shipment completion
            completion_response = self.process_shipment_completion(payload)
            
            # Store completion for tracking
            transaction_id = payload['transaction']['transaction_id']
            self.pending_shipments[transaction_id] = {
                'status': 'completed',
                'completion_time': datetime.now().isoformat() + 'Z',
                'bol_number': payload['bill_of_lading']['bol_number']
            }
            
            return {
                'status': 'success',
                'message': 'Shipment delivered and processed successfully',
                'completion_data': completion_response,
                'timestamp': datetime.now().isoformat() + 'Z'
            }
            
        except Exception as e:
            logger.error(f"Failed to process shipment delivery: {e}")
            return {
                'status': 'error',
                'message': f'Failed to process shipment delivery: {str(e)}',
                'timestamp': datetime.now().isoformat() + 'Z'
            }
    
    async def _handle_validate_payload(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payload validation request"""
        try:
            payload = request.get('payload', {})
            
            # Validate payload
            is_valid, message = self.validate_payload(payload)
            
            return {
                'status': 'success' if is_valid else 'error',
                'message': message,
                'valid': is_valid,
                'timestamp': datetime.now().isoformat() + 'Z'
            }
            
        except Exception as e:
            logger.error(f"Failed to validate payload: {e}")
            return {
                'status': 'error',
                'message': f'Failed to validate payload: {str(e)}',
                'timestamp': datetime.now().isoformat() + 'Z'
            }
    
    async def _handle_get_completion_status(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle completion status request"""
        try:
            transaction_id = request.get('transaction_id')
            
            if not transaction_id:
                return {
                    'status': 'error',
                    'message': 'Transaction ID is required',
                    'timestamp': datetime.now().isoformat() + 'Z'
                }
            
            # Check if transaction exists in pending shipments
            if transaction_id in self.pending_shipments:
                shipment_info = self.pending_shipments[transaction_id]
                return {
                    'status': 'success',
                    'transaction_id': transaction_id,
                    'shipment_status': shipment_info['status'],
                    'completion_time': shipment_info['completion_time'],
                    'bol_number': shipment_info['bol_number'],
                    'timestamp': datetime.now().isoformat() + 'Z'
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Transaction {transaction_id} not found',
                    'timestamp': datetime.now().isoformat() + 'Z'
                }
                
        except Exception as e:
            logger.error(f"Failed to get completion status: {e}")
            return {
                'status': 'error',
                'message': f'Failed to get completion status: {str(e)}',
                'timestamp': datetime.now().isoformat() + 'Z'
            }
    
    async def start_server(self):
        """Start the receiver bridge server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.setblocking(False)
            
            self.running = True
            logger.info(f"Receiver bridge server started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = await asyncio.get_event_loop().run_in_executor(
                        None, self.server_socket.accept
                    )
                    
                    # Handle client in separate task
                    asyncio.create_task(self.handle_client(client_socket, address))
                    
                except BlockingIOError:
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Error accepting connection: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
        finally:
            self.stop_server()
    
    def stop_server(self):
        """Stop the receiver bridge server"""
        self.running = False
        
        # Close all client connections
        for client_socket in self.active_connections:
            try:
                client_socket.close()
            except:
                pass
        self.active_connections.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        logger.info("Receiver bridge server stopped")

async def main():
    """Main function to run the receiver bridge server"""
    receiver_bridge = ReceiverBridge()
    
    try:
        await receiver_bridge.start_server()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    finally:
        receiver_bridge.stop_server()

if __name__ == "__main__":
    asyncio.run(main())