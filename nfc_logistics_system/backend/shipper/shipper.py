"""
Shipper Backend for NFC Logistics System
Handles shipment initiation and ERP integration with Infor SyteLine
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
        logging.FileHandler('shipper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ShipperBackend:
    """Shipper backend server for NFC logistics system"""
    
    def __init__(self, host: str = 'localhost', port: int = 65432):
        self.host = host
        self.port = port
        self.security_manager = SecurityManager()
        self.erp_integration = None
        self.server_socket = None
        self.running = False
        self.active_connections = []
        
        # Initialize ERP integration
        self._initialize_erp()
    
    def _initialize_erp(self):
        """Initialize ERP integration with Infor SyteLine"""
        try:
            config = MOCK_ERP_CONFIGS['infor_syteline']
            self.erp_integration = ERPIntegrationFactory.create_integration('infor_syteline', config)
            
            # Authenticate with ERP
            if self.erp_integration.authenticate():
                logger.info("Successfully connected to Infor SyteLine ERP")
            else:
                logger.error("Failed to authenticate with Infor SyteLine ERP")
                
        except Exception as e:
            logger.error(f"Failed to initialize ERP integration: {e}")
    
    def generate_shipment_payload(self, shipment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complete shipment payload from ERP data"""
        try:
            # Create base payload structure
            payload = {
                'transaction': {
                    'transaction_id': self.security_manager.generate_transaction_id('SHP'),
                    'status': 'initiated',
                    'timestamp': datetime.now().isoformat() + 'Z',
                    'location': {
                        'latitude': 40.1264,  # Westerville, OH coordinates
                        'longitude': -82.9291,
                        'address': '123 Logistics Way',
                        'city': 'Westerville',
                        'state': 'OH',
                        'zip_code': '43081'
                    }
                },
                'packing_slip': {
                    'items': shipment_data.get('items', []),
                    'total_weight': shipment_data.get('total_weight', 0.0),
                    'total_items': sum(item.get('quantity', 0) for item in shipment_data.get('items', [])),
                    'pallet_count': shipment_data.get('pallet_count', 1)
                },
                'bill_of_lading': {
                    'bol_number': shipment_data.get('bol_number', ''),
                    'carrier_name': shipment_data.get('carrier_name', 'Westerville Logistics'),
                    'carrier_id': shipment_data.get('carrier_id', 'CARRIER-001'),
                    'transit_type': shipment_data.get('transit_type', 'truck'),
                    'origin': shipment_data.get('origin', 'Westerville, OH'),
                    'destination': shipment_data.get('destination', ''),
                    'pickup_date': shipment_data.get('pickup_date', datetime.now().isoformat() + 'Z'),
                    'delivery_date': shipment_data.get('delivery_date', '')
                },
                'batch_details': {
                    'batch_id': shipment_data.get('batch_id', ''),
                    'manufacture_date': shipment_data.get('manufacture_date', ''),
                    'expiry_date': shipment_data.get('expiry_date', ''),
                    'batch_size': shipment_data.get('batch_size', 0),
                    'quality_grade': shipment_data.get('quality_grade', 'A')
                },
                'commercial_invoice': {
                    'invoice_number': shipment_data.get('invoice_number', ''),
                    'total_value': shipment_data.get('total_value', 0.0),
                    'currency': shipment_data.get('currency', 'USD'),
                    'payment_terms': shipment_data.get('payment_terms', 'Net 30'),
                    'incoterms': shipment_data.get('incoterms', 'FOB'),
                    'tax_amount': shipment_data.get('tax_amount', 0.0)
                },
                'erp_identifiers': {
                    'shipper_erp_id': 'SHIPPER-001',
                    'shipper_erp_type': 'infor_syteline',
                    'receiver_erp_id': shipment_data.get('receiver_erp_id', ''),
                    'receiver_erp_type': shipment_data.get('receiver_erp_type', 'sap'),
                    'carrier_erp_id': shipment_data.get('carrier_erp_id', 'CARRIER-001')
                },
                'metadata': {
                    'version': '1.0',
                    'created_by': 'shipper_system',
                    'last_modified': datetime.now().isoformat() + 'Z',
                    'priority': shipment_data.get('priority', 'normal'),
                    'special_instructions': shipment_data.get('special_instructions', '')
                }
            }
            
            # Create secure payload with digital signature
            secure_payload = self.security_manager.create_secure_payload(payload)
            
            logger.info(f"Generated secure payload for transaction {secure_payload['transaction']['transaction_id']}")
            return secure_payload
            
        except Exception as e:
            logger.error(f"Failed to generate shipment payload: {e}")
            raise
    
    def create_shipment_in_erp(self, shipment_data: Dict[str, Any]) -> str:
        """Create shipment in Infor SyteLine ERP"""
        try:
            if not self.erp_integration:
                raise Exception("ERP integration not initialized")
            
            # Create shipment in ERP
            shipment_id = self.erp_integration.create_shipment(shipment_data)
            
            # Update inventory levels
            for item in shipment_data.get('items', []):
                self.erp_integration.update_inventory(
                    item['item_id'],
                    item['quantity'],
                    'subtract'  # Remove from shipper inventory
                )
            
            logger.info(f"Created shipment {shipment_id} in Infor SyteLine ERP")
            return shipment_id
            
        except Exception as e:
            logger.error(f"Failed to create shipment in ERP: {e}")
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
            
            if request_type == 'create_shipment':
                return await self._handle_create_shipment(request)
            elif request_type == 'get_shipment_status':
                return await self._handle_get_shipment_status(request)
            elif request_type == 'update_shipment':
                return await self._handle_update_shipment(request)
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
    
    async def _handle_create_shipment(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shipment creation request"""
        try:
            shipment_data = request.get('shipment_data', {})
            
            # Create shipment in ERP
            shipment_id = self.create_shipment_in_erp(shipment_data)
            
            # Generate secure payload
            payload = self.generate_shipment_payload(shipment_data)
            
            # Update shipment ID in payload
            payload['bill_of_lading']['bol_number'] = shipment_id
            
            return {
                'status': 'success',
                'message': 'Shipment created successfully',
                'shipment_id': shipment_id,
                'payload': payload,
                'timestamp': datetime.now().isoformat() + 'Z'
            }
            
        except Exception as e:
            logger.error(f"Failed to create shipment: {e}")
            return {
                'status': 'error',
                'message': f'Failed to create shipment: {str(e)}',
                'timestamp': datetime.now().isoformat() + 'Z'
            }
    
    async def _handle_get_shipment_status(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shipment status request"""
        try:
            shipment_id = request.get('shipment_id')
            
            if not shipment_id:
                return {
                    'status': 'error',
                    'message': 'Shipment ID is required',
                    'timestamp': datetime.now().isoformat() + 'Z'
                }
            
            # Get status from ERP (mock implementation)
            status = 'in_transit'  # This would come from ERP
            
            return {
                'status': 'success',
                'shipment_id': shipment_id,
                'shipment_status': status,
                'timestamp': datetime.now().isoformat() + 'Z'
            }
            
        except Exception as e:
            logger.error(f"Failed to get shipment status: {e}")
            return {
                'status': 'error',
                'message': f'Failed to get shipment status: {str(e)}',
                'timestamp': datetime.now().isoformat() + 'Z'
            }
    
    async def _handle_update_shipment(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shipment update request"""
        try:
            shipment_id = request.get('shipment_id')
            new_status = request.get('status')
            
            if not shipment_id or not new_status:
                return {
                    'status': 'error',
                    'message': 'Shipment ID and status are required',
                    'timestamp': datetime.now().isoformat() + 'Z'
                }
            
            # Update status in ERP
            if self.erp_integration:
                success = self.erp_integration.update_shipment_status(shipment_id, new_status)
                
                if success:
                    return {
                        'status': 'success',
                        'message': f'Shipment {shipment_id} status updated to {new_status}',
                        'timestamp': datetime.now().isoformat() + 'Z'
                    }
                else:
                    return {
                        'status': 'error',
                        'message': f'Failed to update shipment status in ERP',
                        'timestamp': datetime.now().isoformat() + 'Z'
                    }
            else:
                return {
                    'status': 'error',
                    'message': 'ERP integration not available',
                    'timestamp': datetime.now().isoformat() + 'Z'
                }
                
        except Exception as e:
            logger.error(f"Failed to update shipment: {e}")
            return {
                'status': 'error',
                'message': f'Failed to update shipment: {str(e)}',
                'timestamp': datetime.now().isoformat() + 'Z'
            }
    
    async def start_server(self):
        """Start the shipper server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.setblocking(False)
            
            self.running = True
            logger.info(f"Shipper server started on {self.host}:{self.port}")
            
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
        """Stop the shipper server"""
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
        
        logger.info("Shipper server stopped")

async def main():
    """Main function to run the shipper server"""
    shipper = ShipperBackend()
    
    try:
        await shipper.start_server()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    finally:
        shipper.stop_server()

if __name__ == "__main__":
    asyncio.run(main())