import socket
import ssl
from typing import Optional
from . import config_loader

CONFIG: dict = config_loader.load_config()
BIND_IP: str = CONFIG["host"]
BIND_PORT: int = CONFIG["port"]
SSL_ENABLED: bool = CONFIG["ssl_enabled"]


"""
Create an SSL context with a specified protocol and load the
certificate chain and key for the server.
@param ssl.PROTOCOL_TLS_SERVER - The protocol to use for the SSL context.
@param "../security/server.crt" - The path to the server certificate.
@param "../security/server.key" - The path to the server key file.
"""
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.maximum_version = ssl.TLSVersion.TLSv1_3

context.load_cert_chain(
    certfile="../security/server.crt", keyfile="../security/server.key"
)

# Create a new socket using the AF_INET address family and SOCK_STREAM socket type.
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
data: str = ""

# Wrap the given socket for SSL/TLS encryption in server mode within a context manager.
while True:
    data = input()
    with socket.create_connection((BIND_IP, BIND_PORT)) as sock:
        try:
            ssock: Optional[ssl.SSLSocket] = None
            if SSL_ENABLED:
                ssock = context.wrap_socket(sock, server_hostname=BIND_IP)
                ssock.sendall(data.encode())
                response = ssock.recv(1024)
                print(response.decode())

            else:
                sock.sendall(data.encode())
                response = sock.recv(1024)
                print(response.decode())
        finally:
            # Closing socket
            sock.close()
