"""Match every SteamOS window to the desktop launcher and its taskbar icon."""
from pathlib import Path

APP_ID = 'io.projectscope.SteamOS'
ROOT = Path(__file__).resolve().parents[2]


def apply_window_identity(window):
    """Call before realizing a GTK3 window (including transient menus)."""
    window.set_wmclass('projectscope-steamos', APP_ID)
    window.set_icon_name(APP_ID)
    # Keep source-tree previews identifiable even before the icon is installed.
    window.set_icon_from_file(str(ROOT / 'assets/projectscope.png'))
