"""Provides device automations for Device Tracker."""
from typing import List

import voluptuous as vol

from homeassistant.components.automation import AutomationActionType
from homeassistant.components.device_automation import TRIGGER_BASE_SCHEMA
from homeassistant.components.zone import trigger as zone
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_EVENT,
    CONF_PLATFORM,
    CONF_TYPE,
    CONF_ZONE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry
from homeassistant.helpers.typing import ConfigType

from . import DOMAIN

TRIGGER_TYPES = {"enters", "leaves"}

TRIGGER_SCHEMA = TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
        vol.Required(CONF_ZONE): cv.entity_id,
    }
)


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> List[dict]:
    """List device triggers for Device Tracker devices."""
    registry = await entity_registry.async_get_registry(hass)
    triggers = []

    # Get all the integrations entities for this device
    for entry in entity_registry.async_entries_for_device(registry, device_id):
        if entry.domain != DOMAIN:
            continue

        triggers.append(
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_ENTITY_ID: entry.entity_id,
                CONF_TYPE: "enters",
            }
        )
        triggers.append(
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_ENTITY_ID: entry.entity_id,
                CONF_TYPE: "leaves",
            }
        )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: AutomationActionType,
    automation_info: dict,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    config = TRIGGER_SCHEMA(config)

    if config[CONF_TYPE] == "enters":
        event = zone.EVENT_ENTER
    else:
        event = zone.EVENT_LEAVE

    zone_config = {
        CONF_PLATFORM: "zone",
        CONF_ENTITY_ID: config[CONF_ENTITY_ID],
        CONF_ZONE: config[CONF_ZONE],
        CONF_EVENT: event,
    }
    zone_config = zone.TRIGGER_SCHEMA(zone_config)
    return await zone.async_attach_trigger(
        hass, zone_config, action, automation_info, platform_type="device"
    )
