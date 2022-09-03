"""Support for Proxmox VE."""
from __future__ import annotations

from datetime import timedelta
import logging

from proxmoxer import ProxmoxAPI
from proxmoxer.backends.https import AuthenticationError
from proxmoxer.core import ResourceException
import requests.exceptions
from requests.exceptions import ConnectTimeout, SSLError
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant, async_get_hass
from homeassistant.exceptions import ConfigEntryAuthFailed
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    CONF_CONTAINERS,
    CONF_LXC,
    CONF_NODE,
    CONF_NODES,
    CONF_QEMU,
    CONF_REALM,
    CONF_VMS,
    COORDINATORS,
    DEFAULT_PORT,
    DEFAULT_REALM,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    PLATFORMS,
    PROXMOX_CLIENT,
    UPDATE_INTERVAL,
    ProxmoxType,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): cv.string,
                        vol.Required(CONF_USERNAME): cv.string,
                        vol.Required(CONF_PASSWORD): cv.string,
                        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                        vol.Optional(CONF_REALM, default=DEFAULT_REALM): cv.string,
                        vol.Optional(
                            CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL
                        ): cv.boolean,
                        vol.Required(CONF_NODES): vol.All(
                            cv.ensure_list,
                            [
                                vol.Schema(
                                    {
                                        vol.Required(CONF_NODE): cv.string,
                                        vol.Optional(CONF_VMS, default=[]): [
                                            cv.positive_int
                                        ],
                                        vol.Optional(CONF_CONTAINERS, default=[]): [
                                            cv.positive_int
                                        ],
                                    }
                                )
                            ],
                        ),
                    }
                )
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the platform."""
    # import to config flow
    if DOMAIN in config:
        for conf in config[DOMAIN]:
            _LOGGER.warning(
                # Proxmox VE config flow added in 2022.10 and should be removed in 2022.12
                "Configuration of the Proxmox in YAML is deprecated and "
                "will be removed in Home Assistant 2022.12; Your existing configuration "
                "has been imported into the UI automatically and can be safely removed "
                "from your configuration.yaml file"
            )
            # Register a repair
            async_create_issue(
                async_get_hass(),
                DOMAIN,
                f"deprecated_yaml_{DOMAIN}",
                breaks_in_ha_version="2022.12.0",
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key="deprecated_yaml",
                translation_placeholders={
                    "integration": "Proxmox VE",
                    "platform": DOMAIN,
                },
            )
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
                )
            )

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up the platform."""

    entry_data = config_entry.data

    host = entry_data[CONF_HOST]
    port = entry_data[CONF_PORT]
    user = entry_data[CONF_USERNAME]
    realm = entry_data[CONF_REALM]
    password = entry_data[CONF_PASSWORD]
    verify_ssl = entry_data[CONF_VERIFY_SSL]

    try:
        # Construct an API client with the given data for the given host
        proxmox_client = ProxmoxClient(host, port, user, realm, password, verify_ssl)
        await hass.async_add_executor_job(proxmox_client.build_client)
    except AuthenticationError as error:
        raise ConfigEntryAuthFailed from error
    except SSLError:
        _LOGGER.error(
            "Unable to verify proxmox server SSL. "
            'Try using "verify_ssl: false" for proxmox instance %s:%d',
            host,
            port,
        )
        return False
    except ConnectTimeout:
        _LOGGER.warning("Connection to host %s timed out during setup", host)
        return False

    coordinators: dict[str, dict[str, dict[int, DataUpdateCoordinator]]] = {}

    proxmox = await hass.async_add_executor_job(proxmox_client.get_api_client)

    node = entry_data[CONF_NODE]
    node_coordinators = coordinators[node] = {}

    # Proxmox instance info
    coordinator = create_coordinator_container_vm(
        hass, proxmox, entry_data[CONF_HOST], None, None, ProxmoxType.Proxmox
    )

    # Fetch initial data
    await coordinator.async_refresh()

    node_coordinators[ProxmoxType.Proxmox] = coordinator

    # Node info
    coordinator = create_coordinator_container_vm(
        hass, proxmox, entry_data[CONF_HOST], node, None, ProxmoxType.Node
    )

    # Fetch initial data
    await coordinator.async_refresh()

    node_coordinators[ProxmoxType.Node] = coordinator

    # QEMU info
    for vm_id in entry_data[CONF_QEMU]:
        coordinator = create_coordinator_container_vm(
            hass,
            proxmox,
            entry_data[CONF_HOST],
            node,
            vm_id,
            ProxmoxType.QEMU,
        )

        # Fetch initial data
        await coordinator.async_refresh()

        node_coordinators[vm_id] = coordinator

    # LXC info
    for container_id in entry_data[CONF_LXC]:
        coordinator = create_coordinator_container_vm(
            hass,
            proxmox,
            entry_data[CONF_HOST],
            node,
            container_id,
            ProxmoxType.LXC,
        )

        # Fetch initial data
        await coordinator.async_refresh()

        node_coordinators[container_id] = coordinator

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        PROXMOX_CLIENT: proxmox_client,
        COORDINATORS: coordinators,
    }

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def create_coordinator_container_vm(
    hass, proxmox, host_name, node_name, vm_id, vm_type
):
    """Create and return a DataUpdateCoordinator for a vm/container."""

    async def async_update_data():
        """Call the api and handle the response."""

        def poll_api():
            """Call the api."""
            vm_status = call_api_container_vm(proxmox, node_name, vm_id, vm_type)
            return vm_status

        vm_status = await hass.async_add_executor_job(poll_api)

        if vm_status is None:
            _LOGGER.warning(
                "Vm/Container %s unable to be found in node %s", vm_id, node_name
            )
            return None

        return parse_api_container_vm(vm_status, vm_type)

    return DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"proxmox_coordinator_{host_name}_{node_name}_{vm_id}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=UPDATE_INTERVAL),
    )


