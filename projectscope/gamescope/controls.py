"""Portable preset edits for SteamOS keyboard and menu actions."""
import random
import uuid
from pathlib import Path
from ..profiles import loads_profile, dumps_profile, validate_profile
from ..storage import save_named_profile, preset_catalog

COLORS = ('#FFFFFF', '#202020', '#00FFFF', '#003D3D', '#FFFF00', '#403300',
          '#00FF66', '#003D18', '#FF88CC', '#401030', '#FFAA33', '#402000')


def random_profile(current, rng=random):
    opacity = validate_profile(current)['style']['opacity']
    family = rng.choice(('Dot', 'Cross', 'Cross dot', 'Ring dot'))
    token = uuid.uuid4().hex[:8]
    return validate_profile({
        'schema_version': 1, 'id': 'random-' + token, 'name': 'Random ' + family + ' ' + token,
        'description': 'Generated from compact FPS-style ranges. Manually editable; no game awareness.',
        'game': 'General FPS',
        'style': {
            'color': rng.choice(('#00FFFF', '#00FF66', '#FFFF00', '#FFFFFF', '#FF66CC')),
            'opacity': opacity, 'outline_color': '#000000', 'outline_width': rng.choice((1, 1.5)),
            'rotation': 0, 'scale': 1,
            'lines': {'enabled': family in ('Cross', 'Cross dot'),
                      'length': rng.choice((3, 4, 5, 6, 7, 8)),
                      'thickness': rng.choice((1, 1.5, 2)), 'gap': rng.choice((2, 3, 4, 5)),
                      'top': rng.choice((True, True, False))},
            'dot': {'enabled': family != 'Cross', 'radius': rng.choice((1, 1.5, 2))},
            'circle': {'enabled': family == 'Ring dot', 'radius': rng.choice((4, 5, 6, 7)),
                       'thickness': rng.choice((1, 1.5))},
        },
    })


def next_color(current):
    profile = validate_profile(current)
    color = profile['style']['color'].upper()
    if color in COLORS:
        index = COLORS.index(color)
    else:
        rgb = [int(color[index:index+2], 16) / 255 for index in (1, 3, 5)]
        index = 0 if sum(channel * weight for channel, weight in zip(rgb, (.2126, .7152, .0722))) > .5 else -1
    index = (index + 1) % len(COLORS)
    profile['style']['color'] = COLORS[index]
    profile['style']['outline_color'] = '#000000' if index % 2 == 0 else '#FFFFFF'
    return profile


def save_current(cfg, directory=None, stock_directory=None):
    """Save under the current name, updating its personal copy and library."""
    from gi.repository import GLib
    from ..settings import ROOT
    directory = Path(directory) if directory is not None else Path(GLib.get_user_data_dir()) / 'projectscope/presets'
    stock_directory = Path(stock_directory) if stock_directory is not None else ROOT / 'presets'
    current = loads_profile(cfg.get_string('profile'))
    directory.mkdir(parents=True, exist_ok=True)
    saved = save_named_profile(current, directory)
    cfg.set_string('profile', dumps_profile(saved))
    cfg.set_strv('preset-library', [dumps_profile(profile)
                                  for _, profile in preset_catalog(stock_directory, directory)])
    return saved
