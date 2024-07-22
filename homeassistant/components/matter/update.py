"""Matter update."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from chip.clusters import Objects as clusters
from matter_server.common.errors import UpdateCheckError, UpdateError
from matter_server.common.models import MatterSoftwareVersion

from homeassistant.components.update import (
    ATTR_LATEST_VERSION,
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import ExtraStoredData

from .entity import MatterEntity
from .helpers import get_matter
from .models import MatterDiscoverySchema

SCAN_INTERVAL = timedelta(hours=12)
POLL_AFTER_INSTALL = 10

ATTR_SOFTWARE_UPDATE = "software_update"


@dataclass
class MatterUpdateExtraStoredData(ExtraStoredData):
    """Extra stored data for Matter node firmware update entity."""

    software_update: MatterSoftwareVersion | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a dict representation of the extra data."""
        return {
            ATTR_SOFTWARE_UPDATE: self.software_update.as_dict()
            if self.software_update is not None
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MatterUpdateExtraStoredData:
        """Initialize the extra data from a dict."""
        if data[ATTR_SOFTWARE_UPDATE] is None:
            return cls()
        return cls(MatterSoftwareVersion.from_dict(data[ATTR_SOFTWARE_UPDATE]))


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Matter lock from Config Entry."""
    matter = get_matter(hass)
    matter.register_platform_handler(Platform.UPDATE, async_add_entities)


class MatterUpdate(MatterEntity, UpdateEntity):
    """Representation of a Matter node capable of updating."""

    _software_update: MatterSoftwareVersion | None = None
    _cancel_update: CALLBACK_TYPE | None = None

    @callback
    def _update_from_device(self) -> None:
        """Update from device."""

        self._attr_installed_version = self.get_matter_attribute_value(
            clusters.BasicInformation.Attributes.SoftwareVersionString
        )

        if self.get_matter_attribute_value(
            clusters.OtaSoftwareUpdateRequestor.Attributes.UpdatePossible
        ):
            self._attr_supported_features = (
                UpdateEntityFeature.INSTALL
                | UpdateEntityFeature.PROGRESS
                | UpdateEntityFeature.SPECIFIC_VERSION
            )

        update_state: clusters.OtaSoftwareUpdateRequestor.Enums.UpdateStateEnum = (
            self.get_matter_attribute_value(
                clusters.OtaSoftwareUpdateRequestor.Attributes.UpdateState
            )
        )
        if (
            update_state
            == clusters.OtaSoftwareUpdateRequestor.Enums.UpdateStateEnum.kIdle
        ):
            self._attr_in_progress = False
            return

        update_progress: int = self.get_matter_attribute_value(
            clusters.OtaSoftwareUpdateRequestor.Attributes.UpdateStateProgress
        )

        if (
            update_state
            == clusters.OtaSoftwareUpdateRequestor.Enums.UpdateStateEnum.kDownloading
            and update_progress is not None
            and update_progress > 0
        ):
            self._attr_in_progress = update_progress
        else:
            self._attr_in_progress = True

    async def async_update(self) -> None:
        """Call when the entity needs to be updated."""
        try:
            update_information = await self.matter_client.check_node_update(
                node_id=self._endpoint.node.node_id
            )
            if not update_information:
                self._attr_latest_version = self._attr_installed_version
                return

            self._software_update = update_information
            self._attr_latest_version = update_information.software_version_string
            self._attr_release_url = update_information.release_notes_url
        except UpdateCheckError as err:
            raise HomeAssistantError(f"Error finding applicable update: {err}") from err

    async def async_added_to_hass(self) -> None:
        """Call when the entity is added to hass."""
        await super().async_added_to_hass()

        if state := await self.async_get_last_state():
            self._attr_latest_version = state.attributes.get(ATTR_LATEST_VERSION)

        if (extra_data := await self.async_get_last_extra_data()) and (
            matter_extra_data := MatterUpdateExtraStoredData.from_dict(
                extra_data.as_dict()
            )
        ):
            self._software_update = matter_extra_data.software_update
        else:
            # Check for updates when added the first time.
            await self.async_update()

    @property
    def extra_restore_state_data(self) -> MatterUpdateExtraStoredData:
        """Return Matter specific state data to be restored."""
        return MatterUpdateExtraStoredData(self._software_update)

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture to use in the frontend.

        This overrides UpdateEntity.entity_picture because the Matter brand picture
        is not appropriate for a matter device which has its own brand.
        """
        return None

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install a new software version."""

        software_version: str | int | None = version
        if self._software_update is not None and (
            version is None or version == self._software_update.software_version_string
        ):
            # Update to the version previously fetched and shown.
            # We can pass the integer version directly to speedup download.
            software_version = self._software_update.software_version

        if software_version is None:
            raise HomeAssistantError("No software version specified")

        self._attr_in_progress = True
        self.async_write_ha_state()
        try:
            await self.matter_client.update_node(
                node_id=self._endpoint.node.node_id,
                software_version=software_version,
            )
        except UpdateCheckError as err:
            raise HomeAssistantError(f"Error finding applicable update: {err}") from err
        except UpdateError as err:
            raise HomeAssistantError(f"Error updating: {err}") from err
        finally:
            # Check for updates right after the update since Matter devices
            # can have strict update paths (e.g. Eve)
            self._cancel_update = async_call_later(
                self.hass, POLL_AFTER_INSTALL, self._async_update_future
            )

    async def _async_update_future(self, now: datetime | None = None) -> None:
        """Request update."""
        await self.async_update()

    async def async_will_remove_from_hass(self) -> None:
        """Entity removed."""
        await super().async_will_remove_from_hass()
        if self._cancel_update is not None:
            self._cancel_update()


DISCOVERY_SCHEMAS = [
    MatterDiscoverySchema(
        platform=Platform.UPDATE,
        entity_description=UpdateEntityDescription(
            key="MatterUpdate", device_class=UpdateDeviceClass.FIRMWARE, name=None
        ),
        entity_class=MatterUpdate,
        required_attributes=(
            clusters.BasicInformation.Attributes.SoftwareVersion,
            clusters.BasicInformation.Attributes.SoftwareVersionString,
            clusters.OtaSoftwareUpdateRequestor.Attributes.UpdatePossible,
            clusters.OtaSoftwareUpdateRequestor.Attributes.UpdateState,
            clusters.OtaSoftwareUpdateRequestor.Attributes.UpdateStateProgress,
        ),
    ),
]
