"""Support for button."""

from homeassistant.components.button import DOMAIN as ENTITY_DOMAIN

from .const import DOMAIN
from .entities import CatlinkButtonEntity
from .helpers import Helper

async_setup_entry = Helper.async_setup_entry_for(ENTITY_DOMAIN)
