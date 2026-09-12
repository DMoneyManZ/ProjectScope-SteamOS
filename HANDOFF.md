## Current checkpoint — 2026-09-12 private Legion testing

User reports the preview worked and authorized a local commit named
`ProjectScope_v1.20 (SteamOS-Compatability)` on `feature/steamos-overlay`.
Keep this work private: do not push to the public origin or publish a release.
The sections below describe historical, pre-commit checkpoints.

Fresh verification: 67 Python tests, all 30 stock presets, strict schema compilation,
Python compilation, GJS draw/cycle/color/random checks, SteamOS bundle build,
SHA256 checks, payload/source comparison, and installer dependency check passed.
The local system lacks python3-gi-cairo; a matching Ubuntu package was extracted
under /tmp/projectscope-verify-deps for tests only. No system package was installed.
Use PYTHONPATH=/tmp/projectscope-verify-deps/python while that temporary copy exists.
The static review found no Critical/Important blocker to a private local checkpoint.

Next: use the private installer to test Legion Gaming Mode with a real game.
Gaming Mode/game/HUD coexistence, suspend/resume and other hardware remain unverified.
The user did not request a session switch; do not log out or change desktop mode.
The v1.20 label identifies this checkpoint; existing bundle filenames retain
0.1.0-preview. No public release or version tag is created by this checkpoint.

---

## Historical checkpoint — 2026-09-11 controls/precision/icons

Branch feature/steamos-overlay remains uncommitted (do not mistake untracked implementation for absent work).
Default launch opens Welcome; Keyboard/Controller/Both saved in control-mode; explicit studio reaches full editor.
Per-dimension .1/.25/.5 bubbles persist in precision-steps, preserving values; Ubuntu installed editor also patched.
Full keyboard actions, controller stick/dpad selection, Quit, raster icons and shared taskbar identity integrated.
67 tests + 30 preset validation pass, headless studio/overlay/lifecycle smoke pass, GTK4 precision/icon smoke pass.
Latest installed preview rebuilt in dist/steamos and Downloads/ProjectScope-SteamOS-Preview, also Deck Downloads.
Deck active units: projectscope-steamos-overlay, projectscope-steamos-welcome. Studio unit absent (user closed earlier).
Local Ubuntu editor unit: projectscope-precision-editor. Local source-only rollback copies: /tmp/projectscope-before-precision-icons.
Sol capture-only dataset at Documents/DatasetTraining/ProjectScope-SteamOS: 17 validated synthetic examples; no training.
Real Gaming Mode/Steam/game/HUD and physical new chooser navigation still pending. Do not rework SSH.

Git state:
```
 M .github/workflows/checks.yml
 M README.md
 M extension/schemas/org.gnome.shell.extensions.projectscope.gschema.xml
 M projectscope/app.py
 M tests/test_desktop.py
 M tools/desktop_entry.py
 M tools/install.py
?? CONTEXT.md
?? DECISIONS.md
?? HANDOFF.md
?? LEARNING.md
?? PLAN.md
?? assets/projectscope.png
?? docs/STEAMOS.md
?? projectscope/gamescope/
?? projectscope/precision.py
?? tests/gamescope_smoke.py
?? tests/run_gamescope_smoke.py
?? tests/steamos_lifecycle_smoke.py
?? tests/steamos_studio_smoke.py
?? tests/test_controller_chord.py
?? tests/test_gamescope.py
?? tests/test_menu_hotkey.py
?? tests/test_precision_navigation.py
?? tests/test_steamos_controls.py
?? tests/test_steamos_hotkeys.py
?? tests/test_steamos_install.py
?? tools/build_steamos.py
?? tools/install_steamos.py
?? tools/steamos_installer_main.py
```

# ProjectScope SteamOS handoff

2026-09-11. Branch `feature/steamos-overlay`, base `62a3399`. Changes are uncommitted and not published.

Installed preview is running in Desktop Mode. The initial Select + Start confirmation was superseded: user reported it changed Steam control layouts and did not reliably open the quick menu. Replacement L1 + R1 + Y and Ctrl + Alt + Space are installed and user-confirmed to open the menu in Deck Desktop Mode. Do not ask to repeat menu-opening checks. Touchscreen is unavailable; use controller/keyboard. Next: Gaming Mode with a real game, navigation/dismissal, and performance HUD coexistence. Switching sessions requires the user to finish/save current desktop work; do not trigger a logout without coordinating it.

Source installer: `dist/steamos/ProjectScope-SteamOS-0.1.0-preview-linux.run`. Runtime source in `projectscope/gamescope/`; setup guide `docs/STEAMOS.md`. Isolated tests: `tests/run_gamescope_smoke.py` and `--studio`. Never run inner input/capture smoke directly in a normal game session.

Sol collection contains 12 curated synthetic examples at the separate Documents/DatasetTraining/ProjectScope-SteamOS folder. No training started and no raw event, transcript or credential collection.

Local unit-test dependency: temporary PYTHONPATH=/tmp/projectscope-test-deps supplies missing gi-cairo binding without system modification. CI dependency list includes it.

Worktree state before this checkpoint:
```text
 M .github/workflows/checks.yml
 M README.md
?? CONTEXT.md
?? DECISIONS.md
?? LEARNING.md
?? PLAN.md
?? docs/STEAMOS.md
?? projectscope/gamescope/
?? tests/gamescope_smoke.py
?? tests/run_gamescope_smoke.py
?? tests/steamos_studio_smoke.py
?? tests/test_controller_chord.py
?? tests/test_gamescope.py
?? tests/test_steamos_install.py
?? tools/build_steamos.py
?? tools/install_steamos.py
?? tools/steamos_installer_main.py
```

## Latest controller fix

2026-09-11 — Superseding physical test: user reported Select + Start is unreliable and triggers Steam controller action-set switching. Installed vendor template confirms Start long-press CHANGE_PRESET, with Desktop L1=Ctrl, R1=Alt, Y=Space. Replaced default with gamepad L1+R1+Y (600 ms) and X11 Ctrl+Alt+Space (immediate). Added Quick menu editor button and desktop action. Isolated exact-hotkey test passes; 47 unit tests pass. User confirmation of replacement physical gesture remains pending.

## Physical replacement shortcut result

2026-09-11 — User physically confirmed both replacement menu-opening methods work in Deck Desktop Mode: L1 + R1 + Y on the built-in controller and Ctrl + Alt + Space on a mini keyboard. User reports the touchscreen is broken; keep controller/keyboard access sufficient. This confirms menu opening only, not physical navigation/dismissal or real Gaming Mode/game/HUD compatibility.
