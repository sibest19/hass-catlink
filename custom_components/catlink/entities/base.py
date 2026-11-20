"""The component."""

import asyncio

from homeassistant.components import persistent_notification
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from ..const import _LOGGER, DOMAIN
from ..devices.base import Device


class CatlinkEntity(CoordinatorEntity):
    """CatlinkEntity."""

    def __init__(self, name, device: Device, option=None) -> None:
        """Initialize the entity."""
        self.coordinator = device.coordinator
        CoordinatorEntity.__init__(self, self.coordinator)
        self.account = self.coordinator.account
        self._name = name
        self._device = device
        self._option = option or {}
        # has_entity_name lets Home Assistant compose "<device> <entity>" itself
        # and take the entity half from entity.<domain>.<key>.name in the
        # translations.
        #
        # _attr_name is deliberately never set: Entity._name_internal returns it
        # immediately if the attribute exists, short-circuiting the translation
        # lookup. Every entity key must therefore have a name in the translation
        # files - test_every_entity_key_is_translated enforces that.
        self._attr_has_entity_name = True
        self._attr_device_id = f"{device.type}_{device.mac}"
        self._attr_unique_id = f"{self._attr_device_id}-{name}"
        # entity_id is left to Home Assistant, which builds it from the area,
        # device and entity names.
        #
        # The entity key doubles as the translation key, so names, state
        # translations and icons live under entity.<domain>.<key> in
        # translations/*.json and icons.json. An option "translation_key" of None leaves the entity
        # named after its device class.
        self._attr_translation_key = self._option.get("translation_key", slugify(name))
        self._attr_device_class = self._option.get("class")
        self._attr_entity_category = self._option.get("entity_category")
        self._attr_entity_registry_enabled_default = self._option.get(
            "enabled_default", True
        )
        self._attr_options = self._option.get("options")
        self._attr_native_value = None
        self._attr_native_unit_of_measurement = self._option.get("unit")
        self._attr_suggested_unit_of_measurement = self._option.get("suggested_unit")
        self._attr_suggested_display_precision = self._option.get("precision")
        self._attr_state_class = self._option.get("state_class")
        entity_picture = self._option.get("entity_picture")
        if callable(entity_picture):
            self._attr_entity_picture = entity_picture()
        elif entity_picture:
            self._attr_entity_picture = entity_picture
        self._attr_device_info = device.device_info

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        # Keyed by unique_id: entity_id can change while the entity lives.
        self._device.listeners[self.unique_id] = self._handle_coordinator_update
        self._handle_coordinator_update()

    async def async_will_remove_from_hass(self) -> None:
        """Stop device updates from reaching a removed entity."""
        self._device.listeners.pop(self.unique_id, None)
        await super().async_will_remove_from_hass()

    def _handle_coordinator_update(self):
        self.update()
        self.async_write_ha_state()

    async def _async_after_action(self, success: bool, delay: float | None = None) -> None:
        """Run after an action: write state, optional delay, then coordinator refresh."""
        if success:
            self.async_write_ha_state()
            if delay is not None:
                await asyncio.sleep(delay)
            self._handle_coordinator_update()

    def update(self) -> None:
        """Update the entity."""
        if hasattr(self._device, self._name):
            # Each platform reads its value from here (native_value,
            # current_option, is_on), so Home Assistant's unit, device class
            # and enum handling applies.
            self._attr_native_value = getattr(self._device, self._name)
            _LOGGER.debug(
                "Entity update: %s",
                [self.entity_id, self._name, self._attr_native_value],
            )
        entity_picture = self._option.get("entity_picture")
        if callable(entity_picture):
            self._attr_entity_picture = entity_picture()

        fun = self._option.get("state_attrs")
        if callable(fun):
            self._attr_extra_state_attributes = fun()

    async def async_request_api(self, api, params=None, method="GET", **kwargs) -> dict:
        """Request API."""
        throw = kwargs.pop("throw", None)
        rdt = await self.account.request(api, params, method, **kwargs)
        if throw:
            persistent_notification.async_create(
                self.hass,
                f"{rdt}",
                f"Request: {api}",
                f"{DOMAIN}-request",
            )
        return rdt
