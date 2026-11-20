"""Tests for CatLink entity classes."""

from unittest.mock import AsyncMock, MagicMock

from custom_components.catlink.const import DOMAIN
from custom_components.catlink.devices.base import Device
from custom_components.catlink.devices.litterbox import LitterBox
from custom_components.catlink.entities.base import CatlinkEntity
from custom_components.catlink.entities.binary import CatlinkBinarySensorEntity
from custom_components.catlink.entities.button import CatlinkButtonEntity
from custom_components.catlink.entities.number import CatlinkNumberEntity
from custom_components.catlink.entities.select import CatlinkSelectEntity
from custom_components.catlink.entities.sensor import CatlinkSensorEntity
from custom_components.catlink.entities.switch import CatlinkSwitchEntity
import pytest

from homeassistant.const import STATE_OFF, STATE_ON


def _attach_platform(hass, entity, domain="sensor"):
    """Attach an entity platform, as Home Assistant does before reading state.

    Without it `entity.name` cannot resolve its translation key, which is how
    the entity behaves in production but not when constructed bare in a test.
    """
    from pytest_homeassistant_custom_component.common import MockEntityPlatform

    platform = MockEntityPlatform(hass, domain=domain, platform_name=DOMAIN)
    entity.add_to_platform_start(hass, platform, None)
    return entity


@pytest.fixture
def mock_device():
    """Create a mock device with required attributes."""
    device = MagicMock(spec=Device)
    device.id = "dev123"
    device.mac = "AABBCCDDEEFF"
    device.type = "LITTER_BOX_599"
    device.name = "Test Litter Box"
    device.model = "LB599"
    device.detail = {"firmwareVersion": "1.0.0"}
    device.listeners = {}
    return device


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.account = MagicMock()
    return coordinator


@pytest.fixture
def real_device(mock_coordinator):
    """Create a real LitterBox device for entity tests."""
    data = {
        "id": "dev123",
        "mac": "AA:BB:CC:DD:EE:FF",
        "model": "LB599",
        "deviceName": "Test Litter Box",
        "deviceType": "LITTER_BOX_599",
    }
    device = LitterBox(data, mock_coordinator)
    device.detail = {"firmwareVersion": "1.0.0", "currentError": "Normal"}
    device.coordinator = mock_coordinator
    return device


