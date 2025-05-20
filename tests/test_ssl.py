import ssl
import socket
import pytest
import os

# Get absolute paths for certificates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERT_FILE = os.path.join(BASE_DIR, "security/server.crt")
KEY_FILE = os.path.join(BASE_DIR, "security/server.key")
CA_CERT = os.path.join(BASE_DIR, "security/server.crt")

HOST = "127.0.0.1"
PORT = 8080

def test_ssl_connection():
    # Verify certificate files exist
    assert os.path.exists(CERT_FILE), f"Certificate file not found: {CERT_FILE}"
    assert os.path.exists(KEY_FILE), f"Key file not found: {KEY_FILE}"
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    with socket.create_connection((HOST, PORT)) as sock:
        with context.wrap_socket(sock, server_hostname=HOST) as ssock:
            ssock.sendall("test;ssl;query\n".encode())
            response = ssock.recv(1024).decode()
            assert "STRING" in response or "NOT EXIST" in response