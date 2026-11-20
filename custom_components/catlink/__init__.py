"""The component."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICES
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .const import (
    CONF_ACCOUNTS,
    CONF_DEVICE_IDS,
    DOMAIN,
    SUPPORTED_DOMAINS,
)
from .modules.account import Account
from .modules.devices_coordinator import DevicesCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# (platform, entity key) pairs no device creates any more; their registry
# entries would otherwise linger as "unavailable". "online" became a
# connectivity binary sensor.
REMOVED_ENTITIES = {
    ("sensor", "occupied"),
    ("sensor", "online"),
    ("sensor", "toilet_weight_avg"),
    ("sensor", "diet_times"),
    ("sensor", "sport_active_duration"),
    ("binary_sensor", "uv_active"),
    ("binary_sensor", "heating"),
    ("binary_sensor", "hair_cleaning"),
}


@callback
def _async_remove_stale_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove registry entries of entities the integration no longer creates."""
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        # unique_id is "<deviceType>_<mac>-<key>"
        key = entity.unique_id.rsplit("-", 1)[-1]
        pro_ultra_select = entity.domain == "select" and entity.unique_id.startswith(
            "VISUAL_PRO_ULTRA_"
        )
        if (entity.domain, key) in REMOVED_ENTITIES or pro_ultra_select:
            registry.async_remove(entity.entity_id)


async def async_setup(hass: HomeAssistant, hass_config: dict) -> bool:
    """Set up the CatLink component."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(CONF_ACCOUNTS, {})
    hass.data[DOMAIN].setdefault("coordinators", {})
    hass.data[DOMAIN].setdefault("add_entities", {})
    hass.data[DOMAIN].setdefault("config", {})
    hass.data[DOMAIN].setdefault("entry_coordinators", {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CatLink from a config entry."""
    hass.data[DOMAIN].setdefault("config", {})
    hass.data[DOMAIN]["config"].setdefault(CONF_DEVICES, [])

    config = {**entry.data, **(entry.options or {})}
    acc = Account(hass, config)
    device_ids = entry.options.get(CONF_DEVICE_IDS) if entry.options else None
    coordinator = DevicesCoordinator(acc, entry.entry_id, device_ids=device_ids)

    await acc.async_check_auth()
    await coordinator.async_refresh()

    hass.data[DOMAIN][CONF_ACCOUNTS][acc.uid] = acc
    hass.data[DOMAIN]["coordinators"][coordinator.name] = coordinator
    hass.data[DOMAIN]["entry_coordinators"][entry.entry_id] = coordinator

    _async_remove_stale_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, SUPPORTED_DOMAINS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, SUPPORTED_DOMAINS
    )
    if not unload_ok:
        return False

    coordinator = hass.data[DOMAIN]["entry_coordinators"].pop(entry.entry_id, None)
    if coordinator is not None:
        hass.data[DOMAIN][CONF_ACCOUNTS].pop(coordinator.account.uid, None)
        hass.data[DOMAIN]["coordinators"].pop(coordinator.name, None)
    hass.data[DOMAIN].get("add_entities", {}).pop(entry.entry_id, None)

    return True
