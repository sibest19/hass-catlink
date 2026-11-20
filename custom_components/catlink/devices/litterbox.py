"""Litter box class for CatLink."""

import datetime
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.util import dt as dt_util

from ..const import _LOGGER
from ..helpers import as_int, format_api_error, mass_options
from ..models.additional_cfg import AdditionalDeviceConfig
from ..models.api.device import LitterDeviceInfo
from ..models.api.parse import parse_response
from .litter_device import LitterDevice

if TYPE_CHECKING:
    from ..modules.devices_coordinator import DevicesCoordinator


class LitterBox(LitterDevice):
    """Litter box class for CatLink."""

    def __init__(
        self,
        dat: dict,
        coordinator: "DevicesCoordinator",
        additional_config: AdditionalDeviceConfig | None = None,
    ) -> None:
        """Initialize the litter box."""
        super().__init__(dat, coordinator, additional_config)

    @property
    def modes(self) -> dict:
        """Return the modes."""
        return {
            "00": "auto",
            "01": "manual",
            "02": "time",
        }

    @property
    def actions(self) -> dict:
        """Return the actions."""
        # The app's clean, empty and cancel buttons; it never sends a pause.
        return {
            "01": "cleaning",
            "02": "empty",
            "06": "cancel",
        }

    @property
    def garbage_actions(self) -> dict:
        """Return the garbage actions."""
        return {
            "00": "change_bag",
            "01": "reset",
        }

    @property
    def box_full_levels(self) -> dict:
        """Return the box full sensitivity levels."""
        return {
            "LEVEL_01": "level_1",
            "LEVEL_02": "level_2",
            "LEVEL_03": "level_3",
            "LEVEL_04": "level_4",
        }

    @property
    def state(self) -> str:
        """Return the run state the app shows, from the clean/empty/bag status."""
        clean = self.detail.get("cleanStatus")
        empty = self.detail.get("emptyStatus")
        bag = as_int(self.detail.get("replaceGarbageBag"), 0)
        if clean == "01":
            return "cleaning"
        if empty == "01":
            return "emptying"
        if "02" in (clean, empty) or bag == 3:
            return "resetting"
        if bag:
            return "changing_bag"
        return "idle"

    @property
    def error(self) -> str:
        """Return the message the app shows on the device page."""
        if self._action_error:
            return self._action_error
        return (
            self.detail.get("currentMessage")
            or self.detail.get("currentError")
            or "Normal Operation"
        )

    @property
    def litter_remaining_days(self) -> int | None:
        """Return the litter remaining days, or None when not reported."""
        return as_int(self.detail.get("litterCountdown"))

    @property
    def knob_status(self) -> str:
        """Return the knob status."""
        try:
            knob_flab = (
                any(
                    "left_knob_abnormal" in e.get("errkey")
                    for e in self.detail.get("deviceErrorList", [])
                )
                if self.detail
                else False
            )
            return "Empty Mode" if knob_flab else "Cleaning Mode"
        except Exception as exc:
            _LOGGER.error("Got knob status failed: %s", exc)
            return "Unknown"

    @property
    def last_sync(self) -> datetime.datetime | None:
        """Return the last heartbeat time."""
        stamp = as_int(self.detail.get("lastHeartBeatTimestamp"))
        return dt_util.utc_from_timestamp(stamp / 1000) if stamp else None

    @property
    def garbage_tobe_status(self) -> str:
        """Return the waste bin status from the device error keys."""
        keys = {e.get("errkey") for e in self.detail.get("deviceErrorList") or []}
        # The app's full icon follows garbage_full_abnormal.
        if "garbage_full_abnormal" in keys:
            return "full"
        if "garbage_tobe_full_abnormal" in keys:
            return "almost_full"
        return "normal"

    @property
    def hass_sensor(self) -> dict:
        """Return the device sensors."""
        return {
            "state": {
                "class": SensorDeviceClass.ENUM,
                "options": ["idle", "cleaning", "emptying", "resetting", "changing_bag"],
                "state_attrs": self.state_attrs,
            },
            "error": {
                "state_attrs": self.error_attrs,
            },
            "last_log": {
                "state_attrs": self.last_log_attrs,
            },
            "garbage_tobe_status": {
                "class": SensorDeviceClass.ENUM,
                "options": ["normal", "almost_full", "full"],
            },
            "litter_weight": mass_options(self.coordinator.hass),
            "litter_remaining_days": {
                "class": SensorDeviceClass.DURATION,
                "unit": UnitOfTime.DAYS,
            },
            "total_clean_time": {
                "state_class": SensorStateClass.TOTAL_INCREASING,
            },
            "manual_clean_time": {
                "state_class": SensorStateClass.TOTAL_INCREASING,
            },
            "deodorant_countdown": {
                "class": SensorDeviceClass.DURATION,
                "unit": UnitOfTime.DAYS,
            },
            "knob_status": {
                "entity_category": EntityCategory.DIAGNOSTIC,
            },
            "last_sync": {
                "class": SensorDeviceClass.TIMESTAMP,
                "entity_category": EntityCategory.DIAGNOSTIC,
                "enabled_default": False,
            },
        }

    @property
    def hass_select(self) -> dict:
        """Return the device selects."""
        return {
            "mode": {
                "entity_category": EntityCategory.CONFIG,
                "options": list(self.modes.values()),
                "state_attrs": self.mode_attrs,
                "async_select": self.select_mode,
            },
            "action": {
                "options": list(self.actions.values()),
                "async_select": self.select_action,
                "delay_update": 5,
            },
            "garbage": {
                "options": list(self.garbage_actions.values()),
                "async_select": self.changeBag,
                "delay_update": 5,
            },
            "box_full_sensitivity": {
                "entity_category": EntityCategory.CONFIG,
                "options": list(self.box_full_levels.values()),
                "state_attrs": self.box_full_sensitivity_attrs,
                "async_select": self.select_box_full_sensitivity,
            },
        }

    def state_attrs(self) -> dict:
        """Return the state attributes."""
        return {
            **self._base_state_attrs(),
            "last_sync_time": datetime.datetime.fromtimestamp(
                as_int(self.detail.get("lastHeartBeatTimestamp"), 0) / 1000.0
            ).strftime("%Y-%m-%d %H:%M:%S")
            if as_int(self.detail.get("lastHeartBeatTimestamp"))
            else None,
            "box_full_sensitivity": self.detail.get("boxFullSensitivity"),
            "quiet_times": self.detail.get("quietTimes"),
        }

    def error_attrs(self) -> dict:
        """Return the error attributes."""
        try:
            return {
                "errors": self.detail.get("deviceErrorList"),
            }
        except Exception as exc:
            _LOGGER.error("Got error attributes failed: %s", exc)
            return {}

    @property
    def box_full_sensitivity(self) -> str | None:
        """Return the box full sensitivity."""
        sensitivity = self.detail.get("boxFullSensitivity", "")
        mapped_value = self.box_full_levels.get(sensitivity)
        if mapped_value:
            _LOGGER.debug(
                "Box full sensitivity mapped: %s -> %s", sensitivity, mapped_value
            )
            return mapped_value
        if sensitivity and isinstance(sensitivity, (str, int)):
            try:
                if isinstance(sensitivity, str) and sensitivity.isdigit():
                    level_key = f"LEVEL_{sensitivity.zfill(2)}"
                elif isinstance(sensitivity, int):
                    level_key = f"LEVEL_{str(sensitivity).zfill(2)}"
                else:
                    level_key = None
                if level_key:
                    mapped_value = self.box_full_levels.get(level_key)
                    if mapped_value:
                        _LOGGER.debug(
                            "Box full sensitivity mapped (converted): %s -> %s -> %s",
                            sensitivity,
                            level_key,
                            mapped_value,
                        )
                        return mapped_value
            except (ValueError, AttributeError):
                pass
        _LOGGER.warning(
            "Box full sensitivity raw value %r (type: %s) could not be mapped to known levels; valid values: %s",
            sensitivity,
            type(sensitivity).__name__,
            ", ".join(self.box_full_levels.keys()),
        )
        return None

    def box_full_sensitivity_attrs(self) -> dict:
        """Return the box full sensitivity attributes."""
        return {
            "raw_level": self.detail.get("boxFullSensitivity"),
        }

    async def update_logs(self) -> list:
        """Update the logs."""
        return await self._fetch_logs(
            "token/litterbox/stats/log/top5", "scooperLogTop5"
        )

    async def select_mode(self, mode, **kwargs) -> bool:
        """Select the device mode."""
        api = "token/litterbox/changeMode"
        mod = None
        for k, v in self.modes.items():
            if v == mode:
                mod = k
                break
        if mod is None:
            _LOGGER.warning("Select mode failed for %s in %s", mode, self.modes)
            return False
        pms = {
            "workModel": mod,
            "deviceId": self.id,
        }
        rdt = await self.account.request(api, pms, "POST")
        eno = rdt.get("returnCode", 0)
        if eno:
            err_msg = format_api_error(rdt)
            _LOGGER.error("Select mode failed: %s", err_msg)
            self._set_action_error(err_msg)
            return False
        await self.update_device_detail()
        _LOGGER.info("Select mode: %s", [rdt, pms])
        return rdt

    async def select_box_full_sensitivity(self, level, **kwargs) -> bool:
        """Select the box full sensitivity level."""
        api = "token/litterbox/boxFullSetting"
        lvl = None
        for k, v in self.box_full_levels.items():
            if v == level:
                lvl = k
                break
        if lvl is None:
            _LOGGER.warning(
                "Select box full sensitivity failed for %s in %s",
                level,
                self.box_full_levels,
            )
            return False
        pms = {
            "deviceId": self.id,
            "level": lvl,
        }
        rdt = await self.account.request(api, pms, "POST")
        eno = rdt.get("returnCode", 0)
        if eno:
            err_msg = format_api_error(rdt)
            _LOGGER.error("Select box full sensitivity failed: %s", err_msg)
            self._set_action_error(err_msg)
            return False
        await self.update_device_detail()
        _LOGGER.info("Select box full sensitivity: %s", [rdt, pms])
        return rdt

    async def update_device_detail(self) -> dict:
        """Update the device detail."""
        api = "token/litterbox/info"
        pms = {
            "deviceId": self.id,
        }
        rsp = None
        try:
            rsp = await self.account.request(api, pms)
            data = rsp.get("data", {})
            raw = data.get("deviceInfo")
            parsed = parse_response(data, "deviceInfo", LitterDeviceInfo)
            rdt = (
                parsed.model_dump(by_alias=True)
                if hasattr(parsed, "model_dump")
                else (parsed or {})
            )
            if not rdt and raw:
                rdt = raw
                _LOGGER.debug(
                    "Using raw deviceInfo for %s because model parsing failed",
                    self.name,
                )
        except (TypeError, ValueError) as exc:
            rdt = {}
            _LOGGER.error("Got device detail for %s failed: %s", self.name, exc)
        if not rdt:
            _LOGGER.warning("Got device detail for %s failed: %s", self.name, rsp)
        self.detail = rdt
        self._action_error = None
        self._handle_listeners()
        return rdt

    async def select_action(self, action, **kwargs) -> bool:
        """Select the device action."""
        api = "token/litterbox/actionCmd"
        val = None
        for k, v in self.actions.items():
            if v == action:
                val = k
                break
        if val is None:
            _LOGGER.warning("Select action failed for %s in %s", action, self.actions)
            return False
        pms = {
            "cmd": val,
            "deviceId": self.id,
        }
        rdt = await self.account.request(api, pms, "POST")
        eno = rdt.get("returnCode", 0)
        if eno:
            err_msg = format_api_error(rdt)
            _LOGGER.error("Select action failed: %s", err_msg)
            self._set_action_error(err_msg)
            return False
        await self.update_device_detail()
        _LOGGER.info("Select action: %s", [rdt, pms])
        return rdt

    async def changeBag(self, mode, **kwargs) -> bool:
        """Change the garbage bag."""
        api = "token/litterbox/replaceGarbageBagCmd"
        pms = {
            "enable": mode == self.garbage_actions["00"],
            "deviceId": self.id,
        }
        rdt = await self.account.request(api, pms, "POST")
        eno = rdt.get("returnCode", 0)
        if eno:
            err_msg = format_api_error(rdt)
            _LOGGER.error("Change bag failed: %s", err_msg)
            self._set_action_error(err_msg)
            return False
        await self.update_device_detail()
        _LOGGER.info("Change bag: %s", [rdt, pms])
        return rdt

    async def reset_consumable(self, api: str) -> bool:
        """Reset a consumable (litter or deodorant) counter."""
        pms = {"deviceId": self.id}
        rdt = await self.account.request(api, pms, "POST")
        eno = rdt.get("returnCode", 0)
        if eno:
            err_msg = format_api_error(rdt)
            _LOGGER.error("Reset consumable %s failed: %s", api, err_msg)
            self._set_action_error(err_msg)
            return False
        await self.update_device_detail()
        _LOGGER.info("Reset consumable %s: %s", api, [rdt, pms])
        return rdt

    # The endpoints the app's 599 settings and cartridge screens use.
    async def async_reset_litter(self) -> bool:
        """Reset the litter counter."""
        return await self.reset_consumable("token/litterbox/litter/time/reset")

    async def async_reset_deodorant(self) -> bool:
        """Reset the deodorant counter."""
        return await self.reset_consumable("token/litterbox/deodorant/reset")

    @property
    def hass_button(self) -> dict:
        """Return the device buttons."""
        return {
            "reset_litter": {
                "entity_category": EntityCategory.CONFIG,
                "async_press": self.async_reset_litter,
            },
            "reset_deodorant": {
                "entity_category": EntityCategory.CONFIG,
                "async_press": self.async_reset_deodorant,
            },
        }
