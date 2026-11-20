"""Helper functions for the CatLink integration."""

from datetime import timedelta
import re

import phonenumbers
from phonenumbers import NumberParseException

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_conversion import MassConverter
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from .const import (
    API_SERVERS,
    CONF_API_BASE,
    DOMAIN,
)


def parse_phone_number(phone: str) -> tuple[str, str]:
    """Parse a full phone number into country code and national number.

    Accepts formats like +447911123456, 447911123456, or 07911123456.
    Returns (phone_iac, phone_number) for CatLink API.
    """
    cleaned = re.sub(r"[\s\-\.\(\)]", "", str(phone).strip())
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned.lstrip("0")
    try:
        parsed = phonenumbers.parse(cleaned, None)
        return (
            str(parsed.country_code),
            str(parsed.national_number),
        )
    except NumberParseException:
        pass
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) >= 10:
        for length in (3, 2, 1):
            if len(digits) > length:
                return (digits[:length], digits[length:])
    return ("86", digits or "0")


async def discover_region(
    hass: HomeAssistant,
    credentials: dict[str, str],
    region: str | None = None,
) -> str | None:
    """Find the API region that accepts these credentials.

    ``credentials`` identifies the account by either CONF_EMAIL or
    CONF_PHONE/CONF_PHONE_IAC, plus CONF_PASSWORD.

    When ``region`` is given, only that region is tried. Otherwise every region
    is tried in turn — convenient, but it spends a failed login attempt against
    each server when the credentials are simply wrong, so prefer passing the
    region when the user knows it.

    Returns the region key, or None if no region accepted the credentials.
    """
    from .modules.account import Account

    for name in [region] if region else list(API_SERVERS):
        api_base = API_SERVERS.get(name)
        if not api_base:
            continue
        account = Account(hass, {CONF_API_BASE: api_base, **credentials})
        if await account.async_login():
            return name
    return None


def as_int(value: object, default: int | None = None) -> int | None:
    """Coerce an API value to an int, falling back to ``default``.

    CatLink sends JSON null for fields a device does not report, and that null
    survives ``dict.get(key, fallback)`` because the key is present with a null
    value. Countdowns in particular must stay unknown rather than silently
    becoming a misleading zero, so the default here is None.
    """
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# The app's weightUnitTip values, which follow the unit set in the CatLink app.
MASS_UNITS: dict[str, str] = {
    "kg": UnitOfMass.KILOGRAMS,
    "g": UnitOfMass.GRAMS,
    "lb": UnitOfMass.POUNDS,
    "oz": UnitOfMass.OUNCES,
}


def convert_mass(value: object, unit_tip: str | None, to_unit: str) -> float | None:
    """Return a CatLink weight in to_unit, or None when the value or its unit is unknown."""
    unit = MASS_UNITS.get(unit_tip)
    if value is None or unit is None:
        return None
    return MassConverter.convert(float(value), unit, to_unit)


def mass_options(hass: HomeAssistant, small: bool = False) -> dict:
    """Return the options of a weight sensor reporting kg (g when small).

    Home Assistant does not convert weights by unit system on its own, so the
    suggested unit makes them follow it: kg / g for metric, lb / oz for US.
    """
    us = hass.config.units is US_CUSTOMARY_SYSTEM
    if small:
        unit, shown, precision = UnitOfMass.GRAMS, UnitOfMass.OUNCES, 0
    else:
        unit, shown, precision = UnitOfMass.KILOGRAMS, UnitOfMass.POUNDS, 1
    return {
        "class": SensorDeviceClass.WEIGHT,
        "unit": unit,
        "suggested_unit": shown if us else unit,
        "precision": precision,
        "state_class": SensorStateClass.MEASUREMENT,
    }


def format_api_error(rdt: dict) -> str:
    """Build a user-friendly error message from CatLink API response.

    Extracts the 'msg' field when present; otherwise returns a string
    representation of the full response for debugging.
    """
    msg = rdt.get("msg") or rdt.get("message")
    code = rdt.get("returnCode")
    if msg:
        return f"{msg} (returnCode: {code})" if code else str(msg)
    return str(rdt)


class Helper:
    """Helper class for the CatLink integration."""

    @classmethod
    def calculate_update_interval(
        cls, update_interval: str | timedelta | int | float | None
    ) -> timedelta:
        """Calculate the update interval as a timedelta object.

        Args:
            update_interval: A timedelta, seconds (int/float), or "HH:MM:SS" string.

        Returns:
            timedelta: The update interval as a timedelta object.
        """
        if isinstance(update_interval, timedelta):
            return update_interval
        if isinstance(update_interval, (int, float)) and update_interval > 0:
            return timedelta(seconds=int(update_interval))
        if isinstance(update_interval, str) and re.match(
            r"^\d{2}:\d{2}:\d{2}$", update_interval
        ):
            return timedelta(
                hours=int(update_interval[:2]),
                minutes=int(update_interval[3:5]),
                seconds=int(update_interval[6:8]),
            )
        return timedelta(minutes=1)

    @staticmethod
    def async_setup_entry_for(domain: str):
        """Return async_setup_entry bound to the given platform domain."""

        async def _async_setup_entry(
            hass: HomeAssistant,
            config_entry: ConfigEntry,
            async_add_entities,
        ) -> None:
            """Set up the Catlink platform for a config entry."""
            hass.data[DOMAIN].setdefault("add_entities", {})
            hass.data[DOMAIN]["add_entities"].setdefault(config_entry.entry_id, {})[
                domain
            ] = async_add_entities

            coordinator = hass.data[DOMAIN]["entry_coordinators"].get(
                config_entry.entry_id
            )
            if coordinator is not None and coordinator.data is not None:
                for sta in coordinator.data.values():
                    await coordinator.update_hass_entities(domain, sta)

        return _async_setup_entry
