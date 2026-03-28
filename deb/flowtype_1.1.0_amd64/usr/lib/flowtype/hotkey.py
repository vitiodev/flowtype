import threading
import evdev
from evdev import ecodes


# Shorthand aliases for common modifier names → set of possible evdev keycodes
_ALIASES = {
    'ctrl':  {'KEY_LEFTCTRL',  'KEY_RIGHTCTRL'},
    'alt':   {'KEY_LEFTALT',   'KEY_RIGHTALT'},
    'shift': {'KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT'},
    'super': {'KEY_LEFTMETA',  'KEY_RIGHTMETA'},
    'win':   {'KEY_LEFTMETA',  'KEY_RIGHTMETA'},
    'meta':  {'KEY_LEFTMETA',  'KEY_RIGHTMETA'},
}


def _parse_hotkey(hotkey: str):
    """
    Parse hotkey string into a list of "slot" sets.
    Each slot is a set of evdev keycode strings that satisfy it.
    E.g. "ctrl+alt" → [{'KEY_LEFTCTRL','KEY_RIGHTCTRL'}, {'KEY_LEFTALT','KEY_RIGHTALT'}]
    E.g. "KEY_RIGHTSHIFT" → [{'KEY_RIGHTSHIFT'}]
    """
    parts = [p.strip().lower() for p in hotkey.split('+')]
    slots = []
    for part in parts:
        if part in _ALIASES:
            slots.append(_ALIASES[part])
        else:
            # Accept as-is (uppercase) or try to look up via ecodes
            key_upper = part.upper()
            if not key_upper.startswith('KEY_'):
                key_upper = 'KEY_' + key_upper
            slots.append({key_upper})
    return slots


class HotkeyListener:
    def __init__(self, hotkey='KEY_RIGHTSHIFT', on_press=None, on_release=None):
        self.hotkey = hotkey
        self.on_press = on_press
        self.on_release = on_release
        self._threads = []
        self._running = False
        self._slots = _parse_hotkey(hotkey)
        # Track which slots are currently satisfied
        self._slot_satisfied = [False] * len(self._slots)
        self._combo_active = False
        self._lock = threading.Lock()

    def _key_slot(self, keycode: str):
        """Return the index of the slot this keycode satisfies, or -1."""
        for i, slot in enumerate(self._slots):
            if keycode in slot:
                return i
        return -1

    def _find_keyboards(self):
        keyboards = []
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                if ecodes.EV_KEY in dev.capabilities():
                    keyboards.append(dev)
            except Exception:
                pass
        return keyboards

    def _listen(self, device):
        try:
            for event in device.read_loop():
                if not self._running:
                    break
                if event.type == ecodes.EV_KEY:
                    key_event = evdev.categorize(event)
                    keycode = key_event.keycode
                    # keycode can be a list for keys with multiple aliases
                    if isinstance(keycode, list):
                        keycode = keycode[0]
                    slot_idx = self._key_slot(keycode)
                    if slot_idx < 0:
                        continue
                    fire_press = False
                    fire_release = False
                    with self._lock:
                        if key_event.keystate in (key_event.key_down, key_event.key_hold):
                            self._slot_satisfied[slot_idx] = True
                            if all(self._slot_satisfied) and not self._combo_active:
                                self._combo_active = True
                                fire_press = True
                        elif key_event.keystate == key_event.key_up:
                            was_active = self._combo_active
                            self._slot_satisfied[slot_idx] = False
                            self._combo_active = False
                            if was_active:
                                fire_release = True
                    # Start threads outside the lock to avoid holding it during thread creation
                    if fire_press and self.on_press:
                        threading.Thread(target=self.on_press, daemon=True).start()
                    if fire_release and self.on_release:
                        threading.Thread(target=self.on_release, daemon=True).start()
        except Exception:
            pass

    def start(self):
        self._running = True
        self._threads = []
        self._slot_satisfied = [False] * len(self._slots)
        self._combo_active = False
        self._devices = self._find_keyboards()
        if not self._devices:
            print('[flowtype] ERROR: No keyboard devices found. Add user to "input" group:')
            print('  sudo usermod -aG input $USER  (then re-login)')
            return
        for dev in self._devices:
            t = threading.Thread(target=self._listen, args=(dev,), daemon=True)
            t.start()
            self._threads.append(t)
        print(f'[flowtype] Listening on {len(self._devices)} device(s). Hotkey: {self.hotkey}')

    def stop(self):
        self._running = False
        # Close devices to unblock read_loop() in listener threads
        for dev in getattr(self, '_devices', []):
            try:
                dev.close()
            except Exception:
                pass
        self._devices = []
        self._threads = []
