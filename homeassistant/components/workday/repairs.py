"""Repairs platform for the Workday integration."""

from __future__ import annotations

from typing import Any, cast

from holidays import list_supported_countries
import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_COUNTRY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .config_flow import NONE_SENTINEL
from .const import CONF_PROVINCE


class CountryFixFlow(RepairsFlow):
    """Handler for an issue fixing flow."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Create flow."""
        self.entry = entry
        self.country: str | None = None
        super().__init__()

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of a fix flow."""

        return await self.async_step_country()

    async def async_step_country(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the country step of a fix flow."""
        if user_input is not None:
            all_countries = list_supported_countries()
            if not all_countries[user_input[CONF_COUNTRY]]:
                return self.async_create_entry(data={})
            self.country = user_input[CONF_COUNTRY]
            return await self.async_step_province()

        return self.async_show_form(
            step_id="country",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COUNTRY): SelectSelector(
                        SelectSelectorConfig(
                            options=sorted(list_supported_countries()),
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            description_placeholders={"title": self.entry.title},
        )

    async def async_step_province(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the province step of a fix flow."""
        if user_input and user_input.get(CONF_PROVINCE):
            if user_input.get(CONF_PROVINCE, NONE_SENTINEL) == NONE_SENTINEL:
                user_input[CONF_PROVINCE] = None
            options = dict(self.entry.options)
            new_options = {**options, **user_input, CONF_COUNTRY: self.country}
            self.hass.config_entries.async_update_entry(self.entry, options=new_options)
            await self.hass.config_entries.async_reload(self.entry.entry_id)
            return self.async_create_entry(data={})

        assert self.country
        country_provinces = list_supported_countries()[self.country]
        return self.async_show_form(
            step_id="province",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PROVINCE, default=NONE_SENTINEL): SelectSelector(
                        SelectSelectorConfig(
                            options=[NONE_SENTINEL, *country_provinces],
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key=CONF_PROVINCE,
                        )
                    ),
                }
            ),
            description_placeholders={
                CONF_COUNTRY: self.country,
                "title": self.entry.title,
            },
        )


class ProvinceFixFlow(RepairsFlow):
    """Handler for an issue fixing flow."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Create flow."""
        self.entry = entry
        super().__init__()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of a fix flow."""

        return await self.async_step_province()

    async def async_step_province(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the province step of a fix flow."""
        if user_input and user_input.get(CONF_PROVINCE):
            if user_input.get(CONF_PROVINCE, NONE_SENTINEL) == NONE_SENTINEL:
                user_input[CONF_PROVINCE] = None
            options = dict(self.entry.options)
            new_options = {**options, **user_input}
            self.hass.config_entries.async_update_entry(self.entry, options=new_options)
            await self.hass.config_entries.async_reload(self.entry.entry_id)
            return self.async_create_entry(data={})

        country = self.entry.options[CONF_COUNTRY]
        all_countries = list_supported_countries()
        province_list = [NONE_SENTINEL, *all_countries[country]]
        return self.async_show_form(
            step_id="province",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PROVINCE, default=NONE_SENTINEL): SelectSelector(
                        SelectSelectorConfig(
                            options=province_list,
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key=CONF_PROVINCE,
                        )
                    ),
                }
            ),
            description_placeholders={CONF_COUNTRY: country, "title": self.entry.title},
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Create flow."""
    entry = None
    if data and (entry_id := data.get("entry_id")):
        entry_id = cast(str, entry_id)
        entry = hass.config_entries.async_get_entry(entry_id)

    if entry and issue_id == "bad_province":
        # Province does not exist
        return ProvinceFixFlow(entry)

    if entry and issue_id == "bad_country":
        # Country does not exist
        return CountryFixFlow(entry)

    return ConfirmRepairFlow()
