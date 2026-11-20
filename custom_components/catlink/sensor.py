"""Support for sensor."""

import voluptuous as vol

from homeassistant.components.sensor import DOMAIN as ENTITY_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform

from .entities import CatlinkSensorEntity
from .helpers import Helper

_async_setup_entities = Helper.async_setup_entry_for(ENTITY_DOMAIN)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Catlink sensors and the request_api action for a config entry."""
    await _async_setup_entities(hass, config_entry, async_add_entities)
    # Registered once: later config entries find it and return early.
    entity_platform.async_get_current_platform().async_register_entity_service(
        "request_api",
        {
            vol.Required("api"): cv.string,
            vol.Optional("params", default={}): vol.Any(dict, None),
            vol.Optional("method", default="GET"): cv.string,
            vol.Optional("throw", default=True): cv.boolean,
        },
        "async_request_api",
    )
