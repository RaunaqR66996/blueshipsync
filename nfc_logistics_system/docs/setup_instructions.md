# NFC Logistics System - Setup Instructions

## System Overview

This NFC-enabled digital handshake system for logistics consists of three main components:

1. **Shipper Backend** (Python) - Port 65432
2. **Receiver Bridge** (Python) - Port 65433  
3. **Carrier Android App** (Kotlin) - NFC-enabled mobile application

## Prerequisites

### System Requirements
- Python 3.8 or higher
- Android Studio 4.0 or higher
- Android device with NFC capability
- NFC tags (NDEF format)
- Network connectivity

### Python Dependencies
```bash
pip install asyncio
pip install cryptography
pip install requests
pip install logging
pip install json
pip install socket
pip install threading
pip install time
pip install datetime
pip install typing
pip install dataclasses
pip install abc
pip install base64
pip install hashlib
pip install hmac
pip install os
```

## Backend Setup

### 1. Shipper Backend Setup

Navigate to the shipper directory:
```bash
cd nfc_logistics_system/backend/shipper
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Generate security keys (optional):
```bash
python -c "
from common.security import SecurityManager
sm = SecurityManager()
private_key, public_key = sm.generate_key_pair()
sm.save_key_pair(private_key, public_key, 'shipper_private.pem', 'shipper_public.pem')
"
```

Start the shipper server:
```bash
python shipper.py
```

The shipper server will start on `localhost:65432`

### 2. Receiver Bridge Setup

Navigate to the receiver directory:
```bash
cd nfc_logistics_system/backend/receiver
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Generate security keys (optional):
```bash
python -c "
from common.security import SecurityManager
sm = SecurityManager()
private_key, public_key = sm.generate_key_pair()
sm.save_key_pair(private_key, public_key, 'receiver_private.pem', 'receiver_public.pem')
"
```

Start the receiver bridge:
```bash
python receiver_bridge.py
```

The receiver bridge will start on `localhost:65433`

### 3. ERP Configuration

Edit the ERP configurations in `backend/common/erp_integration.py`:

```python
MOCK_ERP_CONFIGS = {
    'infor_syteline': ERPConfig(
        base_url='https://your-infor-syteline-server.com/api/v1',
        api_key='your_api_key_here',
        username='your_username',
        password='your_password',
        timeout=30,
        retry_attempts=3
    ),
    'sap': ERPConfig(
        base_url='https://your-sap-server.com/api/v1',
        api_key='your_api_key_here',
        username='your_username',
        password='your_password',
        timeout=30,
        retry_attempts=3
    )
}
```

## Android App Setup

### 1. Android Studio Setup

1. Open Android Studio
2. Open the project: `nfc_logistics_system/android_app/`
3. Sync Gradle files
4. Ensure all dependencies are downloaded

### 2. Device Configuration

1. Enable Developer Options on your Android device
2. Enable USB Debugging
3. Enable NFC in device settings
4. Connect device to computer via USB

### 3. Build and Install

1. Select your device in Android Studio
2. Click "Run" or press Shift+F10
3. The app will be installed and launched on your device

### 4. Permissions

The app will request the following permissions:
- NFC
- Location (Fine and Coarse)
- Internet
- Network State

Grant all permissions when prompted.

## Network Configuration

### 1. Local Development

For local development, the Android app is configured to connect to:
- Shipper: `localhost:65432`
- Receiver: `localhost:65433`

### 2. Production Deployment

For production deployment, update the network configuration in `NetworkManager.kt`:

```kotlin
companion object {
    private const val SHIPPER_HOST = "your-shipper-server.com"
    private const val SHIPPER_PORT = 65432
    private const val RECEIVER_HOST = "your-receiver-server.com"
    private const val RECEIVER_PORT = 65433
}
```

## Testing the System

### 1. Backend Testing

