"""Moon phase Calendar."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import get_moon_phases
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Moon phase Calendar config entry."""

    obj_moon_phases = get_moon_phases(
        dt_util.now(), (dt_util.now() + timedelta(days=30))
    )

    async_add_entities(
        [
            MoonCalendarEntity(
                config_entry.title,
                obj_moon_phases,
                config_entry.entry_id,
            )
        ],
        True,
    )


class MoonCalendarEntity(CalendarEntity):
    """Representation of a Moon Phase Calendar element."""

    _attr_has_entity_name = True
    _attr_translation_key = "moon_phases"

    def __init__(
        self,
        name: str,
        obj_moon_phases: list[dict[str, Any]],
        unique_id: str,
    ) -> None:
        """Initialize MoonCalendarEntity."""
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            entry_type=DeviceEntryType.SERVICE,
            name=name,
        )
        self._obj_moon_phases = obj_moon_phases

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming moon    phase."""
        next_moon_phase = None
        for moon_phase in self._obj_moon_phases:
            if moon_phase["date"] >= dt_util.now().date():
                next_moon_phase = (
                    moon_phase["date"],
                    moon_phase["phase"],
                    moon_phase["end"],
                )
                break

        if next_moon_phase is None:
            return None

        return CalendarEvent(
            summary=next_moon_phase[1],
            start=next_moon_phase[0],
            end=next_moon_phase[2],
        )

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        obj_moon_phases = get_moon_phases(start_date, end_date)

        event_list: list[CalendarEvent] = []

        for moon_phase in obj_moon_phases:
            if (
                end_date is not None
                and start_date.date() <= moon_phase["date"] <= end_date.date()
            ):
                event = CalendarEvent(
                    summary=moon_phase["phase"],
                    start=moon_phase["date"],
                    end=moon_phase["end"],
                )
                event_list.append(event)

        return event_list
