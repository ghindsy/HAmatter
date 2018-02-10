"""The tests for the Template fan platform."""
import logging

from homeassistant.core import callback
from homeassistant import setup
import homeassistant.components as components
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.components.fan import (
    ATTR_SPEED, ATTR_OSCILLATING, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH)

from tests.common import (
    get_test_home_assistant, assert_setup_component)
_LOGGER = logging.getLogger(__name__)


_TEST_FAN = 'fan.test_fan'
# Represent for fan's state
_STATE_INPUT_BOOLEAN = 'input_boolean.state'
# Represent for fan's speed
_SPEED_INPUT_SELECT = 'input_select.speed'
# Represent for fan's oscillating
_OSC_INPUT_SELECT = 'input_select.osc'


class TestTemplateFan:
    """Test the Template light."""

    hass = None
    calls = None
    # pylint: disable=invalid-name

    def setup_method(self, method):
        """Setup."""
        self.hass = get_test_home_assistant()

        self.calls = []

        @callback
        def record_call(service):
            """Track function calls.."""
            self.calls.append(service)

        self.hass.services.register('test', 'automation', record_call)

    def teardown_method(self, method):
        """Stop everything that was started."""
        self.hass.stop()

    # Configuration tests #
    def test_missing_optional_config(self):
        """Test: missing optional template is ok."""
        with assert_setup_component(1, 'fan'):
            assert setup.setup_component(self.hass, 'fan', {
                'fan': {
                    'platform': 'template',
                    'fans': {
                        'test_fan': {
                            'value_template': "{{ 'on' }}",

                            'turn_on': {
                                'service': 'script.fan_on'
                            },
                            'turn_off': {
                                'service': 'script.fan_off'
                            }
                        }
                    }
                }
            })

        self.hass.start()
        self.hass.block_till_done()

        self._verify(STATE_ON, None, None)

    def test_missing_value_template_config(self):
        """Test: missing 'value_template' will fail."""
        with assert_setup_component(0, 'fan'):
            assert setup.setup_component(self.hass, 'fan', {
                'fan': {
                    'platform': 'template',
                    'fans': {
                        'test_fan': {
                            'turn_on': {
                                'service': 'script.fan_on'
                            },
                            'turn_off': {
                                'service': 'script.fan_off'
                            }
                        }
                    }
                }
            })

        self.hass.start()
        self.hass.block_till_done()

        assert self.hass.states.all() == []

    def test_missing_turn_on_config(self):
        """Test: missing 'turn_on' will fail."""
        with assert_setup_component(0, 'fan'):
            assert setup.setup_component(self.hass, 'fan', {
                'fan': {
                    'platform': 'template',
                    'fans': {
                        'test_fan': {
                            'value_template': "{{ 'on' }}",
                            'turn_off': {
                                'service': 'script.fan_off'
                            }
                        }
                    }
                }
            })

        self.hass.start()
        self.hass.block_till_done()

        assert self.hass.states.all() == []

    def test_missing_turn_off_config(self):
        """Test: missing 'turn_off' will fail."""
        with assert_setup_component(0, 'fan'):
            assert setup.setup_component(self.hass, 'fan', {
                'fan': {
                    'platform': 'template',
                    'fans': {
                        'test_fan': {
                            'value_template': "{{ 'on' }}",
                            'turn_on': {
                                'service': 'script.fan_on'
                            }
                        }
                    }
                }
            })

        self.hass.start()
        self.hass.block_till_done()

        assert self.hass.states.all() == []

    def test_invalid_config(self):
        """Test: missing 'turn_off' will fail."""
        with assert_setup_component(0, 'fan'):
            assert setup.setup_component(self.hass, 'fan', {
                'platform': 'template',
                'fans': {
                    'test_fan': {
                        'value_template': "{{ 'on' }}",
                        'turn_on': {
                            'service': 'script.fan_on'
                        }
                    }
                }
            })

        self.hass.start()
        self.hass.block_till_done()

        assert self.hass.states.all() == []

    # End of configuration tests #

    # Template tests #
    def test_templates_with_entities(self):
        """Test tempalates with values from other entities."""
        with assert_setup_component(1, 'fan'):
            assert setup.setup_component(self.hass, 'fan', {
                'fan': {
                    'platform': 'template',
                    'fans': {
                        'test_fan': {
                            'value_template':
                                "{{ states('input_boolean.state') }}",
                            'speed_template':
                                "{{ states('input_select.speed') }}",
                            'oscillating_template':
                                "{{ states('input_select.osc') }}",

                            'turn_on': {
                                'service': 'script.fan_on'
                            },
                            'turn_off': {
                                'service': 'script.fan_off'
                            }
                        }
                    }
                }
            })

        self.hass.start()
        self.hass.block_till_done()

        self._verify(STATE_OFF, None, None)

        self.hass.states.set(_STATE_INPUT_BOOLEAN, True)
        self.hass.states.set(_SPEED_INPUT_SELECT, SPEED_MEDIUM)
        self.hass.states.set(_OSC_INPUT_SELECT, 'True')
        self.hass.block_till_done()

        self._verify(STATE_ON, SPEED_MEDIUM, True)

    def test_templates_with_valid_values(self):
        """Test templates with valid values."""
        with assert_setup_component(1, 'fan'):
            assert setup.setup_component(self.hass, 'fan', {
                'fan': {
                    'platform': 'template',
                    'fans': {
                        'test_fan': {
                            'value_template':
                                "{{ 'on' }}",
                            'speed_template':
                                "{{ 'medium' }}",
                            'oscillating_template':
                                "{{ 1 == 1 }}",

                            'turn_on': {
                                'service': 'script.fan_on'
                            },
                            'turn_off': {
                                'service': 'script.fan_off'
                            }
                        }
                    }
                }
            })

        self.hass.start()
        self.hass.block_till_done()

        self._verify(STATE_ON, SPEED_MEDIUM, True)

    def test_templates_invalid_values(self):
        """Test templates with invalid values."""
        with assert_setup_component(1, 'fan'):
            assert setup.setup_component(self.hass, 'fan', {
                'fan': {
                    'platform': 'template',
                    'fans': {
                        'test_fan': {
                            'value_template':
                                "{{ 'abc' }}",
                            'speed_template':
                                "{{ '0' }}",
                            'oscillating_template':
                                "{{ 'xyz' }}",

                            'turn_on': {
                                'service': 'script.fan_on'
                            },
                            'turn_off': {
                                'service': 'script.fan_off'
                            }
                        }
                    }
                }
            })

        self.hass.start()
        self.hass.block_till_done()

        self._verify(STATE_OFF, None, None)

    # End of template tests #

    # Function tests #
    def test_on_off(self):
        """Test turn on and turn off."""
        self._register_components()

        # Turn on fan
        components.fan.turn_on(self.hass, _TEST_FAN)
        self.hass.block_till_done()

        # verify
        assert self.hass.states.get(_STATE_INPUT_BOOLEAN).state == STATE_ON
        self._verify(STATE_ON, None, None)

        # Turn off fan
        components.fan.turn_off(self.hass, _TEST_FAN)
        self.hass.block_till_done()

        # verify
        assert self.hass.states.get(_STATE_INPUT_BOOLEAN).state == STATE_OFF
        self._verify(STATE_OFF, None, None)

    def test_on_with_speed(self):
        """Test turn on with speed."""
        self._register_components()

        # Turn on fan with high speed
        components.fan.turn_on(self.hass, _TEST_FAN, SPEED_HIGH)
        self.hass.block_till_done()

        # verify
        assert self.hass.states.get(_STATE_INPUT_BOOLEAN).state == STATE_ON
        assert self.hass.states.get(_SPEED_INPUT_SELECT).state == SPEED_HIGH
        self._verify(STATE_ON, SPEED_HIGH, None)

    def test_set_speed(self):
        """Test set valid speed."""
        self._register_components()

        # Turn on fan
        components.fan.turn_on(self.hass, _TEST_FAN)
        self.hass.block_till_done()

        # Set fan's speed to high
        components.fan.set_speed(self.hass, _TEST_FAN, SPEED_HIGH)
        self.hass.block_till_done()

        # verify
        assert self.hass.states.get(_SPEED_INPUT_SELECT).state == SPEED_HIGH
        self._verify(STATE_ON, SPEED_HIGH, None)

        # Set fan's speed to medium
        components.fan.set_speed(self.hass, _TEST_FAN, SPEED_MEDIUM)
        self.hass.block_till_done()

        # verify
        assert self.hass.states.get(_SPEED_INPUT_SELECT).state == SPEED_MEDIUM
        self._verify(STATE_ON, SPEED_MEDIUM, None)

    def test_set_invalid_speed_from_initial_stage(self):
        """Test set invalid speed when fan is in initial state."""
        self._register_components()

        # Turn on fan
        components.fan.turn_on(self.hass, _TEST_FAN)
        self.hass.block_till_done()

        # Set fan's speed to 'invalid'
        components.fan.set_speed(self.hass, _TEST_FAN, 'invalid')
        self.hass.block_till_done()

        # verify speed is unchanged
        assert self.hass.states.get(_SPEED_INPUT_SELECT).state == ''
        self._verify(STATE_ON, None, None)

    def test_set_invalid_speed(self):
        """Test set invalid speed when fan has valid speed."""
        self._register_components()

        # Turn on fan
        components.fan.turn_on(self.hass, _TEST_FAN)
        self.hass.block_till_done()

        # Set fan's speed to high
        components.fan.set_speed(self.hass, _TEST_FAN, SPEED_HIGH)
        self.hass.block_till_done()

        # verify
        assert self.hass.states.get(_SPEED_INPUT_SELECT).state == SPEED_HIGH
        self._verify(STATE_ON, SPEED_HIGH, None)

        # Set fan's speed to 'invalid'
        components.fan.set_speed(self.hass, _TEST_FAN, 'invalid')
        self.hass.block_till_done()

        # verify speed is unchanged
        assert self.hass.states.get(_SPEED_INPUT_SELECT).state == SPEED_HIGH
        self._verify(STATE_ON, SPEED_HIGH, None)

    def test_custom_speed_list(self):
        """Test set custom speed list."""
        self._register_components(['1', '2', '3'])

        # Turn on fan
        components.fan.turn_on(self.hass, _TEST_FAN)
        self.hass.block_till_done()

        # Set fan's speed to '1'
        components.fan.set_speed(self.hass, _TEST_FAN, '1')
        self.hass.block_till_done()

        # verify
        assert self.hass.states.get(_SPEED_INPUT_SELECT).state == '1'
        self._verify(STATE_ON, '1', None)

        # Set fan's speed to 'medium' which is invalid
        components.fan.set_speed(self.hass, _TEST_FAN, SPEED_MEDIUM)
        self.hass.block_till_done()

        # verify that speed is unchanged
        assert self.hass.states.get(_SPEED_INPUT_SELECT).state == '1'
        self._verify(STATE_ON, '1', None)

    def test_set_osc(self):
        """Test set oscillating."""
        self._register_components()

        # Turn on fan
        components.fan.turn_on(self.hass, _TEST_FAN)
        self.hass.block_till_done()

        # Set fan's osc to True
        components.fan.oscillate(self.hass, _TEST_FAN, True)
        self.hass.block_till_done()

        # verify
        assert self.hass.states.get(_OSC_INPUT_SELECT).state == 'True'
        self._verify(STATE_ON, None, True)

        # Set fan's osc to False
        components.fan.oscillate(self.hass, _TEST_FAN, False)
        self.hass.block_till_done()

        # verify
        assert self.hass.states.get(_OSC_INPUT_SELECT).state == 'False'
        self._verify(STATE_ON, None, False)

    def test_set_invalid_osc_from_initial_state(self):
        """Test set invalid oscillating when fan is in initial state."""
        self._register_components()

        # Turn on fan
        components.fan.turn_on(self.hass, _TEST_FAN)
        self.hass.block_till_done()

        # Set fan's osc to 'invalid'
        components.fan.oscillate(self.hass, _TEST_FAN, 'invalid')
        self.hass.block_till_done()

        # verify
        assert self.hass.states.get(_OSC_INPUT_SELECT).state == ''
        self._verify(STATE_ON, None, None)

    def test_set_invalid_osc(self):
        """Test set invalid oscillating when fan has valid osc."""
        self._register_components()

        # Turn on fan
        components.fan.turn_on(self.hass, _TEST_FAN)
        self.hass.block_till_done()

        # Set fan's osc to True
        components.fan.oscillate(self.hass, _TEST_FAN, True)
        self.hass.block_till_done()

        # verify
        assert self.hass.states.get(_OSC_INPUT_SELECT).state == 'True'
        self._verify(STATE_ON, None, True)

        # Set fan's osc to False
        components.fan.oscillate(self.hass, _TEST_FAN, None)
        self.hass.block_till_done()

        # verify osc is unchanged
        assert self.hass.states.get(_OSC_INPUT_SELECT).state == 'True'
        self._verify(STATE_ON, None, True)

    def _verify(self, expected_state, expected_speed, expected_oscillating):
        """Verify fan's state, speed and osc."""
        state = self.hass.states.get(_TEST_FAN)
        attributes = state.attributes
        assert state.state == expected_state
        assert attributes.get(ATTR_SPEED, None) == expected_speed
        assert attributes.get(ATTR_OSCILLATING, None) == expected_oscillating

    def _register_components(self, speed_list=None):
        """Register basic components for testing."""
        with assert_setup_component(1, 'input_boolean'):
            assert setup.setup_component(
                self.hass,
                'input_boolean',
                {'input_boolean': {'state': None}}
            )

        with assert_setup_component(2, 'input_select'):
            assert setup.setup_component(self.hass, 'input_select', {
                'input_select': {
                    'speed': {
                        'name': 'Speed',
                        'options': ['', SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH,
                                    '1', '2', '3']
                    },

                    'osc': {
                        'name': 'oscillating',
                        'options': ['', 'True', 'False']
                    },
                }
            })

        with assert_setup_component(1, 'fan'):
            test_fan_config = {
                'value_template':
                    "{{ states('input_boolean.state') }}",
                'speed_template':
                    "{{ states('input_select.speed') }}",
                'oscillating_template':
                    "{{ states('input_select.osc') }}",

                'turn_on': {
                    'service': 'input_boolean.turn_on',
                    'entity_id': _STATE_INPUT_BOOLEAN
                },
                'turn_off': {
                    'service': 'input_boolean.turn_off',
                    'entity_id': _STATE_INPUT_BOOLEAN
                },
                'set_speed': {
                    'service': 'input_select.select_option',

                    'data_template': {
                        'entity_id': _SPEED_INPUT_SELECT,
                        'option': '{{ speed }}'
                    }
                },
                'set_oscillating': {
                    'service': 'input_select.select_option',

                    'data_template': {
                        'entity_id': _OSC_INPUT_SELECT,
                        'option': '{{ oscillating }}'
                    }
                }
            }

            if speed_list:
                test_fan_config['speeds'] = speed_list

            assert setup.setup_component(self.hass, 'fan', {
                'fan': {
                    'platform': 'template',
                    'fans': {
                        'test_fan': test_fan_config
                    }
                }
            })

        self.hass.start()
        self.hass.block_till_done()
