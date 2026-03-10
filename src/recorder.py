import threading
import numpy as np
import sounddevice as sd


class Recorder:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self._frames = []
        self._recording = False
        self._lock = threading.Lock()
        self._stream = None

    def _callback(self, indata, frames, time, status):
        if self._recording:
            with self._lock:
                self._frames.append(indata.copy())

    def start(self):
        self._frames = []
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            callback=self._callback,
        )
        self._stream.start()

    def stop(self):
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if self._frames:
                audio = np.concatenate(self._frames, axis=0).flatten()
            else:
                audio = np.array([], dtype='float32')
            self._frames = []
        return audio
