"""Constants for the ClimaCell integration."""
from pyclimacell.const import DAILY, HOURLY, NOWCAST, WeatherCode

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
)

CONF_TIMESTEP = "timestep"
FORECAST_TYPES = [DAILY, HOURLY, NOWCAST]

DEFAULT_NAME = "ClimaCell"
DEFAULT_TIMESTEP = 15
DEFAULT_FORECAST_TYPE = DAILY
DOMAIN = "climacell"
ATTRIBUTION = "Powered by ClimaCell"

MAX_REQUESTS_PER_DAY = 1000

CLEAR_CONDITIONS = {"night": ATTR_CONDITION_CLEAR_NIGHT, "day": ATTR_CONDITION_SUNNY}

MAX_FORECASTS = {
    DAILY: 14,
    HOURLY: 24,
    NOWCAST: 30,
}

# V4 constants
CONDITIONS = {
    WeatherCode.WIND: ATTR_CONDITION_WINDY,
    WeatherCode.LIGHT_WIND: ATTR_CONDITION_WINDY,
    WeatherCode.STRONG_WIND: ATTR_CONDITION_WINDY,
    WeatherCode.FREEZING_RAIN: ATTR_CONDITION_SNOWY_RAINY,
    WeatherCode.HEAVY_FREEZING_RAIN: ATTR_CONDITION_SNOWY_RAINY,
    WeatherCode.LIGHT_FREEZING_RAIN: ATTR_CONDITION_SNOWY_RAINY,
    WeatherCode.FREEZING_DRIZZLE: ATTR_CONDITION_SNOWY_RAINY,
    WeatherCode.ICE_PELLETS: ATTR_CONDITION_HAIL,
    WeatherCode.HEAVY_ICE_PELLETS: ATTR_CONDITION_HAIL,
    WeatherCode.LIGHT_ICE_PELLETS: ATTR_CONDITION_HAIL,
    WeatherCode.SNOW: ATTR_CONDITION_SNOWY,
    WeatherCode.HEAVY_SNOW: ATTR_CONDITION_SNOWY,
    WeatherCode.LIGHT_SNOW: ATTR_CONDITION_SNOWY,
    WeatherCode.FLURRIES: ATTR_CONDITION_SNOWY,
    WeatherCode.THUNDERSTORM: ATTR_CONDITION_LIGHTNING,
    WeatherCode.RAIN: ATTR_CONDITION_POURING,
    WeatherCode.HEAVY_RAIN: ATTR_CONDITION_RAINY,
    WeatherCode.LIGHT_RAIN: ATTR_CONDITION_RAINY,
    WeatherCode.DRIZZLE: ATTR_CONDITION_RAINY,
    WeatherCode.FOG: ATTR_CONDITION_FOG,
    WeatherCode.LIGHT_FOG: ATTR_CONDITION_FOG,
    WeatherCode.CLOUDY: ATTR_CONDITION_CLOUDY,
    WeatherCode.MOSTLY_CLOUDY: ATTR_CONDITION_CLOUDY,
    WeatherCode.PARTLY_CLOUDY: ATTR_CONDITION_PARTLYCLOUDY,
}

CC_ATTR_TIMESTAMP = "startTime"
CC_ATTR_TEMPERATURE = "temperature"
CC_ATTR_TEMPERATURE_HIGH = "temperatureMax"
CC_ATTR_TEMPERATURE_LOW = "temperatureMin"
CC_ATTR_PRESSURE = "pressureSeaLevel"
CC_ATTR_HUMIDITY = "humidity"
CC_ATTR_WIND_SPEED = "windSpeed"
CC_ATTR_WIND_DIRECTION = "windDirection"
CC_ATTR_OZONE = "pollutantO3"
CC_ATTR_CONDITION = "weatherCode"
CC_ATTR_VISIBILITY = "visibility"
CC_ATTR_PRECIPITATION = "precipitationIntensityAvg"
CC_ATTR_PRECIPITATION_PROBABILITY = "precipitationProbability"

# V3 constants
CONDITIONS_V3 = {
    "breezy": ATTR_CONDITION_WINDY,
    "freezing_rain_heavy": ATTR_CONDITION_SNOWY_RAINY,
    "freezing_rain": ATTR_CONDITION_SNOWY_RAINY,
    "freezing_rain_light": ATTR_CONDITION_SNOWY_RAINY,
    "freezing_drizzle": ATTR_CONDITION_SNOWY_RAINY,
    "ice_pellets_heavy": ATTR_CONDITION_HAIL,
    "ice_pellets": ATTR_CONDITION_HAIL,
    "ice_pellets_light": ATTR_CONDITION_HAIL,
    "snow_heavy": ATTR_CONDITION_SNOWY,
    "snow": ATTR_CONDITION_SNOWY,
    "snow_light": ATTR_CONDITION_SNOWY,
    "flurries": ATTR_CONDITION_SNOWY,
    "tstorm": ATTR_CONDITION_LIGHTNING,
    "rain_heavy": ATTR_CONDITION_POURING,
    "rain": ATTR_CONDITION_RAINY,
    "rain_light": ATTR_CONDITION_RAINY,
    "drizzle": ATTR_CONDITION_RAINY,
    "fog_light": ATTR_CONDITION_FOG,
    "fog": ATTR_CONDITION_FOG,
    "cloudy": ATTR_CONDITION_CLOUDY,
    "mostly_cloudy": ATTR_CONDITION_CLOUDY,
    "partly_cloudy": ATTR_CONDITION_PARTLYCLOUDY,
}

CC_V3_ATTR_TIMESTAMP = "observation_time"
CC_V3_ATTR_TEMPERATURE = "temp"
CC_V3_ATTR_TEMPERATURE_HIGH = "max"
CC_V3_ATTR_TEMPERATURE_LOW = "min"
CC_V3_ATTR_PRESSURE = "baro_pressure"
CC_V3_ATTR_HUMIDITY = "humidity"
CC_V3_ATTR_WIND_SPEED = "wind_speed"
CC_V3_ATTR_WIND_DIRECTION = "wind_direction"
CC_V3_ATTR_OZONE = "o3"
CC_V3_ATTR_CONDITION = "weather_code"
CC_V3_ATTR_VISIBILITY = "visibility"
CC_V3_ATTR_PRECIPITATION = "precipitation"
CC_V3_ATTR_PRECIPITATION_DAILY = "precipitation_accumulation"
CC_V3_ATTR_PRECIPITATION_PROBABILITY = "precipitation_probability"
