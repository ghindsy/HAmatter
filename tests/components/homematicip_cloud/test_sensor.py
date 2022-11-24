"""Tests for spencermaticIP Cloud sensor."""
from spencermaticip.base.enums import ValveState

from spencerassistant.components.spencermaticip_cloud import DOMAIN as HMIPC_DOMAIN
from spencerassistant.components.spencermaticip_cloud.generic_entity import (
    ATTR_CONFIG_PENDING,
    ATTR_DEVICE_OVERHEATED,
    ATTR_DEVICE_OVERLOADED,
    ATTR_DEVICE_UNTERVOLTAGE,
    ATTR_DUTY_CYCLE_REACHED,
    ATTR_RSSI_DEVICE,
    ATTR_RSSI_PEER,
)
from spencerassistant.components.spencermaticip_cloud.sensor import (
    ATTR_CURRENT_ILLUMINATION,
    ATTR_HIGHEST_ILLUMINATION,
    ATTR_LEFT_COUNTER,
    ATTR_LOWEST_ILLUMINATION,
    ATTR_RIGHT_COUNTER,
    ATTR_TEMPERATURE_OFFSET,
    ATTR_WIND_DIRECTION,
    ATTR_WIND_DIRECTION_VARIATION,
)
from spencerassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from spencerassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    LENGTH_MILLIMETERS,
    LIGHT_LUX,
    PERCENTAGE,
    POWER_WATT,
    SPEED_KILOMETERS_PER_HOUR,
    TEMP_CELSIUS,
)
from spencerassistant.setup import async_setup_component

from .helper import async_manipulate_test_data, get_and_check_entity_basics


async def test_manually_configured_platform(hass):
    """Test that we do not set up an access point."""
    assert await async_setup_component(
        hass, SENSOR_DOMAIN, {SENSOR_DOMAIN: {"platform": HMIPC_DOMAIN}}
    )
    assert not hass.data.get(HMIPC_DOMAIN)


async def test_hmip_accesspoint_status(hass, default_mock_hap_factory):
    """Test spencermaticipSwitch."""
    entity_id = "sensor.spencer_control_access_point_duty_cycle"
    entity_name = "spencer_CONTROL_ACCESS_POINT Duty Cycle"
    device_model = "HmIP-HAP"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["spencer_CONTROL_ACCESS_POINT"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )
    assert hmip_device
    assert ha_state.state == "8.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE


