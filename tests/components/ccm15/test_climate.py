"""Unit test for CCM15 climate component."""
import unittest

import homeassistant.components.ccm15 as ccm15

# from homeassistant.components.ccm15 import CCM15SlaveDevice


class TestCCM15SlaveDevice(unittest.TestCase):
    """Test the CCM15SlaveDevice class."""

    def test_swing_mode_on(self) -> None:
        """Test that the swing mode is on."""
        data = bytes.fromhex("00000041d2001a")
        device = ccm15.climate.CCM15SlaveDevice(data)
        self.assertTrue(device.is_swing_on)

    def test_swing_mode_off(self) -> None:
        """Test that the swing mode is off."""
        data = bytes.fromhex("00000041d0001a")
        device = ccm15.climate.CCM15SlaveDevice(data)
        self.assertFalse(device.is_swing_on)

    def test_temp_fan_mode(self) -> None:
        """Test that the swing mode is on."""
        data = bytes.fromhex("00000041d2001a")
        device = ccm15.climate.CCM15SlaveDevice(data)
        self.assertEqual(26, device.temperature)
        self.assertEqual(2, device.fan_mode)
        self.assertEqual(0, device.ac_mode)


if __name__ == "__main__":
    unittest.main()
