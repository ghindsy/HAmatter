"""webOS Smart TV trigger dispatcher."""
from __future__ import annotations

from typing import cast

from homeassistant.const import CONF_PLATFORM
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .triggers import TriggersPlatformModule, turn_on

TRIGGERS = {
    "turn_on": turn_on,
}


def _get_trigger_platform(config: ConfigType) -> TriggersPlatformModule:
    """Return trigger platform."""
    trigger = config[CONF_PLATFORM].partition(".")[-1]
    if trigger not in TRIGGERS:
        raise ValueError(
            f"Unknown webOS Smart TV trigger platform {config[CONF_PLATFORM]}"
        )
    return cast(TriggersPlatformModule, TRIGGERS[trigger])


async def async_validate_trigger_config(
    hass: HomeAssistant, config: ConfigType
) -> ConfigType:
    """Validate config."""
    platform = _get_trigger_platform(config)
    return cast(ConfigType, platform.TRIGGER_SCHEMA(config))


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach trigger of specified platform."""
    platform = _get_trigger_platform(config)
    assert hasattr(platform, "async_attach_trigger")
    return cast(
        CALLBACK_TYPE,
        await getattr(platform, "async_attach_trigger")(
            hass, config, action, trigger_info
        ),
    )
