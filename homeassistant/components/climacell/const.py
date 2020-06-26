"""Constants for the ClimaCell integration."""
CONF_FORECAST_TYPE = "forecast_type"
CONF_AQI_COUNTRY = "aqi_country"
CONF_TIMESTEP = "timestep"

DISABLE_FORECASTS = "disable"
DAILY = "daily"
HOURLY = "hourly"
NOWCAST = "nowcast"
USA = "usa"
CHINA = "china"

CURRENT = "current"
FORECASTS = "forecasts"

DEFAULT_NAME = "ClimaCell"
DEFAULT_TIMESTEP = 15
DEFAULT_FORECAST_TYPE = DAILY
DEFAULT_AQI_COUNTRY = USA
DOMAIN = "climacell"
ATTRIBUTION = "Powered by ClimaCell"

MAX_REQUESTS_PER_DAY = 1000

AQI_FIELD_LOOKUP = {USA: "epa_aqi", CHINA: "china_aqi"}

DIRECTIONS_LIST = [
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
]

WIND_DIRECTIONS = {name: idx * 360 / 16 for idx, name in enumerate(DIRECTIONS_LIST)}

CONDITIONS = {
    "freezing_rain_heavy": "snowy-rainy",
    "freezing_rain": "snowy-rainy",
    "freezing_rain_light": "snowy-rainy",
    "freezing_drizzle": "snowy-rainy",
    "ice_pellets_heavy": "hail",
    "ice_pellets": "hail",
    "ice_pellets_light": "hail",
    "snow_heavy": "snowy",
    "snow": "snowy",
    "snow_light": "snowy",
    "flurries": "snowy",
    "tstorm": "lightning",
    "rain_heavy": "pouring",
    "rain": "rainy",
    "rain_light": "rainy",
    "drizzle": "rainy",
    "fog_light": "fog",
    "fog": "fog",
    "cloudy": "cloudy",
    "mostly_cloudy": "cloudy",
    "partly_cloudy": "partlycloudy",
}

CLEAR_CONDITIONS = {"night": "clear-night", "day": "sunny"}
