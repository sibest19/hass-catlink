"""C08 device module for CatLink integration."""

from __future__ import annotations

import asyncio
from functools import partial
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfMass, UnitOfTime
from homeassistant.util import dt as dt_util

from custom_components.catlink.const import _LOGGER
from custom_components.catlink.devices.litter_device import LitterDevice
from custom_components.catlink.helpers import as_int, format_api_error
from custom_components.catlink.models.additional_cfg import AdditionalDeviceConfig
from custom_components.catlink.models.api.device import C08DeviceInfo
from custom_components.catlink.models.api.parse import parse_response

if TYPE_CHECKING:
    from custom_components.catlink.modules.devices_coordinator import DevicesCoordinator

API_LITTERBOX_C08_INFO = "token/litterbox/info/c08"
API_LITTERBOX_ACTION_COMMAND_V3 = "token/litterbox/actionCmd/v3"
API_LITTERBOX_CHANGE_MODE = "token/litterbox/changeMode"
API_LITTERBOX_PET_WEIGHT_AUTO_UPDATE = "token/litterbox/pet/weight/autoUpdate"
API_LITTERBOX_CAT_LITTER_SETTING = "token/litterbox/catLitterSetting"
API_LITTERBOX_DEEP_CLEAN_AUTO_BURIAL = "token/litterbox/deepClean/autoBurial"
API_LITTERBOX_QUIET_MODE = "token/litterbox/quietMode"
API_LITTERBOX_DEEP_CLEAN_CONTINUOUS_CLEANING = (
    "token/litterbox/deepClean/continuousCleaning"
)
API_LITTERBOX_KITTY_MODEL_SWITCH = "token/litterbox/kittyModelSwitch"
API_LITTERBOX_KEY_LOCK = "token/litterbox/keyLock"
API_LITTERBOX_INDICATOR_LIGHT_SETTING = "token/litterbox/indicatorLightSetting"
API_LITTERBOX_KEYPAD_TONE = "token/litterbox/keypadTone"
API_LITTERBOX_SAFE_TIME_SETTING = "token/litterbox/safeTimeSetting"
API_LITTERBOX_NOTICE_CONFIG_SET = "token/litterbox/noticeConfig/set"
API_LITTERBOX_NOTICE_CONFIG_LIST_C08 = "token/litterbox/noticeConfig/list/c08"
API_LITTERBOX_STATS_DATA_COMPARE_V2 = "token/litterbox/stats/data/compare/v2"
API_LITTERBOX_STATS_CATS = "token/litterbox/stats/cats"
API_LITTERBOX_C08_WIFI_INFO = "token/litterbox/wifi/info"

API_LITTERBOX_TODAY_CLEAN_TIMES = "token/litterbox/todayCleanTimes"
API_LITTERBOX_PET_TODAY_COUNTS = "token/litterbox/petTodayCounts"
API_LITTERBOX_LOGS = "token/litterbox/stats/log/top5"
API_LITTERBOX_LOGS_RESPONSE_KEY = "scooperLogTop5"


NOTICE_ITEMS: dict[str, tuple[str, str]] = {
    "cat_came": ("LITTERBOX_599_CAT_CAME", "Cat came"),
    "box_full": ("LITTERBOX_599_BOX_FULL", "Box full"),
    "replace_garbage_bag": ("REPLACE_GARBAGE_BAG", "Replace garbage bag"),
    "wash_scooper": ("WASH_SCOOPER", "Wash scooper"),
    "replace_deodorant": ("REPLACE_DEODORANT", "Replace deodorant"),
    "litter_not_enough": ("LITTERBOX_599_CAT_LITTER_NOT_ENOUGH", "Litter not enough"),
    "sandbox_not_enough": ("LITTERBOX_599_SANDBOX_NOT_ENOUGHT", "Sandbox not enough"),
    "anti_pinch": ("LITTERBOX_599_ANTI_PINCH", "Anti pinch"),
    "firmware_updated": ("LITTERBOX_599_FIRMWARE_UPDATED", "Firmware updated"),
}


