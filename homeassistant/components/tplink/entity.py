"""Common code for tplink."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Coroutine
import logging
from typing import Any, Concatenate, TypedDict, Unpack

from kasa import (
    AuthenticationError,
    Device,
    DeviceType,
    Feature,
    KasaException,
    TimeoutError,
)

from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import legacy_device_id
from .const import DOMAIN, PRIMARY_STATE_ID
from .coordinator import TPLinkDataUpdateCoordinator


class EntityDescriptionExtras(TypedDict, total=False):
    """Extra kwargs that can be provided to entity descriptions."""

    entity_registry_enabled_default: bool


_LOGGER = logging.getLogger(__name__)


def async_refresh_after[_T: CoordinatedTPLinkEntity, **_P](
    func: Callable[Concatenate[_T, _P], Awaitable[None]],
) -> Callable[Concatenate[_T, _P], Coroutine[Any, Any, None]]:
    """Define a wrapper to raise HA errors and refresh after."""

    async def _async_wrap(self: _T, *args: _P.args, **kwargs: _P.kwargs) -> None:
        try:
            await func(self, *args, **kwargs)
        except AuthenticationError as ex:
            self.coordinator.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_authentication",
                translation_placeholders={
                    "func": func.__name__,
                    "exc": str(ex),
                },
            ) from ex
        except TimeoutError as ex:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_timeout",
                translation_placeholders={
                    "func": func.__name__,
                    "exc": str(ex),
                },
            ) from ex
        except KasaException as ex:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_error",
                translation_placeholders={
                    "func": func.__name__,
                    "exc": str(ex),
                },
            ) from ex
        await self.coordinator.async_request_refresh()

    return _async_wrap


class CoordinatedTPLinkEntity(CoordinatorEntity[TPLinkDataUpdateCoordinator], ABC):
    """Common base class for all coordinated tplink entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: Device,
        coordinator: TPLinkDataUpdateCoordinator,
        feature: Feature | None = None,
        parent: Device | None = None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.device: Device = device
        self._feature = feature
        self._attr_device_info = DeviceInfo(
            # connections={(dr.CONNECTION_NETWORK_MAC, device.mac)},
            identifiers={(DOMAIN, str(device.device_id))},
            manufacturer="TP-Link",
            model=device.model,
            name=device.alias,
            sw_version=device.hw_info["sw_ver"],
            hw_version=device.hw_info["hw_ver"],
        )

        if parent is not None:
            self._attr_device_info["via_device"] = (DOMAIN, parent.device_id)

        # The rest of the initialization takes care of setting a proper unique_id
        # This is transitional and will become cleaner as future platforms get converted.

        # If the unique id is already defined, we don't need to do anything.
        if self._attr_unique_id is not None:
            return

        # If no unique id is defined and we have no feature, it's a bug.
        if feature is None:
            raise HomeAssistantError(
                "Entity is not feature-based nor does define unique_id"
            )

        self._attr_entity_category = self._category_for_feature(feature)

        # Special handling for entity classes that define unique_id on their own.
        if feature.id == PRIMARY_STATE_ID:
            self._attr_unique_id = legacy_device_id(device)
        else:
            self._attr_unique_id = f"{legacy_device_id(device)}_{feature.id}"
            _LOGGER.debug(
                "Initializing feature-based %s with category %s",
                self._attr_unique_id,
                self._attr_entity_category,
            )

    def _category_for_feature(self, feature: Feature) -> EntityCategory | None:
        """Return entity category for a feature."""
        match feature.category:
            # Main controls have no category
            case Feature.Category.Primary:
                return None
            case Feature.Category.Config:
                return EntityCategory.CONFIG
            case Feature.Category.Info:
                return EntityCategory.DIAGNOSTIC
            case Feature.Category.Debug:
                return EntityCategory.DIAGNOSTIC
            case _:
                _LOGGER.error(
                    "Unhandled category %s, fallback to DIAGNOSTIC", feature.category
                )
                return EntityCategory.DIAGNOSTIC

    @abstractmethod
    @callback
    def _async_update_attrs(self) -> None:
        """Platforms implement this to update the entity internals."""
        raise NotImplementedError

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            self._async_update_attrs()
            self._attr_available = True
        except Exception as ex:  # noqa: BLE001
            if self._attr_available:
                _LOGGER.warning(
                    "Unable to read data for %s %s: %s",
                    self.device,
                    self.entity_description,
                    ex,
                )
            self._attr_available = False

        super()._handle_coordinator_update()


def _entities_for_device[_E: CoordinatedTPLinkEntity](
    device: Device,
    *,
    feature_type: Feature.Type,
    entity_class: type[_E],
    coordinator: TPLinkDataUpdateCoordinator,
    parent: Device | None = None,
) -> list[_E]:
    """Return a list of entities to add.

    This filters out unwanted features to avoid creating unnecessary entities
    for device features that are implemented by specialized platforms like light.
    """

    def _filter(dev: Device, feat: Feature) -> bool:
        if feat.type != feature_type:
            return False

        # We skip primary features for device types that have specialized platforms.
        ignore_primary_controls_devicetypes = [
            DeviceType.Bulb,
            DeviceType.LightStrip,
            DeviceType.Dimmer,
            DeviceType.Thermostat,
        ]
        if (
            feat.category == Feature.Category.Primary
            and dev.device_type in ignore_primary_controls_devicetypes
        ):
            return False

        return True

    return [
        entity_class(device, coordinator, feat, parent=parent)
        for feat in device.features.values()
        if _filter(device, feat)
    ]


def _entities_for_device_and_its_children[_E: CoordinatedTPLinkEntity](
    device: Device,
    *,
    feature_type: Feature.Type,
    entity_class: type[_E],
    coordinator: TPLinkDataUpdateCoordinator,
) -> list[_E]:
    """Create entities for device and its children.

    This is a helper that calls *_entities_for_device* for the device and its children.
    """
    entities = []
    if device.children:
        _LOGGER.debug("Initializing device with %s children", len(device.children))
        for child in device.children:
            entities.extend(
                _entities_for_device(
                    child,
                    feature_type=feature_type,
                    entity_class=entity_class,
                    coordinator=coordinator,
                    parent=device,
                )
            )

    entities.extend(
        _entities_for_device(
            device,
            feature_type=feature_type,
            entity_class=entity_class,
            coordinator=coordinator,
        )
    )

    return entities


def _description_for_feature[_D: EntityDescription](
    desc_cls: type[_D], feature: Feature, **kwargs: Unpack[EntityDescriptionExtras]
) -> _D:
    """Return description object for the given feature.

    This is responsible for setting the common parameters & deciding based on feature id
    which additional parameters are passed.
    """

    # Disable all debug features that are not explicitly enabled.
    if "entity_registry_enabled_default" not in kwargs:
        kwargs["entity_registry_enabled_default"] = (
            feature.category is not Feature.Category.Debug
        )

    return desc_cls(
        key=feature.id,
        translation_key=feature.id,
        name=feature.name,
        # Setting an icon overrides the translation, so we doing it here.
        # icon=feature.icon,
        **kwargs,
    )
