# Decisions

- 2026-09-11 — Use a GTK3/X11 external overlay with the existing Cairo renderer/profile schema and a separate GTK3 studio. Only the user-invoked menu requests focus. Select + Start holds for 600 ms; release both to rearm. Read gamepad nodes without grabbing or recording; coalesce physical/Steam Input mirrors. Per-user .run source installer first; no AppImage or universal-distro claim.

- 2026-09-11 — Superseding physical test: user reported Select + Start is unreliable and triggers Steam controller action-set switching. Installed vendor template confirms Start long-press CHANGE_PRESET, with Desktop L1=Ctrl, R1=Alt, Y=Space. Replaced default with gamepad L1+R1+Y (600 ms) and X11 Ctrl+Alt+Space (immediate). Added Quick menu editor button and desktop action. Isolated exact-hotkey test passes; 47 unit tests pass. User confirmation of replacement physical gesture remains pending.


### 2026-09-11 — Controls and precision update

- Default launch asks Keyboard/Controller/Both; explicit studio opens editor, including across existing processes via Gio HANDLES_COMMAND_LINE. Home toggles crosshair; menu shortcut remains separate. Controller-only retains CtrlAltSpace for Steam Desktop mapping. Precision increments live outside portable presets; dimensions offer .1/.25/.5 and preserve legacy default where needed. Schema minimums and keyboard .25 increments unchanged.

- 2026-09-12 — User explicitly requested private status. Save the SteamOS work as a local commit titled `ProjectScope_v1.20 (SteamOS-Compatability)`, with no public push, release, or version tag. Preserve current runtime behavior for Legion Gaming Mode testing.
