"""PurePro device module for CatLink integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime

from ..const import _LOGGER
from ..helpers import format_api_error
from ..models.additional_cfg import AdditionalDeviceConfig
from .base import Device
from .mixins.logs import LogsMixin

if TYPE_CHECKING:
    from ..modules.devices_coordinator import DevicesCoordinator

API_PUREPRO_DETAIL = "token/device/purepro/detail"
API_PUREPRO_RUN_MODE = "token/device/purepro/runMode"
API_PUREPRO_STATS_CATS = "token/device/purepro/stats/log/top5"


class PureProDevice(LogsMixin, Device):
    """PurePro device class for CatLink integration."""

    def __init__(
        self,
        dat: dict,
        coordinator: DevicesCoordinator,
        additional_config: AdditionalDeviceConfig | None = None,
    ) -> None:
        """Initialize the device."""
        super().__init__(dat, coordinator, additional_config)

    async def async_init(self) -> None:
        """Initialize the device."""
        await super().async_init()
        await self._async_init_logs()

    @property
    def modes(self) -> dict:
        """Return the modes of the device."""
        return {
            "CONTINUOUS_SPRING": "flowing",
            "INTERMITTENT_SPRING": "eco",
            "INDUCTION_SPRING": "smart",
        }

    @property
    def online(self) -> bool:
        """Return the online status."""
        return (
            self.detail.get("online")
            or self.data.get("online")
            or self.detail.get("onlineStatus") in (True, "ONLINE")
            or self.data.get("onlineStatus") in (True, "ONLINE")
            or False
        )

    @property
    def mode(self) -> str | None:
        """Return the current run mode."""
        return self.modes.get(self.detail.get("runMode"))

    def mode_attrs(self) -> dict:
        """Return the mode attributes."""
        return {"run_mode": self.detail.get("runMode")}

    @property
    def water_level(self) -> str | None:
        """Return the water level text the app shows."""
        return self.detail.get("waterLevelStrDescription")

    @property
    def filter_life(self) -> int | None:
        """Return the filter days left."""
        return self.detail.get("filterElementTimeCountdown")

    @property
    def temperature(self) -> float | None:
        """Return the heater temperature, shown by the app only with a heater bound."""
        value = self.detail.get("temperatureOfHeater")
        try:
            return float(value) if value else None
        except ValueError:
            return None

    @property
    def light_active(self) -> bool:
        """Return whether the light is on."""
        return self.detail.get("pureLightStatus") == "OPEN"

    @property
    def state(self) -> str | None:
        """Return the run mode, the state the app's fountain page shows."""
        return self.mode

    def state_attrs(self) -> dict:
        """Return the state attributes of the device."""
        return {
            "run_mode": self.detail.get("runMode"),
            "water_level": self.water_level,
            "water_level_num": self.detail.get("waterLevelNum"),
            "filter_life": self.filter_life,
            "temperature": self.temperature,
            "light_active": self.light_active,
        }

    @property
    def last_log(self) -> str | None:
        """Return the last log entry formatted for the fountain."""
        log = self._last_log
        if not log:
            return "No activity recorded"
        # The event field usually contains "Cat drank water, X seconds"
        res = f"{log.get('time')} {log.get('event')}".strip()
        _LOGGER.debug("PurePro %s last_log: %s", self.name, res)
        return res

    @property
    def hass_sensor(self) -> dict:
        """Return the device sensors."""
        return {
            "state": {
                "class": SensorDeviceClass.ENUM,
                "options": list(self.modes.values()),
                "state_attrs": self.state_attrs,
            },
            "last_log": {
                "state_attrs": self.last_log_attrs,
            },
            "water_level": {},
            "filter_life": {
                "class": SensorDeviceClass.DURATION,
                "unit": UnitOfTime.DAYS,
            },
            "temperature": {
                "translation_key": None,
                "class": SensorDeviceClass.TEMPERATURE,
                "unit": UnitOfTemperature.CELSIUS,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        }

    @property
    def hass_binary_sensor(self) -> dict:
        """Return the device binary sensors."""
        return {
            "online": {
                "translation_key": None,
                "class": BinarySensorDeviceClass.CONNECTIVITY,
                "entity_category": EntityCategory.DIAGNOSTIC,
            },
            "light_active": {},
        }

    @property
    def hass_select(self) -> dict:
        """Return the device selects."""
        return {
            "mode": {
                "options": list(self.modes.values()),
                "state_attrs": self.mode_attrs,
                "async_select": self.select_mode,
            },
        }

    async def update_device_detail(self) -> dict:
        """Update device detail."""
        pms = {"deviceId": self.id}
        rsp = None
        try:
            rsp = await self.account.request(API_PUREPRO_DETAIL, pms)
            data = rsp.get("data") or {}
            
            # PurePro API might return the detail directly in 'data' 
            # or wrapped in 'deviceInfo' like generic endpoints.
            rdt = data.get("deviceInfo") or data
            
        except (TypeError, ValueError) as exc:
            rdt = {}
            _LOGGER.error("Got device detail for %s failed: %s", self.name, exc)
        
        if not rdt:
            _LOGGER.warning("Got device detail for %s failed: %s", self.name, rsp)
        else:
            _LOGGER.debug("Got device detail for %s: %s", self.name, rdt)
            
        self.detail = rdt
        self._action_error = None
        self._handle_listeners()
        return rdt

    async def select_mode(self, mode, **kwargs) -> bool:
        """Select the device mode."""
        mod = None
        for k, v in self.modes.items():
            if v == mode:
                mod = k
                break
        if mod is None:
            _LOGGER.warning("Select mode failed for %s in %s", mode, self.modes)
            return False
        
        pms = {
            "runMode": mod,
            "deviceId": self.id,
        }
        rdt = await self.account.request(API_PUREPRO_RUN_MODE, pms, "POST")
        eno = rdt.get("returnCode", 0)
        if eno:
            err_msg = format_api_error(rdt)
            _LOGGER.error("Select mode failed: %s", err_msg)
            self._set_action_error(err_msg)
            return False
            
        await self.update_device_detail()
        _LOGGER.info("Select mode: %s", [rdt, pms])
        return True

    async def update_logs(self) -> list:
        """Update device logs."""
        return await self._fetch_logs(API_PUREPRO_STATS_CATS, "pureLogTop5")
