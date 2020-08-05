"""Zone based timeout handling."""
from __future__ import annotations

import asyncio
import enum
import logging
from types import TracebackType
from typing import Any, Dict, List, Optional, Type, Union

from homeassistant.exceptions import HomeAssistantError

ZONE_GLOBAL = "global"

_LOGGER = logging.getLogger(__name__)


class _State(str, enum.Enum):
    """States of a Zone."""

    INIT = "INIT"
    ACTIVE = "ACTIVE"
    TIMEOUT = "TIMEOUT"
    EXIT = "EXIT"


class _FreezeGlobal:
    """Internal Freeze Context Manager object for Global."""

    def __init__(self, manager: ZoneTimeout, loop: asyncio.AbstractEventLoop) -> None:
        """Initialize internal timeout context manager."""
        self._loop: asyncio.AbstractEventLoop = loop
        self._manager: ZoneTimeout = manager

    async def __aenter__(self) -> _FreezeGlobal:
        self._enter()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> Optional[bool]:
        self._exit()
        return None

    def __enter__(self) -> _FreezeGlobal:
        self._loop.call_soon_threadsafe(self._enter)
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> Optional[bool]:
        self._loop.call_soon_threadsafe(self._exit)
        return True

    def _enter(self) -> None:
        """Run freeze."""
        if not self._manager.freezes_done:
            return

        # Global reset
        for task in self._manager.global_tasks:
            task.pause()

        # Zones reset
        for zone in self._manager.zones.values():
            if not zone.freezes_done:
                continue
            zone.pause()

        self._manager.global_freezes.append(self)

    def _exit(self) -> None:
        """Finish freeze."""
        self._manager.global_freezes.remove(self)
        if not self._manager.freezes_done:
            return

        # Global reset
        for task in self._manager.global_tasks:
            task.reset()

        # Zones reset
        for zone in self._manager.zones.values():
            if not zone.freezes_done:
                continue
            zone.reset()


class _FreezeZone:
    """Internal Freeze Context Manager object for Zone."""

    def __init__(self, zone: _Zone, loop: asyncio.AbstractEventLoop) -> None:
        """Initialize internal timeout context manager."""
        self._loop: asyncio.AbstractEventLoop = loop
        self._zone: _Zone = zone

    async def __aenter__(self) -> _FreezeZone:
        self._enter()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> Optional[bool]:
        self._exit()
        return None

    def __enter__(self) -> _FreezeZone:
        self._loop.call_soon_threadsafe(self._enter)
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> Optional[bool]:
        self._loop.call_soon_threadsafe(self._exit)
        return True

    def _enter(self) -> None:
        """Run freeze."""
        if self._zone.freezes_done:
            self._zone.pause()
        self._zone.enter_freeze(self)

    def _exit(self) -> None:
        """Finish freeze."""
        self._zone.exit_freeze(self)
        if not self._zone.freezes_done:
            return
        self._zone.reset()


