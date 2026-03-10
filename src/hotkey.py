import threading
import evdev
from evdev import ecodes


class HotkeyListener:
    def __init__(self, hotkey='KEY_RIGHTSHIFT', on_press=None, on_release=None):
        self.hotkey = hotkey
        self.on_press = on_press
        self.on_release = on_release
        self._threads = []
        self._running = False

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
                    if key_event.keycode == self.hotkey:
                        if key_event.keystate == key_event.key_down:
                            if self.on_press:
                                self.on_press()
                        elif key_event.keystate == key_event.key_up:
                            if self.on_release:
                                self.on_release()
        except Exception:
            pass

    def start(self):
        self._running = True
        keyboards = self._find_keyboards()
        if not keyboards:
            print('[flowtype] ERROR: No keyboard devices found. Add user to "input" group:')
            print('  sudo usermod -aG input $USER  (then re-login)')
            return
        for dev in keyboards:
            t = threading.Thread(target=self._listen, args=(dev,), daemon=True)
            t.start()
            self._threads.append(t)
        print(f'[flowtype] Listening on {len(keyboards)} device(s). Hotkey: {self.hotkey}')

    def stop(self):
        self._running = False
