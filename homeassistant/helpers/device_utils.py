"""Provides useful helpers for dealing with devices."""

from homeassistant.core import HomeAssistant, callback

from . import device_registry as dr, entity_registry as er


@callback
def async_entity_id_to_device_id(
    hass: HomeAssistant,
    entity_id: str,
) -> str | None:
    """Resolve the device id to the entity id."""

    ent_reg = er.async_get(hass)
    if (entity := ent_reg.async_get(entity_id)) is None:
        return None
    return entity.device_id


@callback
def async_device_info_to_link_entity_id(
    hass: HomeAssistant,
    entity_id: str | None,
) -> dr.DeviceInfo | None:
    """DeviceInfo with information to link a device to a configuration entry in the Link category from a entity ID."""

    if (
        entity_id is None
        or (device_id := async_entity_id_to_device_id(hass, entity_id=entity_id))
        is None
    ):
        return None

    return async_device_info_to_link_device_id(
        hass,
        device_id,
    )


@callback
def async_device_info_to_link_device_id(
    hass: HomeAssistant,
    device_id: str | None,
) -> dr.DeviceInfo | None:
    """DeviceInfo with information to link a device to a configuration entry in the Link category from a device ID."""

    dev_reg = dr.async_get(hass)

    if device_id is None or (device := dev_reg.async_get(device_id=device_id)) is None:
        return None

    return dr.DeviceInfo(
        identifiers=device.identifiers,
        connections=device.connections,
    )


@callback
def async_remove_stale_devices_links_keep_entity_device(
    hass: HomeAssistant,
    entry_id: str,
    source_entity_id: str,
) -> None:
    """Remove the link between stales devices and a configuration entry, keeping only the device that the informed entity is linked to."""

    async_remove_stale_devices_links_keep_current_device(
        hass=hass,
        entry_id=entry_id,
        current_device_id=async_entity_id_to_device_id(
            hass, entity_id=source_entity_id
        ),
    )


@callback
def async_remove_stale_devices_links_keep_current_device(
    hass: HomeAssistant,
    entry_id: str,
    current_device_id: str | None,
) -> None:
    """Remove the link between stales devices and a configuration entry, keeping only those informed.

    Device passed in the current_device_id parameter will be kept linked to the configuration entry.
    """

    dev_reg = dr.async_get(hass)
    # Removes all devices from the config entry that are not the same as the current device
    for device in dev_reg.devices.get_devices_for_config_entry_id(entry_id):
        if device.id == current_device_id:
            continue
        dev_reg.async_update_device(device.id, remove_config_entry_id=entry_id)
