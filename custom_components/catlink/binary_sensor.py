"""Support for binary_sensor."""

from homeassistant.components.binary_sensor import (
    DOMAIN as ENTITY_DOMAIN,
    BinarySensorEntity,
)

from .entities import CatlinkBinarySensorEntity
from .helpers import Helper

async_setup_entry = Helper.async_setup_entry_for(ENTITY_DOMAIN)
