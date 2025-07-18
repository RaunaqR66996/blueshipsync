# NFC-Enabled Digital Handshake System for Logistics
## Complete Setup and Deployment Guide

### System Overview

This NFC-enabled digital handshake system automates the logistics workflow between three stakeholders:
- **Shipper**: Generates shipment data from ERP systems
- **Carrier**: Receives, transports, and delivers shipment data via NFC-enabled mobile app
- **Receiver**: Processes deliveries and integrates with destination ERP systems

The system reduces turnaround time from hours to minutes by eliminating manual paperwork and enabling real-time ERP synchronization.

---

## 📋 Prerequisites

### General Requirements
- Python 3.8+ for backend components
- Android Studio 2023.1+ for mobile app development
- Network connectivity between all components
- NFC-enabled Android device (API level 24+)

### Hardware Requirements
- **Shipper/Receiver Servers**: 4GB RAM, 50GB storage
- **Mobile Device**: NFC-enabled Android phone/tablet
- **NFC Tags**: NTAG213/215/216 or compatible

### Account Setup
- Google Cloud Console account (for Google Wallet integration)
- ERP system access credentials (Infor SyteLine, SAP)

---

## 🚀 Quick Start Deployment

### 1. Backend Setup (Shipper & Receiver)

#### Install Python Dependencies
```bash
# Create virtual environment
python -m venv nfc_logistics_env

# Activate environment
# Linux/Mac:
source nfc_logistics_env/bin/activate
# Windows:
nfc_logistics_env\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

#### Create `requirements.txt`:
```txt
requests==2.31.0
cryptography==41.0.7
jsonschema==4.20.0
sqlite3
```

#### Configure Shipper System
1. Edit `shipper.py` configuration:
```python
config = ShipperConfig(
    bridge_host="localhost",  # Change to receiver IP
    bridge_port=65432,
    erp_base_url="https://your-infor-api.com/v1",
    erp_api_key="your_api_key_here",
    erp_tenant="your_tenant_id",
    company_id="YOUR_COMPANY_ID"
)
```

2. Generate digital signature credentials:
```bash
# Generate private key
openssl genrsa -out shipper_private_key.pem 2048

# Generate self-signed certificate (for testing)
openssl req -new -x509 -key shipper_private_key.pem -out shipper_certificate.pem -days 365
```

#### Configure Receiver Bridge
1. Edit `receiver_bridge.py` configuration:
```python
config = ReceiverConfig(
    bridge_port=65432,
    sap_base_url="https://your-sap-api.com/v1",
    sap_username="NFC_LOGISTICS",
    sap_password="your_sap_password",
    company_id="YOUR_RECEIVER_ID"
)
```

2. Set up trusted shippers in `trusted_shippers.json`:
```json
{
  "SHIPPER001": {
    "name": "Your Shipping Partner",
    "certificate": "base64_encoded_certificate",
    "added_date": "2024-01-01T00:00:00Z"
  }
}
```

### 2. Android Carrier App Setup

#### Install Android Studio and Setup
1. Download Android Studio from https://developer.android.com/studio
2. Install Android SDK API level 34
3. Create Android Virtual Device (AVD) with NFC support or use physical device

#### Configure Google Wallet Integration
1. Go to Google Cloud Console
2. Enable Google Wallet API
3. Create service account and download JSON key
4. Add configuration to app:

```kotlin
// In MainActivity.kt
private val WALLET_ENVIRONMENT = WalletConstants.ENVIRONMENT_TEST // Change to PRODUCTION for live
```

#### Build and Install App
```bash
# Navigate to carrier app directory
cd carrier_app

# Build the app
./gradlew assembleDebug

# Install on connected device
./gradlew installDebug
```

### 3. Network Configuration

#### Port Configuration
- **Shipper Initiation**: Port 65432
- **Completion Notifications**: Port 65433
- **Bridge Communication**: Port 65432

#### Firewall Rules
```bash
# Allow bridge communication
sudo ufw allow 65432
sudo ufw allow 65433

# Allow HTTP/HTTPS for ERP integration
sudo ufw allow 80
sudo ufw allow 443
```

---

## 🔧 Detailed Configuration

### ERP Integration Setup

#### Infor SyteLine Configuration (Shipper)
1. Enable REST API access
2. Create dedicated user account for NFC system
3. Grant permissions for:
   - Order reading (`/orders/{order_number}`)
   - Inventory access (`/inventory/batch`)
   - Status updates (`/orders/{order_number}/status`)

Example ERP endpoint mapping:
```python
INFOR_ENDPOINTS = {
    "orders": "/SyteLine/api/sl/orders",
    "inventory": "/SyteLine/api/sl/inventory", 
    "status_update": "/SyteLine/api/sl/orders/{}/status"
}
```

#### SAP Configuration (Receiver)
1. Enable OData services
2. Configure RFC destinations
3. Set up user with appropriate authorizations:
   - MM (Materials Management)
   - FI (Financial) for payment release
   - SD (Sales & Distribution)

Example SAP OData services:
```bash
# Goods Receipt
POST /sap/opu/odata/sap/API_MATERIAL_DOCUMENT_SRV/A_MaterialDocumentHeader

