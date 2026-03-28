"""Voice command matching and execution.

Commands are stored in ~/.config/flowtype/commands.json as a list of:
    {"phrase": "открой терминал", "command": "gnome-terminal", "exact": false}

Matching rules:
- phrase is normalised (lowercase, no punctuation)
- exact=false  → phrase must appear anywhere in the transcribed text
- exact=true   → normalised text must equal the phrase exactly
"""

import json
import re
import subprocess
from pathlib import Path

COMMANDS_PATH = Path.home() / '.config' / 'flowtype' / 'commands.json'

DEFAULT_COMMANDS = [
    {'phrase': 'открой терминал',   'command': 'gnome-terminal',             'exact': False, 'terminal': False},
    {'phrase': 'открыть терминал',  'command': 'gnome-terminal',             'exact': False, 'terminal': False},
    {'phrase': 'открой браузер',    'command': 'xdg-open https://google.com','exact': False, 'terminal': False},
    {'phrase': 'открыть браузер',   'command': 'xdg-open https://google.com','exact': False, 'terminal': False},
    {'phrase': 'открой файловый менеджер', 'command': 'nautilus',            'exact': False, 'terminal': False},
    {'phrase': 'открыть файловый менеджер','command': 'nautilus',            'exact': False, 'terminal': False},
]


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def load_commands() -> list:
    if COMMANDS_PATH.exists():
        try:
            with open(COMMANDS_PATH, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_COMMANDS.copy()


def save_commands(commands: list) -> None:
    COMMANDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(COMMANDS_PATH, 'w', encoding='utf-8') as f:
        json.dump(commands, f, indent=2, ensure_ascii=False)


def _run_in_terminal(shell_cmd: str) -> None:
    """Paste *shell_cmd* into the active terminal window and press Enter."""
    from injector import inject_text
    inject_text(shell_cmd, run_in_terminal=True)


def match_and_run(text: str, commands: list) -> bool:
    """Match *text* against *commands*.  Execute and return True on first match."""
    norm_text = _normalize(text)
    for cmd in commands:
        phrase = cmd.get('phrase', '').strip()
        if not phrase:
            continue
        norm_phrase = _normalize(phrase)
        if cmd.get('exact', False):
            matched = norm_text == norm_phrase
        else:
            matched = norm_phrase in norm_text
        if matched:
            shell_cmd = cmd.get('command', '').strip()
            if shell_cmd:
                print(f'[flowtype] Command matched "{phrase}" → {shell_cmd}')
                if cmd.get('terminal', False):
                    _run_in_terminal(shell_cmd)
                else:
                    subprocess.Popen(shell_cmd, shell=True)
            return True
    return False
