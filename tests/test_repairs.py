"""Tests for the unsupported-device repair issue."""

from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

from custom_components.catlink.const import DOMAIN
from custom_components.catlink.devices.base import Device
from custom_components.catlink.devices.registry import create_device

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir


def _coordinator(hass: HomeAssistant) -> MagicMock:
    coordinator = MagicMock()
    coordinator.hass = hass
    return coordinator


async def test_unknown_type_creates_issue(hass: HomeAssistant) -> None:
    """An unknown deviceType raises a warning that links a pre-filled issue form."""
    dat = {"id": "dev1", "model": "Feeder Pro", "deviceType": "FEEDER_PRO"}
    device = create_device(dat, _coordinator(hass))

    assert type(device) is Device
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "unsupported_device_FEEDER_PRO")
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING
    assert not issue.is_fixable
    assert issue.translation_key == "unsupported_device"
    assert issue.translation_placeholders == {
        "model": "Feeder Pro",
        "deviceType": "FEEDER_PRO",
    }
    url = urlparse(issue.learn_more_url)
    assert url.netloc == "github.com"
    assert url.path == "/sibest19/hass-catlink/issues/new"
    query = parse_qs(url.query)
    assert query["template"] == ["new_device.yml"]
    assert query["device-type"] == ["FEEDER_PRO"]
    assert query["model"] == ["Feeder Pro"]


async def test_supported_type_clears_stale_issue(hass: HomeAssistant) -> None:
    """Once a release supports the type, the old notice goes away."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        "unsupported_device_FEEDER",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="unsupported_device",
    )
    create_device({"id": "f1", "deviceType": "FEEDER"}, _coordinator(hass))

    assert (
        ir.async_get(hass).async_get_issue(DOMAIN, "unsupported_device_FEEDER") is None
    )
