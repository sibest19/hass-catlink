"""Binary entities for CatLink integration."""

from homeassistant.components.binary_sensor import BinarySensorEntity

from ..devices.base import Device
from .base import CatlinkEntity


class CatlinkBinaryEntity(CatlinkEntity):
    """CatlinkBinaryEntity."""

    def __init__(self, name, device: Device, option=None) -> None:
        """Initialize the entity."""
        super().__init__(name, device, option)
        self._attr_is_on = False

    def update(self) -> None:
        """Update the entity."""
        super().update()
        self._attr_is_on = bool(self._attr_native_value)


class CatlinkBinarySensorEntity(CatlinkBinaryEntity, BinarySensorEntity):
    """Binary sensor entity for CatLink."""

