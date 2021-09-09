"""DataUpdateCoordinators for the Fronius integration."""
from __future__ import annotations

from typing import Any, Dict, Mapping

from homeassistant.core import callback
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import SolarNetId
from .descriptions import METER_ENTITY_DESCRIPTIONS


class _FroniusSystemUpdateCoordinator(
    DataUpdateCoordinator[Dict[SolarNetId, Dict[str, Any]]]
):
    """Query Fronius endpoint and keep track of seen conditions."""

    valid_descriptions: Mapping[str, EntityDescription]

    def __init__(self, *args, **kwargs) -> None:
        """Set up the FroniusMeterUpdateCoordinator class."""
        # unregistered_keys are used to create entities in platform module
        self.unregistered_keys: dict[SolarNetId, set[str]] = {}
        super().__init__(*args, **kwargs)

    @staticmethod
    def _get_fronius_device_data(data: dict[str, Any]) -> dict[SolarNetId, Any]:
        """Return data per solar net id from raw data."""
        raise NotImplementedError("_get_fronius_device_data not implemented")

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest data from the source."""
        if self.update_method is None:
            raise NotImplementedError("Update method not implemented")
        raw_data = await self.update_method()
        data = self._get_fronius_device_data(raw_data)
        for solar_net_id in data:
            if solar_net_id not in self.unregistered_keys:
                # id seen for the first time
                self.unregistered_keys[solar_net_id] = set(self.valid_descriptions)
        return data

    @callback
    def add_entities_for_seen_keys(
        self,
        async_add_entities: AddEntitiesCallback,
        entity_constructor: type[FroniusEntity],
    ) -> None:
        """
        Add entities for received keys and registers listener for future seen keys.

        Called from a platforms `async_setup_entry`.
        """

        @callback
        def _add_entities_for_unregistered_keys():
            """Add entities for keys seen for the first time."""
            new_entities: list = []
            for solar_net_id, device_data in self.data.items():
                for key in self.unregistered_keys[solar_net_id].intersection(
                    device_data
                ):
                    new_entities.append(
                        entity_constructor(
                            self, self.valid_descriptions[key], solar_net_id
                        )
                    )
                    self.unregistered_keys[solar_net_id].remove(key)
            if new_entities:
                async_add_entities(new_entities)

        _add_entities_for_unregistered_keys()
        self.async_add_listener(_add_entities_for_unregistered_keys)


class FroniusMeterUpdateCoordinator(_FroniusSystemUpdateCoordinator):
    """Query Fronius system meter endpoint and keep track of seen conditions."""

    valid_descriptions = METER_ENTITY_DESCRIPTIONS

    @staticmethod
    def _get_fronius_device_data(data: dict[str, Any]) -> dict[SolarNetId, Any]:
        """Return data per solar net id from raw data."""
        return data["meters"]


# class FroniusInverterUpdateCoordinator(DataUpdateCoordinator):
#     """Query Fronius endpoint and keep track of seen conditions."""

#     def __init__(self, *args, **kwargs) -> None:
#         """Set up the FroniusInverterUpdateCoordinator class."""
#         self.seen_conditions: dict[SolarNetId, set[str]] = {}
#         self.device_infos: dict[SolarNetId, DeviceInfo] = {}
#         super().__init__(*args, **kwargs)

#     async def async_config_entry_first_refresh(self) -> None:
#         """Refresh data for the first time when a config entry is setup."""
#         await super().async_config_entry_first_refresh()
#         for solar_net_id, meter in self.data["meters"].items():
#             self.device_infos[solar_net_id] = DeviceInfo(
#                 name=meter["model"]["value"],
#                 identifiers={(DOMAIN, meter["serial"]["value"])},
#                 manufacturer=meter["manufacturer"]["value"],
#             )


class FroniusEntity(CoordinatorEntity):
    """Defines a Fronius coordinator entity."""

    def __init__(
        self,
        coordinator: _FroniusSystemUpdateCoordinator,
        entity_description: EntityDescription,
        solar_net_id: str,
    ) -> None:
        """Set up an individual Fronius meter sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self.solar_net_id = solar_net_id

    @property
    def _device_data(self) -> dict[str, Any]:
        return self.coordinator.data[self.solar_net_id]
