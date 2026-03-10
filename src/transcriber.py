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
