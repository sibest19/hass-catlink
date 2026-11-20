"""Tests for CatLink LitterDevice base class."""

from unittest.mock import MagicMock

import pytest

from custom_components.catlink.devices.litterbox import LitterBox
from custom_components.catlink.devices.scooper import ScooperDevice


@pytest.fixture
def mock_coordinator():
    """Create a mock DevicesCoordinator."""
    coordinator = MagicMock()
    coordinator.account = MagicMock()
    coordinator.account.uid = "86-13812345678"
    return coordinator


@pytest.fixture
def sample_device_data():
    """Sample device data from API."""
    return {
        "id": "dev123",
        "mac": "AA:BB:CC:DD:EE:FF",
        "model": "LB599",
        "deviceName": "Living Room Litter",
        "deviceType": "LITTER_BOX_599",
    }


class TestLitterDeviceCleanCounts:
    """Tests for the clean counters the app shows."""

    def test_total_includes_scheduled_cleans(
        self, mock_coordinator, sample_device_data
    ) -> None:
        """Test the total adds auto, manual and scheduled cleans."""
        device = ScooperDevice(sample_device_data, mock_coordinator)
        device.detail = {"inductionTimes": "3", "manualTimes": "1", "timerTimes": "2"}
        assert device.total_clean_time == 6


class TestLitterDeviceState:
    """Tests for the workStatus state the Scooper shows (the 599 has its own)."""

    def test_state_idle(self, mock_coordinator, sample_device_data) -> None:
        """Test state maps workStatus 00 to idle."""
        device = ScooperDevice(sample_device_data, mock_coordinator)
        device.detail = {"workStatus": "00"}
        assert device.state == "idle"

    def test_state_running(self, mock_coordinator, sample_device_data) -> None:
        """Test state maps workStatus 01 to running."""
        device = ScooperDevice(sample_device_data, mock_coordinator)
        device.detail = {"workStatus": "01"}
        assert device.state == "running"

    def test_state_need_reset(self, mock_coordinator, sample_device_data) -> None:
        """Test state maps workStatus 02 to need_reset."""
        device = ScooperDevice(sample_device_data, mock_coordinator)
        device.detail = {"workStatus": "02"}
        assert device.state == "need_reset"

    def test_state_unknown_fallback(self, mock_coordinator, sample_device_data) -> None:
        """Test an unknown workStatus is None, as an enum sensor needs."""
        device = ScooperDevice(sample_device_data, mock_coordinator)
        device.detail = {"workStatus": "99"}
        assert device.state is None

    def test_litterbox_599_state_from_app_fields(
        self, mock_coordinator, sample_device_data
    ) -> None:
        """Test the 599 state follows cleanStatus/emptyStatus/replaceGarbageBag."""
        device = LitterBox(sample_device_data, mock_coordinator)
        cases = [
            ({"workStatus": "01"}, "idle"),
            ({"cleanStatus": "01"}, "cleaning"),
            ({"emptyStatus": "01"}, "emptying"),
            ({"emptyStatus": "02"}, "resetting"),
            ({"replaceGarbageBag": 3}, "resetting"),
            ({"replaceGarbageBag": 1}, "changing_bag"),
        ]
        for detail, expected in cases:
            device.detail = detail
            assert device.state == expected, detail


class TestLitterDeviceLitterWeight:
    """Tests for LitterDevice litter_weight property."""

    def test_litter_weight_calculated(
        self, mock_coordinator, sample_device_data
    ) -> None:
        """Test litter_weight subtracts empty weight from catLitterWeight."""
        device = LitterBox(sample_device_data, mock_coordinator)
        device.empty_litter_box_weight = 1.0
        device.detail = {"catLitterWeight": 3.5}
        assert device.litter_weight == 2.5

    def test_litter_weight_default_empty(
        self, mock_coordinator, sample_device_data
    ) -> None:
        """Test litter_weight when catLitterWeight missing uses empty_weight."""
        device = LitterBox(sample_device_data, mock_coordinator)
        device.empty_litter_box_weight = 1.0
        device.detail = {}
        assert device.litter_weight == 0.0


class TestLitterDeviceCleanTimes:
    """Tests for LitterDevice total_clean_time and manual_clean_time."""

    def test_total_clean_time(self, mock_coordinator, sample_device_data) -> None:
        """Test total_clean_time sums induction and manual times."""
        device = LitterBox(sample_device_data, mock_coordinator)
        device.detail = {"inductionTimes": 10, "manualTimes": 5}
        assert device.total_clean_time == 15

    def test_manual_clean_time(self, mock_coordinator, sample_device_data) -> None:
        """Test manual_clean_time from manualTimes."""
        device = LitterBox(sample_device_data, mock_coordinator)
        device.detail = {"manualTimes": 7}
        assert device.manual_clean_time == 7

    def test_deodorant_countdown(self, mock_coordinator, sample_device_data) -> None:
        """Test deodorant_countdown from detail."""
        device = LitterBox(sample_device_data, mock_coordinator)
        device.detail = {"deodorantCountdown": 30}
        assert device.deodorant_countdown == 30


class TestLitterDeviceOnline:
    """Tests for LitterDevice online property."""

    def test_online_true(self, mock_coordinator, sample_device_data) -> None:
        """Test online returns True when detail has online."""
        device = LitterBox(sample_device_data, mock_coordinator)
        device.detail = {"online": True}
        assert device.online is True

    def test_online_false(self, mock_coordinator, sample_device_data) -> None:
        """Test online returns False when detail has online False."""
        device = LitterBox(sample_device_data, mock_coordinator)
        device.detail = {"online": False}
        assert device.online is False


class TestLitterDeviceBaseStateAttrs:
    """Tests for LitterDevice _base_state_attrs."""

    def test_base_state_attrs(self, mock_coordinator, sample_device_data) -> None:
        """Test _base_state_attrs returns expected keys."""
        device = LitterBox(sample_device_data, mock_coordinator)
        device.detail = {
            "workStatus": "00",
            "alarmStatus": "ok",
            "weight": 2500,
            "catLitterWeight": 3.5,
            "inductionTimes": 10,
            "manualTimes": 5,
            "keyLock": "0",
            "safeTime": 30,
            "catLitterPaveSecond": 60,
            "deodorantCountdown": 30,
            "litterCountdown": 5,
        }
        attrs = device._base_state_attrs()
        assert attrs["mac"] == "AA:BB:CC:DD:EE:FF"
        assert attrs["work_status"] == "00"
        assert attrs["alarm_status"] == "ok"
        assert attrs["weight"] == 2500
        assert attrs["litter_weight_kg"] == 3.5
        assert attrs["total_clean_times"] == 15
        assert attrs["manual_clean_times"] == 5
        assert attrs["deodorant_countdown"] == 30
        assert attrs["litter_countdown"] == 5
