"""
ERP Integration module for NFC Logistics System
Handles integration with various ERP systems (Infor SyteLine, SAP, etc.)
"""

import json
import logging
import requests
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ERPConfig:
    """Configuration for ERP system connection"""
    base_url: str
    api_key: str
    username: str
    password: str
    timeout: int = 30
    retry_attempts: int = 3

class ERPIntegrationError(Exception):
    """Custom exception for ERP integration errors"""
    pass

class BaseERPIntegration(ABC):
    """Abstract base class for ERP integrations"""
    
    def __init__(self, config: ERPConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {config.api_key}'
        })
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with ERP system"""
        pass
    
    @abstractmethod
    def get_inventory_levels(self, item_ids: List[str]) -> Dict[str, int]:
        """Get current inventory levels for items"""
        pass
    
    @abstractmethod
    def update_inventory(self, item_id: str, quantity: int, operation: str) -> bool:
        """Update inventory levels"""
        pass
    
    @abstractmethod
    def create_shipment(self, shipment_data: Dict[str, Any]) -> str:
        """Create shipment in ERP system"""
        pass
    
    @abstractmethod
    def update_shipment_status(self, shipment_id: str, status: str) -> bool:
        """Update shipment status"""
        pass
    
    @abstractmethod
    def release_payment(self, invoice_id: str, amount: float) -> bool:
        """Release payment for invoice"""
        pass
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        url = f"{self.config.base_url}{endpoint}"
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == self.config.retry_attempts - 1:
                    raise ERPIntegrationError(f"Request failed after {self.config.retry_attempts} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def _handle_erp_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ERP system response and extract data"""
        if 'error' in response:
            raise ERPIntegrationError(f"ERP Error: {response['error']}")
        return response.get('data', response)

class InforSyteLineIntegration(BaseERPIntegration):
    """Integration with Infor SyteLine ERP system"""
    
    def authenticate(self) -> bool:
        """Authenticate with Infor SyteLine"""
        try:
            auth_data = {
                'username': self.config.username,
                'password': self.config.password,
                'grant_type': 'password'
            }
            
            response = self._make_request('POST', '/auth/token', auth_data)
            token = response.get('access_token')
            
            if token:
                self.session.headers.update({'Authorization': f'Bearer {token}'})
                logger.info("Successfully authenticated with Infor SyteLine")
                return True
            else:
                logger.error("Failed to obtain access token from Infor SyteLine")
                return False
                
        except Exception as e:
            logger.error(f"Infor SyteLine authentication failed: {e}")
            return False
    
    def get_inventory_levels(self, item_ids: List[str]) -> Dict[str, int]:
        """Get current inventory levels from Infor SyteLine"""
        try:
            endpoint = '/inventory/levels'
            data = {'item_ids': item_ids}
            
            response = self._make_request('POST', endpoint, data)
            response_data = self._handle_erp_response(response)
            
            inventory_levels = {}
            for item in response_data.get('items', []):
                inventory_levels[item['item_id']] = item['quantity']
            
            logger.info(f"Retrieved inventory levels for {len(item_ids)} items")
            return inventory_levels
            
        except Exception as e:
            logger.error(f"Failed to get inventory levels from Infor SyteLine: {e}")
            return {}
    
    def update_inventory(self, item_id: str, quantity: int, operation: str) -> bool:
        """Update inventory in Infor SyteLine"""
        try:
            endpoint = '/inventory/update'
            data = {
                'item_id': item_id,
                'quantity': quantity,
                'operation': operation,  # 'add', 'subtract', 'set'
                'timestamp': datetime.now().isoformat()
            }
            
            response = self._make_request('POST', endpoint, data)
            self._handle_erp_response(response)
            
            logger.info(f"Successfully updated inventory for item {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update inventory in Infor SyteLine: {e}")
            return False
    
    def create_shipment(self, shipment_data: Dict[str, Any]) -> str:
        """Create shipment in Infor SyteLine"""
        try:
            endpoint = '/shipments/create'
            
            # Format shipment data for Infor SyteLine
            formatted_data = {
                'shipment_number': shipment_data.get('bol_number'),
                'origin_warehouse': shipment_data.get('origin'),
                'destination_warehouse': shipment_data.get('destination'),
                'carrier_id': shipment_data.get('carrier_id'),
                'items': shipment_data.get('packing_slip', {}).get('items', []),
                'total_weight': shipment_data.get('packing_slip', {}).get('total_weight'),
                'pickup_date': shipment_data.get('pickup_date'),
                'delivery_date': shipment_data.get('delivery_date')
            }
            
            response = self._make_request('POST', endpoint, formatted_data)
            response_data = self._handle_erp_response(response)
            
            shipment_id = response_data.get('shipment_id')
            logger.info(f"Created shipment in Infor SyteLine: {shipment_id}")
            return shipment_id
            
        except Exception as e:
            logger.error(f"Failed to create shipment in Infor SyteLine: {e}")
            raise ERPIntegrationError(f"Shipment creation failed: {e}")
    
    def update_shipment_status(self, shipment_id: str, status: str) -> bool:
        """Update shipment status in Infor SyteLine"""
        try:
            endpoint = f'/shipments/{shipment_id}/status'
            data = {
                'status': status,
                'timestamp': datetime.now().isoformat()
            }
            
            response = self._make_request('PUT', endpoint, data)
            self._handle_erp_response(response)
            
            logger.info(f"Updated shipment {shipment_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update shipment status in Infor SyteLine: {e}")
            return False
    
    def release_payment(self, invoice_id: str, amount: float) -> bool:
        """Release payment in Infor SyteLine"""
        try:
            endpoint = '/payments/release'
            data = {
                'invoice_id': invoice_id,
                'amount': amount,
                'payment_date': datetime.now().isoformat(),
                'payment_method': 'automated'
            }
            
            response = self._make_request('POST', endpoint, data)
            self._handle_erp_response(response)
            
            logger.info(f"Released payment for invoice {invoice_id}: ${amount}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to release payment in Infor SyteLine: {e}")
            return False

