import socket
import threading
import os
import ssl
from timeit import default_timer as timer
from typing import List, Optional, Union, Tuple
import traceback
import logging

from . import config_loader
from . import utils
from .search_algorithms import (
    binary_search,
    linear_search,
    jump_search,
    exponential_search,
    search_in_set,
)
from .exceptions import InvalidPayloadError, FileAccessError

CONFIG: dict = config_loader.load_config()
"""
Load the configuration settings using the `config_loader` module and retrieve
configuration variables
"""
MAX_PAYLOAD: int = CONFIG["max_payload"]
BIND_IP: str = CONFIG["host"]
BIND_PORT: int = CONFIG["port"]
STRINGS_FILE_PATH: str = CONFIG["linuxpath"]
REREAD_QUERY: bool = CONFIG["reread_on_query"]
SSL_ENABLED: bool = CONFIG["ssl_enabled"]
DEBUG: bool = CONFIG["debug"]
CACHE_DATA: Optional[List[str]] = utils.reread_file(STRINGS_FILE_PATH)
SSL_CERT: str = CONFIG["ssl_certificate"]
SSL_KEY: str = CONFIG["ssl_private_key"]


"""
- Get the directory of the current configuration file
- Then determine the project root directory by moving two levels up from the configuration directory.
"""
config_dir: str = os.path.dirname(os.path.abspath(__file__))
project_root: str = os.path.abspath(os.path.join(config_dir, "../.."))

# Replace relative paths in the config with absolute paths
if STRINGS_FILE_PATH.startswith("../"):
    STRINGS_FILE_PATH = os.path.abspath(
        os.path.join(project_root, STRINGS_FILE_PATH[3:])
    )

if SSL_CERT.startswith("../"):
    SSL_CERT = os.path.abspath(os.path.join(project_root, SSL_CERT[3:]))

if SSL_KEY.startswith("../"):
    SSL_KEY = os.path.abspath(os.path.join(project_root, SSL_KEY[3:]))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Get the file size of string file path file
