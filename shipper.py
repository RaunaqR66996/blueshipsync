#!/usr/bin/env python3
"""
Blue Ships Sync - Shipper client

Generates digitally signed shipping payloads from mock Infor SyteLine ERP data
and sends them to the Blue Ships Sync bridge over a secure socket connection.
"""

import socket
import json
import logging
import os
import base64
import time
from datetime import datetime, timezone
from typing import Dict, Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

BRIDGE_HOST = os.getenv("BRIDGE_HOST", "localhost")
BRIDGE_PORT_INIT = 65432
BRIDGE_PORT_COMPLETE = 65433
KEY_DIR = os.getenv("KEY_DIR", "./keys")
PRIVATE_KEY_FILE = os.path.join(KEY_DIR, "shipper_private.pem")
PUBLIC_KEY_FILE = os.path.join(KEY_DIR, "shipper_public.pem")
SHIPPER_ERP_ID = "SYTELINE-OH-001"
RETRY_DELAY = 5  # seconds
MAX_RETRIES = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] shipper - %(message)s",
)

def ensure_keys() -> rsa.RSAPrivateKey:
    os.makedirs(KEY_DIR, exist_ok=True)
    if not os.path.exists(PRIVATE_KEY_FILE) or not os.path.exists(PUBLIC_KEY_FILE):
        logging.info("Generating new RSA key pair for shipper...")
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with open(PRIVATE_KEY_FILE, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        public_key = private_key.public_key()
        with open(PUBLIC_KEY_FILE, "wb") as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
    else:
        with open(PRIVATE_KEY_FILE, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None
            )
    return private_key


def get_mock_erp_data() -> Dict[str, Any]:
    """
    Simulates a call to Infor SyteLine ERP and returns shipping data.
    In production replace this with real ERP API calls.
    """
    logging.info("Fetching shipping order from Infor SyteLine ERP...")
    return {
        "transaction_id": f"TX-{int(time.time())}",
        "status": "CREATED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": "Westerville, OH",
        "packing_slip": {
            "items": [
                {"sku": "A1001", "description": "Blue Widget", "qty": 25, "weight_kg": 0.5},
                {"sku": "B2002", "description": "Red Widget", "qty": 15, "weight_kg": 0.7}
            ],
            "total_weight_kg": 25 * 0.5 + 15 * 0.7
        },
        "bol_number": "BOL-998877",
        "batch_details": {
            "batch_id": "BATCH-2308-01",
            "manufacture_date": "2023-08-15",
            "expiry_date": "2025-08-14"
        },
        "commercial_invoice": {
            "number": "INV-556677",
            "total_value": 18500,
            "currency": "USD"
        },
        "pallet_count": 4,
        "transit_type": "truck",
        "shipper_erp_id": SHIPPER_ERP_ID,
        "receiver_erp_id": "SAP-OH-009"
    }


def sign_payload(private_key: rsa.RSAPrivateKey, payload_bytes: bytes) -> str:
    signature = private_key.sign(
        payload_bytes,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode("utf-8")


def build_payload(private_key: rsa.RSAPrivateKey) -> Dict[str, Any]:
    data = get_mock_erp_data()
    payload_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
    signature = sign_payload(private_key, payload_bytes)
    data["digital_signature"] = signature
    return data


def send_payload(payload: Dict[str, Any]) -> None:
    serialized = json.dumps(payload).encode("utf-8") + b"\n"
    attempts = 0
    while attempts < MAX_RETRIES:
        try:
            with socket.create_connection((BRIDGE_HOST, BRIDGE_PORT_INIT), timeout=10) as sock:
                sock.sendall(serialized)
                ack = sock.recv(1024).decode().strip()
                if ack == "ACK":
                    logging.info("Payload acknowledged by bridge.")
                    return
                else:
                    raise RuntimeError(f"Unexpected response from bridge: {ack}")
        except Exception as e:
            attempts += 1
            logging.error("Failed to send payload (attempt %d/%d): %s",
                          attempts, MAX_RETRIES, e)
            time.sleep(RETRY_DELAY)
    raise SystemExit("Exceeded maximum retries. Aborting.")


if __name__ == "__main__":
    private_key = ensure_keys()
    payload = build_payload(private_key)
    logging.info("Generated payload with transaction ID %s", payload["transaction_id"])
    send_payload(payload)