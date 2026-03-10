import json
from pathlib import Path

CONFIG_PATH = Path.home() / '.config' / 'flowtype' / 'config.json'

DEFAULTS = {
    'hotkey':            'KEY_RIGHTSHIFT',
    'model':             'base',
    'language':          None,      # None = auto-detect
    'device':            'cpu',     # 'cpu' or 'cuda'
    'sample_rate':       16000,
    'inject_method':     'auto',    # 'auto', 'ydotool', 'xdotool', 'clipboard'
    # Audio quality
    'audio_device':      None,      # None = system default input device
    'silence_threshold': 0.01,      # amplitude below which audio is treated as silence
    'command_mode':      'none',    # 'none', 'terminal' (paste+Enter), 'shell' (run via shell)
}

# Keys from older config versions that map to current names
_COMPAT = {
    'paste_method': 'inject_method',
}


def load():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        # Migrate old field names
        for old, new in _COMPAT.items():
            if old in data and new not in data:
                data[new] = data.pop(old)
        return {**DEFAULTS, **data}
    return DEFAULTS.copy()


def save(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)
