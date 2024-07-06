"""Roborock storage."""

import dataclasses
import logging
import os

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .models import RoborockMapInfo

STORAGE_VERSION = 1
_LOGGER = logging.getLogger(__name__)
MAP_PATH = f"{DOMAIN}/maps"
MAP_UPDATE_FREQUENCY = 3600  # Only save the map once every hour.


@dataclasses.dataclass
class RoborockMapEntry:
    """Describe a map entry stored on disk."""

    map_name: str
    time: float


class RoborockStorage:
    """Store Roborock data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
    ) -> None:
        """Initialize RoborockStorage."""
        self._hass = hass
        self._data: dict[str, RoborockMapEntry] = {}
        self._entry_id = entry_id
        # RoborockMapInfo is a type here - but only so that typing accepts it.
        # The store will auto convert it to a dict.
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{self._entry_id}")
        self._map_info: dict[str, dict[int, RoborockMapInfo]] = {}

    def _should_update(self, map_entry: RoborockMapEntry | None) -> bool:
        return (
            map_entry is None
            or dt_util.utcnow().timestamp() - map_entry.time > MAP_UPDATE_FREQUENCY
        )

    def _get_map_filename(self, map_name: str) -> str:
        return self._hass.config.path(f"{MAP_PATH}/{self._entry_id}/{map_name}")

    def exec_load_maps(self, map_names: list[str]) -> list[bytes | None]:
        """Load map content. Should be called in executor thread."""
        filenames: list[tuple[str, str]] = [
            (map_name, self._get_map_filename(map_name)) for map_name in map_names
        ]

        results: list[bytes | None] = []
        for map_name, filename in filenames:
            try:
                if not os.path.exists(filename):
                    map_data = None
                else:
                    _LOGGER.debug("Reading map from disk store: %s", filename)
                    with open(filename, "rb") as stored_map:
                        map_data = stored_map.read()
            except OSError as err:
                _LOGGER.error("Unable to read map file: %s %s", filename, err)
                results.append(None)
                continue
            if map_data is None:
                results.append(None)
                continue
            self._data[map_name] = RoborockMapEntry(
                map_name,
                dt_util.utcnow().timestamp(),
            )
            results.append(map_data)
        return results

    def _save_map(self, filename: str, content: bytes) -> None:
        """Help other functions save the map. Should not be called separately."""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        _LOGGER.debug("Saving event map to disk store: %s", filename)
        with open(filename, "wb") as stored_map:
            stored_map.write(content)

    async def async_save_map(self, map_name: str, content: bytes) -> None:
        """Write map if it should be updated."""
        await self.async_save_maps([(map_name, content)])

    async def async_save_maps(self, maps: list[tuple[str, bytes]]) -> None:
        """Write maps - update regardless. Should be called as background task."""

        def save_maps(maps: list[tuple[str, bytes]]) -> None:
            for map_name, content in maps:
                map_entry = self._data.get(map_name)
                filename = self._get_map_filename(map_name)
                self._data[map_name] = RoborockMapEntry(
                    map_name, dt_util.utcnow().timestamp()
                )
                try:
                    self._save_map(filename, content)
                except OSError as err:
                    _LOGGER.error("Unable to write map file: %s %s", filename, err)
                    # We don't want the _data dict to be updated with incorrect information.
                    if map_entry is not None:
                        self._data[map_name] = map_entry

        await self._hass.async_add_executor_job(save_maps, maps)

    async def async_remove_maps(self) -> None:
        """Remove all maps associated with a config entry."""

        def remove_maps() -> None:
            directory = self._hass.config.path(f"{MAP_PATH}/{self._entry_id}")
            try:
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    _LOGGER.debug("Removing map from disk store: %s", file_path)
                    os.remove(file_path)
            except OSError as err:
                _LOGGER.error(
                    "Unable to remove map files for: %s %s", self._entry_id, err
                )

        await self._hass.async_add_executor_job(remove_maps)

    async def async_save_map_info(
        self, coord_duid: str, map_info: dict[int, RoborockMapInfo]
    ) -> None:
        """Save the coordinator map info."""
        self._map_info[coord_duid] = map_info
        await self._store.async_save(self._map_info)

    async def async_load_map_info(self, coord_duid: str) -> dict[int, RoborockMapInfo]:
        """Load a coordinator's map info."""
        map_info: dict[str, dict[str, dict]] | None = await self._store.async_load()
        if map_info is None:
            return {}
        # Oddly enough the storage seems to turn the mapflag key into a str. This
        # breaks logic downstream.
        for stored_coord_duid in map_info:
            self._map_info[stored_coord_duid] = {
                int(key): RoborockMapInfo(**value)
                for key, value in map_info[stored_coord_duid].items()
            }
        return self._map_info.get(coord_duid, {})

    async def async_remove_map_info(self) -> None:
        """Remove map info from the store."""
        await self._store.async_remove()
