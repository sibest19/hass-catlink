"""Tests for the CatLink diagnostics download."""

import json
from unittest.mock import AsyncMock, MagicMock

from custom_components.catlink.const import DOMAIN
from custom_components.catlink.devices.base import Device
from custom_components.catlink.devices.feeder import FeederDevice
from custom_components.catlink.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)
from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

SECRETS = [
    "me@example.com",
    "hunter2",
    "tok-secret",
    "AA:BB:CC:DD:EE:01",
    "SN-0001",
    "dev-unknown",
    "dev-feeder",
    "HomeWifi",
    "iot-9",
    "https://img.example/a.png",
    "45.4642",
]


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    """Set up an entry whose coordinator holds a supported and an unknown device."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "email": "me@example.com",
            "password": "hunter2",
            "token": "tok-secret",
            "api_base": "https://app.catlinks.cn/api/",
            "region": "global",
        },
        options={"device_ids": ["dev-feeder"], "update_interval": 60},
    )
    entry.add_to_hass(hass)
    coordinator = MagicMock()
    coordinator.account.request = AsyncMock(
        return_value={
            "returnCode": 0,
            "data": {"deviceInfo": {"sn": "SN-0001", "iotId": "iot-9", "foo": 1}},
        }
    )
    unknown = Device(
        {
            "id": "dev-unknown",
            "mac": "AA:BB:CC:DD:EE:01",
            "model": "Feeder Pro",
            "deviceType": "FEEDER_PRO",
            "wifiName": "HomeWifi",
            "avatar": "https://img.example/a.png",
            "latitude": "45.4642",
        },
        coordinator,
    )
    feeder = FeederDevice(
        {"id": "dev-feeder", "mac": "AA:BB:CC:DD:EE:02", "deviceType": "FEEDER"},
        coordinator,
    )
    feeder.detail = {"weight": 12, "deviceId": "dev-feeder"}
    coordinator.devices = {"dev-unknown": unknown, "dev-feeder": feeder}
    hass.data[DOMAIN] = {"entry_coordinators": {entry.entry_id: coordinator}}
    return entry


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_entry_diagnostics(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Every device is listed with its raw data, and secrets are redacted."""
    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["integration_version"]
    assert diag["entry"]["data"]["api_base"] == "https://app.catlinks.cn/api/"
    assert diag["entry"]["data"]["password"] == REDACTED
    unknown, feeder = diag["devices"]
    assert unknown["deviceType"] == "FEEDER_PRO"
    assert unknown["supported"] is False
    assert unknown["raw_device_info"]["data"]["deviceInfo"]["foo"] == 1
    assert feeder["supported"] is True
    assert feeder["detail"]["weight"] == 12
    assert "raw_device_info" not in feeder

    dump = json.dumps(diag)
    for secret in SECRETS:
        assert secret not in dump


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_device_diagnostics(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Device diagnostics hold only that device."""
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "FEEDER_AA:BB:CC:DD:EE:02")},
    )
    diag = await async_get_device_diagnostics(hass, entry, device)

    assert [d["deviceType"] for d in diag["devices"]] == ["FEEDER"]
