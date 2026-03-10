import os
import subprocess
import time


def _ensure_ydotoold():
    """Start ydotoold daemon if not already running."""
    result = subprocess.run(['pgrep', '-x', 'ydotoold'], capture_output=True)
    if result.returncode == 0:
        return  # already running
    print('[flowtype] Starting ydotoold daemon...')
    subprocess.Popen(
        ['sudo', 'ydotoold'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.5)  # give it a moment to start


def inject_text(text, method='ydotool'):
    if not text:
        return
    if method == 'clipboard':
        _inject_clipboard(text)
    else:
        _inject_ydotool(text)


def _inject_ydotool(text):
    _ensure_ydotoold()
    try:
        subprocess.run(
            ['ydotool', 'type', '--key-delay=0', '--', text],
            check=True,
        )
    except FileNotFoundError:
        print('[flowtype] ydotool not found, falling back to clipboard')
        _inject_clipboard(text)
    except subprocess.CalledProcessError as e:
        print(f'[flowtype] ydotool error: {e}')


def _inject_clipboard(text):
    try:
        subprocess.run(['wl-copy', text], check=True)
        subprocess.run(['ydotool', 'key', '29:1', '47:1', '47:0', '29:0'], check=True)
    except Exception as e:
        print(f'[flowtype] Clipboard inject error: {e}')