class TestCatlinkEntity:
    """Tests for CatlinkEntity base class."""

    def test_entity_initialization(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test CatlinkEntity initializes with correct attributes."""
        mock_device.coordinator = mock_coordinator
        entity = CatlinkEntity("error", mock_device, {})
        entity.coordinator = mock_coordinator
        entity.hass = hass
        _attach_platform(hass, entity, "sensor")

        assert entity._name == "error"
        assert entity._device == mock_device
        # Icons come from icons.json by translation key, and entity_id is left
        # to Home Assistant.
        assert not hasattr(entity, "_attr_icon")
        assert entity.entity_id is None
        # has_entity_name is True, so Home Assistant prepends the device name
        # and takes the entity half from the translations via translation_key.
        assert entity._attr_has_entity_name is True
        assert entity._attr_translation_key == "error"
        # _attr_name must stay unset: Entity._name_internal returns it before it
        # ever looks at the translation, so setting it silently disables i18n.
        assert not hasattr(entity, "_attr_name")
        assert entity._attr_device_id == "LITTER_BOX_599_AABBCCDDEEFF"
        assert entity._attr_unique_id == "LITTER_BOX_599_AABBCCDDEEFF-error"

    async def test_device_listener_follows_unique_id_and_is_removed(
        self, hass, real_device, mock_coordinator
    ) -> None:
        """Test the update callback is keyed by unique_id and dropped on removal.

        Keyed by entity_id it went stale when the user renamed the entity.
        """
        real_device.coordinator = mock_coordinator
        entity = CatlinkSensorEntity("error", real_device)
        entity.hass = hass
        entity.entity_id = "sensor.test"
        _attach_platform(hass, entity, "sensor")

        await entity.async_added_to_hass()
        assert set(real_device.listeners) == {entity.unique_id}

        await entity.async_will_remove_from_hass()
        assert real_device.listeners == {}

    def test_entity_device_info(self, mock_coordinator) -> None:
        """Test the device card shows the app's product name, MAC and firmware."""
        from custom_components.catlink.devices.c08 import C08Device

        device = C08Device(
            {
                "id": "1",
                "mac": "2442E3414413",
                "deviceType": "C08",
                "deviceName": "SCOOPER C08",
                "model": "MODEL_00",
            },
            mock_coordinator,
        )
        device.detail = {"firmwareVersion": "V04.22"}
        entity = CatlinkEntity("state", device)

        assert entity._attr_device_info == {
            "identifiers": {("catlink", "C08_2442E3414413")},
            "connections": {("mac", "24:42:e3:41:44:13")},
            "name": "SCOOPER C08",
            "manufacturer": "CatLink",
            "model": "SCOOPER SE 2",
            "model_id": "C08",
            "sw_version": "V04.22",
        }

    def test_cat_device_info(self, mock_coordinator) -> None:
        """Test a cat's device card has no MAC or firmware."""
        from custom_components.catlink.devices.cat import CatDevice

        device = CatDevice(
            {"id": "cat-1", "mac": "cat-1", "deviceType": "CAT", "deviceName": "Zulu"},
            mock_coordinator,
        )
        assert device.device_info == {
            "identifiers": {("catlink", "CAT_cat-1")},
            "name": "Zulu",
            "manufacturer": "CatLink",
            "model": "Cat",
        }

    def test_entity_update_from_device(
        self, hass, real_device, mock_coordinator
    ) -> None:
        """Test entity update reads state from device."""
        real_device.coordinator = mock_coordinator
        entity = CatlinkSensorEntity("error", real_device)
        entity.coordinator = mock_coordinator
        entity.hass = hass

        entity.update()
        assert entity._attr_native_value == "Normal"

    def test_entity_unique_id_format(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test entity unique_id format."""
        mock_device.coordinator = mock_coordinator
        mock_device.mac = "1122"
        mock_device.id = "dev456"
        entity = CatlinkEntity("litter_weight", mock_device)
        entity.coordinator = mock_coordinator
        entity.hass = hass

        assert entity._attr_unique_id.endswith("-litter_weight")
        assert "LITTER_BOX_599" in entity._attr_unique_id

    def test_entity_picture_static(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test entity picture supports static value."""
        mock_device.coordinator = mock_coordinator
        entity = CatlinkEntity(
            "status", mock_device, {"entity_picture": "https://example.com/cat.jpg"}
        )
        entity.coordinator = mock_coordinator
        entity.hass = hass

        assert entity._attr_entity_picture == "https://example.com/cat.jpg"

    def test_entity_picture_callable_updates(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test entity picture supports callable updates."""
        mock_device.coordinator = mock_coordinator
        mock_device.avatar_url = "https://example.com/cat1.jpg"
        entity = CatlinkEntity(
            "status", mock_device, {"entity_picture": lambda: mock_device.avatar_url}
        )
        entity.coordinator = mock_coordinator
        entity.hass = hass

        assert entity._attr_entity_picture == "https://example.com/cat1.jpg"

        mock_device.avatar_url = "https://example.com/cat2.jpg"
        entity.update()
        assert entity._attr_entity_picture == "https://example.com/cat2.jpg"


class TestCatlinkBinarySensorEntity:
    """Tests for CatlinkBinarySensorEntity."""

    def test_binary_sensor_initialization(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test CatlinkBinarySensorEntity initializes with is_on False."""
        mock_device.coordinator = mock_coordinator
        entity = CatlinkBinarySensorEntity("occupied", mock_device)
        entity.coordinator = mock_coordinator
        entity.hass = hass

        assert entity._attr_is_on is False

    def test_binary_sensor_update_from_device(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test binary sensor update sets is_on from device attribute."""
        mock_device.coordinator = mock_coordinator
        mock_device.occupied = True
        entity = CatlinkBinarySensorEntity("occupied", mock_device)
        entity.coordinator = mock_coordinator
        entity.hass = hass

        entity.update()
        assert entity._attr_is_on is True
        assert entity.state == STATE_ON

    def test_binary_sensor_update_off(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test binary sensor state is OFF when device attribute is falsy."""
        mock_device.coordinator = mock_coordinator
        mock_device.occupied = False
        entity = CatlinkBinarySensorEntity("occupied", mock_device)
        entity.coordinator = mock_coordinator
        entity.hass = hass

        entity.update()
        assert entity._attr_is_on is False
        assert entity.state == STATE_OFF


class TestCatlinkButtonEntity:
    """Tests for CatlinkButtonEntity."""

    async def test_button_press_calls_option(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test async_press calls option's async_press when callable."""
        mock_device.coordinator = mock_coordinator
        mock_press = AsyncMock(return_value=True)
        entity = CatlinkButtonEntity(
            "action",
            mock_device,
            {"async_press": mock_press},
        )
        entity.coordinator = mock_coordinator
        entity.hass = hass

        result = await entity.async_press()
        assert result is True
        mock_press.assert_called_once()

    async def test_button_press_no_option_returns_false(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test async_press returns False when option has no async_press."""
        mock_device.coordinator = mock_coordinator
        entity = CatlinkButtonEntity("action", mock_device, {})
        entity.coordinator = mock_coordinator
        entity.hass = hass

        result = await entity.async_press()
        assert result is False


class TestCatlinkSelectEntity:
    """Tests for CatlinkSelectEntity."""

    def test_select_initialization(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test CatlinkSelectEntity initializes with options from config."""
        mock_device.coordinator = mock_coordinator
        entity = CatlinkSelectEntity(
            "mode",
            mock_device,
            {"options": ["auto", "manual"]},
        )
        entity.coordinator = mock_coordinator
        entity.hass = hass

        assert entity._attr_options == ["auto", "manual"]
        assert entity._attr_current_option is None

    def test_select_update_sets_current_option(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test select update sets current_option from state."""
        mock_device.coordinator = mock_coordinator
        mock_device.mode = "auto"
        entity = CatlinkSelectEntity(
            "mode",
            mock_device,
            {"options": ["auto", "manual"]},
        )
        entity.coordinator = mock_coordinator
        entity.hass = hass

        entity.update()
        assert entity._attr_current_option == "auto"

    async def test_select_option_calls_async_select(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test async_select_option calls option's async_select."""
        mock_device.coordinator = mock_coordinator
        mock_device.mode = "manual"
        mock_select = AsyncMock(return_value=True)
        entity = CatlinkSelectEntity(
            "mode",
            mock_device,
            {"options": ["auto", "manual"], "async_select": mock_select},
        )
        entity.coordinator = mock_coordinator
        entity.hass = hass
        entity.entity_id = "select.test"
        _attach_platform(hass, entity, "select")

        result = await entity.async_select_option("manual")
        assert result is True
        mock_select.assert_called_once_with("manual", entity=entity)
        assert entity._attr_current_option == "manual"


class TestCatlinkSensorEntity:
    """Tests for CatlinkSensorEntity."""

    def test_sensor_initialization(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test CatlinkSensorEntity initializes with sensor config."""
        mock_device.coordinator = mock_coordinator
        mock_device.error = "Normal"
        entity = CatlinkSensorEntity(
            "error",
            mock_device,
            {"icon": "mdi:alert", "state_attrs": lambda: {"key": "val"}},
        )
        entity.coordinator = mock_coordinator
        entity.hass = hass

        assert entity._name == "error"

    def test_sensor_update_sets_state_and_attrs(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test sensor update sets state and extra_state_attributes."""
        mock_device.coordinator = mock_coordinator
        mock_device.litter_remaining_days = 5
        state_attrs = {"days_left": 5}

        def get_attrs():
            return state_attrs

        entity = CatlinkSensorEntity(
            "litter_remaining_days",
            mock_device,
            {"unit": "days", "state_attrs": get_attrs},
        )
        entity.coordinator = mock_coordinator
        entity.hass = hass

        entity.update()
        assert entity._attr_native_value == 5
        assert entity._attr_extra_state_attributes == {"days_left": 5}
        assert entity._attr_native_unit_of_measurement == "days"

    def test_sensor_update_without_state_attrs(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test sensor update when option has no state_attrs."""
        mock_device.coordinator = mock_coordinator
        mock_device.litter_weight = 2.5
        entity = CatlinkSensorEntity(
            "litter_weight",
            mock_device,
            {"unit": "kg"},
        )
        entity.coordinator = mock_coordinator
        entity.hass = hass

        entity.update()
        assert entity._attr_native_value == 2.5
        assert entity._attr_native_unit_of_measurement == "kg"


class TestCatlinkSwitchEntity:
    """Tests for CatlinkSwitchEntity."""

    def test_switch_initialization(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test CatlinkSwitchEntity initializes."""
        mock_device.coordinator = mock_coordinator
        entity = CatlinkSwitchEntity(
            "key_lock",
            mock_device,
            {"async_turn_on": None, "async_turn_off": None},
        )
        entity.coordinator = mock_coordinator
        entity.hass = hass

        assert entity._attr_is_on is False

    async def test_switch_turn_on_calls_option(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test async_turn_on calls option's async_turn_on."""
        mock_device.coordinator = mock_coordinator
        mock_device.key_lock = True
        mock_turn_on = AsyncMock(return_value=True)
        entity = CatlinkSwitchEntity(
            "key_lock",
            mock_device,
            {"async_turn_on": mock_turn_on, "async_turn_off": MagicMock()},
        )
        entity.coordinator = mock_coordinator
        entity.hass = hass
        entity.entity_id = "switch.test"
        _attach_platform(hass, entity, "switch")

        await entity.async_turn_on()
        assert entity._attr_is_on is True
        mock_turn_on.assert_called_once()

    async def test_switch_turn_off_calls_option(
        self, hass, mock_device, mock_coordinator
    ) -> None:
        """Test async_turn_off calls option's async_turn_off."""
        mock_device.coordinator = mock_coordinator
        mock_turn_off = AsyncMock(return_value=True)
        entity = CatlinkSwitchEntity(
            "key_lock",
            mock_device,
            {"async_turn_on": MagicMock(), "async_turn_off": mock_turn_off},
        )
        entity.coordinator = mock_coordinator
        entity.hass = hass
        entity.entity_id = "switch.test"
        _attach_platform(hass, entity, "switch")
        entity._attr_is_on = True

        await entity.async_turn_off()
        assert entity._attr_is_on is False
        mock_turn_off.assert_called_once()


class TestEntityIdLeftToHomeAssistant:
    """Tests that the integration never sets entity_id itself."""

    @pytest.mark.parametrize(
        "cls",
        [
            CatlinkSensorEntity,
            CatlinkBinarySensorEntity,
            CatlinkSwitchEntity,
            CatlinkSelectEntity,
            CatlinkButtonEntity,
            CatlinkNumberEntity,
        ],
    )
    def test_entity_id_is_not_set(self, mock_device, mock_coordinator, cls) -> None:
        """Test Home Assistant generates the entity_id from area, device and name."""
        mock_device.coordinator = mock_coordinator
        entity = cls("state", mock_device, {})
        assert entity.entity_id is None
