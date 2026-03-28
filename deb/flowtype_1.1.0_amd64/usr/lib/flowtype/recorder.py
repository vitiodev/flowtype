import threading
import numpy as np
import sounddevice as sd


class Recorder:
    """Records audio via a persistent stream to minimise open/close latency."""

    def __init__(self, sample_rate=16000, device=None, silence_threshold=0.01):
        self.sample_rate = sample_rate
        self.device = device                      # None = system default
        self.silence_threshold = silence_threshold
        self._frames = []
        self._recording = False
        self._lock = threading.Lock()
        self.amplitude_callback = None
        self._stream = self._open_stream()

    def _open_stream(self):
        device = self.device
        channels = 1
        # If the device doesn't support mono, use its default channel count
        try:
            if device is not None:
                info = sd.query_devices(device, 'input')
                if info['max_input_channels'] < 1:
                    raise sd.PortAudioError("Device has no input channels")
                if info['max_input_channels'] < channels:
                    channels = info['max_input_channels']
        except Exception:
            device = None
            channels = 1
        try:
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=channels,
                dtype='float32',
                device=device,
                callback=self._callback,
            )
        except sd.PortAudioError:
            # Last resort: system default device
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                device=None,
                callback=self._callback,
            )
        stream.start()
        return stream

    def _callback(self, indata, frames, time, status):
        if self._recording:
            with self._lock:
                self._frames.append(indata.copy())
            cb = self.amplitude_callback
            if cb is not None:
                cb(indata.copy())

    def start(self):
        with self._lock:
            self._frames = []
        self._recording = True

    def stop(self):
        self._recording = False
        with self._lock:
            if self._frames:
                audio = np.concatenate(self._frames, axis=0).flatten()
            else:
                audio = np.array([], dtype='float32')
            self._frames = []
        return audio

    def close(self):
        self._recording = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
