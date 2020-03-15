"""Support for AirVisual air quality sensors."""
from logging import getLogger

from homeassistant.components.air_quality import AirQualityEntity
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_STATE,
    ATTR_TEMPERATURE,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_SHOW_ON_MAP,
    CONF_STATE,
    PRECISION_TENTHS,
    TEMP_CELSIUS,
)
from homeassistant.helpers.temperature import display_temp

from . import AirVisualEntity
from .const import (
    CONF_CITY,
    CONF_COUNTRY,
    DATA_CLIENT,
    DOMAIN,
    INTEGRATION_TYPE_GEOGRAPHY,
)

_LOGGER = getLogger(__name__)

ATTR_CITY = "city"
ATTR_COUNTRY = "country"
ATTR_HUMIDITY = "humidity"
ATTR_POLLUTANT_SYMBOL = "pollutant_symbol"
ATTR_POLLUTANT_UNIT = "pollutant_unit"
ATTR_REGION = "region"
ATTR_SENSOR_LIFE = "sensor_life_{0}"
ATTR_VOC = "voc"

MASS_PARTS_PER_MILLION = "ppm"
MASS_PARTS_PER_BILLION = "ppb"
VOLUME_MICROGRAMS_PER_CUBIC_METER = "µg/m3"

GEOGRAPHY_SENSOR_KIND_LEVEL = "air_pollution_level"
GEOGRAPHY_SENSOR_KIND_AQI = "air_quality_index"
GEOGRAPHY_SENSOR_KIND_POLLUTANT = "main_pollutant"
GEOGRAPHY_SENSORS = [
    (GEOGRAPHY_SENSOR_KIND_LEVEL, "Air Pollution Level", "mdi:gauge", None),
    (GEOGRAPHY_SENSOR_KIND_AQI, "Air Quality Index", "mdi:chart-line", "AQI"),
    (GEOGRAPHY_SENSOR_KIND_POLLUTANT, "Main Pollutant", "mdi:chemical-weapon", None),
]
GEOGRAPHY_SENSOR_LOCALES = {"cn": "Chinese", "us": "U.S."}

POLLUTANT_LEVEL_MAPPING = [
    {"label": "Good", "icon": "mdi:emoticon-excited", "minimum": 0, "maximum": 50},
    {"label": "Moderate", "icon": "mdi:emoticon-happy", "minimum": 51, "maximum": 100},
    {
        "label": "Unhealthy for sensitive groups",
        "icon": "mdi:emoticon-neutral",
        "minimum": 101,
        "maximum": 150,
    },
    {"label": "Unhealthy", "icon": "mdi:emoticon-sad", "minimum": 151, "maximum": 200},
    {
        "label": "Very Unhealthy",
        "icon": "mdi:emoticon-dead",
        "minimum": 201,
        "maximum": 300,
    },
    {"label": "Hazardous", "icon": "mdi:biohazard", "minimum": 301, "maximum": 10000},
]