async def test_hmip_heating_thermostat(hass, default_mock_hap_factory):
    """Test spencermaticipHeatingThermostat."""
    entity_id = "sensor.heizkorperthermostat_heating"
    entity_name = "Heizkörperthermostat Heating"
    device_model = "HMIP-eTRV"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["Heizkörperthermostat"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    await async_manipulate_test_data(hass, hmip_device, "valvePosition", 0.37)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "37"

    await async_manipulate_test_data(hass, hmip_device, "valveState", "nn")
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "nn"

    await async_manipulate_test_data(
        hass, hmip_device, "valveState", ValveState.ADAPTION_DONE
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "37"

    await async_manipulate_test_data(hass, hmip_device, "lowBat", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes["icon"] == "mdi:battery-outline"


async def test_hmip_humidity_sensor(hass, default_mock_hap_factory):
    """Test spencermaticipHumiditySensor."""
    entity_id = "sensor.bwth_1_humidity"
    entity_name = "BWTH 1 Humidity"
    device_model = "HmIP-BWTH"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["BWTH 1"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "40"
    assert ha_state.attributes["unit_of_measurement"] == PERCENTAGE
    await async_manipulate_test_data(hass, hmip_device, "humidity", 45)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "45"
    # test common attributes
    assert ha_state.attributes[ATTR_RSSI_DEVICE] == -76
    assert ha_state.attributes[ATTR_RSSI_PEER] == -77


async def test_hmip_temperature_sensor1(hass, default_mock_hap_factory):
    """Test spencermaticipTemperatureSensor."""
    entity_id = "sensor.bwth_1_temperature"
    entity_name = "BWTH 1 Temperature"
    device_model = "HmIP-BWTH"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["BWTH 1"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "21.0"
    assert ha_state.attributes["unit_of_measurement"] == TEMP_CELSIUS
    await async_manipulate_test_data(hass, hmip_device, "actualTemperature", 23.5)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"

    assert not ha_state.attributes.get("temperature_offset")
    await async_manipulate_test_data(hass, hmip_device, "temperatureOffset", 10)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_TEMPERATURE_OFFSET] == 10


async def test_hmip_temperature_sensor2(hass, default_mock_hap_factory):
    """Test spencermaticipTemperatureSensor."""
    entity_id = "sensor.heizkorperthermostat_temperature"
    entity_name = "Heizkörperthermostat Temperature"
    device_model = "HMIP-eTRV"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["Heizkörperthermostat"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "20.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == TEMP_CELSIUS
    await async_manipulate_test_data(hass, hmip_device, "valveActualTemperature", 23.5)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"

    assert not ha_state.attributes.get(ATTR_TEMPERATURE_OFFSET)
    await async_manipulate_test_data(hass, hmip_device, "temperatureOffset", 10)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_TEMPERATURE_OFFSET] == 10


async def test_hmip_temperature_sensor3(hass, default_mock_hap_factory):
    """Test spencermaticipTemperatureSensor."""
    entity_id = "sensor.raumbediengerat_analog_temperature"
    entity_name = "Raumbediengerät Analog Temperature"
    device_model = "ALPHA-IP-RBGa"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["Raumbediengerät Analog"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "23.3"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == TEMP_CELSIUS
    await async_manipulate_test_data(hass, hmip_device, "actualTemperature", 23.5)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"

    assert not ha_state.attributes.get(ATTR_TEMPERATURE_OFFSET)
    await async_manipulate_test_data(hass, hmip_device, "temperatureOffset", 10)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_TEMPERATURE_OFFSET] == 10


async def test_hmip_power_sensor(hass, default_mock_hap_factory):
    """Test spencermaticipPowerSensor."""
    entity_id = "sensor.flur_oben_power"
    entity_name = "Flur oben Power"
    device_model = "HmIP-BSM"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["Flur oben"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "0.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == POWER_WATT
    await async_manipulate_test_data(hass, hmip_device, "currentPowerConsumption", 23.5)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"
    # test common attributes
    assert not ha_state.attributes.get(ATTR_DEVICE_OVERHEATED)
    assert not ha_state.attributes.get(ATTR_DEVICE_OVERLOADED)
    assert not ha_state.attributes.get(ATTR_DEVICE_UNTERVOLTAGE)
    assert not ha_state.attributes.get(ATTR_DUTY_CYCLE_REACHED)
    assert not ha_state.attributes.get(ATTR_CONFIG_PENDING)
    await async_manipulate_test_data(hass, hmip_device, "deviceOverheated", True)
    await async_manipulate_test_data(hass, hmip_device, "deviceOverloaded", True)
    await async_manipulate_test_data(hass, hmip_device, "deviceUndervoltage", True)
    await async_manipulate_test_data(hass, hmip_device, "dutyCycle", True)
    await async_manipulate_test_data(hass, hmip_device, "configPending", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_DEVICE_OVERHEATED]
    assert ha_state.attributes[ATTR_DEVICE_OVERLOADED]
    assert ha_state.attributes[ATTR_DEVICE_UNTERVOLTAGE]
    assert ha_state.attributes[ATTR_DUTY_CYCLE_REACHED]
    assert ha_state.attributes[ATTR_CONFIG_PENDING]


async def test_hmip_illuminance_sensor1(hass, default_mock_hap_factory):
    """Test spencermaticipIlluminanceSensor."""
    entity_id = "sensor.wettersensor_illuminance"
    entity_name = "Wettersensor Illuminance"
    device_model = "HmIP-SWO-B"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["Wettersensor"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "4890.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == LIGHT_LUX
    await async_manipulate_test_data(hass, hmip_device, "illumination", 231)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "231"


async def test_hmip_illuminance_sensor2(hass, default_mock_hap_factory):
    """Test spencermaticipIlluminanceSensor."""
    entity_id = "sensor.lichtsensor_nord_illuminance"
    entity_name = "Lichtsensor Nord Illuminance"
    device_model = "HmIP-SLO"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["Lichtsensor Nord"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "807.3"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == LIGHT_LUX
    await async_manipulate_test_data(hass, hmip_device, "averageIllumination", 231)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "231"
    assert ha_state.attributes[ATTR_CURRENT_ILLUMINATION] == 785.2
    assert ha_state.attributes[ATTR_HIGHEST_ILLUMINATION] == 837.1
    assert ha_state.attributes[ATTR_LOWEST_ILLUMINATION] == 785.2


async def test_hmip_windspeed_sensor(hass, default_mock_hap_factory):
    """Test spencermaticipWindspeedSensor."""
    entity_id = "sensor.wettersensor_pro_windspeed"
    entity_name = "Wettersensor - pro Windspeed"
    device_model = "HmIP-SWO-PR"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["Wettersensor - pro"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "2.6"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == SPEED_KILOMETERS_PER_HOUR
    await async_manipulate_test_data(hass, hmip_device, "windSpeed", 9.4)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "9.4"

    assert ha_state.attributes[ATTR_WIND_DIRECTION_VARIATION] == 56.25
    assert ha_state.attributes[ATTR_WIND_DIRECTION] == "WNW"

    wind_directions = {
        25: "NNE",
        37.5: "NE",
        70: "ENE",
        92.5: "E",
        115: "ESE",
        137.5: "SE",
        160: "SSE",
        182.5: "S",
        205: "SSW",
        227.5: "SW",
        250: "WSW",
        272.5: POWER_WATT,
        295: "WNW",
        317.5: "NW",
        340: "NNW",
        0: "N",
    }

    for direction, txt in wind_directions.items():
        await async_manipulate_test_data(hass, hmip_device, "windDirection", direction)
        ha_state = hass.states.get(entity_id)
        assert ha_state.attributes[ATTR_WIND_DIRECTION] == txt


async def test_hmip_today_rain_sensor(hass, default_mock_hap_factory):
    """Test spencermaticipTodayRainSensor."""
    entity_id = "sensor.weather_sensor_plus_today_rain"
    entity_name = "Weather Sensor – plus Today Rain"
    device_model = "HmIP-SWO-PL"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=["Weather Sensor – plus"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "3.9"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == LENGTH_MILLIMETERS
    await async_manipulate_test_data(hass, hmip_device, "todayRainCounter", 14.2)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "14.2"


async def test_hmip_temperature_external_sensor_channel_1(
    hass, default_mock_hap_factory
):
    """Test spencermaticipTemperatureDifferenceSensor Channel 1 HmIP-STE2-PCB."""
    entity_id = "sensor.ste2_channel_1_temperature"
    entity_name = "STE2 Channel 1 Temperature"
    device_model = "HmIP-STE2-PCB"

    mock_hap = await default_mock_hap_factory.async_get_mock_hap(test_devices=["STE2"])
    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    hmip_device = mock_hap.hmip_device_by_entity_id.get(entity_id)

    await async_manipulate_test_data(hass, hmip_device, "temperatureExternalOne", 25.4)

    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "25.4"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == TEMP_CELSIUS
    await async_manipulate_test_data(hass, hmip_device, "temperatureExternalOne", 23.5)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"


async def test_hmip_temperature_external_sensor_channel_2(
    hass, default_mock_hap_factory
):
    """Test spencermaticipTemperatureDifferenceSensor Channel 2 HmIP-STE2-PCB."""
    entity_id = "sensor.ste2_channel_2_temperature"
    entity_name = "STE2 Channel 2 Temperature"
    device_model = "HmIP-STE2-PCB"

    mock_hap = await default_mock_hap_factory.async_get_mock_hap(test_devices=["STE2"])
    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    hmip_device = mock_hap.hmip_device_by_entity_id.get(entity_id)

    await async_manipulate_test_data(hass, hmip_device, "temperatureExternalTwo", 22.4)

    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "22.4"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == TEMP_CELSIUS
    await async_manipulate_test_data(hass, hmip_device, "temperatureExternalTwo", 23.4)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.4"


async def test_hmip_temperature_external_sensor_delta(hass, default_mock_hap_factory):
    """Test spencermaticipTemperatureDifferenceSensor Delta HmIP-STE2-PCB."""
    entity_id = "sensor.ste2_delta_temperature"
    entity_name = "STE2 Delta Temperature"
    device_model = "HmIP-STE2-PCB"

    mock_hap = await default_mock_hap_factory.async_get_mock_hap(test_devices=["STE2"])
    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    hmip_device = mock_hap.hmip_device_by_entity_id.get(entity_id)

    await async_manipulate_test_data(hass, hmip_device, "temperatureExternalDelta", 0.4)

    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "0.4"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == TEMP_CELSIUS
    await async_manipulate_test_data(
        hass, hmip_device, "temperatureExternalDelta", -0.5
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "-0.5"


async def test_hmip_passage_detector_delta_counter(hass, default_mock_hap_factory):
    """Test spencermaticipPassageDetectorDeltaCounter."""
    entity_id = "sensor.spdr_1"
    entity_name = "SPDR_1"
    device_model = "HmIP-SPDR"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=[entity_name]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "164"
    assert ha_state.attributes[ATTR_LEFT_COUNTER] == 966
    assert ha_state.attributes[ATTR_RIGHT_COUNTER] == 802
    await async_manipulate_test_data(hass, hmip_device, "leftRightCounterDelta", 190)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "190"