class C08Device(LitterDevice):
    """C08 litter box device class."""

    def __init__(
        self,
        dat: dict,
        coordinator: DevicesCoordinator,
        additional_config: AdditionalDeviceConfig | None = None,
    ) -> None:
        """Initialize the device."""
        super().__init__(dat, coordinator, additional_config)
        self._device_stats: dict | None = None
        self._pet_stats: list | None = None
        self._wifi_info: dict | None = None
        self._notice_configs: list | None = None
        self._notice_config_map: dict[str, bool] = {}
        self._today_clean_times: int | None = None
        self._today_toilet_count: int | None = None

    def __getattr__(self, name: str):
        """Return notice switch state for dynamic notice attributes."""
        if name.startswith("notice_"):
            slug = name.removeprefix("notice_")
            if slug in NOTICE_ITEMS:
                item_code = NOTICE_ITEMS[slug][0]
                return bool(self._notice_config_map.get(item_code))
        raise AttributeError(
            f"{self.__class__.__name__} object has no attribute {name}"
        )

    @property
    def modes(self) -> dict:
        """Return the modes of the device."""
        return {
            "00": "auto",
            "01": "manual",
            "02": "scheduled",
        }

    @property
    def state(self) -> str:
        """Return the run state the app shows, from finalStatus."""
        final = self.detail.get("finalStatus") or ""
        if final == "CLEAN_RUN":
            return "cleaning"
        if final == "PAVE_RUN":
            return "leveling"
        if final == "EMPTY_RUN":
            return "emptying"
        if final.endswith("_PAUSE"):
            return "paused"
        if final.endswith("_CANCEL"):
            return "cancelling"
        return "idle"

    @property
    def action(self) -> str | None:
        """Return the running action, from finalStatus as the app shows it."""
        return {
            "CLEAN_RUN": "clean_start",
            "CLEAN_PAUSE": "clean_pause",
            "CLEAN_CANCEL": "clean_cancel",
            "PAVE_RUN": "pave_start",
            "PAVE_PAUSE": "pave_pause",
        }.get(self.detail.get("finalStatus"))

    @property
    def litter_types(self) -> dict:
        """Return the litter types."""
        return {
            "00": "bentonite",
            "02": "mixed",
        }

    @property
    def safe_time_options(self) -> dict:
        """Return safe time options."""
        return {
            "1": "min_1",
            "3": "min_3",
            "5": "min_5",
            "7": "min_7",
            "10": "min_10",
            "15": "min_15",
            "30": "min_30",
        }

    @property
    def litter_type(self) -> str | None:
        """Return the current litter type."""
        raw = self.detail.get("litterType")
        if raw is None:
            return None
        return self.litter_types.get(f"{raw}".zfill(2), f"{raw}")

    @property
    def safe_time(self) -> str | None:
        """Return the safe time setting."""
        raw = self.detail.get("safeTime")
        if raw is None:
            return None
        return self.safe_time_options.get(f"{raw}", f"{raw}")

    @property
    def auto_burial(self) -> bool:
        """Return the auto burial setting."""
        return self._bool_value(self.detail.get("autoBurial"))

    @property
    def continuous_cleaning(self) -> bool:
        """Return the continuous cleaning setting."""
        return self._bool_value(self.detail.get("continuousCleaning"))

    @property
    def quiet_mode(self) -> bool:
        """Return the quiet mode setting."""
        quiet_enable = self.detail.get("quietEnable")
        if quiet_enable is not None:
            return self._bool_value(quiet_enable)
        return bool(self.detail.get("quietTimes"))

    @property
    def child_lock(self) -> bool:
        """Return the child lock setting."""
        return self._string_flag(
            self.detail.get("keyLock"), true_values={"01", "LOCKED", "ON"}
        )

    @property
    def indicator_light(self) -> bool:
        """Return the indicator light setting."""
        return self._string_flag(
            self.detail.get("indicatorLight"), true_values={"ALWAYS_OPEN", "01", "ON"}
        )

    @property
    def keypad_tone(self) -> bool:
        """Return the keypad tone setting."""
        return self._string_flag(
            self.detail.get("paneltone"), true_values={"01", "ENABLED", "ON"}
        )

    @property
    def auto_pet_weight_update(self) -> bool:
        """Return the auto pet weight update setting."""
        return self._bool_value(self.detail.get("autoUpdatePetWeight"))

    @property
    def kitty_model(self) -> bool:
        """Return the kitty model setting."""
        return self._bool_value(self.detail.get("kittenModel"))

    @property
    def error(self) -> str:
        """Return the device error."""
        if self._action_error:
            return self._action_error
        # The app's red banner, then its warning banner.
        errors = self.detail.get("deviceErrorList") or []
        warn = self.detail.get("deviceWarn") or {}
        return (
            (errors[0].get("errDesc") if errors else None)
            or warn.get("errDesc")
            or "Normal Operation"
        )

    @property
    def hass_sensor(self) -> dict:
        """Return the device sensors."""
        return {
            "state": {
                "class": SensorDeviceClass.ENUM,
                "options": ["idle", "cleaning", "leveling", "emptying", "paused", "cancelling"],
                "state_attrs": self.state_attrs,
            },
            "error": {
                "state_attrs": self.error_attrs,
            },
            "last_log": {
                "state_attrs": self.last_log_attrs,
            },
            "litter_weight": {
                "class": SensorDeviceClass.WEIGHT,
                "unit": UnitOfMass.KILOGRAMS,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            "litter_remaining_days": {
                "class": SensorDeviceClass.DURATION,
                "unit": UnitOfTime.DAYS,
            },
            "total_clean_time": {
                "state_class": SensorStateClass.TOTAL_INCREASING,
                "translation_key": "cleanings_today",
            },
            "manual_clean_time": {
                "state_class": SensorStateClass.TOTAL_INCREASING,
            },
            "deodorant_countdown": {
                "class": SensorDeviceClass.DURATION,
                "unit": UnitOfTime.DAYS,
            },
            "wifi_rssi": {
                "entity_category": EntityCategory.DIAGNOSTIC,
            },
            "wifi_ssid": {
                "entity_category": EntityCategory.DIAGNOSTIC,
                "enabled_default": False,
            },
            "stats_times": {
                "state_class": SensorStateClass.TOTAL_INCREASING,
                "translation_key": "visits_today",
            },
            "stats_weight_avg": {},
            "stats_duration_avg": {},
            "notice_config_count": {
                "entity_category": EntityCategory.DIAGNOSTIC,
                "enabled_default": False,
            },
            "pet_stats_count": {
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
                "options": list(self._action_options()),
                "async_select": self.select_action,
                "delay_update": 5,
            },
            "litter_type": {
                "entity_category": EntityCategory.CONFIG,
                "options": list(self.litter_types.values()),
                "async_select": self.select_litter_type,
            },
            "safe_time": {
                "entity_category": EntityCategory.CONFIG,
                "options": list(self.safe_time_options.values()),
                "async_select": self.select_safe_time,
            },
        }

    @property
    def hass_switch(self) -> dict:
        """Return the device switches."""
        switches = {
            "quiet_mode": {
                "async_turn_on": partial(self.async_set_quiet_mode, True),
                "async_turn_off": partial(self.async_set_quiet_mode, False),
            },
            "auto_burial": {
                "async_turn_on": partial(self.async_set_auto_burial, True),
                "async_turn_off": partial(self.async_set_auto_burial, False),
            },
            "continuous_cleaning": {
                "async_turn_on": partial(self.async_set_continuous_cleaning, True),
                "async_turn_off": partial(self.async_set_continuous_cleaning, False),
            },
            "child_lock": {
                "async_turn_on": partial(self.async_set_child_lock, True),
                "async_turn_off": partial(self.async_set_child_lock, False),
            },
            "indicator_light": {
                "async_turn_on": partial(self.async_set_indicator_light, True),
                "async_turn_off": partial(self.async_set_indicator_light, False),
            },
            "keypad_tone": {
                "async_turn_on": partial(self.async_set_keypad_tone, True),
                "async_turn_off": partial(self.async_set_keypad_tone, False),
            },
            "auto_pet_weight_update": {
                "async_turn_on": partial(self.async_set_auto_pet_weight_update, True),
                "async_turn_off": partial(self.async_set_auto_pet_weight_update, False),
            },
            "kitty_model": {
                "async_turn_on": partial(self.async_set_kitty_model, True),
                "async_turn_off": partial(self.async_set_kitty_model, False),
            },
        }
        for slug, (item_code, _label) in NOTICE_ITEMS.items():
            switches[f"notice_{slug}"] = {
                "async_turn_on": partial(self.async_set_notice, item_code, True),
                "async_turn_off": partial(self.async_set_notice, item_code, False),
                # The app has no row for these two.
                "enabled_default": slug
                not in ("litter_not_enough", "sandbox_not_enough"),
            }
        for switch in switches.values():
            switch["entity_category"] = EntityCategory.CONFIG
        return switches

    def state_attrs(self) -> dict:
        """Return the state attributes."""
        return {
            **self._base_state_attrs(),
            "quiet_times": self.detail.get("quietTimes"),
            "auto_burial": self.auto_burial,
            "continuous_cleaning": self.continuous_cleaning,
            "indicator_light": self.detail.get("indicatorLight"),
            "panel_tone": self.detail.get("paneltone"),
            "auto_update_pet_weight": self.detail.get("autoUpdatePetWeight"),
            "kitten_model": self.detail.get("kittenModel"),
            "litter_type": self.detail.get("litterType"),
            "box_full_sensitivity": self.detail.get("boxFullSensitivity"),
            "garbage_status": self.detail.get("garbageStatus"),
            "wifi_info": self._wifi_info or {},
            "notice_configs": self._notice_configs or [],
            "device_stats": self._device_stats or {},
            "pet_stats": self._pet_stats or [],
        }

    def error_attrs(self) -> dict:
        """Return the error attributes."""
        return {
            "errors": self.detail.get("deviceErrorList"),
        }

    @property
    def wifi_rssi(self) -> str | None:
        """Return the WiFi RSSI."""
        return self._wifi_info.get("rssi") if self._wifi_info else None

    @property
    def wifi_ssid(self) -> str | None:
        """Return the WiFi SSID."""
        if not self._wifi_info:
            return None
        return self._wifi_info.get("wifiName") or self._wifi_info.get("wifi_name")

    @property
    def total_clean_time(self) -> int | None:
        """Return today's clean count, the app's "Clean" chip."""
        return self._today_clean_times

    @property
    def stats_times(self) -> int | None:
        """Return today's toilet visits of all cats, the app's "Toilet" chip."""
        return self._today_toilet_count

    @property
    def stats_weight_avg(self) -> float | None:
        """Return the average weight from stats."""
        return self._device_stats.get("weightAvg") if self._device_stats else None

    @property
    def stats_duration_avg(self) -> int | None:
        """Return the average duration from stats."""
        return self._device_stats.get("durationAvg") if self._device_stats else None

    @property
    def notice_config_count(self) -> int:
        """Return the number of notice configurations."""
        return len(self._notice_configs or [])

    @property
    def pet_stats_count(self) -> int:
        """Return the number of pet stats entries."""
        return len(self._pet_stats or [])

    async def update_device_detail(self) -> dict:
        """Update the device detail."""
        rsp = None
        try:
            rsp = await self.account.request(
                API_LITTERBOX_C08_INFO, {"deviceId": self.id}
            )
            data = rsp.get("data", {})
            raw = data.get("deviceInfo")
            parsed = parse_response(data, "deviceInfo", C08DeviceInfo)
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
        await self.async_refresh_c08_extras()
        self._handle_listeners()
        return rdt

    async def update_logs(self) -> list:
        """Update device logs."""
        return await self._fetch_logs(
            API_LITTERBOX_LOGS, API_LITTERBOX_LOGS_RESPONSE_KEY
        )

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
        rdt = await self.account.request(
            API_LITTERBOX_CHANGE_MODE, {"workModel": mod, "deviceId": self.id}, "POST"
        )
        return await self._handle_action_result(rdt, "Select mode")

    async def select_action(self, action, **kwargs) -> bool:
        """Select the device action."""
        action_payload = self._action_options().get(action)
        if action_payload is None:
            _LOGGER.warning("Select action failed for %s", action)
            return False
        rdt = await self.account.request(
            API_LITTERBOX_ACTION_COMMAND_V3,
            {
                "action": action_payload[0],
                "behavior": action_payload[1],
                "deviceId": self.id,
            },
            "POST",
        )
        return await self._handle_action_result(rdt, "Select action")

    async def select_litter_type(self, litter_type, **kwargs) -> bool:
        """Select the litter type."""
        type_code = None
        for k, v in self.litter_types.items():
            if v == litter_type:
                type_code = k
                break
        if type_code is None:
            _LOGGER.warning("Select litter type failed for %s", litter_type)
            return False
        rdt = await self.account.request(
            API_LITTERBOX_CAT_LITTER_SETTING,
            {"litterType": type_code, "deviceId": self.id},
            "POST",
        )
        return await self._handle_action_result(rdt, "Select litter type")

    async def select_safe_time(self, safe_time, **kwargs) -> bool:
        """Select the safe time option."""
        safe_value = None
        for k, v in self.safe_time_options.items():
            if v == safe_time:
                safe_value = k
                break
        if safe_value is None:
            _LOGGER.warning("Select safe time failed for %s", safe_time)
            return False
        rdt = await self.account.request(
            API_LITTERBOX_SAFE_TIME_SETTING,
            {"safeTime": safe_value, "deviceId": self.id},
            "POST",
        )
        return await self._handle_action_result(rdt, "Select safe time")

    async def async_set_auto_pet_weight_update(self, enable: bool, **kwargs) -> bool:
        """Set auto pet weight update."""
        return await self._issue_toggle(
            API_LITTERBOX_PET_WEIGHT_AUTO_UPDATE, enable, "auto pet weight update"
        )

    async def async_set_quiet_mode(self, enable: bool, **kwargs) -> bool:
        """Enable or disable quiet mode."""
        return await self._issue_toggle(API_LITTERBOX_QUIET_MODE, enable, "Quiet mode")

    async def async_set_auto_burial(self, enable: bool, **kwargs) -> bool:
        """Enable or disable automatic burial."""
        return await self._issue_toggle(
            API_LITTERBOX_DEEP_CLEAN_AUTO_BURIAL, enable, "Auto burial"
        )

    async def async_set_continuous_cleaning(self, enable: bool, **kwargs) -> bool:
        """Enable or disable continuous cleaning."""
        return await self._issue_toggle(
            API_LITTERBOX_DEEP_CLEAN_CONTINUOUS_CLEANING,
            enable,
            "Continuous cleaning",
        )

    async def async_set_child_lock(self, enable: bool, **kwargs) -> bool:
        """Enable or disable child lock."""
        status = "01" if enable else "00"
        rdt = await self.account.request(
            API_LITTERBOX_KEY_LOCK,
            {"lockStatus": status, "deviceId": self.id},
            "POST",
        )
        return await self._handle_action_result(rdt, "Child lock")

    async def async_set_indicator_light(self, enable: bool, **kwargs) -> bool:
        """Enable or disable indicator light."""
        status = "ALWAYS_OPEN" if enable else "CLOSED"
        rdt = await self.account.request(
            API_LITTERBOX_INDICATOR_LIGHT_SETTING,
            {"status": status, "deviceId": self.id},
            "POST",
        )
        return await self._handle_action_result(rdt, "Indicator light")

    async def async_set_keypad_tone(self, enable: bool, **kwargs) -> bool:
        """Enable or disable keypad tone."""
        panel_tone = "01" if enable else "00"
        rdt = await self.account.request(
            API_LITTERBOX_KEYPAD_TONE,
            {"panelTone": panel_tone, "kind": "00", "deviceId": self.id},
            "POST",
        )
        return await self._handle_action_result(rdt, "Keypad tone")

    async def async_set_kitty_model(self, enable: bool, **kwargs) -> bool:
        """Enable or disable kitty model."""
        return await self._issue_toggle(
            API_LITTERBOX_KITTY_MODEL_SWITCH, enable, "Kitty model"
        )

    async def async_set_notice(self, item: str, enable: bool, **kwargs) -> bool:
        """Enable or disable a notice item."""
        rdt = await self.account.request(
            API_LITTERBOX_NOTICE_CONFIG_SET,
            {"noticeItem": item, "noticeSwitch": enable, "deviceId": self.id},
            "POST",
        )
        return await self._handle_action_result(rdt, "Notice config")

    async def async_refresh_c08_extras(self) -> None:
        """Refresh supplemental C08 data."""
        # "Today" in the device's own time zone, as the app asks for it.
        tz_id = self.detail.get("timezoneId")
        tz = dt_util.get_time_zone(tz_id) if tz_id else None
        today = dt_util.now(tz).date().isoformat()
        requests = [
            self.account.request(
                API_LITTERBOX_STATS_DATA_COMPARE_V2, {"deviceId": self.id}
            ),
            self.account.request(API_LITTERBOX_STATS_CATS, {"deviceId": self.id}),
            self.account.request(API_LITTERBOX_C08_WIFI_INFO, {"deviceId": self.id}),
            self.account.request(
                API_LITTERBOX_NOTICE_CONFIG_LIST_C08, {"deviceId": self.id}
            ),
            self.account.request(
                API_LITTERBOX_TODAY_CLEAN_TIMES, {"deviceId": self.id, "date": today}
            ),
            self.account.request(
                API_LITTERBOX_PET_TODAY_COUNTS,
                {"deviceId": self.id, "petId": "-1", "date": today},
            ),
        ]
        (
            stats_rsp,
            pets_rsp,
            wifi_rsp,
            notice_rsp,
            clean_rsp,
            toilet_rsp,
        ) = await asyncio.gather(*requests)

        self._device_stats = stats_rsp.get("data", {}).get("compareData", {})
        self._pet_stats = pets_rsp.get("data", {}).get("cats", [])
        self._wifi_info = wifi_rsp.get("data", {}).get("wifiInfo", {})
        self.set_notice_configs(notice_rsp.get("data", {}).get("noticeConfigs", []))
        self._today_clean_times = (clean_rsp.get("data") or {}).get("cleanTimes")
        self._today_toilet_count = as_int(
            (toilet_rsp.get("data") or {}).get("toiletCount")
        )

    def set_notice_configs(self, configs: list | None) -> None:
        """Set notice configs and update the notice map."""
        self._notice_configs = configs or []
        self._notice_config_map = {
            cfg.get("noticeItem"): bool(cfg.get("noticeSwitch"))
            for cfg in self._notice_configs
            if cfg.get("noticeItem") is not None
        }

    async def _issue_toggle(self, api: str, enable: bool, name: str) -> bool:
        """Issue a simple enable/disable command."""
        rdt = await self.account.request(
            api,
            {"enable": enable, "deviceId": self.id},
            "POST",
        )
        return await self._handle_action_result(rdt, name)

    async def _handle_action_result(self, rdt: dict, action_name: str) -> bool:
        """Handle the action response."""
        eno = rdt.get("returnCode", 0)
        if eno:
            err_msg = format_api_error(rdt)
            _LOGGER.error("%s failed: %s", action_name, err_msg)
            self._set_action_error(err_msg)
            return False
        await self.update_device_detail()
        _LOGGER.info("%s: %s", action_name, rdt)
        return True

    def _action_options(self) -> dict[str, tuple[str, str]]:
        """Return C08 action options mapping."""
        return {
            "clean_start": ("RUN", "CLEAN"),
            "clean_pause": ("PAUSE", "CLEAN"),
            "clean_cancel": ("CANCEL", "CLEAN"),
            "pave_start": ("RUN", "PAVE"),
            "pave_pause": ("PAUSE", "PAVE"),
        }

    @staticmethod
    def _bool_value(value) -> bool:
        """Return a boolean value from a loosely typed field."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @staticmethod
    def _string_flag(value, true_values: set[str]) -> bool:
        """Return a bool for string flags."""
        if value is None:
            return False
        return str(value).upper() in {v.upper() for v in true_values}
