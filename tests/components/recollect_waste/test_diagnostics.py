"""Test ReCollect Waste diagnostics."""
from spencerassistant.components.diagnostics import REDACTED

from tests.components.diagnostics import get_diagnostics_for_config_entry


async def test_entry_diagnostics(
    hass, config_entry, hass_client, setup_recollect_waste
):
    """Test config entry diagnostics."""
    assert await get_diagnostics_for_config_entry(hass, hass_client, config_entry) == {
        "entry": {
            "entry_id": config_entry.entry_id,
            "version": 2,
            "domain": "recollect_waste",
            "title": REDACTED,
            "data": {"place_id": REDACTED, "service_id": "12345"},
            "options": {},
            "pref_disable_new_entities": False,
            "pref_disable_polling": False,
            "source": "user",
            "unique_id": REDACTED,
            "disabled_by": None,
        },
        "data": [
            {
                "date": {
                    "__type": "<class 'datetime.date'>",
                    "isoformat": "2022-01-23",
                },
                "pickup_types": [
                    {"name": "garbage", "friendly_name": "Trash Collection"}
                ],
                "area_name": REDACTED,
            }
        ],
    }