class _TaskGlobal:
    """Internal Timeout Context Manager object for ALL Zones."""

    def __init__(
        self,
        manager: ZoneTimeout,
        task: asyncio.Task[Any],
        timeout: float,
        cool_down: float,
    ) -> None:
        """Initialize internal timeout context manager."""
        self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._manager: ZoneTimeout = manager
        self._task: asyncio.Task[Any] = task
        self._timeout: float = timeout
        self._time: Optional[float] = None
        self._timeout_handler: Optional[asyncio.Handle] = None
        self._wait_zone: asyncio.Event = asyncio.Event()
        self._state: _State = _State.INIT
        self._cool_down: float = cool_down

    async def __aenter__(self) -> _TaskGlobal:
        self._manager.global_tasks.append(self)
        self._start_timer()
        self._state = _State.ACTIVE
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> Optional[bool]:
        self._stop_timer()
        self._manager.global_tasks.remove(self)

        # Timeout on exit
        if exc_type is asyncio.CancelledError and self.state == _State.TIMEOUT:
            raise asyncio.TimeoutError

        self._state = _State.EXIT
        self._wait_zone.set()
        return None

    @property
    def state(self) -> _State:
        """Return state of the Global task."""
        return self._state

    def zones_done_signal(self) -> None:
        """Signal that all zones are done."""
        self._wait_zone.set()

    def _start_timer(self) -> None:
        """Start timeout handler."""
        if self._timeout_handler:
            return

        self._time = self._loop.time() + self._timeout
        self._timeout_handler = self._loop.call_at(self._time, self._on_timeout)

    def _stop_timer(self) -> None:
        """Stop zone timer."""
        if self._timeout_handler is None:
            return

        self._timeout_handler.cancel()
        self._timeout_handler = None
        # Calculate new timeout
        assert self._time
        self._timeout = self._time - self._loop.time()

    def _on_timeout(self) -> None:
        """Process timeout."""
        self._state = _State.TIMEOUT
        self._timeout_handler = None

        # Reset timer if zones are running
        if not self._manager.zones_done:
            asyncio.create_task(self._on_wait())
        else:
            self._cancel_task()

    def _cancel_task(self) -> None:
        """Cancel own task."""
        if self._task.done():
            return
        self._task.cancel()

    def pause(self) -> None:
        """Pause timers while it freeze."""
        self._stop_timer()

    def reset(self) -> None:
        """Reset timer after freeze."""
        self._start_timer()

    async def _on_wait(self) -> None:
        """Wait until zones are done."""
        await self._wait_zone.wait()
        await asyncio.sleep(self._cool_down)  # Allow context switch
        if not self.state == _State.TIMEOUT:
            return
        self._cancel_task()


class _TaskZone:
    """Internal Timeout Context Manager object for Task."""

    def __init__(self, zone: _Zone, task: asyncio.Task[Any], timeout: float) -> None:
        """Initialize internal timeout context manager."""
        self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._zone: _Zone = zone
        self._task: asyncio.Task[Any] = task
        self._state: _State = _State.INIT
        self._timeout: float = timeout
        self._time: Optional[float] = None
        self._timeout_handler: Optional[asyncio.Handle] = None

    @property
    def state(self) -> _State:
        """Return state of the Zone task."""
        return self._state

    async def __aenter__(self) -> _TaskZone:
        self._zone.enter_task(self)
        self._state = _State.ACTIVE

        # Zone is on freeze
        if self._zone.freezes_done:
            self._start_timer()

        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> Optional[bool]:
        self._zone.exit_task(self)
        self._stop_timer()

        # Timeout on exit
        if exc_type is asyncio.CancelledError and self.state == _State.TIMEOUT:
            raise asyncio.TimeoutError

        self._state = _State.EXIT
        return None

    def _start_timer(self) -> None:
        """Start timeout handler."""
        if self._timeout_handler:
            return

        self._time = self._loop.time() + self._timeout
        self._timeout_handler = self._loop.call_at(self._time, self._on_timeout)

    def _stop_timer(self) -> None:
        """Stop zone timer."""
        if self._timeout_handler is None:
            return

        self._timeout_handler.cancel()
        self._timeout_handler = None
        # Calculate new timeout
        assert self._time
        self._timeout = self._time - self._loop.time()

    def _on_timeout(self) -> None:
        """Process timeout."""
        self._state = _State.TIMEOUT
        self._timeout_handler = None

        # Timeout
        if self._task.done():
            return
        self._task.cancel()

    def pause(self) -> None:
        """Pause timers while it freeze."""
        self._stop_timer()

    def reset(self) -> None:
        """Reset timer after freeze."""
        self._start_timer()