POLLUTANT_MAPPING = {
    "co": {"label": "Carbon Monoxide", "unit": CONCENTRATION_PARTS_PER_MILLION},
    "n2": {"label": "Nitrogen Dioxide", "unit": CONCENTRATION_PARTS_PER_BILLION},
    "o3": {"label": "Ozone", "unit": CONCENTRATION_PARTS_PER_BILLION},
    "p1": {"label": "PM10", "unit": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER},
    "p2": {"label": "PM2.5", "unit": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER},
    "s2": {"label": "Sulfur Dioxide", "unit": CONCENTRATION_PARTS_PER_BILLION},
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up AirVisual sensors based on a config entry."""
    airvisual = hass.data[DOMAIN][DATA_CLIENT][config_entry.entry_id]

    if airvisual.integration_type == INTEGRATION_TYPE_GEOGRAPHY:
        entities = [
            AirVisualGeographySensor(
                airvisual, config_entry, kind, name, icon, unit, locale, geography_id
            )
            for geography_id in airvisual.data
            for locale in GEOGRAPHY_SENSOR_LOCALES
            for kind, name, icon, unit in GEOGRAPHY_SENSORS
        ]
    else:
        entities = [AirVisualNodeProSensor(airvisual)]

    async_add_entities(entities, True)


class AirVisualGeographySensor(AirVisualEntity):
    """Define an AirVisual sensor for a geographical location."""

    def __init__(
        self, airvisual, config_entry, kind, name, icon, unit, locale, geography_id
    ):
        """Initialize."""
        super().__init__(airvisual)

        self._attrs.update(
            {
                ATTR_CITY: airvisual.data[geography_id].get(CONF_CITY),
                ATTR_STATE: airvisual.data[geography_id].get(CONF_STATE),
                ATTR_COUNTRY: airvisual.data[geography_id].get(CONF_COUNTRY),
            }
        )
        self._geography_id = geography_id
        self._icon = icon
        self._kind = kind
        self._locale = locale
        self._name = name
        self._state = None
        self._unit = unit

    @property
    def available(self):
        """Return True if entity is available."""
        try:
            return bool(
                self._airvisual.data[self._geography_id]["current"]["pollution"]
            )
        except KeyError:
            return False

    @property
    def name(self):
        """Return the name."""
        return f"{GEOGRAPHY_SENSOR_LOCALES[self._locale]} {self._name}"

    @property
    def state(self):
        """Return the state."""
        return self._state

    @property
    def unique_id(self):
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._geography_id}_{self._locale}_{self._kind}"

    async def async_update(self):
        """Update the sensor."""
        try:
            data = self._airvisual.data[self._geography_id]["current"]["pollution"]
        except KeyError:
            return

        if self._kind == GEOGRAPHY_SENSOR_KIND_LEVEL:
            aqi = data[f"aqi{self._locale}"]
            [level] = [
                i
                for i in POLLUTANT_LEVEL_MAPPING
                if i["minimum"] <= aqi <= i["maximum"]
            ]
            self._state = level["label"]
            self._icon = level["icon"]
        elif self._kind == GEOGRAPHY_SENSOR_KIND_AQI:
            self._state = data[f"aqi{self._locale}"]
        elif self._kind == GEOGRAPHY_SENSOR_KIND_POLLUTANT:
            symbol = data[f"main{self._locale}"]
            self._state = POLLUTANT_MAPPING[symbol]["label"]
            self._attrs.update(
                {
                    ATTR_POLLUTANT_SYMBOL: symbol,
                    ATTR_POLLUTANT_UNIT: POLLUTANT_MAPPING[symbol]["unit"],
                }
            )

        if CONF_LATITUDE in self._airvisual.geography_data:
            if self._airvisual.options[CONF_SHOW_ON_MAP]:
                self._attrs[ATTR_LATITUDE] = self._airvisual.geography_data[
                    CONF_LATITUDE
                ]
                self._attrs[ATTR_LONGITUDE] = self._airvisual.geography_data[
                    CONF_LONGITUDE
                ]
                self._attrs.pop("lati", None)
                self._attrs.pop("long", None)
            else:
                self._attrs["lati"] = self._airvisual.geography_data[CONF_LATITUDE]
                self._attrs["long"] = self._airvisual.geography_data[CONF_LONGITUDE]
                self._attrs.pop(ATTR_LATITUDE, None)
                self._attrs.pop(ATTR_LONGITUDE, None)


class AirVisualNodeProSensor(AirVisualEntity, AirQualityEntity):
    """Define a sensor for a AirVisual Node/Pro."""

    def __init__(self, airvisual):
        """Initialize."""
        super().__init__(airvisual)

        self._icon = "mdi:chemical-weapon"
        self._unit = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER

    @property
    def air_quality_index(self):
        """Return the Air Quality Index (AQI)."""
        if self._airvisual.data["settings"]["is_aqi_usa"]:
            return self._airvisual.data["measurements"][0]["pm25_AQIUS"]
        return self._airvisual.data["measurements"][0]["pm25_AQICN"]

    @property
    def available(self):
        """Return True if entity is available."""
        return bool(self._airvisual.data)

    @property
    def carbon_dioxide(self):
        """Return the CO2 (carbon dioxide) level."""
        return self._airvisual.data["measurements"][0].get("co2_ppm")

    @property
    def device_info(self):
        """Return device registry information for this entity."""
        return {
            "identifiers": {(DOMAIN, self._airvisual.data["serial_number"])},
            "name": self._airvisual.data["settings"]["node_name"],
            "manufacturer": "AirVisual",
            "model": f'{self._airvisual.data["status"]["model"]}',
            "sw_version": (
                f'Version {self._airvisual.data["status"]["system_version"]}'
                f'{self._airvisual.data["status"]["app_version"]}'
            ),
        }

    @property
    def name(self):
        """Return the name."""
        return f"{self._airvisual.data['settings']['node_name']} Air Quality"

    @property
    def particulate_matter_2_5(self):
        """Return the particulate matter 2.5 level."""
        return self._airvisual.data["measurements"][0].get("pm25_ugm3")

    @property
    def particulate_matter_10(self):
        """Return the particulate matter 10 level."""
        return self._airvisual.data["measurements"][0].get("pm10_ugm3")

    @property
    def particulate_matter_0_1(self):
        """Return the particulate matter 0.1 level."""
        return self._airvisual.data["measurements"][0].get("pm01_ugm3")

    @property
    def unique_id(self):
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return self._airvisual.data["serial_number"]

    async def async_update(self):
        """Update the Node/Pro's data."""
        sensor_life_attrs = {
            ATTR_SENSOR_LIFE.format(pollutant): lifespan
            for pollutant, lifespan in self._airvisual.data["status"][
                "sensor_life"
            ].items()
        }

        self._attrs.update(
            {
                ATTR_BATTERY_LEVEL: self._airvisual.data["status"]["battery"],
                ATTR_HUMIDITY: self._airvisual.data["measurements"][0].get(
                    "humidity_RH"
                ),
                ATTR_TEMPERATURE: display_temp(
                    self.hass,
                    float(self._airvisual.data["measurements"][0].get("temperature_C")),
                    TEMP_CELSIUS,
                    PRECISION_TENTHS,
                ),
                ATTR_VOC: self._airvisual.data["measurements"][0].get("voc_ppb"),
                **sensor_life_attrs,
            }
        )