# Purchase Order Update  
PATCH /sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder('{po_number}')

# Payment Release
POST /sap/opu/odata/sap/API_PAYMENTDOCUMENT_CREATE_SRV/A_PaymentDocument
```

### Security Configuration

#### Digital Signatures
1. Generate RSA key pairs for each shipper:
```bash
# Production key generation
openssl genrsa -aes256 -out shipper_private_key.pem 4096
openssl rsa -in shipper_private_key.pem -pubout -out shipper_public_key.pem
```

2. Certificate Authority setup (recommended for production):
```bash
# Create CA private key
openssl genrsa -aes256 -out ca_private_key.pem 4096

# Create CA certificate
openssl req -new -x509 -days 3650 -key ca_private_key.pem -out ca_certificate.pem
```

#### HTTPS Configuration
```bash
# Generate SSL certificate for bridge
openssl req -newkey rsa:2048 -nodes -keyout bridge_private_key.pem -x509 -days 365 -out bridge_certificate.pem
```

### Database Setup

#### Receiver Transaction Database
The receiver bridge automatically creates SQLite database. For production, consider PostgreSQL:

```sql
-- PostgreSQL schema
CREATE TABLE transactions (
    transaction_id VARCHAR(20) PRIMARY KEY,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL,
    received_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    processed_timestamp TIMESTAMP WITH TIME ZONE,
    shipper_id VARCHAR(50),
    order_number VARCHAR(50),
    carrier_name VARCHAR(100),
    total_value DECIMAL(15,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_transaction_status ON transactions(status);
CREATE INDEX idx_transaction_received ON transactions(received_timestamp);
```

---

## 🏃‍♂️ Running the System

### 1. Start Receiver Bridge
```bash
python receiver_bridge.py
```
Expected output:
```
2024-01-01 10:00:00 - INFO - NFC Receiver Bridge started on port 65432
2024-01-01 10:00:00 - INFO - Press Ctrl+C to stop...
```

### 2. Start Shipper System
```bash
python shipper.py
```

### 3. Launch Carrier App
1. Open app on NFC-enabled Android device
2. Verify NFC is enabled in device settings
3. Check app shows "NFC Status: Ready"

### 4. Test Workflow

#### Complete End-to-End Test
1. **Shipper**: Generate test shipment
```python
# In shipper.py main function
carrier_info = {
    "name": "Test Carrier",
    "transit_type": "truck"
}
bridge.process_shipment("SO-TEST-001", carrier_info)
```

2. **Carrier**: Receive shipment data
   - Tap NFC tag with shipment data
   - Verify data appears in "Active Shipments"
   - Confirm Google Wallet pass is created

3. **Receiver**: Process delivery
   - Carrier taps NFC pad at delivery location
   - Verify goods receipt is created in SAP
   - Check payment release

---

## 📱 Mobile App Usage Guide

### For Carriers

#### Receiving Shipments
1. Open NFC Logistics Carrier app
2. Go to "NFC Operations" tab
3. Hold device near NFC tag from shipper
4. Verify shipment appears in "Active Shipments"
5. Check Google Wallet for secure storage

#### Delivering Shipments
1. Select shipment from "Active Shipments"
2. Go to "NFC Operations" tab
3. At delivery location, tap NFC pad
4. Wait for "ACK" confirmation
5. Shipment moves to "History" tab

#### Troubleshooting
- **NFC not working**: Check device NFC settings
- **No shipments**: Verify bridge connectivity
- **Google Wallet issues**: Check Google Play Services

---

## 🔧 Configuration Reference

### Payload Structure Validation
The system validates all payloads against the JSON schema in `payload_structure.json`. Required fields:

```json
{
  "transaction_id": "TXN-XXXXXXXXXX",
  "status": "initiated|in_transit|delivered|confirmed", 
  "timestamp": "ISO 8601 datetime",
  "location": {
    "latitude": 40.1262,
    "longitude": -82.9291,
    "address": "Street address"
  },
  "packing_slip": {
    "slip_number": "PS-XXX",
    "items": [...],
    "total_weight": 100.5
  },
  "bol": {
    "number": "BOL-XXX",
    "carrier": "Carrier Name",
    "origin": "Origin City",
    "destination": "Destination City"
  }
}
```

### Environment Variables

#### Shipper Environment
```bash
export INFOR_API_KEY="your_api_key"
export INFOR_TENANT="your_tenant"
export BRIDGE_HOST="receiver_ip_address"
export COMPANY_ID="SHIPPER001"
```

#### Receiver Environment  
```bash
export SAP_USERNAME="nfc_logistics_user"
export SAP_PASSWORD="secure_password"
export SAP_CLIENT="100"
export WAREHOUSE_LOCATION="Westerville Distribution Center"
```

#### Android App Environment
Set in `build.gradle`:
```kotlin
buildConfigField "String", "BRIDGE_HOST", "\"your_bridge_ip\""
buildConfigField "String", "WALLET_ENVIRONMENT", "\"PRODUCTION\""
```

---

## 🚨 Production Considerations

### Security Hardening
1. **Use HTTPS** for all ERP communications
2. **Certificate pinning** in mobile app
3. **Regular key rotation** (quarterly recommended)
4. **Input validation** at all endpoints
5. **Rate limiting** on bridge endpoints

### Monitoring and Logging
```python
# Enhanced logging configuration
import logging.handlers

# Rotating file handler
handler = logging.handlers.RotatingFileHandler(
    'nfc_logistics.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)

# Syslog for centralized logging
syslog_handler = logging.handlers.SysLogHandler(address=('logs.company.com', 514))
```

### Performance Optimization
1. **Connection pooling** for ERP APIs
2. **Async processing** for non-critical operations
3. **Database indexing** for transaction queries
4. **Caching** of frequently accessed data

### Backup and Recovery
```bash
# Daily database backup
0 2 * * * pg_dump nfc_logistics > /backup/nfc_logistics_$(date +\%Y\%m\%d).sql

# Configuration backup
0 3 * * * tar -czf /backup/nfc_config_$(date +\%Y\%m\%d).tar.gz /opt/nfc_logistics/config/
```

---

## 🐛 Troubleshooting Guide

### Common Issues

#### "NFC not supported" Error
**Cause**: Device lacks NFC hardware
**Solution**: Use NFC-enabled device or QR code fallback

#### "Failed to sync with bridge" Error
**Cause**: Network connectivity issues
**Solution**: 
1. Check firewall rules
2. Verify bridge IP/port configuration
3. Test with `telnet bridge_ip 65432`

#### "Signature validation failed" Error
**Cause**: Certificate mismatch or expired certificates
**Solution**:
1. Update trusted_shippers.json
2. Regenerate certificates if expired
3. Check system clock synchronization

#### "ERP connection timeout" Error
**Cause**: ERP system unreachable or credentials invalid
**Solution**:
1. Verify ERP endpoint URLs
2. Check authentication credentials
3. Review ERP system logs

### Diagnostic Commands

#### Test Bridge Connectivity
```bash
# Test shipper to receiver bridge
nc -zv receiver_ip 65432

# Test HTTP endpoint
curl -X POST http://receiver_ip:65432/health
```

#### Validate Payload Structure
```python
import jsonschema
import json

# Load schema and validate
with open('payload_structure.json') as f:
    schema = json.load(f)

jsonschema.validate(payload_data, schema)
```

#### Check NFC Status
```bash
# Android Debug Bridge commands
adb shell dumpsys nfc
adb logcat | grep NFC
```

---

## 📞 Support and Maintenance

### Log Analysis
Key log patterns to monitor:
```bash
# Successful transactions
grep "Successfully processed delivery" receiver_bridge.log

# Failed operations
grep "ERROR" *.log | tail -20

# Performance metrics
grep "Processing time" *.log | awk '{print $NF}' | sort -n
```

### System Health Checks
```bash
#!/bin/bash
# health_check.sh

# Check bridge processes
pgrep -f "receiver_bridge.py" || echo "ALERT: Receiver bridge down"
pgrep -f "shipper.py" || echo "ALERT: Shipper system down"

# Check database connectivity
python -c "import sqlite3; sqlite3.connect('receiver_transactions.db').execute('SELECT 1')" || echo "ALERT: Database issue"

# Check disk space
df -h | grep -E "(9[0-9]%|100%)" && echo "ALERT: Disk space low"
```

### Update Procedures
1. **Code updates**: Use blue-green deployment
2. **Certificate renewal**: Update all components simultaneously  
3. **Database migrations**: Test in staging environment first
4. **App updates**: Use Google Play Console staged rollout

---

## 📈 Scaling Considerations

### Horizontal Scaling
- **Load balancers** for multiple bridge instances
- **Database sharding** by geographic region
- **Microservices architecture** for larger deployments

### Multi-Region Deployment
```yaml
# Docker Compose example
version: '3.8'
services:
  receiver-bridge-us:
    image: nfc-logistics/receiver-bridge
    environment:
      - REGION=us-east-1
      - SAP_ENDPOINT=https://sap-us.company.com
    ports:
      - "65432:65432"
  
  receiver-bridge-eu:
    image: nfc-logistics/receiver-bridge
    environment:
      - REGION=eu-west-1
      - SAP_ENDPOINT=https://sap-eu.company.com
    ports:
      - "65433:65432"
```

### Performance Benchmarks
Target performance metrics:
- **NFC read/write**: < 2 seconds
- **ERP integration**: < 5 seconds
- **End-to-end transaction**: < 30 seconds
- **System availability**: 99.9%

---

For additional support or custom deployment assistance, contact the NFC Logistics System team.

**Version**: 1.0.0  
**Last Updated**: January 2024  
**Compatibility**: Android API 24+, Python 3.8+