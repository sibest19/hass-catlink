# CatLink for Home Assistant

Monitor and control CatLink litter boxes, feeders, water fountains and cat profiles from Home Assistant.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![GitHub release](https://img.shields.io/github/v/release/sibest19/hass-catlink)](https://github.com/sibest19/hass-catlink/releases)
[![License](https://img.shields.io/github/license/sibest19/hass-catlink)](LICENSE)
[![hassfest](https://img.shields.io/github/actions/workflow/status/sibest19/hass-catlink/validate-hassfest.yml?branch=main&label=hassfest)](https://github.com/sibest19/hass-catlink/actions/workflows/validate-hassfest.yml)
[![HACS validation](https://img.shields.io/github/actions/workflow/status/sibest19/hass-catlink/validate-hacs.yml?branch=main&label=HACS%20validation)](https://github.com/sibest19/hass-catlink/actions/workflows/validate-hacs.yml)
[![Tests](https://img.shields.io/github/actions/workflow/status/sibest19/hass-catlink/tests.yaml?branch=main&label=tests)](https://github.com/sibest19/hass-catlink/actions/workflows/tests.yaml)

> [!NOTE]
> This is an **unofficial** integration. It is not made, supported or endorsed by CatLink.
> It talks to the same cloud API as the CatLink app.

This project continues [hasscc/catlink](https://github.com/hasscc/catlink), which has had no
activity since February 2026 (last release v2.1.1). It uses the same `catlink` domain, so you can
switch over without losing your entities. See [Migrating from hasscc/catlink](#migrating-from-hassccatlink).

## Contents

- [Device support](#device-support)
- [Help add or test your device](#help-add-or-test-your-device)
- [Before you start: use a second CatLink account](#before-you-start-use-a-second-catlink-account)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entities](#entities)
- [Migrating from hasscc/catlink](#migrating-from-hassccatlink)
- [Troubleshooting](#troubleshooting)
- [Credits](#credits)
- [Development](#development)
- [License](#license)

## Device support

> [!WARNING]
> **Only the SCOOPER SE 2 and cat profiles have been tested on real hardware.**
>
> - **SCOOPER SE 2** (called `C08` in the CatLink API) and **cat profiles**: the maintainer owns
>   these. All readings were checked live against the official app. The controls (switches and
>   selects) send exactly what the official app sends, but not every one of them was tried on the
>   device.
> - **All other devices**: the code was matched against the official app's code, but **nobody has
>   tested it on real hardware yet**. It may show wrong values or not work at all.
>
> If you own one of the untested devices, please tell us how it works, good or bad. See
> [Help add or test your device](#help-add-or-test-your-device).
>
> Devices marked **beta** are only in a pre-release, waiting for test reports. You get them only
> if you turn on pre-releases (see below).

| Device | API `deviceType` | Status |
| --- | --- | --- |
| SCOOPER SE 2 | `C08` | Verified on hardware (controls: payloads match the app, not all tried) |
| Cat profiles | — | Verified on hardware |
| Scooper (SE / Pro) | `SCOOPER` | Matched to the app's code, not tested on hardware |
| Scooper C1 | `LITTER_BOX_599` | Matched to the app's code, not tested on hardware |
| Scooper Pro Ultra | `VISUAL_PRO_ULTRA` | Limited (read-only sensors), not tested on hardware |
| Feeder | `FEEDER` | Matched to the app's code, not tested on hardware |
| PurePro water fountain | `PUREPRO` | Matched to the app's code, not tested on hardware |

Other device types show up as "Limited support" during setup and get almost no entities. Whether
you add them or not, Home Assistant shows a repair notice under **Settings → System → Repairs**
asking for help to support them.

## Help add or test your device

To add a device, or to confirm that an untested one works, we need four things from you:

1. **The model** as named in the CatLink app (and its `deviceType`, if you know it).
2. **The diagnostics file.** Go to **Settings → Devices & services → CatLink**, open the menu (⋮)
   and choose **Download diagnostics**. It contains what the CatLink API returns for your devices.
   Your email, phone number, password, tokens, device IDs, serial numbers, MAC addresses and Wi-Fi
   name are removed. Open it and check before you share it.
3. **Screenshots** of the device page in the CatLink app next to the same device in Home Assistant.
4. **What you tested**: which readings match the app, and which controls made the device react.

Send them with the [Device support / test report](https://github.com/sibest19/hass-catlink/issues/new?template=new_device.yml)
form: drag the diagnostics file and the screenshots into the form. For an unsupported device, the
**Learn more** link in the repair notice opens the form already filled in.

### Try a beta

New devices are first released as a beta (a GitHub pre-release such as `3.1.0b1`). You only get
betas if you turn them on:

- **Marketplace** (Home Assistant 2026.11 and later): open **CatLink** in the Marketplace and turn
  on its **Pre-release** switch.
- **HACS** (before 2026.11): HACS creates a **Pre-release** switch for each repository, disabled by
  default. Go to **Settings → Devices & services → HACS**, open the CatLink repository, enable the
  switch and turn it on.

The beta then shows up as an update. Turn the switch off to get only stable releases again; to
leave a beta right away, pick the latest stable version from the CatLink menu (⋮ →
**Redownload**). Please report back with the same form, even if everything works.

## Before you start: use a second CatLink account

> [!IMPORTANT]
> CatLink allows **only one active login per account**. When Home Assistant logs in, your phone
> app is logged out. When the app logs back in, Home Assistant's token stops working, and the
> integration logs in again by itself. The two keep kicking each other out.

To avoid this:

1. Create a second CatLink account (a different email or phone number).
2. In the CatLink app, signed in with your main account, share your devices and cats with the second account.
3. Use the second account in Home Assistant. Keep using your main account on your phone.

## Installation

You need **Home Assistant 2026.3.0 or newer**.

### Option 1: Marketplace or HACS (recommended)

From Home Assistant 2026.11, HACS is built in as the **Marketplace**. On older versions, install
[HACS](https://hacs.xyz/) first.

Click this button to open the repository in your Home Assistant:

[![Open your Home Assistant instance and open a repository in the Marketplace.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sibest19&repository=hass-catlink&category=integration)

It opens HACS before 2026.11 and the Marketplace from 2026.11. Until this integration is in the
default catalog, Home Assistant offers to add it as a custom repository. Accept, then download it.

Or add it by hand:

1. Open the Marketplace (or HACS).
2. Open the menu (three dots, top right) and choose **Custom repositories**.
3. Enter `https://github.com/sibest19/hass-catlink` and pick the type **Integration**.
4. Search for **CatLink** and download it.
5. Restart Home Assistant.

### Option 2: Manual

1. Download the [latest release](https://github.com/sibest19/hass-catlink/releases/latest).
2. Copy the `custom_components/catlink` folder into the `custom_components` folder of your Home
   Assistant config directory. The result is `<config>/custom_components/catlink/manifest.json`.
3. Restart Home Assistant.

### Add the integration

After the restart, click this button, or go to **Settings → Devices & services → Add integration**
and search for **CatLink**:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=catlink)

## Configuration

Setup is done in the UI. There is no YAML configuration.

1. **Sign-in method.** Choose **Email address** or **Phone number**, the same way you sign in to
   the CatLink app.
2. **Credentials.**
   - Email: your email address and password.
   - Phone: your phone number **with the country code**, for example `+447911123456`, and your
     password. Without the country code the country is guessed, and the guess is usually wrong.
   - **Server region** (optional): *Detect automatically* (default), *Global*, *China*,
     *United States* or *Singapore*. Automatic tries each server until one accepts the login. If
     you know your region, pick it: a wrong password then costs one failed attempt instead of four.
3. **Devices.** The integration lists the devices on the account. Each is marked "Supported" or
   "Limited support". Supported devices are pre-selected. You also set the **refresh interval**
   (30 to 3600 seconds, default 60).

Cats on the account are always added, each as its own device.

You can change the device selection and refresh interval later: **Settings → Devices & services →
CatLink → Configure**. The integration reloads when you save. Devices shared with the account after
setup are picked up automatically, unless you have narrowed the selection down.

If CatLink refuses the saved password (for example after you change it), Home Assistant shows
**Re-authentication required** under **Settings → Devices & services**. Click it and sign in again;
your devices and entities stay as they are.

## Entities

Entity names below are the English names you see in Home Assistant. Home Assistant puts the
device name in front, for example "Litter box Litter weight". Italian translations are included.

Labels used in the tables:

- **Diagnostic** / **Config**: shown in the diagnostic or configuration section of the device page.
- **Disabled**: created but disabled by default. Enable it on the entity's settings page if you need it.

Values marked "today" reset every day, like the counters in the app. Cat values show the same
numbers as the cat's page in the CatLink app.

### SCOOPER SE 2 (`C08`)

| Type | Entities |
| --- | --- |
| Sensor | State (Idle, Cleaning, Leveling litter, Emptying, Paused, Cancelling), Error, Last event, Litter weight, Litter days left, Cleanings today, Manual cleanings, Deodorant days left, Litter box visits today, Average weight, Average duration |
| Sensor (Diagnostic) | Wi-Fi signal; Wi-Fi network, Notifications, Tracked pets (Disabled) |
| Binary sensor (Diagnostic) | Connectivity |
| Select | Action (Clean: start / pause / cancel, Level litter: start / pause) |
| Select (Config) | Mode (Auto, Manual, Scheduled), Litter type (Bentonite, Mixed), Safe time (1 to 30 minutes) |
| Switch (Config) | Quiet mode, Auto burial, Continuous cleaning, Child lock, Indicator light, Keypad tone, Automatic pet weight update, Kitten mode |
| Switch (Config) | Notify: cat visit, Notify: bin full, Notify: replace waste bag, Notify: clean litter box, Notify: replace deodorant, Notify: anti-pinch triggered, Notify: firmware update; Notify: low litter, Notify: low litter bin capacity (Disabled, the app has no setting for these) |

### Scooper (`SCOOPER`)

| Type | Entities |
| --- | --- |
| Sensor | State (Idle, Running, Needs reset), Error, Last event, Litter weight, Litter days left, Total cleanings, Manual cleanings, Deodorant days left, Temperature, Humidity |
| Binary sensor (Diagnostic) | Connectivity |
| Select | Action (Start, Pause) |
| Select (Config) | Mode (Auto, Manual, Scheduled, Empty) |

### Scooper C1 (`LITTER_BOX_599`)

| Type | Entities |
| --- | --- |
| Sensor | State (Idle, Cleaning, Emptying, Resetting, Changing bag), Error, Last event, Waste bin status (Normal, Almost full, Full), Litter weight, Litter days left, Total cleanings, Manual cleanings, Deodorant days left |
| Sensor (Diagnostic) | Knob position; Last sync (Disabled) |
| Binary sensor (Diagnostic) | Connectivity |
| Select | Action (Clean, Empty, Cancel), Waste bag (Change bag, Reset) |
| Select (Config) | Mode (Auto, Manual, Scheduled), Bin full sensitivity (Level 1 to 4) |
| Button (Config) | Reset litter, Reset deodorant |

### Scooper Pro Ultra (`VISUAL_PRO_ULTRA`), limited

Read-only. The app controls this model over a different channel that the integration does not use.

| Type | Entities |
| --- | --- |
| Sensor | Last event, Litter days left, Deodorant days left, Total cleanings |

### Feeder (`FEEDER`)

| Type | Entities |
| --- | --- |
| Sensor | State, Weight, Error, Last event |
| Button | Feed |
| Number | Portions (1 to 10, used by the Feed button) |

### PurePro water fountain (`PUREPRO`)

| Type | Entities |
| --- | --- |
| Sensor | State (Flowing, Eco, Smart), Last event, Water level, Filter days left, Temperature (heater temperature, only when a heater is attached) |
| Binary sensor | Light |
| Binary sensor (Diagnostic) | Connectivity |
| Select | Mode (Flowing, Eco, Smart) |

### Cats

| Type | Entities |
| --- | --- |
| Sensor | Health status, Weight, Age (years), Age (months), Gender (Male, Female, Neutered male, Neutered female), Breed, Birthday, Avatar, Litter box visits today, Urinations today, Defecations today, Drinks today, Food eaten today |

Weights follow your Home Assistant unit system: kg and g with the metric system, lb and oz with the
US customary system, whatever unit the CatLink app is set to. To use another unit for one entity,
change it in the entity's settings.

### Action: `catlink.request_api`

An advanced action that calls a CatLink API path with your account and shows the reply as a
notification. It is meant for debugging and for helping add new devices. Target any CatLink sensor.

```yaml
action: catlink.request_api
target:
  entity_id: sensor.litter_box_state
data:
  api: token/device/union/list/sorted
  params:
    key: val
```

## Migrating from hasscc/catlink

This integration uses the same `catlink` domain. Your config entry and entities carry over.

1. In HACS, remove the `hasscc/catlink` custom repository. Do **not** remove the CatLink
   integration from **Settings → Devices & services**.
2. Install this repository as described in [Installation](#installation). It replaces the files in
   `custom_components/catlink`.
3. Restart Home Assistant.

Existing entities keep their entity IDs. New entities get entity IDs generated by Home Assistant
from the device and entity name.

### Breaking changes

Check your automations, scripts, templates and dashboards for these:

- **Removed entities** (Home Assistant removes them from the registry automatically):
  - `occupied` sensor on litter boxes. It was a guess based on litter weight, not a CatLink value.
  - `online` text sensor. It is replaced by a **Connectivity** binary sensor (on / off).
  - Cat sensors `toilet_weight_avg`, `diet_times` and `sport_active_duration`. The app does not show them.
  - PurePro binary sensors `uv_active`, `heating` and `hair_cleaning`.
  - Scooper Pro Ultra **Mode** and **Action** selects. They never worked: the app controls this model another way.
- **Enum states are now lowercase keys.** Home Assistant translates them in the UI, but
  automations compare the raw value:

  | Entity | Before | After |
  | --- | --- | --- |
  | Litter type | `Bentonite`, `Mixed` | `bentonite`, `mixed` |
  | Safe time | `1 min` … `30 min` | `min_1` … `min_30` |
  | Action (SCOOPER SE 2) | `Clean: start` | `clean_start` |
  | Action (Scooper C1) | `Cleaning`, `Pause` | `cleaning`, `empty`, `cancel` (no pause, like the app) |
  | Waste bag | `Change Bag`, `Reset` | `change_bag`, `reset` |
  | Bin full sensitivity | `Level 1` … `Level 4` | `level_1` … `level_4` |
  | Mode (PurePro) | `Flowing mode`, `Eco-mode`, `Smart mode` | `flowing`, `eco`, `smart` |
  | Waste bin status | `Normal`, `Full` | `normal`, `almost_full`, `full` |
  | Cat Gender | `Male`, `Neutered male` | `male`, `neutered_male` |

  Values that were already lowercase (`auto`, `manual`, `idle`, `running`, `need_reset`, `start`,
  `pause`, `time`, `empty`) are unchanged.
- **The State sensor of the SCOOPER SE 2 and the Scooper C1 shows the app's run state** (for
  example `cleaning`, `emptying`) instead of `running` / `need_reset`. See the
  [entity tables](#entities) for the values.
- **SCOOPER SE 2 "Total cleanings" is now "Cleanings today"** and "Visits" is now "Litter box
  visits today", the counts the app shows. The entity IDs stay the same, but the values now reset
  daily.
- **Values now match the app**, so some numbers change meaning: PurePro "Water level" is the app's
  text instead of a number, "Filter days left" is days instead of a percentage, and "Temperature"
  is the heater temperature. Scooper and Scooper C1 "Total cleanings" now also count scheduled cleans. Cat
  weight comes from the app's weight card. Countdown sensors show *unknown* instead of `0` when
  the device does not report them.

The full list is in the [changelog](CHANGELOG.md).

## Troubleshooting

### Enable debug logging

Add this to `configuration.yaml` and restart:

```yaml
logger:
  default: warning
  logs:
    custom_components.catlink: debug
```

Or, without a restart: **Settings → Devices & services → CatLink → Enable debug logging**. Reproduce
the problem, then disable it again to download the log.

Logs are in **Settings → System → Logs** (click **Show full logs**), or in `home-assistant.log` in
your config directory.

### Common problems

| Problem | What to do |
| --- | --- |
| Login is rejected but the password is right | Your account is on another server. Pick the **Server region** by hand. For phone sign-in, make sure the number starts with `+` and the country code. |
| The phone app keeps logging you out | Home Assistant and the app share one account. Use a [second account](#before-you-start-use-a-second-catlink-account). |
| A device is missing | Open **Configure** on the integration and select the device. If it is not listed, check that it is shared with the account Home Assistant uses. |
| A value is wrong or an entity is unavailable | Compare it with the official app, then report it (see below). |

### Report a problem

Open an issue using the [issue templates](https://github.com/sibest19/hass-catlink/issues/new/choose).
Include your device model, Home Assistant version, integration version, the debug log and, if
you can, the [diagnostics file](#help-add-or-test-your-device).

> [!CAUTION]
> Before you post a log, remove your **email address, phone number, tokens and device IDs/MAC
> addresses**.

## Credits

This integration builds on [hasscc/catlink](https://github.com/hasscc/catlink) and the work of its
contributors, including Alone, Milos Ljubenovic (milosljubenovic), Fuz2er, toplut
(pantan-cymk), Radosław Zagórski and kingkong1946. The C08 support was based on
[pycatlink](https://github.com/eulemitkeule/pycatlink).

CatLink and the CatLink logo are trademarks of their owner. Home Assistant is a trademark of the
Open Home Foundation. They are used here only to describe what this integration works with. No
affiliation or endorsement is implied.

## Development

Want to help, or add a device? See [CONTRIBUTING.md](CONTRIBUTING.md). Please follow the
[Code of Conduct](CODE_OF_CONDUCT.md).

## License

[Apache License 2.0](LICENSE).
