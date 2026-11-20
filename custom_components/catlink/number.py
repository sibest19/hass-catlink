"""Support for number."""

from homeassistant.components.number import DOMAIN as ENTITY_DOMAIN

from .const import DOMAIN
from .entities.number import CatlinkNumberEntity
from .helpers import Helper

async_setup_entry = Helper.async_setup_entry_for(ENTITY_DOMAIN)
