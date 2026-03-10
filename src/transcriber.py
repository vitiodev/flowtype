from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self, model='base', device='cpu', language=None):
        self.language = language
        print(f'[flowtype] Loading Whisper model "{model}" on {device}...')
        self.model = WhisperModel(model, device=device, compute_type='int8')
        print('[flowtype] Model ready.')

    def transcribe(self, audio):
        # audio — numpy float32, 16 kHz, mono
        if len(audio) < 1600:  # < 0.1 sec
            return ''
        segments, _ = self.model.transcribe(
            audio,
            language=self.language,
            vad_filter=True,
            vad_parameters={'min_silence_duration_ms': 500},
        )
        return ' '.join(seg.text.strip() for seg in segments).strip()
