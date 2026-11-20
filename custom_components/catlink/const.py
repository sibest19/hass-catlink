"""Constants for the CatLink integration."""

import datetime
import logging

# account.py imports CONF_SCAN_INTERVAL from here.
from homeassistant.const import CONF_SCAN_INTERVAL  # noqa: F401

DOMAIN = "catlink"
_LOGGER = logging.getLogger(__name__)

CONFIG = "config"
SCAN_INTERVAL = datetime.timedelta(minutes=1)

CONF_ACCOUNTS = "accounts"
CONF_API_BASE = "api_base"
CONF_REGION = "region"
CONF_USER_ID = "uid"
CONF_PHONE = "phone"
CONF_PHONE_IAC = "phone_iac"
CONF_LANGUAGE = "language"

CONF_CATS = "cats"
CONF_DEVICE_IDS = "device_ids"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_API_BASE = "https://app.catlinks.cn/api/"
DEFAULT_UPDATE_INTERVAL = 60

# Login endpoints. The account can be identified either by email address or by
# phone number; both take the same RSA-encrypted password and the same request
# signature, they only differ in the identity fields they expect.
LOGIN_API_EMAIL = "login/email"
LOGIN_API_PHONE = "login/password"

# Device types with full support (sensors, switches, selects, etc.)
# Must stay in sync with DEVICE_TYPES in devices/registry.py: a device with a
# class there but missing here is labelled "Limited support" in the config flow
# and is not pre-selected, so it silently never gets added.
SUPPORTED_DEVICE_TYPES = frozenset(
    {"C08", "SCOOPER", "LITTER_BOX_599", "FEEDER", "PUREPRO", "VISUAL_PRO_ULTRA"}
)

# Sentinel for "try every region until one accepts the credentials".
REGION_AUTO = "auto"

# API server regions: value is the API base URL
API_SERVERS: dict[str, str] = {
    "global": "https://app.catlinks.cn/api/",
    "china": "https://app-sh.catlinks.cn/api/",
    "usa": "https://app-usa.catlinks.cn/api/",
    "singapore": "https://app-sgp.catlinks.cn/api/",
}

# Config flow error keys
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_INVALID_AUTH = "invalid_auth"

SIGN_KEY = "00109190907746a7ad0e2139b6d09ce47551770157fe4ac5922f3a5454c82712"
RSA_PUBLIC_KEY = (
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCCA9I+iEl2AI8dnhdwwxPxHVK8iNAt6aTq6UhNsLsguWS5qtbLnuGz2RQdfNS"
    "aKSU2B6D/vE2gb1fM6f1A5cKndqF/riWGWn1EfL3FFQZduOTxoA0RTQzhrTa5LHcJ/an/NuHUwShwIOij0Mf4g8faTe4FT7/HdA"
    "oK7uW0cG9mZwIDAQAB"
)

SUPPORTED_DOMAINS = [
    "sensor",
    "binary_sensor",
    "switch",
    "select",
    "button",
    "number",
]
