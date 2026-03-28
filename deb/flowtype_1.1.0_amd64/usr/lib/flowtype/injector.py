import os
import subprocess
import time


def _is_wayland():
    return bool(os.environ.get('WAYLAND_DISPLAY'))


def _ensure_ydotoold():
    """Start ydotoold daemon if not already running (Wayland only)."""
    result = subprocess.run(['pgrep', '-x', 'ydotoold'], capture_output=True)
    if result.returncode == 0:
        return
    print('[flowtype] Starting ydotoold daemon...')
    subprocess.Popen(
        ['sudo', 'ydotoold'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.5)


def inject_text(text, method='auto', run_in_terminal=False):
    if not text:
        return
    if method == 'auto':
        # Clipboard paste is always instant regardless of text length.
        # xdotool/ydotool type each character individually — very slow for long text.
        method = 'clipboard'
    if method == 'clipboard':
        if _is_wayland():
            _inject_clipboard_wayland(text)
        else:
            _inject_clipboard_x11(text, run_in_terminal=run_in_terminal)
    elif method == 'xdotool':
        _inject_xdotool(text)
        if run_in_terminal:
            subprocess.run(['xdotool', 'key', 'Return'])
    else:
        _inject_ydotool(text)


def run_shell_command(cmd):
    """Run transcribed text as a shell command in the background."""
    if not cmd:
        return
    print(f'[flowtype] Running shell command: {cmd}')
    try:
        subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f'[flowtype] Shell command error: {e}')


def _inject_ydotool(text):
    _ensure_ydotoold()
    try:
        subprocess.run(
            ['ydotool', 'type', '--key-delay=0', '--', text],
            check=True,
        )
    except FileNotFoundError:
        print('[flowtype] ydotool not found, falling back to xdotool')
        _inject_xdotool(text)
    except subprocess.CalledProcessError as e:
        print(f'[flowtype] ydotool error: {e}')


def _inject_xdotool(text):
    try:
        subprocess.run(
            ['xdotool', 'type', '--clearmodifiers', '--delay', '0', '--', text],
            check=True,
        )
    except FileNotFoundError:
        print('[flowtype] xdotool not found, falling back to clipboard')
        _inject_clipboard_x11(text)
    except subprocess.CalledProcessError as e:
        print(f'[flowtype] xdotool error: {e}')


def _inject_clipboard_wayland(text):
    try:
        subprocess.run(['wl-copy', text], check=True)
        subprocess.run(['ydotool', 'key', '29:1', '47:1', '47:0', '29:0'], check=True)
    except Exception as e:
        print(f'[flowtype] Wayland clipboard inject error: {e}')


_TERMINAL_CLASSES = {
    'gnome-terminal', 'xterm', 'konsole', 'tilix', 'alacritty',
    'kitty', 'terminator', 'xfce4-terminal', 'lxterminal', 'urxvt',
    'st', 'foot', 'wezterm',
}


def _active_window_is_terminal():
    try:
        wid = subprocess.check_output(
            ['xdotool', 'getactivewindow'], text=True
        ).strip()
        out = subprocess.check_output(
            ['xprop', '-id', wid, 'WM_CLASS'], text=True
        ).lower()
        return any(t in out for t in _TERMINAL_CLASSES)
    except Exception:
        return False


def _inject_clipboard_x11(text, run_in_terminal=False):
    try:
        subprocess.run(
            ['xclip', '-selection', 'clipboard'],
            input=text.encode(),
            check=True,
        )
        is_terminal = _active_window_is_terminal()
        paste_key = 'ctrl+shift+v' if is_terminal else 'ctrl+v'
        subprocess.run(['xdotool', 'key', paste_key], check=True)
        if run_in_terminal and is_terminal:
            subprocess.run(['xdotool', 'key', 'Return'], check=True)
    except Exception as e:
        print(f'[flowtype] X11 clipboard inject error: {e}')
