<p align="center">
  <img src="assets/banner.svg" alt="ProjectScope — Your crosshair. Your setup." width="100%">
</p>

<p align="center">
  <strong>A native crosshair studio for GNOME.</strong><br>
  Build a design, tune it live, and keep it on screen with the editor closed.
</p>

<p align="center">
  <a href="https://github.com/DMoneyManZ/ProjectScope/releases/latest">Download</a> ·
  <a href="docs/INSTALL.md">Install</a> ·
  <a href="docs/USER-GUIDE.md">User guide</a> ·
  <a href="docs/DEVELOPMENT.md">Development</a> ·
  <a href="https://github.com/DMoneyManZ/ProjectScope/issues">Report an issue</a>
</p>

![ProjectScope editor with its preset library, live preview, and appearance controls](docs/images/editor.png)

## SteamOS preview

A separate [SteamOS preview](docs/STEAMOS.md) adds a standalone Gamescope/X11 overlay, preset studio, and **L1 + R1 + Y** controller menu. It has passed isolated compositor tests on a Steam Deck; physical Gaming Mode and real-game checks are still pending. The GNOME release below is unchanged.

## Make it yours

- **30 ready-made presets.** Start with a minimal dot, a precise cross, a ring, or one of the Sniper, SMG, Shotgun, and Pistol designs.
- **Live editing.** Adjust geometry, color, outline, opacity, rotation, and scale from 0.25× to 8×.
- **Controls within reach.** Toggle, cycle, randomize, save, recolor, and resize with customizable global shortcuts.
- **An independent overlay.** Close the GTK4 editor and the GNOME extension keeps the crosshair available.
- **Portable profiles.** Save personal presets and import or export a single design as validated JSON.
- **Display controls.** Choose a monitor, set offsets, and optionally invert the crosshair against the background.

## Install

**Requires GNOME Shell 50 on Wayland, Python 3.10+, GTK4, PyGObject, Pycairo, and GLib tools.** Other GNOME versions and desktop environments are unsupported by this release. Check your actual GNOME version; an Ubuntu version alone does not establish compatibility.

Download **[ProjectScope-1.0.0-linux.run](https://github.com/DMoneyManZ/ProjectScope/releases/download/v1.0.0/ProjectScope-1.0.0-linux.run)** and **[SHA256SUMS](https://github.com/DMoneyManZ/ProjectScope/releases/download/v1.0.0/SHA256SUMS)** into the same folder, then run:

```bash
sha256sum --check --ignore-missing SHA256SUMS
chmod +x ProjectScope-1.0.0-linux.run
./ProjectScope-1.0.0-linux.run --check
./ProjectScope-1.0.0-linux.run
```

Proceed only when the checksum succeeds. The dependency check is read-only; the installer asks before installing into your user account. **Do not run it with sudo.** This is a Python-based runnable installer; system dependencies are installed separately.

**Log out and back in**, then open **ProjectScope** from your application menu. Choose a preset and press **Home** to toggle it.

Missing libraries? Run `./ProjectScope-1.0.0-linux.run --install-dependencies` for the optional Ubuntu/Debian dependency setup, then repeat the check. It uses your system package manager, requires internet access and administrator authorization, and does not upgrade GNOME.

See [Installation](docs/INSTALL.md) for dependency packages, source installation, extraction, updates, and removal.

## Default shortcuts

| Keys | Action |
|---|---|
| Home | Show / hide |
| Page Up / Page Down | Previous / next saved preset |
| Pause | Random design |
| Insert | Save under the current preset name |
| End | Next color |
| Shift + Page Up / Page Down | Increase / decrease size |
| Ctrl + Page Up / Page Down | Increase / decrease thickness |

Change or disable any action in **Settings**. Saving under an existing name replaces your personal copy; rename first to keep a separate variant. [Read the user guide →](docs/USER-GUIDE.md)

## Pick a starting point

![Twenty-four weapon-style presets arranged by Sniper, SMG, Shotgun, and Pistol](support/preset-gallery.png)

The gallery shows 24 of the 30 stock designs. Every preset is editable. These are visual styles; they do not detect weapons, track recoil, or predict bullet impact. [Explore the preset guide →](support/PRESET-GUIDE.md)

<details>
<summary><strong>See the overlay in use</strong></summary>

![ProjectScope crosshair overlay in a desktop session](docs/images/overlay.png)

</details>

## How it works

ProjectScope pairs a native Python/GTK4 editor with a GNOME Shell extension. The editor saves settings and profiles; the extension draws a click-through overlay at a chosen monitor's center, with optional offsets. It does not read game memory, inject into games, or automate input.

Game and server rules still apply. Overlay permission and anti-cheat compatibility are not guaranteed, and a monitor-centered mark may differ from a game's actual aim. See [compatibility and limits](docs/USER-GUIDE.md#compatibility-and-resource-use) and the [recorded validation](VALIDATION.md).

## Build with us

See [Development](docs/DEVELOPMENT.md) for the source layout and checks, and [Contributing](CONTRIBUTING.md) for useful bug reports and changes.

## Support development

ProjectScope is free and open source. If it helps you, you can [support development with PayPal](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=demurphy242%40gmail.com&item_name=Support+ProjectScope+development&currency_code=USD). Choose any amount; contributions are optional and help support maintenance and improvements.

## License

[GNU General Public License v3.0](LICENSE) (`GPL-3.0-only`).

Copyright © 2026 DMoneyManZ.
