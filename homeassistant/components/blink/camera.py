"""Support for Blink system camera."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import contextlib
import logging
from typing import Any

from requests.exceptions import ChunkedEncodingError

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_BRAND, DOMAIN, SERVICE_TRIGGER
from .coordinator import BlinkUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

ATTR_VIDEO_CLIP = "video"
ATTR_IMAGE = "image"


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a Blink Camera."""
    coordinator: BlinkUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
    entities = [
        BlinkCamera(coordinator, name, camera)
        for name, camera in coordinator.api.cameras.items()
    ]

    async_add_entities(entities)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(SERVICE_TRIGGER, {}, "trigger_camera")


class BlinkCamera(CoordinatorEntity, Camera):
    """An implementation of a Blink Camera."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: BlinkUpdateCoordinator, name, camera) -> None:
        """Initialize a camera."""
        super().__init__(coordinator)
        Camera.__init__(self)
        self._coordinator = coordinator
        self._camera = camera
        self._attr_unique_id = f"{camera.serial}-camera"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, camera.serial)},
            name=name,
            manufacturer=DEFAULT_BRAND,
            model=camera.camera_type,
        )
        _LOGGER.debug("Initialized blink camera %s", self.name)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the camera attributes."""
        return self._camera.attributes

    async def async_enable_motion_detection(self) -> None:
        """Enable motion detection for the camera."""
        try:
            await self._camera.async_arm(True)

        except asyncio.TimeoutError as er:
            raise HomeAssistantError("Blink failed to arm camera") from er

        self._camera.motion_enabled = True
        await self._coordinator.async_refresh()

    async def async_disable_motion_detection(self) -> None:
        """Disable motion detection for the camera."""
        try:
            await self._camera.async_arm(False)
        except asyncio.TimeoutError as er:
            raise HomeAssistantError("Blink failed to disarm camera") from er

        self._camera.motion_enabled = False
        await self._coordinator.async_refresh()

    @property
    def motion_detection_enabled(self) -> bool:
        """Return the state of the camera."""
        return self._camera.arm

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update camera data."""
        self.async_write_ha_state()

    @property
    def brand(self) -> str | None:
        """Return the camera brand."""
        return DEFAULT_BRAND

    async def trigger_camera(self) -> None:
        """Trigger camera to take a snapshot."""
        with contextlib.suppress(asyncio.TimeoutError):
            await self._camera.snap_picture()

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""
        try:
            return self._camera.image_from_cache
        except ChunkedEncodingError:
            _LOGGER.debug("Could not retrieve image for %s", self._camera.name)
            return None
        except TypeError:
            _LOGGER.debug("No cached image for %s", self._camera.name)
            return None
