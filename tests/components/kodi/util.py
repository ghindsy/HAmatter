"""Test the Kodi config flow."""
from homeassistant.components.kodi.const import DEFAULT_SSL

TEST_HOST = {
    "host": "1.1.1.1",
    "port": 8080,
    "ssl": DEFAULT_SSL,
}


TEST_CREDENTIALS = {"username": "username", "password": "password"}


TEST_WS_PORT = {"ws_port": 9090}

UUID = "11111111-1111-1111-1111-111111111111"
TEST_DISCOVERY = {
    "host": "1.1.1.1",
    "port": 8080,
    "hostname": "hostname.local.",
    "type": "_xbmc-jsonrpc-h._tcp.local.",
    "name": "hostname._xbmc-jsonrpc-h._tcp.local.",
    "properties": {"uuid": UUID},
}


TEST_IMPORT = {
    "name": "name",
    "host": "1.1.1.1",
    "port": 8080,
    "ws_port": 9090,
    "username": "username",
    "password": "password",
    "ssl": True,
    "timeout": 7,
}


class MockConnection:
    """A mock kodi connection."""


    def __init__(self, connected=True):
        """Mock the Kodi connection."""
        self._connected = connected

    async def connect(self):
        """Mock connect."""
        pass

    @property
    def connected(self):
        """Mock connected."""
        return self._connected

    @property
    def can_subscribe(self):
        """Mock can_subscribe."""
        return False

    async def close(self):
        """Mock close."""
        pass

    @property
    def server(self):
        """Mock server."""
        return None
