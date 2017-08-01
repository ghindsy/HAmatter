"""The tests for the mqtt climate component."""
import unittest

from homeassistant.util.unit_system import (
    METRIC_SYSTEM
)
from homeassistant.setup import setup_component
from homeassistant.components import climate
from homeassistant.const import (STATE_OFF)

from tests.common import (get_test_home_assistant, mock_mqtt_component)

ENTITY_CLIMATE = 'climate.test'
ENT_SENSOR = 'sensor.test'


class BaseMQTT(unittest.TestCase):
    """Base climate hvac test."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.mock_publish = mock_mqtt_component(self.hass)
        self.hass.config.units = METRIC_SYSTEM
        self.assertTrue(setup_component(self.hass, climate.DOMAIN, {
            'climate': {
                'platform': 'mqtt',
                'name': 'test',
                'target_sensor': ENT_SENSOR,
                'mode_command_topic': 'mode-topic',
                'temperature_command_topic': 'temperature-topic',
                'fan_mode_command_topic': 'fan-mode-topic',
                'swing_mode_command_topic': 'swing-mode-topic',
            }}))

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_setup_params(self):
        """Test the initial parameters."""
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual(24, state.attributes.get('temperature'))
        self.assertEqual("low", state.attributes.get('fan_mode'))
        self.assertEqual("off", state.attributes.get('swing_mode'))
        self.assertEqual("off", state.attributes.get('operation_mode'))


class TestMQTTClimate(BaseMQTT):
    """Test the mqtt climate hvac."""

    def test_get_operation_modes(self):
        """Test that the operation list returns the correct modes."""
        state = self.hass.states.get(ENTITY_CLIMATE)
        modes = state.attributes.get('operation_list')
        self.assertEqual([
          climate.STATE_AUTO, STATE_OFF, climate.STATE_COOL,
          climate.STATE_HEAT, climate.STATE_DRY, climate.STATE_FAN_ONLY
        ], modes)

    def test_set_fan_mode_bad_attr(self):
        """Test setting fan mode without required attribute."""
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual("low", state.attributes.get('fan_mode'))
        climate.set_fan_mode(self.hass, None, ENTITY_CLIMATE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual("low", state.attributes.get('fan_mode'))

    def test_set_fan_mode(self):
        """Test setting of new fan mode."""
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual("low", state.attributes.get('fan_mode'))
        climate.set_fan_mode(self.hass, "low", ENTITY_CLIMATE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual("low", state.attributes.get('fan_mode'))

    def test_set_swing_mode_bad_attr(self):
        """Test setting swing mode without required attribute."""
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual("off", state.attributes.get('swing_mode'))
        climate.set_swing_mode(self.hass, None, ENTITY_CLIMATE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual("off", state.attributes.get('swing_mode'))

    def test_set_swing(self):
        """Test setting of new swing mode."""
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual("off", state.attributes.get('swing_mode'))
        climate.set_swing_mode(self.hass, "on", ENTITY_CLIMATE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual("on", state.attributes.get('swing_mode'))


class TestMQTTClimateMode(BaseMQTT):
    """Test the mqtt climate hvac operation mode."""

    def test_set_operation_bad_attr_and_state(self):
        """Test setting operation mode without required attribute.

        Also check the state.
        """
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual("off", state.attributes.get('operation_mode'))
        self.assertEqual("off", state.state)
        climate.set_operation_mode(self.hass, None, ENTITY_CLIMATE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual("off", state.attributes.get('operation_mode'))
        self.assertEqual("off", state.state)

    def test_set_operation(self):
        """Test setting of new operation mode."""
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual("off", state.attributes.get('operation_mode'))
        self.assertEqual("off", state.state)
        climate.set_operation_mode(self.hass, "cool", ENTITY_CLIMATE)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY_CLIMATE)
        self.assertEqual("cool", state.attributes.get('operation_mode'))
        self.assertEqual("cool", state.state)
        self.assertEqual(('mode-topic', 'cool', 0, False),
                         self.mock_publish.mock_calls[-2][1])
