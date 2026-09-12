# Context

- 2026-09-11 — ProjectScope SteamOS preview is implemented on feature/steamos-overlay in this isolated worktree. Original GNOME application remains unchanged. User requested Select + Start menu access in Gaming Mode and Desktop Mode. The tested device provides GTK3, Cairo and a readable standard gamepad. Runtime overlay and studio are now active on its X11 desktop.

- 2026-09-11 — User physically confirmed that holding Select + Start opens the quick menu on the Steam Deck in Desktop Mode. This verifies menu opening only; controller navigation, dismissal, and real Gaming Mode/game/HUD coexistence still need physical confirmation.

- 2026-09-11 — Superseding physical test: user reported Select + Start is unreliable and triggers Steam controller action-set switching. Installed vendor template confirms Start long-press CHANGE_PRESET, with Desktop L1=Ctrl, R1=Alt, Y=Space. Replaced default with gamepad L1+R1+Y (600 ms) and X11 Ctrl+Alt+Space (immediate). Added Quick menu editor button and desktop action. Isolated exact-hotkey test passes; 47 unit tests pass. User confirmation of replacement physical gesture remains pending.

- 2026-09-11 — User physically confirmed both replacement menu-opening methods work in Deck Desktop Mode: L1 + R1 + Y on the built-in controller and Ctrl + Alt + Space on a mini keyboard. User reports the touchscreen is broken; keep controller/keyboard access sufficient. This confirms menu opening only, not physical navigation/dismissal or real Gaming Mode/game/HUD compatibility.


### 2026-09-11 — Controls and precision update

- Installed controls/precision/icon update on Deck and local Ubuntu. Deck currently uses projectscope-steamos-overlay plus projectscope-steamos-welcome transient user units; earlier studio unit had already exited. Installed GNOME editor runs projectscope-precision-editor. Live Deck chooser/overlay WM_CLASS matches io.projectscope.SteamOS; both expose 128x128 raster icons. No session mode switch performed.

### 2026-09-12 — Private checkpoint for Legion testing

User reports the preview worked and authorized committing the existing implementation as `ProjectScope_v1.20 (SteamOS-Compatability)`. Keep it local/private; no public push or release. Legion Gaming Mode testing is the next intended use. Fresh 67-test suite, 30 presets, GJS checks and rebuilt SteamOS installer verification pass with the missing local gi-cairo dependency supplied temporarily from /tmp.
