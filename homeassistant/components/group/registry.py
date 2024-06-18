"""Provide the functionality to group entities.

Legacy group support will not be extended for new domains.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from homeassistant.components.climate import HVACMode
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_CUSTOM_BYPASS,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_ARMED_VACATION,
    STATE_ALARM_TRIGGERED,
    STATE_CLOSED,
    STATE_HOME,
    STATE_IDLE,
    STATE_LOCKED,
    STATE_LOCKING,
    STATE_NOT_HOME,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_OPENING,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_UNLOCKED,
    STATE_UNLOCKING,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.integration_platform import (
    async_process_integration_platforms,
)

from .const import DOMAIN, REG_KEY

EXCLUDED_DOMAINS = {"air_quality", "sensor", "weather"}

ON_OFF_STATES = {
    "alarm_control_panel": (
        {
            STATE_ON,
            STATE_ALARM_ARMED_AWAY,
            STATE_ALARM_ARMED_CUSTOM_BYPASS,
            STATE_ALARM_ARMED_HOME,
            STATE_ALARM_ARMED_NIGHT,
            STATE_ALARM_ARMED_VACATION,
            STATE_ALARM_TRIGGERED,
        },
        STATE_ON,
        STATE_OFF,
    ),
    "climate": (
        {
            STATE_ON,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.HEAT_COOL,
            HVACMode.AUTO,
            HVACMode.FAN_ONLY,
        },
        STATE_ON,
        STATE_OFF,
    ),
    "cover": ({STATE_OPEN}, STATE_OPEN, STATE_CLOSED),
    "device_tracker": ({STATE_HOME}, STATE_HOME, STATE_NOT_HOME),
    "lock": (
        {
            STATE_LOCKING,
            STATE_OPEN,
            STATE_OPENING,
            STATE_UNLOCKED,
            STATE_UNLOCKING,
        },
        STATE_UNLOCKED,
        STATE_LOCKED,
    ),
    "media_player": (
        {
            STATE_ON,
            STATE_PAUSED,
            STATE_PLAYING,
            STATE_IDLE,
        },
        STATE_ON,
        STATE_OFF,
    ),
}


async def async_setup(hass: HomeAssistant) -> None:
    """Set up the Group integration registry of integration platforms."""
    hass.data[REG_KEY] = GroupIntegrationRegistry(hass)

    await async_process_integration_platforms(
        hass, DOMAIN, _process_group_platform, wait_for_platforms=True
    )


class GroupProtocol(Protocol):
    """Define the format of group platforms."""

    def async_describe_on_off_states(
        self, hass: HomeAssistant, registry: GroupIntegrationRegistry
    ) -> None:
        """Describe group on off states."""


@callback
def _process_group_platform(
    hass: HomeAssistant, domain: str, platform: GroupProtocol
) -> None:
    """Process a group platform."""
    registry: GroupIntegrationRegistry = hass.data[REG_KEY]
    platform.async_describe_on_off_states(hass, registry)


@dataclass(frozen=True, slots=True)
class SingleStateType:
    """Dataclass to store a single state type."""

    on_state: str
    off_state: str


class GroupIntegrationRegistry:
    """Class to hold a registry of integrations."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Imitialize registry."""
        self.hass = hass
        self.on_off_mapping: dict[str, str] = {STATE_ON: STATE_OFF}
        self.off_on_mapping: dict[str, str] = {STATE_OFF: STATE_ON}
        self.on_states_by_domain: dict[str, set[str]] = {}
        self.exclude_domains: set[str] = EXCLUDED_DOMAINS
        self.state_group_mapping: dict[str, SingleStateType] = {}
        for domain, on_off_states in ON_OFF_STATES.items():
            self.on_off_states(domain, *on_off_states)

    @callback
    def exclude_domain(self, domain: str) -> None:
        """Exclude the current domain."""
        self.exclude_domains.add(domain)

    @callback
    def on_off_states(
        self, domain: str, on_states: set[str], default_on_state: str, off_state: str
    ) -> None:
        """Register on and off states for the current domain.

        Legacy group support will not be extended for new domains.
        """
        for on_state in on_states:
            if on_state not in self.on_off_mapping:
                self.on_off_mapping[on_state] = off_state

        if off_state not in self.off_on_mapping:
            self.off_on_mapping[off_state] = default_on_state
        self.state_group_mapping[domain] = SingleStateType(default_on_state, off_state)

        self.on_states_by_domain[domain] = on_states
