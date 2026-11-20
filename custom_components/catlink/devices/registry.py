"""Device registry for CatLink integration."""

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from homeassistant.helpers import issue_registry as ir

from ..const import DOMAIN
from .base import Device
from .cat import CatDevice
from .c08 import C08Device
from .feeder import FeederDevice
from .litterbox import LitterBox
from .scooper import ScooperDevice
from .scooper_pro_ultra import ScooperProUltraDevice
from .purepro import PureProDevice

if TYPE_CHECKING:
    from ..models.additional_cfg import AdditionalDeviceConfig
    from ..modules.devices_coordinator import DevicesCoordinator

DEVICE_TYPES: dict[str, type[Device]] = {
    "CAT": CatDevice,
    "C08": C08Device,
    "SCOOPER": ScooperDevice,
    "LITTER_BOX_599": LitterBox,  # SCOOPER C1
    "VISUAL_PRO_ULTRA": ScooperProUltraDevice,
    "FEEDER": FeederDevice,
    "PUREPRO": PureProDevice,
}


def create_device(
    dat: dict,
    coordinator: "DevicesCoordinator",
    additional_config: "AdditionalDeviceConfig | None" = None,
) -> Device:
    """Create a device instance from API data."""
    typ = dat.get("deviceType")
    device_cls = DEVICE_TYPES.get(typ, Device)
    return device_cls(dat, coordinator, additional_config)


def async_update_unsupported_issue(hass, typ: str | None, model: str | None) -> None:
    """Ask for help with an unknown deviceType; drop the notice once it is supported."""
    issue_id = f"unsupported_device_{typ}"
    if typ in DEVICE_TYPES:
        # A release added support since the notice was raised.
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    model = model or typ
    query = urlencode(
        {
            "template": "new_device.yml",
            "title": f"Device support: {model} ({typ})",
            "model": model,
            "device-type": typ,
        }
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="unsupported_device",
        translation_placeholders={"model": model, "deviceType": typ},
        learn_more_url=f"https://github.com/sibest19/hass-catlink/issues/new?{query}",
    )
