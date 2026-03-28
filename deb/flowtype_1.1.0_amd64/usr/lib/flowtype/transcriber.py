import io
import wave
import numpy as np
from faster_whisper import WhisperModel


# Initial prompts help the model calibrate spacing and punctuation per language.
# This significantly reduces BPE token boundary errors (e.g. "сноватес тируюи").
_INITIAL_PROMPTS = {
    'ru': 'Привет. Сегодня я расскажу вам о следующем. Итак, начнём.',
    'en': 'Hello. Today I will tell you about the following. Let us begin.',
    'de': 'Hallo. Heute werde ich Ihnen folgendes erklären. Fangen wir an.',
    'fr': 'Bonjour. Aujourd\'hui je vais vous parler de ce qui suit. Commençons.',
}


def _trim_silence(audio: np.ndarray, threshold: float = 0.01, sample_rate: int = 16000) -> np.ndarray:
    """Trim leading and trailing silence by amplitude threshold."""
    if len(audio) == 0:
        return audio
    above = np.abs(audio) > threshold
    if not np.any(above):
        return audio
    first = int(np.argmax(above))
    last = int(len(above) - np.argmax(above[::-1]) - 1)
    pad = int(0.1 * sample_rate)
    first = max(0, first - pad)
    last = min(len(audio) - 1, last + pad)
    return audio[first:last + 1]


def _audio_to_wav_bytes(audio: np.ndarray, sample_rate: int = 16000) -> bytes:
    """Convert float32 numpy audio to WAV bytes (PCM int16, mono)."""
    pcm = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def _join_words(segments) -> str:
    """Join word-level tokens (used when word_timestamps=True)."""
    words = []
    for seg in segments:
        for w in (seg.words or []):
            words.append(w.word)
    return ''.join(words).strip()


def _join_segments(segments) -> str:
    """Join segment texts preserving leading spaces (word boundary markers)."""
    parts = [seg.text.rstrip() for seg in segments if seg.text.strip()]
    return ''.join(parts).strip()


class Transcriber:
    def __init__(self, model='base', device='cpu', language=None, silence_threshold=0.01):
        self.language = language
        self.initial_prompt = _INITIAL_PROMPTS.get(language or '', None)
        self.sample_rate = 16000
        self._model_size = model.split('.')[0]  # strip suffixes like ".en"
        self._silence_threshold = silence_threshold
        print(f'[flowtype] Loading Whisper model "{model}" on {device}...')
        compute_type = 'int8_float16' if device == 'cuda' else 'int8'
        self.model = WhisperModel(model, device=device, compute_type=compute_type)
        print('[flowtype] Model ready.')

    def set_silence_threshold(self, threshold: float):
        self._silence_threshold = threshold

    def transcribe(self, audio: np.ndarray) -> str:
        audio = _trim_silence(audio,
                              threshold=self._silence_threshold,
                              sample_rate=self.sample_rate)
        if len(audio) < 1600:  # < 0.1 sec
            return ''

        # word_timestamps adds DTW alignment overhead — only use it for small
        # models (base/tiny) that need help with word boundaries. Larger models
        # (small/medium/large) produce clean boundaries on their own.
        use_word_ts = self._model_size in ('tiny', 'base')

        segments, _ = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=1,
            word_timestamps=use_word_ts,
            condition_on_previous_text=True,
            initial_prompt=self.initial_prompt,
        )
        return _join_words(segments) if use_word_ts else _join_segments(segments)


class ApiTranscriber:
    def __init__(self, api_url, api_key, model, language=None, silence_threshold=0.01):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.language = language
        self.sample_rate = 16000
        self._silence_threshold = silence_threshold
        print(f'[flowtype] API transcription: {self.api_url}, model={self.model}')

    def set_silence_threshold(self, threshold: float):
        self._silence_threshold = threshold

    def transcribe(self, audio: np.ndarray) -> str:
        import urllib.request
        import urllib.error
        import json
        audio = _trim_silence(audio, self._silence_threshold, self.sample_rate)
        if len(audio) < 1600:
            return ''
        wav_bytes = _audio_to_wav_bytes(audio, self.sample_rate)
        boundary = b'----FlowTypeBoundary'
        body = (
            b'--' + boundary + b'\r\n'
            b'Content-Disposition: form-data; name="model"\r\n\r\n' +
            self.model.encode() + b'\r\n'
        )
        if self.language:
            body += (
                b'--' + boundary + b'\r\n'
                b'Content-Disposition: form-data; name="language"\r\n\r\n' +
                self.language.encode() + b'\r\n'
            )
        body += (
            b'--' + boundary + b'\r\n'
            b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
            b'Content-Type: audio/wav\r\n\r\n' +
            wav_bytes + b'\r\n'
            b'--' + boundary + b'--\r\n'
        )
        req = urllib.request.Request(
            f'{self.api_url}/audio/transcriptions',
            data=body,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': f'multipart/form-data; boundary={boundary.decode()}',
                'User-Agent': 'Mozilla/5.0',
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read()).get('text', '').strip()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'HTTP {e.code}: {e.read().decode(errors="replace")}') from e


def make_transcriber(cfg: dict):
    """Instantiate the correct transcriber based on config."""
    silence = cfg.get('silence_threshold', 0.01)
    if cfg.get('transcription_mode') == 'api':
        return ApiTranscriber(
            api_url=cfg.get('api_url', 'https://api.openai.com/v1'),
            api_key=cfg.get('api_key', ''),
            model=cfg.get('api_model', 'whisper-1'),
            language=cfg.get('language'),
            silence_threshold=silence,
        )
    return Transcriber(
        model=cfg.get('model', 'base'),
        device=cfg.get('device', 'cpu'),
        language=cfg.get('language'),
        silence_threshold=silence,
    )
