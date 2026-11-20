"""Tests for the unsupported-device repair issue."""

from urllib.parse import parse_qs, urlparse

from custom_components.catlink.const import DOMAIN
from custom_components.catlink.devices.registry import async_update_unsupported_issue

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir


async def test_unknown_type_creates_issue(hass: HomeAssistant) -> None:
    """An unknown deviceType raises a warning that links a pre-filled issue form."""
    async_update_unsupported_issue(hass, "FEEDER_PRO", "Feeder Pro")

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
    async_update_unsupported_issue(hass, "FEEDER", None)

    assert (
        ir.async_get(hass).async_get_issue(DOMAIN, "unsupported_device_FEEDER") is None
    )