FILE_SIZE: Optional[int] = utils.get_file_size(STRINGS_FILE_PATH)
# print(f"[INFO] File size: {FILE_SIZE}" if DEBUG else "")
"""
Create an SSL context with a specified protocol and load the
certificate chain and key for the server.

Args:
    ssl.PROTOCOL_TLS_SERVER - The protocol to use for the SSL context.
    "../security/server.crt" - The path to the server certificate.
    "../security/server.key" - The path to the server key file.
"""
context = ssl._create_unverified_context(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(SSL_CERT, SSL_KEY)


# Validate and handle client request
class StringSearchServer:
    # Initiate object
    def __init__(self):
        self.cache_lock = threading.Lock()
        if not SSL_ENABLED:
            logger.info("SSL is disabled")

        # Performance metrics
        self.performance_stats = {
            "total_queries": 0,
            "avg_response_time": 0,
            "max_concurrent": 0,
        }

    def handle_client(
        self,
        client_sock: Union[socket.socket, ssl.SSLSocket],
        client_addr: Tuple[str, int],
    ) -> None:
        """
        Handle a client connection by receiving a request, processing it,
        and sending a response.

        Args:
            client_socket: The client socket object (regular or SSL)
            client_address: The address of the client (ip, port)
        """
        try:
            request: str = self._strip_exceeding_received_data(client_sock, MAX_PAYLOAD)
            # Check if the request is empty and return STRING NOT EXIST to client
            if not request:
                response = "STRING NOT EXIST"
                client_sock.sendall(response.encode())
                logger.error("Empty payload received from client")
                return

            response: str = ""
            logger.info(f"Search query: {request}")
            # Load the file content
            search_data: List[str] = []
            if str(REREAD_QUERY) == "True":
                logger.info(f"Reading file: {STRINGS_FILE_PATH}")
                reread_time_start = timer()
                file_dt: Optional[List[str]] = self._load_file_contents(
                    STRINGS_FILE_PATH
                )
                if isinstance(file_dt, list):
                    reread_time_end = timer()
                    search_data = file_dt
                    reread_time: float = (reread_time_end - reread_time_start) * 1000
                    logger.info(f"Reread search time: {reread_time:.2f}ms")
            else:
                search_data = CACHE_DATA
            # Search query in the file
            try:
                logger.info(f"Searching for string: {request}")
                start: float = timer()
                found: bool = search_in_set(request, search_data)
                end: float = timer()
                response_time: float = (end - start) * 1000
                logger.info(f"Search time: {response_time:.2f}ms")

                # Update performance stats
                with threading.Lock():
                    self.performance_stats["total_queries"] += 1
                    self.performance_stats["avg_response_time"] = (
                        self.performance_stats["avg_response_time"]
                        * (self.performance_stats["total_queries"] - 1)
                        + response_time
                    ) / self.performance_stats["total_queries"]

                response = "STRING EXISTS" if found else "STRING NOT EXIST"
                logger.info(f"{response}- {'200:OK' if found else '404:NOT FOUND'}")
                # Send response to client
                client_sock.sendall(response.encode())
                logger.debug(f"Response sent: {response}")
                return
            except Exception as e:
                logger.error(f"Error searching: {e}")
                response = "SERVER ERROR"
                client_sock.sendall(response.encode())
        except InvalidPayloadError as e:
            logger.error(f"Invalid payload: {str(e)}")
            client_sock.sendall(f"ERROR: {str(e)}".encode())
        except Exception:
            logger.error(f"Unexpected error:\n{traceback.format_exc()}")
            client_sock.sendall("SERVER ERROR".encode())
        finally:
            client_sock.close()

    def _load_file_contents(self, path: str) -> Optional[List[str]]:
        """Thread-safe file loading with metrics"""
        with self.cache_lock:
            start = timer()
            try:
                data: List[str] = utils.reread_file(path)
                load_time = (timer() - start) * 1000
                logger.debug(f"File loaded in {load_time:.2f}ms")
                return data
            except FileNotFoundError:
                raise FileAccessError("File not found")
            except Exception as e:
                logger.error(f"Error loading file: {e}")
                raise FileAccessError(f"Failed to load file: {str(e)}")

    def _strip_exceeding_received_data(
        self, sock: socket.socket, max_payload_size: int
    ) -> Optional[bytes]:
        """
        Receive data from a socket connection with size validation.

        Args:
            sock: The socket connection
            max_payload_size: The maximum allowed payload size in bytes

        Returns:
            The received data as bytes, or None if connection was closed
        """
        try:
            data: str = sock.recv(max_payload_size).decode().strip()
            if not data:
                raise InvalidPayloadError("Empty payload received")
            if len(data) > max_payload_size:
                data = data.rstrip("\x00")
            return data
        except Exception as e:
            logger.error(f"Error receiving data: {e}")
            raise InvalidPayloadError from e


def start_server(host: str, port: int, debug: bool) -> None:
    """
    Start the server and handle incoming client connections.

    Args:
        host: The host address to bind to
        port: The port number to listen on
        debug: Whether to print debug information
    """
    try:
        sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket: Union[socket.socket, ssl.SSLSocket] = sock

        if SSL_ENABLED:
            # Wrap socket if ssl is enabled
            try:
                server_socket = context.wrap_socket(sock, server_side=True)
                logger.info("SSL enabled connection")
            except Exception as e:
                logger.error(f"SSL error: {e}")
                sock.close()
                return

        # Bind connection
        server_socket.bind((host, port))
        # Listent to requests from clients
        server_socket.listen(5)
        logger.info(
            f"Server listening on {host}:{port} {'(DEBUG MODE)' if debug else ''}"
        )

        while True:
            try:
                # Get connection details of the client making request
                client_socket: Union[socket.socket, ssl.SSLSocket]
                address: Tuple[str, int]
                client_socket, address = server_socket.accept()
                logger.debug(f"Connection from {address}")

                # Create an instance of client operation class
                client_operation: StringSearchServer = StringSearchServer()

                # Update concurrency metrics
                with threading.Lock():
                    current_threads = (
                        threading.active_count() - 1
                    )  # Subtract main thread
                    client_operation.performance_stats["max_concurrent"] = max(
                        client_operation.performance_stats["max_concurrent"],
                        current_threads,
                    )
                    logger.info(f"Current threads: {current_threads}")
                    logger.info(
                        f"Max concurrent: {client_operation.performance_stats['max_concurrent']}"
                    )

                # Implement threading to enable simultenous connections
                client_thread: threading.Thread = threading.Thread(
                    target=client_operation.handle_client, args=(client_socket, address)
                )
                client_thread.start()

            except Exception as e:
                logger.error(f"Connection error: {e}")
                raise
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        if "server_socket" in locals():
            server_socket.close()