class _Zone:
    """Internal Zone Timeout Manager."""

    def __init__(
        self, manager: ZoneTimeout, zone: str, loop: asyncio.AbstractEventLoop
    ) -> None:
        """Initialize internal timeout context manager."""
        self._loop: asyncio.AbstractEventLoop = loop
        self._manager: ZoneTimeout = manager
        self._zone: str = zone
        self._tasks: List[_TaskZone] = []
        self._freezes: List[_FreezeZone] = []

    @property
    def name(self) -> str:
        """Return Zone name."""
        return self._zone

    @property
    def active(self) -> bool:
        """Return True if zone is active."""
        return self._tasks or self._freezes

    @property
    def freezes_done(self) -> bool:
        """Return True if all freeze are done."""
        return len(self._freezes) == 0 and self._manager.freezes_done

    def enter_task(self, task: _TaskZone) -> None:
        """Start into new Task."""
        self._tasks.append(task)

    def exit_task(self, task: _TaskZone) -> None:
        """Exit a running Task."""
        self._tasks.remove(task)

        # On latest listener
        if not self.active:
            self._manager.drop_zone(self.name)

    def enter_freeze(self, freeze: _FreezeZone) -> None:
        """Start into new freeze."""
        self._freezes.append(freeze)

    def exit_freeze(self, freeze: _FreezeZone) -> None:
        """Exit a running Freeze."""
        self._freezes.remove(freeze)

        # On latest listener
        if not self.active:
            self._manager.drop_zone(self.name)

    def pause(self) -> None:
        """Stop timers while it freeze."""
        if not self.active:
            return

        # Forward pause
        for task in self._tasks:
            task.pause()

    def reset(self) -> None:
        """Reset timer after freeze."""
        if not self.active:
            return

        # Forward reset
        for task in self._tasks:
            task.reset()


class ZoneTimeout:
    """Async zone based timeout handler."""

    def __init__(self) -> None:
        """Initialize ZoneTimeout handler."""
        self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._zones: Dict[str, _Zone] = {}
        self._globals: List[_TaskGlobal] = []
        self._freezes: List[_FreezeGlobal] = []

    @property
    def zones_done(self) -> bool:
        """Return True if all zones are finish."""
        return not bool(self._zones)

    @property
    def freezes_done(self) -> bool:
        """Return True if all freezes are finish."""
        return not self._freezes

    @property
    def zones(self) -> Dict[str, _Zone]:
        """Return all Zones."""
        return self._zones

    @property
    def global_tasks(self) -> List[_TaskGlobal]:
        """Return all global Tasks."""
        return self._globals

    @property
    def global_freezes(self) -> List[_FreezeGlobal]:
        """Return all global Freezes."""
        return self._freezes

    def drop_zone(self, zone_name: str) -> None:
        """Drop a zone out of scope."""
        self._zones.pop(zone_name, None)
        if self._zones:
            return

        # Signal Global task, all zones are done
        for task in self._globals:
            task.zones_done_signal()

    def async_timeout(
        self, timeout: float, zone_name: str = ZONE_GLOBAL, cool_down: float = 0
    ) -> Union[_TaskZone, _TaskGlobal]:
        """Timeout based on a zone.

        For using as Async Context Manager.
        """
        current_task: Optional[asyncio.Task[Any]] = asyncio.current_task()
        assert current_task

        # Global Zone
        if zone_name == ZONE_GLOBAL:
            task = _TaskGlobal(self, current_task, timeout, cool_down)
            return task

        # Zone Handling
        if zone_name in self.zones:
            zone: _Zone = self.zones[zone_name]
        else:
            self.zones[zone_name] = zone = _Zone(self, zone_name, self._loop)

        # Create Task
        return _TaskZone(zone, current_task, timeout)

    def freeze(self, zone_name: str = ZONE_GLOBAL) -> Union[_FreezeZone, _FreezeGlobal]:
        """Freeze all timer until job is done.

        For using as (Async) Context Manager.
        """
        # Global Freeze
        if zone_name == ZONE_GLOBAL:
            return _FreezeGlobal(self, self._loop)

        # Zone Freeze
        if zone_name in self.zones:
            zone: _Zone = self.zones[zone_name]
        else:
            self.zones[zone_name] = zone = _Zone(self, zone_name, self._loop)

        return _FreezeZone(zone, self._loop)