Test the shipper backend:
```bash
curl -X POST http://localhost:65432 \
  -H "Content-Type: application/json" \
  -d '{
    "type": "create_shipment",
    "shipment_data": {
      "bol_number": "TEST-BOL-001",
      "items": [
        {
          "item_id": "ITEM-001",
          "description": "Test Item",
          "quantity": 10,
          "unit_weight": 1.0
        }
      ],
      "total_weight": 10.0,
      "destination": "Columbus, OH"
    }
  }'
```

Test the receiver bridge:
```bash
curl -X POST http://localhost:65433 \
  -H "Content-Type: application/json" \
  -d '{
    "type": "validate_payload",
    "payload": {
      "transaction": {
        "transaction_id": "TXN-2024-001-001",
        "status": "initiated"
      }
    }
  }'
```

### 2. Android App Testing

1. Launch the app on your NFC-enabled device
2. Connect to shipper and receiver systems
3. Enable NFC reading mode
4. Tap an NFC tag to read payload
5. Enable NFC writing mode
6. Tap an NFC tag to write payload
7. Test Google Wallet integration

### 3. End-to-End Testing

1. Create a shipment in the shipper system
2. Read the payload via NFC on the carrier app
3. Save to Google Wallet
4. Deliver to receiver via NFC
5. Verify ERP updates

## Security Configuration

### 1. Digital Signatures

The system uses RSA digital signatures for payload validation. Generate keys:

```bash
# Generate shipper keys
cd backend/shipper
python -c "
from common.security import SecurityManager
sm = SecurityManager()
private_key, public_key = sm.generate_key_pair()
sm.save_key_pair(private_key, public_key, 'shipper_private.pem', 'shipper_public.pem')
"

# Generate receiver keys
cd ../receiver
python -c "
from common.security import SecurityManager
sm = SecurityManager()
private_key, public_key = sm.generate_key_pair()
sm.save_key_pair(private_key, public_key, 'receiver_private.pem', 'receiver_public.pem')
"
```

### 2. Encryption

The system uses AES-256 encryption for payload data. Keys are automatically generated.

## Monitoring and Logging

### 1. Log Files

Backend logs are written to:
- `shipper.log` - Shipper backend logs
- `receiver_bridge.log` - Receiver bridge logs

### 2. Log Levels

Configure log levels in the backend files:
```python
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detail
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Troubleshooting

### Common Issues

1. **NFC not working**
   - Ensure NFC is enabled on device
   - Check if device supports NFC
   - Verify NFC tag is NDEF format

2. **Connection failures**
   - Check if backend servers are running
   - Verify network connectivity
   - Check firewall settings

3. **ERP integration errors**
   - Verify ERP credentials
   - Check ERP server connectivity
   - Review ERP API documentation

4. **Android app crashes**
   - Check logcat for error details
   - Verify all permissions are granted
   - Ensure device meets minimum requirements

### Debug Mode

Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Production Deployment

### 1. Server Setup

For production deployment:

1. Use production-grade servers
2. Configure SSL/TLS certificates
3. Set up proper firewall rules
4. Configure load balancing if needed
5. Set up monitoring and alerting

### 2. Database Integration

For production, consider adding database storage:

```python
# Add database configuration
DATABASE_CONFIG = {
    'host': 'your-db-host',
    'port': 5432,
    'database': 'logistics_db',
    'user': 'db_user',
    'password': 'db_password'
}
```

### 3. Scaling

For high-volume operations:

1. Implement connection pooling
2. Add caching layers
3. Use message queues for async processing
4. Implement horizontal scaling

## Support and Maintenance

### 1. Regular Maintenance

- Monitor log files for errors
- Update security keys periodically
- Backup configuration files
- Monitor system performance

### 2. Updates

- Keep Python dependencies updated
- Update Android app regularly
- Monitor for security patches
- Test updates in staging environment

## Contact Information

For technical support or questions:
- Email: support@westervillelogistics.com
- Phone: (614) 555-0123
- Documentation: https://docs.westervillelogistics.com

---

**Note**: This system is designed for logistics companies in Westerville, Ohio, and surrounding areas. Ensure compliance with local regulations and industry standards.