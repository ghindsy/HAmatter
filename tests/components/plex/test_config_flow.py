"""Tests for Plex config flow."""
from unittest.mock import MagicMock, Mock, patch, PropertyMock
import plexapi.exceptions
import requests.exceptions

from homeassistant.components.plex import config_flow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN, CONF_URL

from tests.common import mock_coro


class MockAvailableServer:
    """Mock avilable server objects."""

    def __init__(self, name, client_id):
        """Initialize the object."""
        self.name = name
        self.clientIdentifier = client_id
        self.provides = ["server"]


class MockConnection:
    """Mock a single account resource connection object."""

    def __init__(self):
        """Initialize the object."""
        self.httpuri = "http://1.2.3.4:32400"
        self.uri = "http://4.3.2.1:32400"
        self.local = True


class MockConnections:
    """Mock a list of resource connections."""

    def __init__(self):
        """Initialize the object."""
        self.connections = [MockConnection()]


async def test_bad_credentials(hass, aioclient_mock):
    """Test when provided credentials are rejected."""

    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"

    with patch(
        "plexapi.myplex.MyPlexAccount", side_effect=plexapi.exceptions.Unauthorized
    ):

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_TOKEN: "12345"}
        )

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == "faulty_credentials"


async def test_import_file_from_discovery(hass, aioclient_mock):
    """Test importing a legacy file during discovery."""

    mock_file_contents = {
        "1.2.3.4:32400": {"ssl": False, "token": "12345", "verify": True}
    }
    file_host_and_port, file_config = list(mock_file_contents.items())[0]
    used_url = f"http://{file_host_and_port}"

    with patch("plexapi.server.PlexServer") as mock_plex_server, patch(
        "homeassistant.components.plex.config_flow.load_json",
        return_value=mock_coro(mock_file_contents),
    ):
        type(mock_plex_server.return_value).machineIdentifier = PropertyMock(
            return_value="unique_id_123"
        )
        type(mock_plex_server.return_value).friendlyName = PropertyMock(
            return_value="Mock Server"
        )
        type(mock_plex_server.return_value)._baseurl = PropertyMock(
            return_value=used_url
        )

        result = await hass.config_entries.flow.async_init(
            config_flow.DOMAIN,
            context={"source": "discovery"},
            data={CONF_HOST: "1.2.3.4", CONF_PORT: "32400"},
        )
        print(result)

        assert result["type"] == "create_entry"
        assert result["title"] == "Mock Server"
        assert result["data"][config_flow.CONF_SERVER] == "Mock Server"
        assert result["data"][config_flow.CONF_SERVER_IDENTIFIER] == "unique_id_123"
        assert result["data"][config_flow.PLEX_SERVER_CONFIG][CONF_URL] == used_url
        assert (
            result["data"][config_flow.PLEX_SERVER_CONFIG][CONF_TOKEN]
            == file_config[CONF_TOKEN]
        )


async def test_discovery(hass, aioclient_mock):
    """Test starting a flow from discovery."""

    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN,
        context={"source": "discovery"},
        data={CONF_HOST: "1.2.3.4", CONF_PORT: "32400"},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"


async def test_import_bad_hostname(hass, aioclient_mock):
    """Test when an invalid address is provided."""

    with patch(
        "plexapi.server.PlexServer", side_effect=requests.exceptions.ConnectionError
    ):
        result = await hass.config_entries.flow.async_init(
            config_flow.DOMAIN,
            context={"source": "import"},
            data={CONF_TOKEN: "12345", CONF_URL: "http://1.2.3.4:32400"},
        )

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == "not_found"


async def test_unknown_exception(hass, aioclient_mock):
    """Test when an unknown exception is encountered."""

    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"

    with patch("plexapi.myplex.MyPlexAccount", side_effect=Exception):
        result = await hass.config_entries.flow.async_init(
            config_flow.DOMAIN, context={"source": "user"}, data={CONF_TOKEN: "12345"}
        )
        print(result)

        assert result["type"] == "abort"
        assert result["reason"] == "unknown"


async def test_no_servers_found(hass, aioclient_mock):
    """Test when no servers are on an account."""

    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"

    mm_plex_account = MagicMock()
    mm_plex_account.resources = Mock(return_value=[])

    with patch("plexapi.myplex.MyPlexAccount", return_value=mm_plex_account):

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_TOKEN: "12345"}
        )

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == "no_servers"


async def test_single_available_server(hass, aioclient_mock):
    """Test creating an entry with one server available."""

    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"

    mock_connections = MockConnections()
    mock_servers = ["Server1"]
    server1 = MockAvailableServer("Server1", "1")

    mm_plex_account = MagicMock()
    mm_plex_account.resources = Mock(return_value=[server1])
    mm_plex_account.resource = Mock(return_value=mock_connections)

    with patch("plexapi.myplex.MyPlexAccount", return_value=mm_plex_account), patch(
        "plexapi.server.PlexServer"
    ) as mock_plex_server:
        type(mock_plex_server.return_value).machineIdentifier = PropertyMock(
            return_value="unique_id_123"
        )
        type(mock_plex_server.return_value).friendlyName = PropertyMock(
            return_value=mock_servers[0]
        )
        type(mock_plex_server.return_value)._baseurl = PropertyMock(
            return_value=mock_connections.connections[0].httpuri
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_TOKEN: "12345"}
        )

        assert result["type"] == "create_entry"
        assert result["title"] == mock_servers[0]
        assert result["data"][config_flow.CONF_SERVER] == mock_servers[0]
        assert result["data"][config_flow.CONF_SERVER_IDENTIFIER] == "unique_id_123"


async def test_multiple_servers_with_selection(hass, aioclient_mock):
    """Test creating an entry with multiple servers available."""

    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"

    mock_connections = MockConnections()
    mock_servers = ["Server1", "Server2"]
    server1 = MockAvailableServer("Server1", "1")
    server2 = MockAvailableServer("Server2", "2")

    mm_plex_account = MagicMock()
    mm_plex_account.resources = Mock(return_value=[server1, server2])
    mm_plex_account.resource = Mock(return_value=mock_connections)

    with patch("plexapi.myplex.MyPlexAccount", return_value=mm_plex_account), patch(
        "plexapi.server.PlexServer"
    ) as mock_plex_server:
        type(mock_plex_server.return_value).machineIdentifier = PropertyMock(
            return_value="unique_id_123"
        )
        type(mock_plex_server.return_value).friendlyName = PropertyMock(
            return_value=mock_servers[0]
        )
        type(mock_plex_server.return_value)._baseurl = PropertyMock(
            return_value=mock_connections.connections[0].httpuri
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_TOKEN: "12345"}
        )

        assert result["type"] == "form"
        assert result["step_id"] == "select_server"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={config_flow.CONF_SERVER: mock_servers[0]}
        )

        assert result["type"] == "create_entry"
        assert result["title"] == mock_servers[0]
        assert result["data"][config_flow.CONF_SERVER] == mock_servers[0]
        assert result["data"][config_flow.CONF_SERVER_IDENTIFIER] == "unique_id_123"
