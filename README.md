# FlowType

Voice dictation for Ubuntu 24/25. Hold a hotkey — speak — release. Text is transcribed offline and typed at the cursor.

Works on both **X11** and **Wayland**.

![demo placeholder](https://via.placeholder.com/600x80?text=Hold+hotkey+→+speak+→+release+→+text+appears)

## Features

- **Offline** — speech recognition runs locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper), no cloud, no subscription
- **Low latency** — persistent audio stream, model stays in memory; CUDA gives ~0.7 s for 17 s of speech
- **Any hotkey** — single key or combo (e.g. `Right Shift`, `Ctrl+Alt`, `Ctrl+F9`)
- **Smart injection** — clipboard-based paste with automatic terminal detection (uses `Ctrl+Shift+V` in terminal emulators)
- **System tray** — quick access to settings and transcription history
- **Visual indicator** — small pill that appears near the cursor while recording

## Requirements

- Ubuntu 24.04 or 25.04 (x86-64)
- Python 3.10+
- NVIDIA GPU optional (CUDA for fast transcription)

## Install

Download the latest `.deb` from [Releases](https://github.com/vitiodev/flowtype/releases) and install:

```bash
sudo dpkg -i flowtype_1.2.0_amd64.deb
sudo apt-get install -f   # fix any missing dependencies
```

Then launch:

```bash
flowtype
```

The app starts in the system tray.

## Usage

1. Open **Settings** from the tray icon to choose your hotkey, Whisper model, and language
2. **Hold** the hotkey to start recording (pill indicator appears)
3. **Release** to stop — text is transcribed and typed at the cursor

## Settings

| Option | Default | Description |
|--------|---------|-------------|
| Hotkey | `Right Shift` | Key or combo to hold while speaking |
| Model | `base` | Whisper model size: `tiny` / `base` / `small` / `medium` / `large` |
| Language | auto | Force a language (e.g. `ru`, `en`) or leave auto |
| Device | `cpu` | `cpu` or `cuda` (requires NVIDIA GPU) |
| Inject method | auto | `clipboard` or `ydotool` (Wayland) |

Larger models are more accurate but slower to load and transcribe.

## GPU acceleration (CUDA)

If you have an NVIDIA GPU, select **Device: cuda** in Settings. The app handles CUDA library paths automatically via the bundled pip packages.

Recommended models for CUDA: `medium` or `large-v3`.

## Building from source

```bash
git clone https://github.com/vitiodev/flowtype
cd flowtype/src
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python flowtype.py
```

To build the `.deb` package:

```bash
cd deb
dpkg-deb --build flowtype_1.1.0_amd64 ../flowtype_1.2.0_amd64.deb
```

## Architecture

| File | Role |
|------|------|
| `flowtype.py` | Main app, Qt signals between threads |
| `hotkey.py` | evdev keyboard listener, combo hotkeys |
| `recorder.py` | Persistent `sounddevice.InputStream` |
| `transcriber.py` | faster-whisper wrapper |
| `injector.py` | Text injection via clipboard (xclip + xdotool) |
| `config.py` | JSON config at `~/.config/flowtype/config.json` |
| `ui/` | PyQt6 tray, indicator, settings, history |

## License

MIT
