# Blue Ships Sync – Deployment Guide

This guide walks you through setting up the complete NFC-enabled digital handshake system on a single workstation for testing. Adapt IP addresses and TLS certificates for a real multi-host deployment.

---

## 1. Prerequisites

1. **Operating System**: Linux/macOS/Windows with Python 3.9+
2. **Android Studio**: Arctic Fox or later (for building the carrier app)
3. **ADB-enabled Android device** with NFC (API 26+)
4. **Python packages** (see `requirements.txt` below)

```bash
python -m venv venv
source venv/bin/activate
pip install cryptography flask
```

> For production you should pin exact versions in `requirements.txt` and use `pip install -r requirements.txt`.

## 2. Generate RSA Key Pair (Shipper)

`shipper.py` **auto-generates** a 2048-bit RSA key pair on first run and stores it in `./keys`. Copy `shipper_public.pem` to the bridge host if running on different machines.

```bash
python shipper.py  # first time run triggers key generation and sends sample payload
```

## 3. Start the Bridge/Receiver Service

In a new terminal:

```bash
python receiver_bridge.py
```

You should see logs indicating the TCP servers (ports **65432** and **65433**) and the Flask API (port **5000**) are up.

### Health Checks

```bash
curl http://localhost:5000/payloads | jq
```

## 4. Build & Deploy Carrier Android App

1. Open `carrier_app` in Android Studio.
2. Update the IP address in `MainActivity.kt` if your bridge isn’t running on the same machine (look for `10.0.2.2`).
3. Connect your NFC-capable device and click **Run**.
4. Pass the transaction ID as an *extra* when launching the activity (for testing hard-coded placeholder is used).

When prompted, tap the device against a powered NFC reader on the receiver side to transmit the payload.

## 5. Marking Delivery (Receiver)

The receiver device (or a back-office service) should call:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"receiver_signature":"SIGNED-OK"}' \
  http://<bridge_host>:5000/payloads/<TX_ID>/delivered
```

The bridge validates, syncs to the mock SAP endpoint, **notifies the shipper** on port **65433**, and sets status to `DELIVERED`.

## 6. ERP Integration Stubs

- **Infor SyteLine (shipper)** – simulated inside `shipper.py::get_mock_erp_data()`.
- **SAP (receiver)** – replace `receiver_bridge.py::push_to_sap()` with real REST calls and authentication tokens.

## 7. Security Notes

1. **TLS** – Wrap socket traffic in TLS (e.g. `ssl.create_default_context()` in Python).
2. **Signature Validation** – Implement public-key rotation and certificate pinning.
3. **Wallet Passes** – Use Google Wallet *Passes API* to store payload securely on the carrier device.
4. **Audit Logs** – Log files are written to `stdout` but can be shipped to Elastic/Splunk.

## 8. Troubleshooting

| Symptom | Possible Cause | Fix |
|---------|----------------|-----|
| `INVALID_SIGNATURE` | Key mismatch | Copy correct `shipper_public.pem` to bridge |
| Android app can’t fetch payload | Incorrect IP | Update URL in `MainActivity.kt` |
| Shipper retries exhausted | Bridge offline | Start `receiver_bridge.py` first |

---

Enjoy real-time, paper-free logistics automation! ✈️🚚🚢