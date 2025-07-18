# NFC-Enabled Digital Handshake System for Logistics

A production-ready system that revolutionizes supply chain operations by eliminating manual paperwork through NFC technology and automated ERP synchronization.

## 🚀 Key Features

- **Automated Data Transfer**: Eliminate manual data entry with NFC-enabled handshakes
- **Multi-ERP Integration**: Seamless integration with Infor SyteLine and SAP
- **Real-time Synchronization**: Instant updates across all stakeholders
- **Digital Security**: Cryptographic signatures ensure data integrity
- **Google Wallet Integration**: Secure in-transit document storage
- **Reduced Processing Time**: From hours to minutes

## 📋 System Components

### 1. Shipper Backend (`backend/shipper.py`)
- Python-based service on port 65432
- Integrates with Infor SyteLine ERP
- Generates digitally signed shipment payloads
- Manages shipment lifecycle

### 2. Blue Ships Sync Bridge (`backend/receiver_bridge.py`)
- Middleware for multi-stakeholder communication
- WebSocket server for real-time carrier updates
- Manages transaction state across the supply chain
- Ports: 65433 (Bridge), 65435 (NFC), 8765 (WebSocket)

### 3. Carrier Android App (`carrier_app/`)
- Kotlin-based NFC-enabled mobile application
- Real-time WebSocket connection to bridge
- Google Wallet integration for secure storage
- NFC read/write capabilities

### 4. Receiver Integration
- SAP ERP integration
- Automated goods receipt creation
- Inventory updates and payment release
- Digital signature validation

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Shipper   │────▶│  Blue Ships     │◀────│   Carrier    │
│   (Infor)   │     │  Sync Bridge    │     │ Android App  │
└─────────────┘     └─────────────────┘     └──────────────┘
                             │                        │
                             │                        │ NFC
                             ▼                        ▼
                    ┌─────────────────┐      ┌──────────────┐
                    │    Receiver     │◀─────│  NFC Pad/    │
                    │     (SAP)       │      │   Reader     │
                    └─────────────────┘      └──────────────┘
```

## 📦 Payload Structure

The system uses a comprehensive JSON payload containing:
- Transaction details (ID, status, timestamp, location)
- Packing slip with item details
- Bill of Lading (BOL)
- Batch information and expiry dates
- Commercial invoice
- Logistics data (pallets, transit type)
- ERP identifiers
- Digital signatures for security

See `backend/payload_structure.json` for complete schema.

## 🔧 Quick Start

### Prerequisites
- Python 3.8+
- Android Studio (for carrier app)
- NFC-enabled Android device

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd nfc-logistics-system
```

2. **Install Python dependencies**
```bash
cd backend
pip install -r requirements.txt
```

3. **Start the services**

Terminal 1 - Receiver/Bridge:
```bash
python receiver_bridge.py
```

Terminal 2 - Shipper:
```bash
python shipper.py
```

4. **Build and deploy Android app**
- Open `carrier_app` in Android Studio
- Build and run on NFC-enabled device

5. **Test the system**
```bash
python test_client.py
```

## 📱 Android App Usage

1. **Connect to Bridge**: App automatically connects on launch
2. **Receive Shipments**: New shipments appear in real-time
3. **Select Shipment**: Tap to add to Google Wallet
4. **NFC Delivery**: At receiver location, tap NFC pad
5. **Confirmation**: Receive instant delivery confirmation

## 🔒 Security Features

- **Digital Signatures**: ECDSA-SHA256 for payload integrity
- **Encrypted Communication**: TLS/SSL for production
- **Authentication Tokens**: Secure ERP access
- **Audit Trail**: Complete transaction logging

## 🚀 Production Deployment

See `docs/setup_instructions.md` for detailed deployment guide including:
- Security hardening
- Network configuration
- Monitoring setup
- Backup procedures
- Compliance requirements

## 📊 Performance

- **Processing Time**: <1 minute end-to-end
- **Concurrent Connections**: 100+ carriers
- **Payload Size**: ~2-4KB per transaction
- **NFC Transfer**: <1 second

## 🛠️ Customization

### Adding New ERPs
1. Implement ERP integration class
2. Map fields to standard payload
3. Update configuration

### Extending Payload
1. Update `payload_structure.json`
2. Modify data classes in all components
3. Update validation logic

## 📞 Support

- Documentation: `docs/setup_instructions.md`
- Test Client: `backend/test_client.py`
- Issues: Create GitHub issue

## 📄 License

This project is proprietary software for logistics operations.

---

Built with ❤️ for logistics companies in Westerville, Ohio