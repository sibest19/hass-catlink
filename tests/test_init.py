"""Tests for CatLink integration setup."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from custom_components.catlink import async_setup
from custom_components.catlink.const import (
    CONF_ACCOUNTS,
    CONF_PHONE,
    CONF_PHONE_IAC,
    DOMAIN,
    SUPPORTED_DOMAINS,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PHONE_IAC: "86",
            CONF_PHONE: "13812345678",
            "api_base": "https://app.catlinks.cn/api/",
            "password": "testpass",
        },
        options={},
        entry_id="test-entry-id",
    )


@pytest.fixture
def mock_account():
    """Mock Account class."""
    with patch("custom_components.catlink.Account") as mock:
        instance = mock.return_value
        instance.uid = "86-13812345678"
        instance.async_check_auth = AsyncMock()
        yield mock


@pytest.fixture
def mock_coordinator():
    """Mock DevicesCoordinator class."""
    with patch("custom_components.catlink.DevicesCoordinator") as mock:
        instance = mock.return_value
        instance.name = f"{DOMAIN}-86-13812345678-devices"
        instance.async_config_entry_first_refresh = AsyncMock()
        instance.data = {}
        yield mock


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_setup(hass: HomeAssistant) -> None:
    """Test async_setup initializes hass.data structure."""
    result = await async_setup(hass, {})

    assert result is True
    assert DOMAIN in hass.data
    assert CONF_ACCOUNTS in hass.data[DOMAIN]
    assert "coordinators" in hass.data[DOMAIN]
    assert "add_entities" in hass.data[DOMAIN]
    assert "config" in hass.data[DOMAIN]
    assert "entry_coordinators" in hass.data[DOMAIN]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_account,
    mock_coordinator,
) -> None:
    """Test async_setup_entry loads config entry and forwards platforms."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(CONF_ACCOUNTS, {})
    hass.data[DOMAIN].setdefault("coordinators", {})
    hass.data[DOMAIN].setdefault("add_entities", {})
    hass.data[DOMAIN].setdefault("config", {})
    hass.data[DOMAIN].setdefault("entry_coordinators", {})

    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    assert mock_config_entry.state is ConfigEntryState.LOADED
    mock_account.return_value.async_check_auth.assert_called_once()
    mock_coordinator.return_value.async_config_entry_first_refresh.assert_called_once()
    assert mock_account.return_value.uid in hass.data[DOMAIN][CONF_ACCOUNTS]
    assert mock_config_entry.entry_id in hass.data[DOMAIN]["entry_coordinators"]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_setup_retries_when_devices_cannot_be_listed(
    hass: HomeAssistant, mock_config_entry, mock_account
) -> None:
    """Test a failed device listing retries setup instead of loading empty."""
    mock_account.return_value.hass = hass
    mock_account.return_value.update_interval = timedelta(minutes=1)
    mock_account.return_value.get_devices = AsyncMock(return_value=None)
    mock_account.return_value.login_rejected = False
    await async_setup(hass, {})
    mock_config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_setup_asks_for_password_when_login_is_rejected(
    hass: HomeAssistant, mock_config_entry, mock_account
) -> None:
    """Test CatLink refusing the login starts Home Assistant's re-auth flow."""
    mock_account.return_value.hass = hass
    mock_account.return_value.update_interval = timedelta(minutes=1)
    mock_account.return_value.get_devices = AsyncMock(return_value=None)
    mock_account.return_value.login_rejected = True
    await async_setup(hass, {})
    mock_config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [f["context"]["source"] for f in flows] == ["reauth"]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_unload_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_account,
    mock_coordinator,
) -> None:
    """Test async_unload_entry cleans up hass.data, whatever the account uid format."""
    mock_account.return_value.uid = "email-cat@example.com"
    mock_coordinator.return_value.account = mock_account.return_value
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(CONF_ACCOUNTS, {})
    hass.data[DOMAIN].setdefault("coordinators", {})
    hass.data[DOMAIN].setdefault("add_entities", {})
    hass.data[DOMAIN].setdefault("config", {})
    hass.data[DOMAIN].setdefault("entry_coordinators", {})

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    assert hass.data[DOMAIN][CONF_ACCOUNTS] == {}
    assert hass.data[DOMAIN]["coordinators"] == {}
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]["entry_coordinators"]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_setup_entry_forwards_all_platforms(
    hass: HomeAssistant,
    mock_config_entry,
    mock_account,
    mock_coordinator,
) -> None:
    """Test async_setup_entry forwards all supported domains."""
    with patch.object(
        hass.config_entries,
        "async_forward_entry_setups",
        new_callable=AsyncMock,
    ) as mock_forward:
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN].setdefault(CONF_ACCOUNTS, {})
        hass.data[DOMAIN].setdefault("coordinators", {})
        hass.data[DOMAIN].setdefault("add_entities", {})
        hass.data[DOMAIN].setdefault("config", {})
        hass.data[DOMAIN].setdefault("entry_coordinators", {})

        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        mock_forward.assert_called_once()
        call_args = mock_forward.call_args
        assert call_args[0][1] == SUPPORTED_DOMAINS


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_setup_removes_stale_entities(
    hass: HomeAssistant,
    mock_config_entry,
    mock_account,
    mock_coordinator,
) -> None:
    """Test setup drops registry entries of entities no device creates any more."""
    from homeassistant.helpers import entity_registry as er

    mock_config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    stale = registry.async_get_or_create(
        "sensor", DOMAIN, "C08_AABB-occupied", config_entry=mock_config_entry
    )
    moved = registry.async_get_or_create(
        "sensor", DOMAIN, "C08_AABB-online", config_entry=mock_config_entry
    )
    pro_ultra = registry.async_get_or_create(
        "select", DOMAIN, "VISUAL_PRO_ULTRA_CCDD-mode", config_entry=mock_config_entry
    )
    kept = registry.async_get_or_create(
        "sensor", DOMAIN, "C08_AABB-error", config_entry=mock_config_entry
    )

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert registry.async_get(stale.entity_id) is None
    assert registry.async_get(moved.entity_id) is None
    assert registry.async_get(pro_ultra.entity_id) is None
    assert registry.async_get(kept.entity_id) is not None
