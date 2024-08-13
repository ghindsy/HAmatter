"""Creates a calendar entity for the mower."""

from datetime import datetime
import logging

from aioautomower.model import AutomowerCalendarEvent
from ical.calendar import Calendar
from ical.event import Event
from ical.types.recur import Recur

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AutomowerConfigEntry
from .coordinator import AutomowerDataUpdateCoordinator
from .entity import AutomowerBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutomowerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up lawn mower platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        AutomowerCalendarEntity(mower_id, coordinator) for mower_id in coordinator.data
    )


class AutomowerCalendarEntity(AutomowerBaseEntity, CalendarEntity):
    """Representation of the Automower Calendar element."""

    _attr_name: str | None = None

    def __init__(
        self,
        mower_id: str,
        coordinator: AutomowerDataUpdateCoordinator,
    ) -> None:
        """Set up AutomowerCalendarEntity."""
        super().__init__(mower_id, coordinator)
        self._attr_unique_id = mower_id
        self.calendar = Calendar()

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event."""
        self._automower_to_ical_event(self.mower_attributes.calendar.events)
        return _ical_to_calendar_event(self.calendar.events[0])

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range.

        This is only called when opening the calendar in the UI.
        """
        self.calendar = await hass.async_add_executor_job(Calendar)
        self._automower_to_ical_event(self.mower_attributes.calendar.events)
        events = self.calendar.timeline_tz(start_date.tzinfo).overlapping(
            start_date,
            end_date,
        )
        return [_ical_to_calendar_event(event) for event in events]

    def _automower_to_ical_event(
        self, event_list: list[AutomowerCalendarEvent]
    ) -> None:
        """Convert the automower event to an ical event an store it."""
        schedule_no: dict = {}
        for event in event_list:
            if event.work_area_id is not None:
                schedule_no[event.work_area_id] = 0
            if event.work_area_id is None:
                schedule_no["-1"] = 0
        for event in self.mower_attributes.calendar.events:
            wa_name = ""
            if event.work_area_id is not None:
                if self.mower_attributes.work_areas is not None:
                    _work_areas = self.mower_attributes.work_areas
                    wa_name = f"{_work_areas[event.work_area_id].name} "
                    schedule_no[event.work_area_id] = (
                        schedule_no[event.work_area_id] + 1
                    )
                    number = schedule_no[event.work_area_id]
            if event.work_area_id is None:
                schedule_no["-1"] = schedule_no["-1"] + 1
                number = schedule_no["-1"]
            self.calendar.events.append(
                Event(
                    dtstart=event.start,
                    dtend=event.end,
                    rrule=Recur.from_rrule(event.rrule),
                    summary=f"{wa_name}Schedule {number}",
                    uid=event.uid,
                )
            )


def _ical_to_calendar_event(event: Event) -> CalendarEvent:
    """Return a CalendarEvent from an ical event."""

    return CalendarEvent(
        summary=event.summary,
        start=event.start,
        end=event.end,
        description=event.description,
        uid=event.uid,
        rrule=event.rrule.as_rrule_str() if event.rrule else None,
    )
