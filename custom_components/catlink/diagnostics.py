"""Diagnostics for CatLink: what maintainers need to add or verify a device."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.loader import async_get_integration

from .const import DOMAIN, SUPPORTED_DEVICE_TYPES
from .devices.base import Device

# Exact key names, matched at any depth of the dump.
TO_REDACT = {
    "email",
    "phone",
    "mobile",
    "password",
    "token",
    "uid",
    "userId",
    "mac",
    "sn",
    "serialNumber",
    "id",
    "deviceId",
    "device_ids",
    "pet_id",
    "petId",
    "iotId",
    "ssid",
    "wifiName",
    "wifiSsid",
    "userName",
    "nickName",
    "nickname",
    "masterName",
    "avatar",
    "avatarUrl",
    "petAvatar",
    "headUrl",
    "latitude",
    "longitude",
    "lat",
    "lng",
}


async def _device_diagnostics(dvc: Device) -> dict[str, Any]:
    """Return what the API reports for one device."""
    info: dict[str, Any] = {
        "deviceType": dvc.type,
        "model": dvc.model,
        "class": type(dvc).__name__,
        "supported": dvc.type == "CAT" or dvc.type in SUPPORTED_DEVICE_TYPES,
        "data": dvc.data,
        "detail": dvc.detail,
        "logs": getattr(dvc, "logs", None),
    }
    # Unknown types get no detail parsing, so show the raw generic endpoint.
    if type(dvc) is Device:
        info["raw_device_info"] = await dvc.account.request(
            "token/device/info", {"deviceId": dvc.id}
        )
    return info


async def _async_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, identifiers: set | None = None
) -> dict[str, Any]:
    """Return the entry and its devices, only those matching identifiers if given."""
    coordinator = hass.data[DOMAIN]["entry_coordinators"].get(entry.entry_id)
    devices = [
        dvc
        for dvc in (coordinator.devices.values() if coordinator else ())
        if identifiers is None or identifiers & dvc.device_info["identifiers"]
    ]
    integration = await async_get_integration(hass, DOMAIN)
    return async_redact_data(
        {
            "integration_version": str(integration.version),
            "entry": {"data": dict(entry.data), "options": dict(entry.options)},
            "devices": [await _device_diagnostics(dvc) for dvc in devices],
        },
        TO_REDACT,
    )


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return await _async_diagnostics(hass, entry)


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for one device."""
    return await _async_diagnostics(hass, entry, device.identifiers)
