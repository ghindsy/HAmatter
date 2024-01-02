"""Helpers used for Met Office integration."""
from __future__ import annotations

import logging
import sys

from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util.dt import utcnow

from .const import MODE_3HOURLY
from .data import MetOfficeData

if sys.version_info < (3, 12):
    import datapoint
    from datapoint.Site import Site


_LOGGER = logging.getLogger(__name__)


def fetch_site(
    connection: datapoint.Manager, latitude: float, longitude: float
) -> Site | None:
    """Fetch site information from Datapoint API."""
    try:
        return connection.get_nearest_forecast_site(
            latitude=latitude, longitude=longitude
        )
    except datapoint.exceptions.APIException as err:
        _LOGGER.error("Received error from Met Office Datapoint: %s", err)
        return None


def fetch_data(connection: datapoint.Manager, site: Site, mode: str) -> MetOfficeData:
    """Fetch weather and forecast from Datapoint API."""

    if mode == MODE_3HOURLY:
        datapoint_mode = "3hourly"
    else:
        datapoint_mode = "daily"

    try:
        forecast = connection.get_forecast_for_site(site.id, datapoint_mode)
    except (ValueError, datapoint.exceptions.APIException) as err:
        _LOGGER.error("Check Met Office connection: %s", err.args)
        raise UpdateFailed from err

    time_now = utcnow()
    return MetOfficeData(
        now=forecast.now(),
        forecast=[
            timestep
            for day in forecast.days
            for timestep in day.timesteps
            if timestep.date > time_now
        ],
        site=site,
    )
