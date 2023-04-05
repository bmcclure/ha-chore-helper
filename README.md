# Chore Helper for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

This component allows you to set up and manage all of your recurring household chores
in a flexible way using Home Assistant helpers.

Chore Helper is in its infancy and might not work well for your use case. But it
desperately wants to, so let me know how you'd like to use it!

**This component will set up the following platforms.**

| Platform   | Description                           |
| ---------- | ------------------------------------- |
| `sensor`   | Contains the state for a single chore |
| `calendar` | A Chore calendar for easy tracking    |

This helper is very loosely inspired by the way that the Tody app for Android works,
except it is entirely managed within Home Assistant and benefits from the power of
calendars, automations, and sensors.

## Installation

### Option 1: HACS (Recommended)

1. Add this repository to HACS.
2. Search for "Chore Helper" under "Integrations".
3. Install the integration.
4. Restart Home Assistant.

### Option 2: Manual

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `chore_helper`.
4. Download _all_ the files from the `custom_components/chore_helper/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant.


## Configuration

All configuration is done in the UI.

1. In the HA UI go to "Settings" -> "Devices & Services" -> "Helpers", click the "Create Helper" button, and search for Chore
2. Enter your chore details and submit to add the helper.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[buymecoffee]: https://www.buymeacoffee.com/benmcclure
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/bmcclure/ha-chore-helper.svg?style=for-the-badge
[commits]: https://github.com/bmcclure/ha-chore-helper/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/custom-components/blueprint.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Ben%20McClure%20%40bmcclure-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/bmcclure/ha-chore-helper.svg?style=for-the-badge
[releases]: https://github.com/bmcclure/ha-chore-helper/releases
