# ProjectScope for SteamOS

An early SteamOS preview with a transparent crosshair, preset studio, and controller quick menu. Uses the existing ProjectScope icon, preset format and GPL-3.0 license.

## Install

Download `ProjectScope-SteamOS-0.1.0-preview-linux.run`, open a terminal in its folder and run:

```sh
python3 ProjectScope-SteamOS-0.1.0-preview-linux.run --check
python3 ProjectScope-SteamOS-0.1.0-preview-linux.run --install
```

Open **ProjectScope SteamOS** from the application menu or its Desktop shortcut. Choose **Keyboard**, **Controller** or **Start using both control options**. The overlay starts automatically; choose a preset in the studio. Closing the studio leaves the overlay running. **Quit ProjectScope**, in the quick menu or **Controls & settings**, closes both. The Desktop shortcut also offers quick-menu, show/hide and stop actions.

The installer writes only below your home directory. Do not use sudo or disable SteamOS read-only protection. Application updates preserve personal presets. This `.run` bundle contains application source; it is **not an AppImage** and uses installed system libraries.

Dependencies: Python 3.10+, GTK 3, PyGObject with the Cairo binding, Pycairo, GdkX11, Gio/GSettings with a session bus, `glib-compile-schemas`, and `xprop`. Gamescope is required for Gaming Mode; a composited X11 session is required for Desktop preview. All runtime dependencies were already present on the tested SteamOS 3.8.16 device.

For Ubuntu X11 desktops, the corresponding packages are:

```sh
sudo apt install python3-gi python3-gi-cairo python3-cairo gir1.2-gtk-3.0 libglib2.0-bin x11-utils
```

This standalone backend does not require GNOME. Desktop Wayland sessions outside Gamescope are not supported by this preview; Xwayland alone does not guarantee a global desktop overlay. Fedora, Bazzite, Arch and Legion/Steam Machine hardware require their own validation before being listed as tested platforms.

## L1 + R1 + Y menu

While the overlay is running, **hold L1 + R1 + Y for 0.6 seconds** to open or close the quick menu. L1 and R1 are the top shoulder buttons, also labeled LB and RB. In a gamepad layout, release all three buttons before using the chord again. The Desktop keyboard shortcut activates immediately and rearms when Space/Y is released; holding the bumpers is allowed. The Deck’s default Desktop layout maps this combo to **Ctrl + Alt + Space**, which ProjectScope registers as a desktop shortcut. You can also press that keyboard shortcut directly or use the studio’s **Quick menu** button.

- D-pad or left stick: move through actions.
- A: choose the action.
- B: return to the game.
- Touch or mouse: choose any button.

The same listener runs in Gaming Mode and X11 Desktop Mode. It reads only accessible Linux gamepad devices exposing standard L1, R1 and Y buttons, without grabbing them. The game can still receive gamepad button presses, so game actions assigned to those buttons may also fire. Steam Input layouts that hide or remap these buttons can prevent the chord from reaching ProjectScope. Keyboard mode registers the shortcuts below on the reachable Xwayland servers in the same Gamescope session. Controller mode keeps Ctrl + Alt + Space as the Deck Desktop-layout bridge. It does not read keyboard devices or record keyboard/controller events.

The main overlay remains non-interactive. Only the menu you explicitly open requests focus. Closing it releases that focus. The menu's **Open full editor** action opens the separate studio; during Gaming Mode you may need to select ProjectScope from Steam's running applications to see the full editor.

If your controller is not accessible, use the desktop actions or `projectscope-steamos menu`. Do not add blanket input-device permissions. Controller discovery retries when devices connect.

## Keyboard controls and precision

Keyboard and Both modes use Home to show/hide, Page Up/Down for previous/next preset,
Pause to randomize, Insert to save the current named preset, End to cycle colors,
Shift + Page Up/Down to change size, and Ctrl + Page Up/Down to change thickness.
Ctrl + Alt + Space opens the menu in every mode. Switch modes in **Controls & settings**.
The startup tiles support mouse, keyboard arrows/Enter, D-pad and left stick + A.
The full preset editor supports mouse and keyboard; raw controller navigation is for
the startup screen and quick menu.

Size, dot radius, arm/ring dimensions and outline width have compact **0.1 / 0.25 / 0.5**
step selectors under their numeric fields. Each field remembers its step. The existing
step is the initial default; choosing another step does not change the current value.
You can also type a precise value. Portable preset minimums are retained; use overall
size to reduce the rendered crosshair further. Keyboard size/thickness shortcuts still
use 0.25 steps. Opacity and rotation retain their existing increments.

## Gaming Mode

