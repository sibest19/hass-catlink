"""Cat device class for CatLink integration."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfMass
from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.catlink.const import DOMAIN
from custom_components.catlink.devices.base import Device

if TYPE_CHECKING:
    from custom_components.catlink.modules.devices_coordinator import DevicesCoordinator


# As in the app's GenderUtils.
GENDER_LABELS: dict[int, str] = {
    1: "male",
    2: "neutered_male",
    3: "female",
    4: "neutered_female",
}

# The app's weightUnitTip values, which follow the account's unit setting.
MASS_UNITS: dict[str, str] = {
    "kg": UnitOfMass.KILOGRAMS,
    "g": UnitOfMass.GRAMS,
    "lb": UnitOfMass.POUNDS,
    "oz": UnitOfMass.OUNCES,
}


class CatDevice(Device):
    """Cat device class for CatLink integration."""

    def __init__(
        self,
        dat: dict,
        coordinator: DevicesCoordinator,
        additional_config: Any | None = None,
    ) -> None:
        """Initialize the cat device."""
        super().__init__(dat, coordinator, additional_config)

    async def async_init(self) -> None:
        """Initialize the device."""
        self.detail = self.data

    def update_data(self, dat: dict) -> None:
        """Update device data."""
        super().update_data(dat)
        self.detail = dat

    async def update_device_detail(self) -> dict:
        """Update device detail (cats use list payload)."""
        self.detail = self.data
        self._handle_listeners()
        return self.detail

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device card details: a cat has no MAC or firmware."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.type}_{self.mac}")},
            name=self.name,
            manufacturer="CatLink",
            model="Cat",
        )

    @property
    def pet_id(self) -> str | None:
        """Return the pet id."""
        return self.data.get("pet_id") or self.data.get("id")

    @property
    def weight(self) -> float | None:
        """Return the measured weight shown on the app's weight card."""
        return self._summary_section("weightsInfo").get("currentWeight")

    @property
    def age_years(self) -> int | None:
        """Return the pet age in years."""
        return self.data.get("age")

    @property
    def age_months(self) -> int | None:
        """Return the pet age in months."""
        return self.data.get("month")

    @property
    def breed(self) -> str | None:
        """Return the pet breed."""
        return self.data.get("breedName")

    @property
    def gender_label(self) -> str | None:
        """Return the pet gender label."""
        gender = self.data.get("gender")
        if isinstance(gender, str) and gender.isdigit():
            gender = int(gender)
        if isinstance(gender, int):
            return GENDER_LABELS.get(gender)
        return None

    @property
    def birthday(self) -> date | None:
        """Return the pet birthday as ISO date, as the app's edit page shows it."""
        # Not the cats-list timestamp: it is midnight China time, a day off in UTC.
        value = (self.data.get("pet_info") or {}).get("birthdayString")
        return date.fromisoformat(value) if value else None

    @property
    def avatar_url(self) -> str | None:
        """Return the pet avatar URL."""
        return self.data.get("avatar")

    @property
    def avatar(self) -> None:
        """Return the avatar state."""
        return None

    def _summary(self) -> dict:
        return self.data.get("summary_simple") or {}

    def _summary_section(self, name: str) -> dict:
        summary = self._summary()
        return summary.get(name) or {}

    def _mass_unit(self, section: str) -> str | None:
        return MASS_UNITS.get(self._summary_section(section).get("weightUnitTip"))

    @staticmethod
    def _count(value) -> int | None:
        return None if value is None else int(value)

    @property
    def status(self) -> str | None:
        """Return the pet health status description."""
        return (self.data.get("health_status") or {}).get("statusDescription")

    @property
    def toilet_times(self) -> int | None:
        """Return the toilet visits: poo, pee and unknown, as the app adds them."""
        toilet = self._summary_section("toiletInfo")
        counts = [
            toilet.get(k)
            for k in ("stoolFrequency", "urinateFrequency", "toiletFrequency")
        ]
        if all(c is None for c in counts):
            return None
        return int(sum(c or 0 for c in counts))

    @property
    def pee_times(self) -> int | None:
        """Return the number of pee events."""
        return self._count(self._summary_section("toiletInfo").get("urinateFrequency"))

    @property
    def poo_times(self) -> int | None:
        """Return the number of poo events."""
        return self._count(self._summary_section("toiletInfo").get("stoolFrequency"))

    @property
    def drink_times(self) -> int | None:
        """Return the drink times."""
        return self._count(self._summary_section("drinkInfo").get("drinkCount"))

    @property
    def diet_intakes(self) -> float | None:
        """Return the amount eaten today."""
        return self._summary_section("eatInfo").get("eatTotalAmount")

    def cat_attrs(self) -> dict:
        """Return the cat attributes."""
        return {
            "pet_id": self.pet_id,
            "breed": self.breed,
            "gender": self.gender_label,
            "birthday": self.birthday,
            "weight": self.weight,
            "age_years": self.age_years,
            "age_months": self.age_months,
            "toilet_times": self.toilet_times,
            "pee_times": self.pee_times,
            "poo_times": self.poo_times,
            "drink_times": self.drink_times,
            "diet_intakes": self.diet_intakes,
        }

    @property
    def hass_sensor(self) -> dict:
        """Return cat sensors."""
        return {
            "status": {
                "state_attrs": self.cat_attrs,
            },
            "weight": {
                "translation_key": None,
                "class": SensorDeviceClass.WEIGHT,
                "state_class": SensorStateClass.MEASUREMENT,
                "unit": self._mass_unit("weightsInfo"),
            },
            "age_years": {},
            "age_months": {},
            "gender_label": {
                "class": SensorDeviceClass.ENUM,
                "options": list(GENDER_LABELS.values()),
            },
            "breed": {},
            "birthday": {
                "class": SensorDeviceClass.DATE,
            },
            "avatar": {
                "entity_picture": self.avatar_url,
            },
            "toilet_times": {
                "state_class": SensorStateClass.TOTAL_INCREASING,
            },
            "pee_times": {
                "state_class": SensorStateClass.TOTAL_INCREASING,
            },
            "poo_times": {
                "state_class": SensorStateClass.TOTAL_INCREASING,
            },
            "drink_times": {
                "state_class": SensorStateClass.TOTAL_INCREASING,
            },
            "diet_intakes": {
                "state_class": SensorStateClass.MEASUREMENT,
                "class": SensorDeviceClass.WEIGHT,
                "unit": self._mass_unit("eatInfo"),
            },
        }

    @property
    def hass_binary_sensor(self) -> dict:
        """Return empty binary sensors for cats."""
        return {}

    @property
    def hass_switch(self) -> dict:
        """Return empty switches for cats."""
        return {}

    @property
    def hass_button(self) -> dict:
        """Return empty buttons for cats."""
        return {}

    @property
    def hass_select(self) -> dict:
        """Return empty selects for cats."""
        return {}
