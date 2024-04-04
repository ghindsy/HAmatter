"""DataUpdateCoordinator for System Bridge."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import logging
from typing import Any

from systembridgeconnector.exceptions import (
    AuthenticationException,
    ConnectionClosedException,
    ConnectionErrorException,
)
from systembridgeconnector.websocket_client import WebSocketClient
from systembridgemodels.modules import (
    GetData,
    Module,
    ModulesData,
    RegisterDataListener,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, MODULES
from .data import SystemBridgeData


class SystemBridgeDataUpdateCoordinator(DataUpdateCoordinator[SystemBridgeData]):
    """Class to manage fetching System Bridge data from single endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        LOGGER: logging.Logger,
        *,
        entry: ConfigEntry,
    ) -> None:
        """Initialize global System Bridge data updater."""
        self.title = entry.title
        self.unsub: Callable | None = None

        self.registered = False
        self.websocket_client = WebSocketClient(
            api_host=entry.data[CONF_HOST],
            api_port=entry.data[CONF_PORT],
            token=entry.data[CONF_TOKEN],
            session=async_get_clientsession(hass),
            can_close_session=False,
        )

        self._host = entry.data[CONF_HOST]

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

        self.data = SystemBridgeData()

    async def check_websocket_connected(self) -> None:
        """Check if WebSocket is connected."""
        if not self.websocket_client.connected:
            await self.websocket_client.connect()
            self.registered = False

    async def close_websocket(self) -> None:
        """Close WebSocket connection."""
        await self.websocket_client.close()

    async def clean_disconnect(self) -> None:
        """Clean disconnect WebSocket."""
        if self.unsub:
            self.unsub()
            self.unsub = None
        self.last_update_success = False
        self.async_update_listeners()

    async def async_get_data(
        self,
        modules: list[Module],
    ) -> ModulesData:
        """Get data from WebSocket."""
        if not self.websocket_client.connected:
            await self.websocket_client.connect()

        modules_data = await self.websocket_client.get_data(GetData(modules=modules))

        # Merge new data with existing data
        for module in MODULES:
            if hasattr(modules_data, module):
                self.logger.debug("[async_get_data] Set new data for: %s", module)
                setattr(self.data, module, getattr(modules_data, module))

        return modules_data

    async def async_handle_module(
        self,
        module_name: str,
        module: Any,
    ) -> None:
        """Handle data from the WebSocket client."""
        self.logger.debug("[async_handle_module] Set new data for: %s", module_name)
        setattr(self.data, module_name, module)
        self.async_set_updated_data(self.data)

    async def _listen_for_data(self) -> None:
        """Listen for events from the WebSocket."""
        try:
            await self.websocket_client.listen(callback=self.async_handle_module)
        except AuthenticationException as exception:
            self.logger.error(
                "Authentication failed while listening for %s: %s",
                self.title,
                exception,
            )
            await self.clean_disconnect()
        except (ConnectionClosedException, ConnectionResetError) as exception:
            self.logger.debug(
                "[_listen_for_data] Websocket connection closed for %s. Will retry: %s",
                self.title,
                exception,
            )
            await self.clean_disconnect()
        except ConnectionErrorException as exception:
            self.logger.debug(
                "[_listen_for_data] Connection error occurred for %s. Will retry: %s",
                self.title,
                exception,
            )
            await self.clean_disconnect()

    async def _async_update_data(self) -> SystemBridgeData:
        """Update System Bridge data from WebSocket."""
        self.logger.debug(
            "[_async_update_data] WebSocket Connected: %s",
            self.websocket_client.connected,
        )

        if not self.registered:
            try:
                self.hass.async_create_background_task(
                    self._listen_for_data(),
                    name="System Bridge WebSocket Listener",
                )

                await self.websocket_client.register_data_listener(
                    RegisterDataListener(modules=MODULES)
                )
                self.registered = True

                self.last_update_success = True
                self.async_update_listeners()
            except AuthenticationException as exception:
                self.logger.error(
                    "Authentication failed at setup for %s: %s", self.title, exception
                )
                if self.unsub:
                    self.unsub()
                    self.unsub = None
                self.last_update_success = False
                self.async_update_listeners()
                raise ConfigEntryAuthFailed from exception
            except (ConnectionClosedException, ConnectionErrorException) as exception:
                self.logger.warning(
                    "Connection error occurred for %s. Will retry: %s",
                    self.title,
                    exception,
                )
                self.last_update_success = False
                self.async_update_listeners()
            except TimeoutError as exception:
                self.logger.warning(
                    "Timed out waiting for %s. Will retry: %s",
                    self.title,
                    exception,
                )
                self.last_update_success = False
                self.async_update_listeners()

            # Clean disconnect WebSocket on Home Assistant shutdown
            self.unsub = self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STOP,
                lambda _: self.close_websocket(),
            )

        self.logger.debug("[_async_update_data] Done")

        return self.data
