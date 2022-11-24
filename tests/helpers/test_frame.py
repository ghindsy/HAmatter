"""Test the frame helper."""
# pylint: disable=protected-access
from unittest.mock import Mock, patch

import pytest

from spencerassistant.helpers import frame


async def test_extract_frame_integration(caplog, mock_integration_frame):
    """Test extracting the current frame from integration context."""
    found_frame, integration, path = frame.get_integration_frame()

    assert integration == "hue"
    assert path == "spencerassistant/components/"
    assert found_frame == mock_integration_frame


async def test_extract_frame_integration_with_excluded_integration(caplog):
    """Test extracting the current frame from integration context."""
    correct_frame = Mock(
        filename="/spencer/dev/spencerassistant/components/mdns/light.py",
        lineno="23",
        line="self.light.is_on",
    )
    with patch(
        "spencerassistant.helpers.frame.extract_stack",
        return_value=[
            Mock(
                filename="/spencer/dev/spencerassistant/core.py",
                lineno="23",
                line="do_something()",
            ),
            correct_frame,
            Mock(
                filename="/spencer/dev/spencerassistant/components/zeroconf/usage.py",
                lineno="23",
                line="self.light.is_on",
            ),
            Mock(
                filename="/spencer/dev/mdns/lights.py",
                lineno="2",
                line="something()",
            ),
        ],
    ):
        found_frame, integration, path = frame.get_integration_frame(
            exclude_integrations={"zeroconf"}
        )

    assert integration == "mdns"
    assert path == "spencerassistant/components/"
    assert found_frame == correct_frame


async def test_extract_frame_no_integration(caplog):
    """Test extracting the current frame without integration context."""
    with patch(
        "spencerassistant.helpers.frame.extract_stack",
        return_value=[
            Mock(
                filename="/spencer/paulus/spencerassistant/core.py",
                lineno="23",
                line="do_something()",
            ),
            Mock(
                filename="/spencer/paulus/aiohue/lights.py",
                lineno="2",
                line="something()",
            ),
        ],
    ), pytest.raises(frame.MissingIntegrationFrame):
        frame.get_integration_frame()


@pytest.mark.usefixtures("mock_integration_frame")
@patch.object(frame, "_REPORTED_INTEGRATIONS", set())
async def test_prevent_flooding(caplog):
    """Test to ensure a report is only written once to the log."""

    what = "accessed hi instead of hello"
    key = "/spencer/paulus/spencerassistant/components/hue/light.py:23"

    frame.report(what, error_if_core=False)
    assert what in caplog.text
    assert key in frame._REPORTED_INTEGRATIONS
    assert len(frame._REPORTED_INTEGRATIONS) == 1

    caplog.clear()

    frame.report(what, error_if_core=False)
    assert what not in caplog.text
    assert key in frame._REPORTED_INTEGRATIONS
    assert len(frame._REPORTED_INTEGRATIONS) == 1


async def test_report_missing_integration_frame(caplog):
    """Test reporting when no integration is detected."""

    what = "teststring"
    with patch(
        "spencerassistant.helpers.frame.get_integration_frame",
        side_effect=frame.MissingIntegrationFrame,
    ):
        frame.report(what, error_if_core=False)
        assert what in caplog.text
        assert caplog.text.count(what) == 1
