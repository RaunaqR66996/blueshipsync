#!/usr/bin/env python3
"""
Test Client for NFC Logistics System
Demonstrates the complete workflow from shipment creation to delivery
"""

import socket
import json
import time
import sys
from datetime import datetime

def create_shipment(order_id="SO-2024-TEST001"):
    """Create a new shipment through the shipper server"""
    print(f"\n[SHIPPER] Creating shipment for order: {order_id}")
    
    try:
        # Connect to shipper server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 65432))
        
        # Create shipment request
        request = {
            'action': 'create_shipment',
            'order_id': order_id
        }
        
        # Send request
        sock.sendall(json.dumps(request).encode())
        
        # Get response
        response_data = sock.recv(4096).decode()
        response = json.loads(response_data)
        
        if response['status'] == 'success':
            print(f"[SHIPPER] ✓ Shipment created successfully!")
            print(f"[SHIPPER] Transaction ID: {response['transaction_id']}")
            print(f"[SHIPPER] Message: {response['message']}")
            return response['transaction_id']
        else:
            print(f"[SHIPPER] ✗ Error: {response['message']}")
            return None
            
    except Exception as e:
        print(f"[SHIPPER] ✗ Connection error: {e}")
        return None
    finally:
        sock.close()

def check_shipment_status(transaction_id):
    """Check the status of a shipment"""
    print(f"\n[SHIPPER] Checking status for transaction: {transaction_id}")
    
    try:
        # Connect to shipper server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 65432))
        
        # Create status request
        request = {
            'action': 'get_status',
            'transaction_id': transaction_id
        }
        
        # Send request
        sock.sendall(json.dumps(request).encode())
        
        # Get response
        response_data = sock.recv(4096).decode()
        response = json.loads(response_data)
        
        if response['status'] == 'success':
            print(f"[SHIPPER] Shipment Status: {response['shipment_status']}")
            print(f"[SHIPPER] Last Update: {response['last_update']}")
        else:
            print(f"[SHIPPER] ✗ Error: {response['message']}")
            
    except Exception as e:
        print(f"[SHIPPER] ✗ Connection error: {e}")
    finally:
        sock.close()

def simulate_nfc_delivery(transaction_id):
    """Simulate NFC delivery at receiver location"""
    print(f"\n[CARRIER] Simulating NFC tap for delivery...")
    
    # In real scenario, this would be done by the Android app
    # Here we'll create a mock payload to demonstrate
    
    mock_payload = {
        "type": "nfc_delivery",
        "payload": {
            "transaction": {
                "id": transaction_id,
                "status": "delivered",
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "location": {
                    "latitude": 40.1263,
                    "longitude": -82.9290,
                    "address": "456 Receiver Dock, Westerville, OH 43081"
                }
            },
            "packing_slip": {
                "items": [
                    {
                        "sku": "PART-001",
                        "description": "Industrial Component A",
                        "quantity": 100,
                        "weight": 50.5,
                        "unit": "kg"
                    }
                ],
                "total_weight": 50.5,
                "weight_unit": "kg"
            },
            "bol": {
                "number": "BOL-2024-TEST",
                "date": datetime.utcnow().isoformat() + 'Z',
                "carrier_name": "Express Logistics LLC",
                "carrier_id": "CARR-OH-123"
            },
            "batch_details": {
                "batch_id": "BATCH-2024-Q1-001",
                "manufacture_date": "2024-01-01T00:00:00Z",
                "expiry_date": "2025-01-01T00:00:00Z",
                "lot_numbers": ["LOT-A123"]
            },
            "commercial_invoice": {
                "number": "INV-2024-TEST",
                "date": datetime.utcnow().isoformat() + 'Z',
                "total_value": 15000.00,
                "currency": "USD",
                "terms": "NET30"
            },
            "logistics": {
                "pallet_count": 2,
                "transit_type": "truck",
                "vehicle_id": "TRUCK-OH-456",
                "driver_id": "DRV-789"
            },
            "erp_identifiers": {
                "shipper": {
                    "system": "Infor SyteLine",
                    "company_id": "SHIP-001",
                    "order_id": "SO-2024-TEST001"
                },
                "receiver": {
                    "system": "SAP",
                    "company_id": "REC-001",
                    "po_number": "PO-2024-5678"
                }
            },
            "security": {
                "digital_signature": "MOCK-SIGNATURE",
                "signature_algorithm": "ECDSA-SHA256",
                "signature_timestamp": datetime.utcnow().isoformat() + 'Z',
                "public_key_id": "KEY-SHIP-001",
                "public_key": "MOCK-PUBLIC-KEY"
            }
        }
    }
    
    try:
        # Connect to NFC receiver
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 65435))
        
        # Send NFC payload
        sock.sendall(json.dumps(mock_payload).encode())
        
        # Get response
        response_data = sock.recv(4096).decode()
        response = json.loads(response_data)
        
        if response['status'] == 'success':
            print(f"[RECEIVER] ✓ Delivery processed successfully!")
            print(f"[RECEIVER] Goods Receipt: {response['gr_number']}")
            print(f"[RECEIVER] Payment Released: {response['payment_released']}")
        else:
            print(f"[RECEIVER] ✗ Error: {response['error']}")
            
    except Exception as e:
        print(f"[RECEIVER] ✗ Connection error: {e}")
    finally:
        sock.close()

def main():
    """Run the complete test workflow"""
    print("=" * 60)
    print("NFC LOGISTICS SYSTEM - TEST CLIENT")
    print("=" * 60)
    print("\nThis test demonstrates the complete workflow:")
    print("1. Shipper creates shipment from ERP data")
    print("2. Payload sent to Blue Ships Sync bridge")
    print("3. Carrier receives via WebSocket (simulated)")
    print("4. NFC delivery at receiver location")
    print("5. Receiver validates and updates ERP")
    
    input("\nPress Enter to start the test workflow...")
    
    # Step 1: Create shipment
    transaction_id = create_shipment()
    if not transaction_id:
        print("\n✗ Failed to create shipment. Ensure shipper server is running.")
        return
    
    # Wait a moment
    time.sleep(2)
    
    # Step 2: Check status
    check_shipment_status(transaction_id)
    
    # Step 3: Simulate carrier activities
    print(f"\n[CARRIER] In real scenario:")
    print(f"[CARRIER] - App receives shipment via WebSocket")
    print(f"[CARRIER] - Driver adds to Google Wallet")
    print(f"[CARRIER] - Status changes to 'in_transit'")
    
    input("\nPress Enter to simulate NFC delivery...")
    
    # Step 4: Simulate NFC delivery
    simulate_nfc_delivery(transaction_id)
    
    print("\n" + "=" * 60)
    print("TEST WORKFLOW COMPLETED")
    print("=" * 60)
    print("\nIn production:")
    print("- Real ERP APIs would be called")
    print("- Android app would handle NFC communication")
    print("- Digital signatures would be properly validated")
    print("- All data would be synchronized in real-time")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python test_client.py")
        print("\nEnsure the following services are running:")
        print("1. python receiver_bridge.py (Bridge/Receiver)")
        print("2. python shipper.py (Shipper)")
    else:
        main()