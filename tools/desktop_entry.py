"""Register the same application identity for GTK, GNOME Shell and the icon theme."""
import shutil
import subprocess

APP_ID = 'io.projectscope.Crosshair'


def install_icons(app, data, app_id):
    """Keep a raster fallback for shells without an SVG icon loader."""
    for directory, suffix in (('scalable', 'svg'), ('128x128', 'png')):
        source = app / 'assets' / ('projectscope.' + suffix)
        target = data / 'icons/hicolor' / directory / 'apps' / (app_id + '.' + suffix)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def remove_icons(data, app_id):
    for directory, suffix in (('scalable', 'svg'), ('128x128', 'png')):
        (data / 'icons/hicolor' / directory / 'apps' / (app_id + '.' + suffix)).unlink(missing_ok=True)


def refresh_desktop_caches(data):
    """Refresh only per-user caches; absent desktop utilities are harmless."""
    for name, args, directory in (
        ('gtk-update-icon-cache', ['--force', '--ignore-theme-index'], data / 'icons/hicolor'),
        ('update-desktop-database', [], data / 'applications'),
    ):
        executable = shutil.which(name)
        if executable and directory.is_dir():
            try:
                subprocess.run([executable, *args, str(directory)], check=False,
                               capture_output=True, timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                pass  # Cache generation is optional; the installed files remain valid.


def quoted(path):
    return '"' + str(path).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def install_launchers(app, data, desktop, executable):
    install_icons(app, data, APP_ID)
    body = '\n'.join([
        '[Desktop Entry]', 'Type=Application', 'Version=1.0', 'Name=ProjectScope',
        'Comment=Customize your crosshair · Home toggles visibility',
        f'Exec={quoted(executable)} {quoted(app / "launch.py")}',
        'Icon=' + APP_ID, 'StartupWMClass=' + APP_ID,
        'Terminal=false', 'Categories=Utility;Game;', 'StartupNotify=true', ''])
    launcher = data / 'applications' / (APP_ID + '.desktop')
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(body)
    # Keep old pinned shortcuts usable, without creating a duplicate application-menu entry.
    legacy = data / 'applications/projectscope.desktop'
    if legacy.exists():
        legacy.write_text(body + 'NoDisplay=true\n')
    desktop.mkdir(parents=True, exist_ok=True)
    shortcut = desktop / 'ProjectScope.desktop'
    shortcut.write_text(body); shortcut.chmod(0o755)
    refresh_desktop_caches(data)
    return launcher, shortcut
