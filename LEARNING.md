# Learning

- 2026-09-11 — Actual Deck headless Gamescope verification passed alpha-composited pixel checks, game focus and click-through, live visibility, quick-menu focus restoration, and stop. Studio edit/save/cycle and 1050x700 size checks pass. Cross-device temporary capture moves require copy then unlink. Direct remote child launches did not persist; transient user-session units successfully launched the installed preview. Reviewer found duplicate-pad and batched-release edge cases; both fixed with regression tests.

- 2026-09-11 — User physically confirmed that holding Select + Start opens the quick menu on the Steam Deck in Desktop Mode. This verifies menu opening only; controller navigation, dismissal, and real Gaming Mode/game/HUD coexistence still need physical confirmation.

- 2026-09-11 — Superseding physical test: user reported Select + Start is unreliable and triggers Steam controller action-set switching. Installed vendor template confirms Start long-press CHANGE_PRESET, with Desktop L1=Ctrl, R1=Alt, Y=Space. Replaced default with gamepad L1+R1+Y (600 ms) and X11 Ctrl+Alt+Space (immediate). Added Quick menu editor button and desktop action. Isolated exact-hotkey test passes; 47 unit tests pass. User confirmation of replacement physical gesture remains pending.

- 2026-09-11 — User physically confirmed both replacement menu-opening methods work in Deck Desktop Mode: L1 + R1 + Y on the built-in controller and Ctrl + Alt + Space on a mini keyboard. User reports the touchscreen is broken; keep controller/keyboard access sufficient. This confirms menu opening only, not physical navigation/dismissal or real Gaming Mode/game/HUD compatibility.


### 2026-09-11 — Controls and precision update

- Unscrolled Controls tab expanded studio height to 835; fixed with scroller and verified 1050x700. Gtk SpinButton.spin STEP_FORWARD must receive increment=0 to exercise configured step; increment=1 overrides it. App full Quit must avoid synchronous Dbus self-call. Icon repair includes raster fallback and WM_CLASS identity for every window.