def parse_api_container_vm(status, info_type):
    """Get the container or vm api data and return it formatted in a dictionary.

    It is implemented in this way to allow for more data to be added for sensors
    in the future.
    """
    if info_type == ProxmoxType.Proxmox:
        return {
            "version": status["version"],
        }
    if info_type is ProxmoxType.Node:
        return {
            "uptime": status["uptime"],
        }
    if info_type in (ProxmoxType.QEMU, ProxmoxType.LXC):
        return {
            "status": status["status"],
            "name": status["name"],
        }


def call_api_container_vm(proxmox, node_name, vm_id, info_type):
    """Make proper api calls."""
    status = None

    try:
        if info_type == ProxmoxType.Proxmox:
            status = proxmox.version.get()
        elif info_type is ProxmoxType.Node:
            status = proxmox.nodes(node_name).status.get()
        elif info_type == ProxmoxType.QEMU:
            status = proxmox.nodes(node_name).qemu(vm_id).status.current.get()
        elif info_type == ProxmoxType.LXC:
            status = proxmox.nodes(node_name).lxc(vm_id).status.current.get()
    except (ResourceException, requests.exceptions.ConnectionError):
        return None

    return status


class ProxmoxEntity(CoordinatorEntity):
    """Represents any entity created for the Proxmox VE platform."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        unique_id,
        name,
        icon,
        node_name,
        vm_id=None,
    ):
        """Initialize the Proxmox entity."""
        super().__init__(coordinator)

        self.coordinator = coordinator
        self._unique_id = unique_id
        self._name = name
        self._icon = icon
        self._available = True
        self._node_name = node_name
        self._vm_id = vm_id

        self._state = None

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this sensor."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def icon(self) -> str:
        """Return the mdi icon of the entity."""
        return self._icon

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self._available


class ProxmoxClient:
    """A wrapper for the proxmoxer ProxmoxAPI client."""

    def __init__(self, host, port, user, realm, password, verify_ssl):
        """Initialize the ProxmoxClient."""

        self._host = host
        self._port = port
        self._user = user
        self._realm = realm
        self._password = password
        self._verify_ssl = verify_ssl

        self._proxmox = None
        self._connection_start_time = None

    def build_client(self):
        """Construct the ProxmoxAPI client. Allows inserting the realm within the `user` value."""

        if "@" in self._user:
            user_id = self._user
        else:
            user_id = f"{self._user}@{self._realm}"

        self._proxmox = ProxmoxAPI(
            self._host,
            port=self._port,
            user=user_id,
            password=self._password,
            verify_ssl=self._verify_ssl,
        )

    def get_api_client(self):
        """Return the ProxmoxAPI client."""
        return self._proxmox
