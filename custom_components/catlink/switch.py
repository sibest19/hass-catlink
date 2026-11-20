"""Support for switch."""

from homeassistant.components.switch import DOMAIN as ENTITY_DOMAIN

from .entities import CatlinkSwitchEntity
from .helpers import Helper

async_setup_entry = Helper.async_setup_entry_for(ENTITY_DOMAIN)
