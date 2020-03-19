"""Tests for the AlarmDecoder alarm control panel device."""
from homeassistant.components.alarmdecoder import DOMAIN
from homeassistant.components.alarmdecoder.alarm_control_panel import (
    AlarmDecoderAlarmPanel,
)
from unittest.mock import patch, call
import pytest


@pytest.mark.parametrize(
    "auto_bypass,code_arm_required,code,expected",
    [
        (True, True, "1234", ["12347"]),
        (True, False, "1234", ["12347"]),
        (False, True, "1234", ["12347"]),
        (False, False, "1234", ["12347"]),
        (True, True, None, []),
        (True, False, None, ["#7"]),
        (False, True, None, []),
        (False, False, None, ["#7"]),
    ],
)
def test_alarm_arm_night(auto_bypass, code_arm_required, code, expected):
    """Test all variations of alarm_arm_night."""
    with patch.object(AlarmDecoderAlarmPanel, "hass", autospec=True) as mock_hass:
        alarm_panel = AlarmDecoderAlarmPanel(auto_bypass, code_arm_required)
        alarm_panel.alarm_arm_night(code=code)
        assert mock_hass.data[DOMAIN].send.call_args_list == [call(x) for x in expected]


@pytest.mark.parametrize(
    "auto_bypass,code_arm_required,code,expected",
    [
        (True, True, "1234", ["12346#", "12343"]),
        (True, False, "1234", ["12346#", "12343"]),
        (False, True, "1234", ["12343"]),
        (False, False, "1234", ["12343"]),
        (True, True, None, []),
        (True, False, None, ["#3"]),
        (False, True, None, []),
        (False, False, None, ["#3"]),
    ],
)
def test_alarm_arm_home(auto_bypass, code_arm_required, code, expected):
    """Test all variations of alarm_arm_home."""
    with patch.object(AlarmDecoderAlarmPanel, "hass", autospec=True) as mock_hass:
        alarm_panel = AlarmDecoderAlarmPanel(auto_bypass, code_arm_required)
        alarm_panel.alarm_arm_home(code=code)
        assert mock_hass.data[DOMAIN].send.call_args_list == [call(x) for x in expected]


@pytest.mark.parametrize(
    "auto_bypass,code_arm_required,code,expected",
    [
        (True, True, "1234", ["12346#", "12342"]),
        (True, False, "1234", ["12346#", "12342"]),
        (False, True, "1234", ["12342"]),
        (False, False, "1234", ["12342"]),
        (True, True, None, []),
        (True, False, None, ["#2"]),
        (False, True, None, []),
        (False, False, None, ["#2"]),
    ],
)
def test_alarm_arm_away(auto_bypass, code_arm_required, code, expected):
    """Test all variations of alarm_arm_away."""
    with patch.object(AlarmDecoderAlarmPanel, "hass", autospec=True) as mock_hass:
        alarm_panel = AlarmDecoderAlarmPanel(auto_bypass, code_arm_required)
        alarm_panel.alarm_arm_away(code=code)
        assert mock_hass.data[DOMAIN].send.call_args_list == [call(x) for x in expected]
