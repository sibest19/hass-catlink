# Contributing

Thanks for helping. This file covers bug reports, device reports, the development setup, the
coding rules of this repository and the release process.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Report a bug or a device

Use the [issue templates](https://github.com/sibest19/hass-catlink/issues/new/choose).

Most devices are **not tested on real hardware** (see the support table in the
[README](README.md#device-support)). If you own one, a report saying "everything works" is just as
useful as a bug report.

Before you open an issue:

1. Update to the latest release. The bug may already be fixed.
2. Search the [existing issues](https://github.com/sibest19/hass-catlink/issues).
3. Turn on debug logging (see [Troubleshooting](README.md#troubleshooting)) and reproduce the problem.

Include:

- the device model, as shown in the CatLink app, and its `deviceType` if you know it;
- the Home Assistant version and the integration version;
- how you installed it (Marketplace / HACS or manual);
- what you expected, what happened, and what the official app shows for the same value;
- the debug log.

**Remove your email address, phone number, tokens, device IDs and MAC addresses from logs before
you post them.**

To request a new device or report how an untested one works, open a **Device support / test
report** issue and attach the diagnostics file (**Settings → Devices & services → CatLink → ⋮ →
Download diagnostics**). It holds the raw API data of every device, already redacted, and for
unknown device types a fresh copy of the generic `token/device/info` response. For anything else,
the `catlink.request_api` action (see the README) calls any API path.

## Development setup

You need Python 3.14 (Home Assistant 2026.3 and later need it) and git.

```shell
git clone https://github.com/<your-user>/hass-catlink.git
cd hass-catlink
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt pytest-timeout
```

Run the tests (CI runs them the same way):

```shell
pytest tests/ --timeout=10
```

Lint and format the files you change with [ruff](https://docs.astral.sh/ruff/). The repository
has no ruff configuration yet, so the defaults apply, and older files may not be clean:

```shell
pip install ruff
ruff check custom_components tests
ruff format custom_components tests
```

### Local Home Assistant with Docker

The repository ships a Docker Compose stack that runs Home Assistant with the integration
bind-mounted from your working tree.

```shell
docker compose up -d          # start; the first boot takes a minute
open http://localhost:8123    # onboard with any throwaway account
```

Then add the integration from **Settings → Devices & services → Add integration → CatLink**.

| Command | What it does |
| --- | --- |
| `docker compose logs -f` | Follow logs. `custom_components.catlink` logs at debug level. |
| `docker compose restart` | Load your Python or translation changes. |
| `docker compose up -d --build` | Rebuild after changing the requirements in `manifest.json`. |
| `docker compose down` | Stop. The Home Assistant config in `dev/ha-config` is kept. |
| `docker compose down && rm -rf dev/ha-config/.storage` | Full reset back to onboarding. |
| `HA_VERSION=2026.7 docker compose up -d` | Run a specific Home Assistant version. |

Good to know:

- [dev/Dockerfile](dev/Dockerfile) pre-installs the `manifest.json` requirements. Without it, a
  failed requirement install shows up only as "Invalid handler specified" in the UI. A new
  requirement therefore needs `--build`, not just a restart.
- Your edits are visible in the container at once, but Home Assistant imports Python modules only
  at startup. Restart the container after every code or translation change.
- [dev/ha-config/configuration.yaml](dev/ha-config/configuration.yaml) turns on debug logging and
  `debugpy` on port 5678. In VS Code, run the **Attach to Home Assistant (Docker)** launch
  configuration to set breakpoints in `custom_components/catlink`. Startup does not wait for the
  debugger.
- Use a CatLink account you can afford to log out (see the README on the
  [one-login limit](README.md#before-you-start-use-a-second-catlink-account)).

## How the code is organised

```
custom_components/catlink/
  __init__.py            setup, unload, removal of entities that no longer exist
  config_flow.py         sign-in, region, device selection, options, re-auth
  const.py               constants, API servers, SUPPORTED_DEVICE_TYPES
  modules/account.py     login, request signing, token renewal
  modules/devices_coordinator.py   polling, one coordinator per config entry
  devices/               one class per device type, plus the cat profile
  devices/registry.py    deviceType -> device class
  entities/              the generic Home Assistant entity classes
  translations/*.json    entity names and states (en.json, it.json)
  icons.json             entity icons
```

Each device class exposes its entities through `hass_sensor`, `hass_binary_sensor`, `hass_switch`,
`hass_select`, `hass_button` and `hass_number`. Each returns a dict: the key is a property name on
the device, the value is an options dict. The generic entity reads the value from the property of
the same name. For example:

```python
@property
def hass_sensor(self) -> dict:
    return {
        "litter_weight": {
            "class": SensorDeviceClass.WEIGHT,
            "unit": UnitOfMass.KILOGRAMS,
            "state_class": SensorStateClass.MEASUREMENT,
        },
        "wifi_ssid": {
            "entity_category": EntityCategory.DIAGNOSTIC,
            "enabled_default": False,
        },
    }
```

Options in use: `class`, `unit`, `state_class`, `entity_category`, `enabled_default`, `options`
(enum sensors and selects), `state_attrs`, `entity_picture`, `translation_key`, `async_select`,
`async_turn_on` / `async_turn_off`, `async_press`, `min` / `max` / `step` (numbers) and
`delay_update` (seconds to wait before refreshing after an action).

## Coding rules

- **Values must come from the same endpoint and field as the official app.** Before you add or
  change a value, find where the CatLink app reads it (API endpoint and JSON field) and use that.
  Do not compute your own numbers from other fields, and do not add entities the app does not
  show. The goal is that Home Assistant and the app always show the same thing. Commands must send
  the same payload the app sends. Say in the PR where you checked this (app version, endpoint,
  field).
- **No hard-coded entity IDs, names or icons.** Home Assistant builds the entity ID. The entity key
  is the translation key, so the name lives in `translations/*.json` under
  `entity.<platform>.<key>.name`, and the icon in `icons.json`. Set `"translation_key": None` only
  when the entity should be named after its device class (for example Temperature, Weight,
  Connectivity).
- **Translations.** Custom integrations ship finished `translations/*.json` files, and there is no
  `strings.json`: `translations/en.json` is the source, and hassfest validates it. Every language
  file needs a name for every entity key and enum state; `test_every_entity_key_is_translated`
  fails otherwise. If you cannot translate, copy the English text into the other files and say so
  in the PR.
- **Enum states are lowercase keys** (`clean_start`, `almost_full`), translated under
  `entity.<platform>.<key>.state`. Never use display text as a state.
- **Use Home Assistant constants**: device classes, `UnitOf...` units, state classes and entity
  categories. Diagnostic extras are `EntityCategory.DIAGNOSTIC`; things most users do not need are
  `enabled_default: False`.
- **Return `None` when the device does not report a value**, so the entity shows *unknown*. Do not
  invent a `0`.
- **Removing an entity is a breaking change.** Add its `(platform, key)` to `REMOVED_ENTITIES` in
  `__init__.py` so it is cleaned out of users' registries, and list it in the changelog.
- **Never log secrets.** No passwords, tokens or full request signatures in log lines.
- Add or update tests in `tests/` for every change in behaviour.

## Adding a new device type

1. Collect real API responses for the device (see [Report a bug or a device](#report-a-bug-or-a-device)),
   and find in the app which endpoints and fields it uses.
2. Create `custom_components/catlink/devices/<name>.py` with a class that extends `Device` (or
   `LitterDevice` for litter boxes). Implement `update_device_detail()` for the device's detail
   endpoint, a property per value, and the `hass_*` dicts.
3. Register the class in `DEVICE_TYPES` in `devices/registry.py`, and add the `deviceType` to
   `SUPPORTED_DEVICE_TYPES` in `const.py`. Both lists must match, or the device is shown as
   "Limited support" and not pre-selected.
4. Add names and states to every file in `translations/`, and icons to `icons.json`.
5. Add tests in `tests/test_devices.py` using the real (redacted) API responses.
6. Add the device to the support table and the entity tables in `README.md`, marked as not tested
   on hardware unless you tested it yourself.

### From new device to stable

A device nobody has tested goes out as a beta first:

1. **Request.** A user opens a *Device support / test report* issue with the diagnostics file and
   app screenshots. Unknown device types show a repair notice in Home Assistant that links to the
   pre-filled form.
2. **Beta.** Add the device as above, then publish a pre-release (see
   [Release process](#release-process)), for example `3.1.0b1`. Mark the device "beta" in the README
   support table and ask in the issue for testers.
3. **Test reports.** Testers turn on pre-releases for CatLink in the Marketplace or HACS, install
   the beta and answer in the issue with the same form: diagnostics, screenshots, and which
   readings and controls work. Fix what they report in `3.1.0b2` and so on.
4. **Stable.** When the readings match the app and the controls work, release `3.1.0` and update
   the support table ("tested by users" or "verified on hardware").

## Pull requests

Fork the repository, create a branch from `main`, and open a pull request against `main`.

Checklist:

- [ ] `pytest tests/ --timeout=10` passes.
- [ ] `ruff check` and `ruff format` report nothing new in the files you changed.
- [ ] Values and commands match the official app; the PR says how you checked.
- [ ] New strings are in every `translations/*.json`; icons are in `icons.json`.
- [ ] Removed entities are in `REMOVED_ENTITIES`.
- [ ] `CHANGELOG.md` has an entry under **Unreleased**, written for users.
- [ ] `README.md` is updated if entities, setup or support status changed.
- [ ] You tested on real hardware, or the PR says you did not.

## Release process

For maintainers:

1. Move the **Unreleased** entries in `CHANGELOG.md` under a new version heading with the date.
2. Set `version` in `custom_components/catlink/manifest.json` to the same version.
3. Commit, then create a GitHub release whose tag is `v` plus that version (for example `v3.0.0`).
   The release workflow fails if they differ.
   HACS and the Marketplace install from releases, so the tag and the manifest version must match.
4. Paste the changelog section into the release notes.

**Betas.** Use a PEP 440 pre-release version such as `3.1.0b1` (or `3.1.0rc1`) in `manifest.json`
and the tag `v3.1.0b1`, and tick **Set as a pre-release** on GitHub. Home Assistant accepts this
format and sorts it before `3.1.0`. The release workflow fails if the pre-release box does not
match the version: a version with a letter must be a pre-release, a plain `x.y.z` must not. The
Marketplace and HACS offer a pre-release only to users who turned on pre-releases for CatLink, and
only while it is newer than the latest stable release. A beta changelog can stay under
**Unreleased**; move it under the version heading for the stable release.

## License

This project is licensed under the [Apache License 2.0](LICENSE). By submitting a contribution you
agree that it is licensed under the same terms, as described in section 5 of the license.
