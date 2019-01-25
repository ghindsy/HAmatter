"""Basic checks for HomeKitSwitch."""
from tests.components.homekit_controller.common import (
    add_fake_homekit_accessory)


async def test_switch_change_light_state(hass):
    """Test that we can turn a HomeKit light on and off again."""
    from homekit.model.services import BHSLightBulbService

    helper = await add_fake_homekit_accessory(hass, [BHSLightBulbService()])

    await hass.services.async_call('light', 'turn_on', {
        'entity_id': 'light.testdevice',
        'brightness': 255,
        'hs_color': [4, 5],
    }, blocking=True)
    assert helper.characteristics[('lightbulb', 'on')].value == 1
    assert helper.characteristics[('lightbulb', 'brightness')].value == 100
    assert helper.characteristics[('lightbulb', 'hue')].value == 4
    assert helper.characteristics[('lightbulb', 'saturation')].value == 5

    await hass.services.async_call('light', 'turn_off', {
        'entity_id': 'light.testdevice',
    }, blocking=True)
    assert helper.characteristics[('lightbulb', 'on')].value == 0


async def test_switch_read_light_state(hass):
    """Test that we can read the state of a HomeKit light accessory."""
    from homekit.model.services import BHSLightBulbService

    helper = await add_fake_homekit_accessory(hass, [BHSLightBulbService()])

    # Initial state is that the light is off
    light_1 = await helper.get_state()
    assert light_1.state == 'off'

    # Simulate that someone switched on the device in the real world not via HA
    helper.characteristics[('lightbulb', 'on')].set_value(True)
    light_1 = await helper.get_state()
    assert light_1.state == 'on'

    # Simulate that device switched off in the real world not via HA
    helper.characteristics[('lightbulb', 'on')].set_value(False)
    light_1 = await helper.get_state()
    assert light_1.state == 'off'