class SAPIntegration(BaseERPIntegration):
    """Integration with SAP ERP system"""
    
    def authenticate(self) -> bool:
        """Authenticate with SAP"""
        try:
            auth_data = {
                'client': '100',
                'username': self.config.username,
                'password': self.config.password,
                'language': 'EN'
            }
            
            response = self._make_request('POST', '/sap/auth', auth_data)
            session_id = response.get('session_id')
            
            if session_id:
                self.session.headers.update({'X-SAP-Session': session_id})
                logger.info("Successfully authenticated with SAP")
                return True
            else:
                logger.error("Failed to obtain session ID from SAP")
                return False
                
        except Exception as e:
            logger.error(f"SAP authentication failed: {e}")
            return False
    
    def get_inventory_levels(self, item_ids: List[str]) -> Dict[str, int]:
        """Get current inventory levels from SAP"""
        try:
            endpoint = '/sap/inventory/query'
            data = {
                'material_numbers': item_ids,
                'plant': '1000'  # Default plant
            }
            
            response = self._make_request('POST', endpoint, data)
            response_data = self._handle_erp_response(response)
            
            inventory_levels = {}
            for material in response_data.get('materials', []):
                inventory_levels[material['material_number']] = material['available_stock']
            
            logger.info(f"Retrieved inventory levels for {len(item_ids)} materials from SAP")
            return inventory_levels
            
        except Exception as e:
            logger.error(f"Failed to get inventory levels from SAP: {e}")
            return {}
    
    def update_inventory(self, item_id: str, quantity: int, operation: str) -> bool:
        """Update inventory in SAP"""
        try:
            endpoint = '/sap/inventory/movement'
            data = {
                'material_number': item_id,
                'quantity': quantity,
                'movement_type': self._map_operation_to_sap(operation),
                'plant': '1000',
                'storage_location': '0001',
                'posting_date': datetime.now().strftime('%Y%m%d')
            }
            
            response = self._make_request('POST', endpoint, data)
            self._handle_erp_response(response)
            
            logger.info(f"Successfully updated inventory for material {item_id} in SAP")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update inventory in SAP: {e}")
            return False
    
    def create_shipment(self, shipment_data: Dict[str, Any]) -> str:
        """Create shipment in SAP"""
        try:
            endpoint = '/sap/shipments/create'
            
            # Format shipment data for SAP
            formatted_data = {
                'delivery_number': shipment_data.get('bol_number'),
                'sold_to_party': shipment_data.get('receiver_erp_id'),
                'ship_to_party': shipment_data.get('receiver_erp_id'),
                'items': self._format_sap_items(shipment_data.get('packing_slip', {}).get('items', [])),
                'shipping_conditions': '01',  # Standard shipping
                'delivery_date': shipment_data.get('delivery_date')
            }
            
            response = self._make_request('POST', endpoint, formatted_data)
            response_data = self._handle_erp_response(response)
            
            delivery_number = response_data.get('delivery_number')
            logger.info(f"Created delivery in SAP: {delivery_number}")
            return delivery_number
            
        except Exception as e:
            logger.error(f"Failed to create shipment in SAP: {e}")
            raise ERPIntegrationError(f"Shipment creation failed: {e}")
    
    def update_shipment_status(self, shipment_id: str, status: str) -> bool:
        """Update shipment status in SAP"""
        try:
            endpoint = f'/sap/shipments/{shipment_id}/status'
            data = {
                'status': self._map_status_to_sap(status),
                'timestamp': datetime.now().isoformat()
            }
            
            response = self._make_request('PUT', endpoint, data)
            self._handle_erp_response(response)
            
            logger.info(f"Updated shipment {shipment_id} status to {status} in SAP")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update shipment status in SAP: {e}")
            return False
    
    def release_payment(self, invoice_id: str, amount: float) -> bool:
        """Release payment in SAP"""
        try:
            endpoint = '/sap/financial/payment'
            data = {
                'invoice_number': invoice_id,
                'amount': amount,
                'currency': 'USD',
                'payment_date': datetime.now().strftime('%Y%m%d'),
                'payment_method': 'BANK'
            }
            
            response = self._make_request('POST', endpoint, data)
            self._handle_erp_response(response)
            
            logger.info(f"Released payment for invoice {invoice_id}: ${amount} in SAP")
            return True
            
        except Exception as e:
            logger.error(f"Failed to release payment in SAP: {e}")
            return False
    
    def _map_operation_to_sap(self, operation: str) -> str:
        """Map operation to SAP movement type"""
        mapping = {
            'add': '261',      # Goods receipt
            'subtract': '262',  # Goods issue
            'set': '309'        # Transfer posting
        }
        return mapping.get(operation, '261')
    
    def _map_status_to_sap(self, status: str) -> str:
        """Map status to SAP delivery status"""
        mapping = {
            'initiated': 'A',      # Created
            'in_transit': 'B',     # Partially delivered
            'delivered': 'C',      # Completely delivered
            'completed': 'D'       # Completed
        }
        return mapping.get(status, 'A')
    
    def _format_sap_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format items for SAP delivery"""
        formatted_items = []
        for item in items:
            formatted_items.append({
                'material_number': item['item_id'],
                'quantity': item['quantity'],
                'unit': 'EA',  # Each
                'plant': '1000'
            })
        return formatted_items

class ERPIntegrationFactory:
    """Factory for creating ERP integration instances"""
    
    @staticmethod
    def create_integration(erp_type: str, config: ERPConfig) -> BaseERPIntegration:
        """Create ERP integration instance based on type"""
        if erp_type.lower() == 'infor_syteline':
            return InforSyteLineIntegration(config)
        elif erp_type.lower() == 'sap':
            return SAPIntegration(config)
        else:
            raise ValueError(f"Unsupported ERP type: {erp_type}")

# Mock ERP configurations for testing
MOCK_ERP_CONFIGS = {
    'infor_syteline': ERPConfig(
        base_url='https://mock-infor-syteline.example.com/api/v1',
        api_key='mock_infor_api_key_12345',
        username='shipper_user',
        password='shipper_pass',
        timeout=30,
        retry_attempts=3
    ),
    'sap': ERPConfig(
        base_url='https://mock-sap.example.com/api/v1',
        api_key='mock_sap_api_key_67890',
        username='receiver_user',
        password='receiver_pass',
        timeout=30,
        retry_attempts=3
    )
}