1. In Desktop Mode, install and open ProjectScope SteamOS.
2. Add its launcher to Steam as a **non-Steam game** (use the Desktop shortcut's Add to Steam action if available). The executable is `/home/deck/.local/bin/projectscope-steamos` on a standard Deck account.
3. Return to Gaming Mode and launch ProjectScope. Do not force Proton; this is a native Linux application.
4. Choose your control option, then use Steam to start your game while keeping ProjectScope running.
5. Hold L1 + R1 + Y to access the quick menu. Use **Back to game** or B to dismiss it.

This sequence is prepared for physical Gaming Mode testing. Do not interpret the isolated compositor test below as a completed real-game compatibility check.

## Commands

```sh
~/.local/bin/projectscope-steamos             # Choose controls
~/.local/bin/projectscope-steamos studio      # Open full editor directly
~/.local/bin/projectscope-steamos overlay     # Run Gamescope overlay
~/.local/bin/projectscope-steamos overlay --desktop-preview
~/.local/bin/projectscope-steamos menu        # Toggle quick menu
~/.local/bin/projectscope-steamos toggle
~/.local/bin/projectscope-steamos next
~/.local/bin/projectscope-steamos previous
~/.local/bin/projectscope-steamos status
~/.local/bin/projectscope-steamos stop
~/.local/bin/projectscope-steamos profile ./my-preset.json
```

The CLI uses the same account's session bus. Start/stop is single-instance per desktop login. Invalid imports leave the last valid preset intact. Changes are rendered on settings events, rather than continuously redrawing the crosshair.

Personal presets: `${XDG_DATA_HOME:-$HOME/.local/share}/projectscope/presets`.

Uninstall:

```sh
~/.local/bin/projectscope-steamos stop
python3 ~/.local/share/projectscope-steamos/app/tools/install_steamos.py --uninstall
```

## Verified and remaining checks

Verified on actual Steam Deck hardware, SteamOS 3.8.16 and Gamescope 3.16.23.4, using an isolated headless compositor and a synthetic game:

- 32-bit RGBA window, Gamescope external-overlay property and empty input region.
- Game keeps focus and receives clicks through the crosshair.
- Composited pixel checks: background stays visible; cyan crosshair appears at the center.
- Live hide/show commands change the composited result.
- Quick menu takes focus only when opened; closing returns focus to the synthetic game.
- Quit from the quick menu cleanly ends the overlay.
- Startup tiles fit the display; simulated controller navigation selects and saves the mode.
- Actual X11 keyboard shortcuts, live mode switching, randomization and preset saving.
- Precision step selection preserves the value and the next adjustment changes it by 0.1.
- Studio has a matching taskbar window class and a 128 × 128 icon.

Controller chord timing, cancellation, release-to-rearm and reset behavior are covered by unit tests. The Deck exposes a readable standard gamepad with all three buttons. The earlier Select + Start shortcut conflicted with Steam’s Start long-press action-set switch. The user physically confirmed both L1 + R1 + Y on the built-in Deck controller and Ctrl + Alt + Space on a mini keyboard open the menu in Desktop Mode. The keyboard shortcut also passed the isolated menu-focus test. Physical navigation/dismissal and Gaming Mode use remain unverified.

Remaining: real Gaming Mode with Steam and a real game, Steam performance HUD coexistence, external monitor/scaling changes, sleep/resume, other controllers/devices and desktop compositors. The legacy Gamescope external-overlay slot may conflict with MangoHud/performance overlays; simultaneous operation is not promised. Background inversion and fading labels are not included.

Tests: `python3 -m unittest discover -s tests -v`. Developers with Gamescope can run `python3 tests/run_gamescope_smoke.py` and `python3 tests/run_gamescope_smoke.py --studio`. The runner creates a separate compositor and temporary settings. Never run the inner `gamescope_smoke.py` directly in a real game session; its input and capture probes are for a disposable synthetic scene only.

Protocol references: [Valve Gamescope implementation](https://github.com/ValveSoftware/gamescope/blob/master/src/steamcompmgr.cpp), [Gamescope control protocol](https://github.com/ValveSoftware/gamescope/blob/master/protocol/gamescope-control.xml).

### Shortcut correction

Select + Start is no longer the default: Steam uses a Start long-press to change its Desktop/Gamepad controller action set. That changes input mappings, not the operating-system desktop session. The replacement uses the verified vendor mappings L1 → Ctrl, R1 → Alt, Y → Space in the default Deck Desktop action set. Customized Steam Input layouts may need the keyboard shortcut mapped explicitly.

## AppImage preparation

`python3 tools/build_appimage.py` assembles `dist/appimage/ProjectScope-SteamOS.AppDir`
(AppRun, root `.desktop` with relative `Exec=`, root icon and `.DirIcon`, `usr/bin` launcher,
compiled schema and application source under `usr/lib/projectscope-steamos`) and validates it,
including `desktop-file-validate` when available. If `appimagetool` is on `PATH` it also writes
`ProjectScope-SteamOS-0.1.0-preview-x86_64.AppImage`; otherwise it stops after the AppDir with a
warning (`--require-tool` turns that into a failure, `--check` only re-validates an existing AppDir).

⚠ The AppDir uses the host Python, GTK 3, PyGObject and Pycairo exactly like the `.run` installer;
it does **not** bundle them. Producing a self-contained AppImage that runs on hosts without those
libraries still requires linuxdeploy with linuxdeploy-plugin-gtk on a build machine. No AppImage
has been built or tested on SteamOS yet.
