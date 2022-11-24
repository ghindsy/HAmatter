"""Tests for instance ID helper."""
from unittest.mock import patch

from spencerassistant.helpers import instance_id


async def test_get_id_empty(hass, hass_storage):
    """Get unique ID."""
    uuid = await instance_id.async_get(hass)
    assert uuid is not None
    # Assert it's stored
    assert hass_storage["core.uuid"]["data"]["uuid"] == uuid


async def test_get_id_migrate(hass, hass_storage):
    """Migrate existing file."""
    with patch(
        "spencerassistant.util.json.load_json", return_value={"uuid": "1234"}
    ), patch("os.path.isfile", return_value=True), patch("os.remove") as mock_remove:
        uuid = await instance_id.async_get(hass)

    assert uuid == "1234"

    # Assert it's stored
    assert hass_storage["core.uuid"]["data"]["uuid"] == uuid

    # assert old deleted
    assert len(mock_remove.mock_calls) == 1
