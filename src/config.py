import json
from pathlib import Path

CONFIG_PATH = Path.home() / '.config' / 'flowtype' / 'config.json'

DEFAULTS = {
    'hotkey': 'KEY_RIGHTSHIFT',
    'model': 'base',
    'language': None,       # None = auto-detect
    'device': 'cpu',        # 'cpu' or 'cuda'
    'sample_rate': 16000,
    'inject_method': 'ydotool',  # 'ydotool' or 'clipboard'
}

def load():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return {**DEFAULTS, **json.load(f)}
    return DEFAULTS.copy()

def save(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)
