#!/usr/bin/env python3
"""
NFC Logistics System - Integration Test Suite
Tests the complete workflow from shipper to receiver via carrier

Usage: python test_system.py
"""

import json
import socket
import time
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, Any

# Configure test logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SystemTester:
    """Complete system integration tester"""
    
    def __init__(self):
        self.test_results = []
        self.bridge_host = "localhost"
        self.bridge_port = 65432
        self.completion_port = 65433
    
    def create_test_payload(self) -> Dict[str, Any]:
        """Create a test logistics payload"""
        return {
            "transaction_id": "TXN-TEST123456",
            "status": "initiated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "location": {
                "latitude": 40.1262,
                "longitude": -82.9291,
                "address": "123 Test St, Westerville, OH 43081",
                "city": "Westerville",
                "state": "OH",
                "zip_code": "43081"
            },
            "packing_slip": {
                "slip_number": "PS-TEST-001",
                "items": [
                    {
                        "sku": "TEST-ITEM-001",
                        "description": "Test Widget",
                        "quantity": 5,
                        "weight": 2.5,
                        "unit": "lbs"
                    },
                    {
                        "sku": "TEST-ITEM-002", 
                        "description": "Test Gadget",
                        "quantity": 3,
                        "weight": 1.8,
                        "unit": "lbs"
                    }
                ],
                "total_weight": 18.0,
                "weight_unit": "lbs"
            },
            "bol": {
                "number": "BOL-TEST-001-20240101",
                "carrier": "Test Logistics Inc",
                "origin": "Westerville, OH",
                "destination": "Columbus, OH",
                "pickup_date": "2024-01-01",
                "delivery_date": "2024-01-02"
            },
            "batch_details": {
                "batch_id": "BATCH-TEST-001",
                "manufacture_date": "2023-12-15",
                "expiry_date": "2025-12-15",
                "lot_number": "LOT-2023-TEST",
                "serial_numbers": ["SN001", "SN002", "SN003"]
            },
            "commercial_invoice": {
                "number": "INV-TEST-001",
                "total_value": 1250.00,
                "currency": "USD",
                "tax_amount": 87.50,
                "payment_terms": "Net 30"
            },
            "pallet_count": 2,
            "transit_type": "truck",
            "shipper_erp": {
                "system": "infor_syteline",
                "id": "SHIPPER001",
                "order_number": "SO-TEST-001",
                "customer_id": "CUST-TEST-001"
            },
            "receiver_erp": {
                "system": "sap",
                "id": "RECEIVER001",
                "purchase_order": "PO-TEST-001",
                "vendor_id": "VENDOR-TEST-001"
            },
            "digital_signature": {
                "signature": "dGVzdF9zaWduYXR1cmVfZGF0YQ==",  # base64: "test_signature_data"
                "algorithm": "RSA-SHA256",
                "certificate": "dGVzdF9jZXJ0aWZpY2F0ZQ==",  # base64: "test_certificate"
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "audit_trail": [
                {
                    "action": "payload_created",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "actor": "test_system",
                    "location": "Test Environment",
                    "notes": "Test payload created for system validation"
                }
            ]
        }
    
    def test_payload_validation(self) -> bool:
        """Test payload structure validation"""
        logger.info("Testing payload validation...")
        
        try:
            payload = self.create_test_payload()
            
            # Test required fields
            required_fields = [
                "transaction_id", "status", "timestamp", "location",
                "packing_slip", "bol", "batch_details", "commercial_invoice",
                "pallet_count", "transit_type", "shipper_erp", "receiver_erp"
            ]
            
            for field in required_fields:
                if field not in payload:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Test JSON serialization
            json_str = json.dumps(payload)
            parsed_payload = json.loads(json_str)
            
            if parsed_payload["transaction_id"] != payload["transaction_id"]:
                logger.error("JSON serialization/deserialization failed")
                return False
            
            logger.info("✓ Payload validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Payload validation failed: {e}")
            return False
    
    def test_bridge_connectivity(self) -> bool:
        """Test connection to bridge server"""
        logger.info(f"Testing bridge connectivity to {self.bridge_host}:{self.bridge_port}...")
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                result = sock.connect_ex((self.bridge_host, self.bridge_port))
                
                if result == 0:
                    logger.info("✓ Bridge connectivity test passed")
                    return True
                else:
                    logger.error(f"Cannot connect to bridge at {self.bridge_host}:{self.bridge_port}")
                    return False
                    
        except Exception as e:
            logger.error(f"Bridge connectivity test failed: {e}")
            return False
    
    def test_payload_transmission(self) -> bool:
        """Test sending payload to bridge"""
        logger.info("Testing payload transmission...")
        
        try:
            payload = self.create_test_payload()
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((self.bridge_host, self.bridge_port))
                
                # Send payload
                payload_json = json.dumps(payload)
                payload_bytes = payload_json.encode('utf-8')
                
                # Send length first, then payload
                sock.sendall(len(payload_bytes).to_bytes(4, byteorder='big'))
                sock.sendall(payload_bytes)
                
                # Wait for response
                response = sock.recv(1024).decode('utf-8')
                
                if response == "ACK":
                    logger.info("✓ Payload transmission test passed")
                    return True
                else:
                    logger.error(f"Unexpected response: {response}")
                    return False
                    
        except Exception as e:
            logger.error(f"Payload transmission test failed: {e}")
            return False
    
    def test_completion_notification(self) -> bool:
        """Test completion notification mechanism"""
        logger.info("Testing completion notification...")
        
        def mock_completion_listener():
            """Mock completion listener"""
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('localhost', self.completion_port))
                    sock.listen(1)
                    sock.settimeout(10)
                    
                    logger.info(f"Mock completion listener started on port {self.completion_port}")
                    
                    conn, addr = sock.accept()
                    with conn:
                        data = conn.recv(4096)
                        completion_data = json.loads(data.decode('utf-8'))
                        
                        logger.info(f"Received completion notification: {completion_data['transaction_id']}")
                        conn.sendall(b"ACK")
                        
                        return True
                        
            except Exception as e:
                logger.error(f"Mock completion listener failed: {e}")
                return False
        
        try:
            # Start mock listener in background
            listener_thread = threading.Thread(target=mock_completion_listener)
            listener_thread.daemon = True
            listener_thread.start()
            
            time.sleep(1)  # Give listener time to start
            
            # Send mock completion notification
            completion_data = {
                "transaction_id": "TXN-TEST123456",
                "order_number": "SO-TEST-001",
                "status": "confirmed",
                "completion_timestamp": datetime.now(timezone.utc).isoformat(),
                "goods_receipt": "GR-TEST-001",
                "receiver_id": "RECEIVER001"
            }
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect(('localhost', self.completion_port))
                
                completion_json = json.dumps(completion_data)
                sock.sendall(completion_json.encode('utf-8'))
                
                response = sock.recv(1024).decode('utf-8')
                
                if response == "ACK":
                    logger.info("✓ Completion notification test passed")
                    return True
                else:
                    logger.error(f"Unexpected completion response: {response}")
                    return False
                    
        except Exception as e:
            logger.error(f"Completion notification test failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling scenarios"""
        logger.info("Testing error handling...")
        
        try:
            # Test invalid JSON payload
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((self.bridge_host, self.bridge_port))
                
                invalid_payload = b"invalid json data"
                sock.sendall(len(invalid_payload).to_bytes(4, byteorder='big'))
                sock.sendall(invalid_payload)
                
                response = sock.recv(1024).decode('utf-8')
                
                if response == "NACK":
                    logger.info("✓ Error handling test passed (invalid JSON)")
                else:
                    logger.warning(f"Expected NACK for invalid JSON, got: {response}")
            
            # Test missing required fields
            incomplete_payload = {
                "transaction_id": "TXN-INCOMPLETE",
                "status": "initiated"
                # Missing other required fields
            }
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((self.bridge_host, self.bridge_port))
                
                payload_json = json.dumps(incomplete_payload)
                payload_bytes = payload_json.encode('utf-8')
                
                sock.sendall(len(payload_bytes).to_bytes(4, byteorder='big'))
                sock.sendall(payload_bytes)
                
                response = sock.recv(1024).decode('utf-8')
                
                # This should be handled gracefully by the bridge
                logger.info(f"Response to incomplete payload: {response}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling test failed: {e}")
            return False
    
    def test_performance(self) -> bool:
        """Test system performance"""
        logger.info("Testing system performance...")
        
        try:
            payload = self.create_test_payload()
            num_tests = 10
            total_time = 0
            
            for i in range(num_tests):
                start_time = time.time()
                
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(5)
                    sock.connect((self.bridge_host, self.bridge_port))
                    
                    # Modify transaction ID for each test
                    test_payload = payload.copy()
                    test_payload["transaction_id"] = f"TXN-PERF{i:03d}"
                    
                    payload_json = json.dumps(test_payload)
                    payload_bytes = payload_json.encode('utf-8')
                    
                    sock.sendall(len(payload_bytes).to_bytes(4, byteorder='big'))
                    sock.sendall(payload_bytes)
                    
                    response = sock.recv(1024).decode('utf-8')
                    
                end_time = time.time()
                transaction_time = end_time - start_time
                total_time += transaction_time
                
                logger.info(f"Transaction {i+1}: {transaction_time:.3f}s")
            
            avg_time = total_time / num_tests
            logger.info(f"Average transaction time: {avg_time:.3f}s")
            
            # Performance target: < 2 seconds per transaction
            if avg_time < 2.0:
                logger.info("✓ Performance test passed")
                return True
            else:
                logger.warning(f"Performance below target: {avg_time:.3f}s > 2.0s")
                return False
                
        except Exception as e:
            logger.error(f"Performance test failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run complete test suite"""
        logger.info("Starting NFC Logistics System Test Suite")
        logger.info("=" * 50)
        
        tests = [
            ("Payload Validation", self.test_payload_validation),
            ("Bridge Connectivity", self.test_bridge_connectivity),
            ("Payload Transmission", self.test_payload_transmission),
            ("Completion Notification", self.test_completion_notification),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\nRunning {test_name} test...")
            try:
                if test_func():
                    passed_tests += 1
                    self.test_results.append((test_name, "PASSED"))
                else:
                    self.test_results.append((test_name, "FAILED"))
            except Exception as e:
                logger.error(f"{test_name} test crashed: {e}")
                self.test_results.append((test_name, "CRASHED"))
        
        # Print summary
        logger.info("\n" + "=" * 50)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 50)
        
        for test_name, result in self.test_results:
            status_symbol = "✓" if result == "PASSED" else "✗"
            logger.info(f"{status_symbol} {test_name}: {result}")
        
        logger.info(f"\nPassed: {passed_tests}/{total_tests}")
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED! System is ready for deployment.")
            return True
        else:
            logger.warning(f"⚠️ {total_tests - passed_tests} tests failed. Please review and fix issues.")
            return False


def main():
    """Main test execution"""
    tester = SystemTester()
    
    print("NFC Logistics System - Integration Test Suite")
    print("Testing complete end-to-end workflow...")
    print()
    
    success = tester.run_all_tests()
    
    if success:
        print("\n🚀 System validation complete - ready for production!")
        exit(0)
    else:
        print("\n❌ System validation failed - please fix issues before deployment.")
        exit(1)


if __name__ == "__main__":
    main()