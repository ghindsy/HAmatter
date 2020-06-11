"""Support for monitoring a Smappee energy sensor."""
import logging

from homeassistant.const import ATTR_VOLTAGE, ENERGY_WATT_HOUR, POWER_WATT
from homeassistant.helpers.entity import Entity

from .const import BASE, DOMAIN

_LOGGER = logging.getLogger(__name__)

TREND_SENSORS = {
    "total_power": [
        "Total consumption - Active power",
        "mdi:power-plug",
        POWER_WATT,
        "total_power",
    ],
    "total_reactive_power": [
        "Total consumption - Reactive power",
        "mdi:power-plug",
        POWER_WATT,
        "total_reactive_power",
    ],
    "alwayson": ["Always on - Active power", "mdi:sleep", POWER_WATT, "alwayson"],
    "power_today": [
        "Total consumption - Today",
        "mdi:power-plug",
        ENERGY_WATT_HOUR,
        "power_today",
    ],
    "power_current_hour": [
        "Total consumption - Current hour",
        "mdi:power-plug",
        ENERGY_WATT_HOUR,
        "power_current_hour",
    ],
    "power_last_5_minutes": [
        "Total consumption - Last 5 minutes",
        "mdi:power-plug",
        ENERGY_WATT_HOUR,
        "power_last_5_minutes",
    ],
    "alwayson_today": [
        "Always on - Today",
        "mdi:sleep",
        ENERGY_WATT_HOUR,
        "alwayson_today",
    ],
}
SOLAR_SENSORS = {
    "solar_power": [
        "Total production - Active power",
        "mdi:white-balance-sunny",
        POWER_WATT,
        "solar_power",
    ],
    "solar_today": [
        "Total production - Today",
        "mdi:white-balance-sunny",
        ENERGY_WATT_HOUR,
        "solar_today",
    ],
    "solar_current_hour": [
        "Total production - Current hour",
        "mdi:white-balance-sunny",
        ENERGY_WATT_HOUR,
        "solar_current_hour",
    ],
}
VOLTAGE_SENSORS = {
    "phase_voltages_a": [
        "Phase voltages - A",
        "mdi:flash",
        ATTR_VOLTAGE,
        "phase_voltage_a",
        ["ONE", "TWO", "THREE_STAR", "THREE_DELTA"],
    ],
    "phase_voltages_b": [
        "Phase voltages - B",
        "mdi:flash",
        ATTR_VOLTAGE,
        "phase_voltage_b",
        ["TWO", "THREE_STAR", "THREE_DELTA"],
    ],
    "phase_voltages_c": [
        "Phase voltages - C",
        "mdi:flash",
        ATTR_VOLTAGE,
        "phase_voltage_c",
        ["THREE_STAR"],
    ],
    "line_voltages_a": [
        "Line voltages - A",
        "mdi:flash",
        ATTR_VOLTAGE,
        "line_voltage_a",
        ["ONE", "TWO", "THREE_STAR", "THREE_DELTA"],
    ],
    "line_voltages_b": [
        "Line voltages - B",
        "mdi:flash",
        ATTR_VOLTAGE,
        "line_voltage_b",
        ["TWO", "THREE_STAR", "THREE_DELTA"],
    ],
    "line_voltages_c": [
        "Line voltages - C",
        "mdi:flash",
        ATTR_VOLTAGE,
        "line_voltage_c",
        ["THREE_STAR", "THREE_DELTA"],
    ],
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Smappee sensor."""
    smappee_base = hass.data[DOMAIN][BASE]

    dev = []
    for _, service_location in smappee_base.smappee.service_locations.items():
        # Add all basic sensors (realtime values and aggregators)
        for sensor in TREND_SENSORS:
            dev.append(
                SmappeeSensor(
                    smappee_base=smappee_base,
                    service_location=service_location,
                    sensor=sensor,
                    attributes=TREND_SENSORS[sensor],
                )
            )

        # Add solar sensors
        if service_location.has_solar_production:
            for sensor in SOLAR_SENSORS:
                dev.append(
                    SmappeeSensor(
                        smappee_base=smappee_base,
                        service_location=service_location,
                        sensor=sensor,
                        attributes=SOLAR_SENSORS[sensor],
                    )
                )

        # Add all CT measurements
        for measurement_id, measurement in service_location.measurements.items():
            dev.append(
                SmappeeSensor(
                    smappee_base=smappee_base,
                    service_location=service_location,
                    sensor="load",
                    attributes=[
                        measurement.name,
                        "mdi:power-plug",
                        POWER_WATT,
                        measurement_id,
                    ],
                )
            )

        # Add phase- and line voltages
        for sensor_name, sensor in VOLTAGE_SENSORS.items():
            if service_location.phase_type in sensor[4]:
                dev.append(
                    SmappeeSensor(
                        smappee_base=smappee_base,
                        service_location=service_location,
                        sensor=sensor_name,
                        attributes=sensor,
                    )
                )

        # Add Gas and Water sensors
        for sensor_id, sensor in service_location.sensors.items():
            for channel in sensor.channels:
                dev.append(
                    SmappeeSensor(
                        smappee_base=smappee_base,
                        service_location=service_location,
                        sensor="sensor",
                        attributes=[
                            channel.get("name"),
                            "mdi:water"
                            if channel.get("type") == "water"
                            else "mdi:gas-cylinder",
                            channel.get("uom"),
                            f"{sensor_id}-{channel.get('channel')}",
                        ],
                    )
                )

    async_add_entities(dev, True)


class SmappeeSensor(Entity):
    """Implementation of a Smappee sensor."""

    def __init__(self, smappee_base, service_location, sensor, attributes):
        """Initialize the Smappee sensor."""
        self._smappee_base = smappee_base
        self._service_location = service_location
        self._attributes = attributes
        self._sensor = sensor
        self.data = None
        self._state = None
        self._name = self._attributes[0]
        self._icon = self._attributes[1]
        self._unit_of_measurement = self._attributes[2]
        self._sensor_id = self._attributes[3]

    @property
    def name(self):
        """Return the name for this sensor."""
        if self._sensor in ["sensor", "load"]:
            return (
                f"{self._service_location.service_location_name} - "
                f"{self._sensor.title()} - {self._name}"
            )

        return f"{self._service_location.service_location_name} - {self._name}"

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return self._icon

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def unique_id(self,):
        """Return the unique ID for this sensor."""
        if self._sensor in ["load", "sensor"]:
            return (
                f"{self._service_location.device_serial_number}-"
                f"{self._service_location.service_location_id}-"
                f"{self._sensor}-{self._sensor_id}"
            )

        return (
            f"{self._service_location.device_serial_number}-"
            f"{self._service_location.service_location_id}-"
            f"{self._sensor}"
        )

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attributes = {
            "Service location name": self._service_location.service_location_name,
            "Device serialnumber": self._service_location.device_serial_number,
            "Sensor": self._sensor,
        }
        if self._sensor == "sensor":
            sensor_id, _ = self._sensor_id.split("-")
            sensor = self._service_location.sensors.get(int(sensor_id))
            attributes["Temperature"] = sensor.temperature
            attributes["Humidity"] = sensor.humidity
            attributes["Battery"] = sensor.battery
        return attributes

    @property
    def device_info(self):
        """Return the device info for this sensor."""
        return {
            "identifiers": {(DOMAIN, self._service_location.device_serial_number)},
            "name": self._service_location.service_location_name,
            "manufacturer": "Smappee",
            "model": self._service_location.device_model,
            "sw_version": self._service_location.firmware_version,
        }

    async def async_update(self):
        """Get the latest data from Smappee and update the state."""
        await self._smappee_base.async_update()

        if self._sensor == "total_power":
            self._state = self._service_location.total_power
        elif self._sensor == "total_reactive_power":
            self._state = self._service_location.total_reactive_power
        elif self._sensor == "solar_power":
            self._state = self._service_location.solar_power
        elif self._sensor == "alwayson":
            self._state = self._service_location.alwayson
        elif self._sensor in [
            "phase_voltages_a",
            "phase_voltages_b",
            "phase_voltages_c",
        ]:
            phase_voltages = self._service_location.phase_voltages
            if phase_voltages is not None:
                if self._sensor == "phase_voltages_a":
                    self._state = phase_voltages[0]
                elif self._sensor == "phase_voltages_b":
                    self._state = phase_voltages[1]
                elif self._sensor == "phase_voltages_c":
                    self._state = phase_voltages[2]
        elif self._sensor in ["line_voltages_a", "line_voltages_b", "line_voltages_c"]:
            line_voltages = self._service_location.line_voltages
            if line_voltages is not None:
                if self._sensor == "line_voltages_a":
                    self._state = line_voltages[0]
                elif self._sensor == "line_voltages_b":
                    self._state = line_voltages[1]
                elif self._sensor == "line_voltages_c":
                    self._state = line_voltages[2]
        elif self._sensor in [
            "power_today",
            "power_current_hour",
            "power_last_5_minutes",
            "solar_today",
            "solar_current_hour",
            "alwayson_today",
        ]:
            trend_value = self._service_location.aggregated_values.get(self._sensor)
            self._state = round(trend_value) if trend_value is not None else None
        elif self._sensor == "load":
            self._state = self._service_location.measurements.get(
                self._sensor_id
            ).active_total
        elif self._sensor == "sensor":
            sensor_id, channel_id = self._sensor_id.split("-")
            sensor = self._service_location.sensors.get(int(sensor_id))
            for channel in sensor.channels:
                if channel.get("channel") == int(channel_id):
                    self._state = channel.get("value_today")
