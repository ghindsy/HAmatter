"""Support for Fully Kiosk Browser image."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fullykiosk import FullyKiosk, FullyKioskError

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .const import DOMAIN
from .coordinator import FullyKioskDataUpdateCoordinator
from .entity import FullyKioskEntity


@dataclass(frozen=True, kw_only=True)
class FullyImageEntityDescription(ImageEntityDescription):
    """Fully Kiosk Browser image entity description."""

    image_action: Callable[[FullyKiosk], Coroutine[Any, Any, bytes]]


IMAGES: tuple[FullyImageEntityDescription, ...] = (
    FullyImageEntityDescription(
        key="screenshot",
        translation_key="screenshot",
        image_action=lambda fully: fully.getScreenshot(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Fully Kiosk Browser image entities."""
    coordinator: FullyKioskDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        FullyImageEntity(coordinator, description) for description in IMAGES
    )


class FullyImageEntity(FullyKioskEntity, ImageEntity):
    """Implement the image entity for Fully Kiosk Browser."""

    entity_description: FullyImageEntityDescription
    _attr_content_type = "image/png"

    def __init__(
        self,
        coordinator: FullyKioskDataUpdateCoordinator,
        description: FullyImageEntityDescription,
    ) -> None:
        """Initialize the entity."""
        FullyKioskEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, coordinator.hass)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data['deviceID']}-{description.key}"

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        try:
            image_bytes = await self.entity_description.image_action(
                self.coordinator.fully
            )
            self._attr_image_last_updated = dt_util.utcnow()
            return image_bytes
        except FullyKioskError as err:
            raise HomeAssistantError(err) from err
