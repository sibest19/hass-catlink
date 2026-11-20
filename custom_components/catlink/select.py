"""Support for select."""

from homeassistant.components.select import DOMAIN as ENTITY_DOMAIN

from .const import DOMAIN
from .entities import CatlinkSelectEntity
from .helpers import Helper

async_setup_entry = Helper.async_setup_entry_for(ENTITY_DOMAIN)
