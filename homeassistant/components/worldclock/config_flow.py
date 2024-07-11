"""Config flow for World clock."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast
import zoneinfo

import voluptuous as vol

from homeassistant.const import CONF_NAME, CONF_TIME_ZONE
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler,
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
)
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import CONF_TIME_FORMAT, DEFAULT_NAME, DEFAULT_TIME_STR_FORMAT, DOMAIN


async def validate_duplicate(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate already existing entry."""
    handler.parent_handler._async_abort_entries_match({**handler.options, **user_input})  # noqa: SLF001

    return user_input


async def get_schema(handler: SchemaCommonFlowHandler) -> vol.Schema:
    """Get available timezones."""
    get_timezones: list[str] = list(
        await handler.parent_handler.hass.async_add_executor_job(
            zoneinfo.available_timezones
        )
    )
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=DEFAULT_NAME): TextSelector(),
            vol.Required(CONF_TIME_ZONE): SelectSelector(
                SelectSelectorConfig(
                    options=get_timezones, mode=SelectSelectorMode.DROPDOWN, sort=True
                )
            ),
        }
    ).extend(DATA_SCHEMA_OPTIONS.schema)


DATA_SCHEMA_OPTIONS = vol.Schema(
    {vol.Optional(CONF_TIME_FORMAT, default=DEFAULT_TIME_STR_FORMAT): TextSelector()}
)


CONFIG_FLOW = {
    "user": SchemaFlowFormStep(
        schema=get_schema,
        validate_user_input=validate_duplicate,
    ),
    "import": SchemaFlowFormStep(
        schema=get_schema,
        validate_user_input=validate_duplicate,
    ),
}
OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(
        DATA_SCHEMA_OPTIONS,
        validate_user_input=validate_duplicate,
    )
}


class WorldclockConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Worldclock."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return cast(str, options[CONF_NAME])
