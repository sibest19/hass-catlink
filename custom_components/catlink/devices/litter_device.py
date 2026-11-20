"""Litter device base class for LitterBox and ScooperDevice."""

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import EntityCategory

from ..const import _LOGGER
from ..helpers import as_int
from ..models.additional_cfg import AdditionalDeviceConfig
from .base import Device
from .mixins.logs import LogsMixin

if TYPE_CHECKING:
    from ..modules.devices_coordinator import DevicesCoordinator


class LitterDevice(LogsMixin, Device):
    """Base class for litter-related devices (LitterBox, ScooperDevice)."""

    def __init__(
        self,
        dat: dict,
        coordinator: "DevicesCoordinator",
        additional_config: AdditionalDeviceConfig | None = None,
    ) -> None:
        """Initialize the litter device."""
        super().__init__(dat, coordinator, additional_config)
        self.empty_litter_box_weight = self.additional_config.empty_weight or 0.0

    @property
    def state(self) -> str | None:
        """Return the device state, None for a code the app does not know."""
        return {"00": "idle", "01": "running", "02": "need_reset"}.get(
            f"{self.detail.get('workStatus', '')}".strip()
        )

    @property
    def litter_weight(self) -> float | None:
        """Return the litter weight, None when the device sends a null weight."""
        litter_weight = 0.0
        try:
            cat_litter_weight = self.detail.get(
                "catLitterWeight", self.empty_litter_box_weight
            )
            if cat_litter_weight is None:
                return None
            litter_weight = cat_litter_weight - self.empty_litter_box_weight
            if litter_weight == 0.0:
                _LOGGER.debug(
                    "litter_weight is 0: catLitterWeight=%r, empty_litter_box_weight=%r (detail keys: %s)",
                    cat_litter_weight,
                    self.empty_litter_box_weight,
                    list(self.detail.keys()) if self.detail else "none",
                )
        except Exception as exc:
            _LOGGER.error("Got litter weight failed: %s", exc)
        return litter_weight

    @property
    def litter_remaining_days(self) -> str | int:
        """Return the litter remaining days."""
        try:
            return self.detail.get("litterCountdown", "unknown")
        except Exception as exc:
            _LOGGER.error("Get litter remaining days failed: %s", exc)
            return "unknown"

    @property
    def total_clean_time(self) -> int:
        """Return the auto, manual and scheduled cleans the app counts separately."""
        return sum(
            as_int(self.detail.get(k), 0)
            for k in ("inductionTimes", "manualTimes", "timerTimes")
        )

    @property
    def manual_clean_time(self) -> int:
        """Return the manual clean time."""
        return as_int(self.detail.get("manualTimes"), 0)

    @property
    def deodorant_countdown(self) -> int | None:
        """Return the deodorant countdown, or None when the device omits it."""
        return as_int(self.detail.get("deodorantCountdown"))

    @property
    def online(self) -> bool:
        """Return the online status."""
        return bool(self.detail.get("online"))

    @property
    def hass_binary_sensor(self) -> dict:
        """Return the device binary sensors."""
        return {
            "online": {
                "translation_key": None,
                "class": BinarySensorDeviceClass.CONNECTIVITY,
                "entity_category": EntityCategory.DIAGNOSTIC,
            },
        }

    async def async_init(self) -> None:
        """Initialize the device."""
        await super().async_init()
        await self._async_init_logs()

    def _base_state_attrs(self) -> dict:
        """Return base state attributes shared by LitterBox and ScooperDevice."""
        return {
            "mac": self.mac,
            "work_status": self.detail.get("workStatus"),
            "alarm_status": self.detail.get("alarmStatus"),
            "weight": self.detail.get("weight"),
            "litter_weight_kg": self.detail.get("catLitterWeight"),
            "total_clean_times": self.total_clean_time,
            "manual_clean_times": self.detail.get("manualTimes"),
            "key_lock": self.detail.get("keyLock"),
            "safe_time": self.detail.get("safeTime"),
            "pave_second": self.detail.get("catLitterPaveSecond"),
            "deodorant_countdown": self.detail.get("deodorantCountdown"),
            "litter_countdown": self.detail.get("litterCountdown"),
        }
