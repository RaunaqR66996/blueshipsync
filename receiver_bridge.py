#!/usr/bin/env python3
"""
Blue Ships Sync - Bridge and Receiver service

Acts as intermediary between shipper, carrier (Android app), and receiver ERP.
"""

import socket
import socketserver
import threading
from threading import Thread
import json
import os
import logging
import base64
from datetime import datetime, timezone
from typing import Dict, Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from flask import Flask, jsonify, request, abort

BRIDGE_PORT_INIT = 65432
BRIDGE_PORT_COMPLETE = 65433
KEY_DIR = os.getenv("KEY_DIR", "./keys")
SHIPPER_PUBLIC_KEY_FILE = os.path.join(KEY_DIR, "shipper_public.pem")
APP_HOST = "0.0.0.0"
APP_PORT = 5000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] bridge - %(message)s",
)

# In-memory storage; replace with persistent store in production
PAYLOAD_STORE: Dict[str, Dict[str, Any]] = {}


def load_shipper_public_key():
    if not os.path.exists(SHIPPER_PUBLIC_KEY_FILE):
        raise FileNotFoundError("Shipper public key not found. Make sure shipper.py has generated keys.")
    with open(SHIPPER_PUBLIC_KEY_FILE, "rb") as f:
        return serialization.load_pem_public_key(f.read())


SHIPPER_PUBLIC_KEY = load_shipper_public_key()


def verify_signature(public_key, payload: Dict[str, Any]) -> bool:
    sig_b64 = payload.pop("digital_signature", None)
    if not sig_b64:
        return False
    try:
        signature = base64.b64decode(sig_b64)
    except Exception:
        return False
    message = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    try:
        public_key.verify(
            signature,
            message,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception as exc:
        logging.error("Signature verification failed: %s", exc)
        return False
    finally:
        # restore signature for persistence
        payload["digital_signature"] = sig_b64


class ShipperInitHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = b""
        while not data.endswith(b"\n"):
            packet = self.request.recv(4096)
            if not packet:
                break
            data += packet
        try:
            payload = json.loads(data.decode("utf-8").strip())
            if not verify_signature(SHIPPER_PUBLIC_KEY, payload):
                self.request.sendall(b"INVALID_SIGNATURE\n")
                logging.warning("Rejected payload due to invalid signature.")
                return
            tx_id = payload["transaction_id"]
            PAYLOAD_STORE[tx_id] = payload
            logging.info("Stored payload %s", tx_id)
            self.request.sendall(b"ACK\n")
        except Exception as e:
            logging.error("Error processing payload: %s", e)
            self.request.sendall(b"ERROR\n")


class ShipperCompleteHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = b""
        while not data.endswith(b"\n"):
            packet = self.request.recv(4096)
            if not packet:
                break
            data += packet
        logging.info("Received completion acknowledgment from receiver: %s", data.decode("utf-8").strip())


def start_socket_server(handler_cls, port):
    server = socketserver.ThreadingTCPServer((APP_HOST, port), handler_cls)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    logging.info("Started socket server %s on port %d", handler_cls.__name__, port)


# Flask REST API for carrier app and receiver
app = Flask(__name__)


@app.route("/payloads/<tx_id>", methods=["GET"])
def get_payload(tx_id):
    payload = PAYLOAD_STORE.get(tx_id)
    if not payload:
        abort(404)
    return jsonify(payload)


@app.route("/payloads", methods=["GET"])
def list_payloads():
    return jsonify(list(PAYLOAD_STORE.keys()))


@app.route("/payloads/<tx_id>/delivered", methods=["POST"])
def mark_delivered(tx_id):
    payload = PAYLOAD_STORE.get(tx_id)
    if not payload:
        abort(404)
    data = request.get_json()
    receiver_signature = data.get("receiver_signature")
    if not receiver_signature:
        abort(400, "receiver_signature missing")
    payload["status"] = "DELIVERED"
    payload["delivered_timestamp"] = datetime.now(timezone.utc).isoformat()
    payload["receiver_signature"] = receiver_signature
    logging.info("Transaction %s marked as delivered.", tx_id)
    # Trigger mock SAP ERP call
    push_to_sap(payload)
    notify_shipper_completed(payload)
    return jsonify({"status": "success"})


def push_to_sap(payload: Dict[str, Any]):
    # Simulate SAP ERP integration
    logging.info("Syncing delivered payload %s to SAP ERP...", payload["transaction_id"])
    # Real implementation would perform REST API call here.


def notify_shipper_completed(payload: Dict[str, Any]):
    message = json.dumps({"transaction_id": payload["transaction_id"], "status": "DELIVERED"}).encode("utf-8") + b"\n"
    try:
        with socket.create_connection(("localhost", BRIDGE_PORT_COMPLETE), timeout=5) as sock:
            sock.sendall(message)
        logging.info("Notified shipper of delivery completion.")
    except Exception as e:
        logging.error("Failed to notify shipper: %s", e)


def main():
    start_socket_server(ShipperInitHandler, BRIDGE_PORT_INIT)
    start_socket_server(ShipperCompleteHandler, BRIDGE_PORT_COMPLETE)
    logging.info("Starting Flask app on port %d", APP_PORT)
    app.run(host=APP_HOST, port=APP_PORT)


if __name__ == "__main__":
    main()