# NFC Logistics System - Setup and Deployment Guide

## System Overview

This NFC-enabled digital handshake system streamlines logistics operations by automating data transfer between Shippers, Carriers, and Receivers. The system eliminates manual paperwork and enables real-time ERP synchronization, reducing processing time from hours to minutes.

## Architecture Components

1. **Shipper Backend** (`shipper.py`) - Python service integrating with Infor SyteLine ERP
2. **Blue Ships Sync Bridge** (`receiver_bridge.py`) - Middleware for multi-stakeholder communication
3. **Carrier Android App** - NFC-enabled mobile app with Google Wallet integration
4. **Receiver Backend** - Python service integrating with SAP ERP

## Prerequisites

### Backend Requirements
- Python 3.8+
- pip package manager
- Network connectivity between all components

### Android App Requirements
- Android Studio Arctic Fox or later
- Android SDK 24+ (minimum)
- Physical Android device with NFC capability (for testing)
- Kotlin 1.8+

## Installation Instructions

### 1. Backend Setup

#### Install Python Dependencies
```bash
cd nfc-logistics-system/backend
pip install -r requirements.txt
```

Create `requirements.txt`:
```
requests==2.31.0
websockets==12.0
cryptography==41.0.7
asyncio==3.4.3
```

#### Configure Environment Variables
Create `.env` file in the backend directory:
```
# Shipper Configuration
SHIPPER_HOST=0.0.0.0
SHIPPER_PORT=65432
INFOR_API_URL=https://api.infor-syteline.mock
INFOR_API_TOKEN=your-infor-api-token

# Bridge Configuration
BRIDGE_HOST=0.0.0.0
BRIDGE_PORT=65433
WEBSOCKET_PORT=8765

# Receiver Configuration
RECEIVER_HOST=0.0.0.0
NFC_RECEIVER_PORT=65435
SAP_API_URL=https://api.sap.mock
SAP_API_TOKEN=your-sap-api-token
```

### 2. Start Backend Services

#### Terminal 1 - Start Receiver/Bridge Server
```bash
cd nfc-logistics-system/backend
python receiver_bridge.py
```

This starts:
- Bridge server on port 65433
- NFC receiver on port 65435
- WebSocket server on port 8765

#### Terminal 2 - Start Shipper Server
```bash
cd nfc-logistics-system/backend
python shipper.py
```

This starts the shipper server on port 65432.

### 3. Android App Setup

#### Build the Android App
1. Open Android Studio
2. Import project: `nfc-logistics-system/carrier_app`
3. Sync Gradle files
4. Configure the app for your environment:
   - Update WebSocket URL in `MainActivity.kt` if not using emulator
   - For physical device, replace `10.0.2.2` with actual server IP

#### Install on Device
1. Enable Developer Options and USB Debugging on Android device
2. Connect device via USB
3. Run the app from Android Studio

### 4. Testing the System

#### Test Workflow
1. **Initiate Shipment** (Shipper):
   ```python
   import socket
   import json
   
   # Connect to shipper server
   sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   sock.connect(('localhost', 65432))
   
   # Create shipment
   request = {
       'action': 'create_shipment',
       'order_id': 'SO-2024-TEST001'
   }
   sock.send(json.dumps(request).encode())
   
   # Get response
   response = json.loads(sock.recv(4096).decode())
   print(f"Transaction ID: {response['transaction_id']}")
   ```

2. **Carrier Receives Shipment**:
   - Open carrier app
   - Verify connection to bridge (green status)
   - See new shipment appear in list
   - Tap shipment to select and add to Google Wallet

3. **NFC Delivery**:
   - At receiver location, ensure NFC is enabled
   - Select shipment in carrier app
   - Tap phone on NFC tag/reader
   - Verify "Delivery completed successfully!" message

4. **Verify Receiver Processing**:
   - Check receiver logs for goods receipt creation
   - Verify inventory update
   - Confirm payment release trigger

## Production Deployment

### 1. Security Hardening
- Replace mock ERP endpoints with actual API URLs
- Implement proper API authentication tokens
- Use HTTPS/WSS for all communications
- Store keys securely (use key management service)
- Implement certificate pinning in Android app

### 2. Network Configuration
- Configure firewalls to allow required ports
- Set up load balancers for high availability
- Implement VPN for secure ERP access
- Use static IPs or DNS names for services

### 3. Android App Distribution
- Sign app with production certificate
- Deploy via Google Play Store or enterprise MDM
- Configure Google Wallet production API keys
- Implement app update mechanism

### 4. Monitoring and Logging
- Set up centralized logging (ELK stack recommended)
- Implement health check endpoints
- Configure alerts for failures
- Monitor transaction processing times

### 5. Backup and Recovery
- Regular backup of transaction data
- Implement transaction replay capability
- Document recovery procedures
- Test disaster recovery plan

## Configuration for Different ERPs

### Infor SyteLine Integration
Update `INFOR_SYTELINE_API` in `shipper.py`:
```python
INFOR_SYTELINE_API = {
    'base_url': 'https://your-syteline-instance.com/api',
    'auth_token': 'your-production-token',
    'company_id': 'your-company-id'
}
```

### SAP Integration
Update `SAP_API` in `receiver_bridge.py`:
```python
SAP_API = {
    'base_url': 'https://your-sap-instance.com/api',
    'auth_token': 'your-production-token',
    'company_id': 'your-company-id'
}
```

### Other ERPs
The system is designed to be ERP-agnostic. To integrate new ERPs:
1. Implement the ERP integration class following the existing pattern
2. Map ERP fields to the standard payload structure
3. Update authentication and API endpoints

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check firewall settings
   - Verify bridge server is running
   - Confirm correct IP/port in Android app

2. **NFC Not Working**
   - Ensure NFC is enabled on device
   - Check NFC permissions in app settings
   - Try different NFC tags/readers

3. **ERP Integration Errors**
   - Verify API credentials
   - Check network connectivity
   - Review ERP API logs

4. **Signature Validation Failed**
   - Ensure clocks are synchronized
   - Verify public key distribution
   - Check for payload tampering

### Debug Mode
Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Support Contacts
- Technical Support: support@nfc-logistics.com
- Documentation: docs.nfc-logistics.com
- Emergency: +1-xxx-xxx-xxxx

## Performance Optimization

### Recommended Settings
- Socket buffer size: 4096 bytes
- WebSocket ping interval: 30 seconds
- Connection timeout: 10 seconds
- Max concurrent connections: 100

### Scaling Considerations
- Use connection pooling for ERP APIs
- Implement caching for frequently accessed data
- Consider message queuing for high volume
- Deploy multiple instances behind load balancer

## Compliance and Regulations

### Data Privacy
- Comply with GDPR/CCPA requirements
- Implement data retention policies
- Provide audit trails
- Enable data export/deletion

### Industry Standards
- Follow GS1 standards for logistics data
- Implement ISO 27001 security controls
- Maintain SOC 2 compliance
- Regular security audits

## Version History
- v1.0.0 - Initial release with core functionality
- Future: Multi-language support, offline mode, analytics dashboard