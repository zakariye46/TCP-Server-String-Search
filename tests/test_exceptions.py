import pytest
from server.server.exceptions import InvalidPayloadError, FileAccessError
from server.server.server import StringSearchServer

class MockSocket:
    def __init__(self, data):
        self.data = data.encode() if data else b""

    def recv(self, _):
        return self.data

@pytest.fixture
def server():
    return StringSearchServer()

def test_invalid_payload_empty(server):
    """Test that empty payloads raise InvalidPayloadError"""
    with pytest.raises(InvalidPayloadError, match="Empty payload received"):
        server.handle_client(MockSocket(""))

def test_file_access_error(server):
    """Test that accessing nonexistent files raises FileAccessError"""
    with pytest.raises(FileAccessError, match="File not found"):
        server._load_file_contents("/nonexistent/file.txt")