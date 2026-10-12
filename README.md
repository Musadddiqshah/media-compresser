# media-compresser

> **A powerful TUI-based media compression tool built for Termux.**
> Compress videos, audio, and images — all from your phone, with a beautiful terminal interface.

![Version](https://img.shields.io/badge/version-3.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-yellow)
![Platform](https://img.shields.io/badge/platform-Termux-green)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## ✨ Features

- 🎥 **Video Compression** — MP4, MKV, AVI, MOV, WEBM, FLV, M4V
- 🎵 **Audio Compression** — MP3, M4A, AAC, WAV, FLAC, OGG, OPUS
- 🖼️ **Image Compression** — JPG, PNG, WEBP, BMP, TIFF, HEIC
- 🔄 **Video → Audio** — Extract MP3 from any video
- 🧠 **Smart Compression** — Output is **ALWAYS smaller** than the original, or the original is kept
- ⚡ **5 Compression Presets** — Best Size / Small / Balanced / Fast / Ultra Fast
- 🎨 **Beautiful Curses TUI** — Arrow-key navigation, colors, centered layout
- 🛡️ **RAM Protection** — Auto-detects device RAM with 3-tier confirmation warnings
- 📊 **Live Progress** — Spinner + gradient progress bar + ETA
- 📱 **Zoom-Safe** — Adaptive UI that doesn't break on terminal resize
- 🚀 **Zero Configuration** — Works out of the box on Termux

---

## 🛠️ Built With

| Tool | Purpose |
|------|---------|
| **Python 3** | Core language |
| **curses** | Terminal UI framework |
| **FFmpeg** | Media encoding/decoding |
| **FFprobe** | Media info (duration, resolution) |
| **threading** | Background compression + live progress |
| **subprocess** | FFmpeg integration |
| **shutil / pathlib** | File operations |

No third-party Python libraries — **only standard library + FFmpeg**.

---

## 📱 Requirements

- **Termux** (F-Droid version recommended, not Play Store)
- **Android 7.0+**
- ~50 MB free storage (Python + FFmpeg + script)
- 500 MB+ free RAM recommended

> ⚠️ **This tool is designed ONLY for Termux on Android.** It will also work on Linux/macOS terminals, but Termux is the primary target.

---

## 📦 Installation

### Quick Install (One Command)

```bash
pkg install python ffmpeg git -y
git clone https://github.com/YOUR_USERNAME/media-compresser.git
cd media-compresser
python media-compresser.py
```

### Manual Install

```bash
# 1. Update Termux
pkg update && pkg upgrade -y

# 2. Install dependencies
pkg install python ffmpeg -y

# 3. Download script
git clone https://github.com/YOUR_USERNAME/media-compresser.git
cd media-compresser

# 4. Run
python media-compresser.py
```

### Optional: Termux Storage Access

If you want to compress files from `/sdcard/Download` or `/sdcard/DCIM`:

```bash
termux-setup-storage
```

---

## 🚀 Usage

```bash
python media-compresser.py
```

### Menu Options

```
1. Compress specific files
2. Compress FULL FOLDER
3. Extract AUDIO from videos (VIDEO to MP3)
4. Quit
```

### Controls

| Key | Action |
|-----|--------|
| **↑ / ↓** | Navigate menu |
| **Enter / Space** | Select |
| **Esc / q** | Back / Quit |
| **1-9** | Quick jump |
| **Home / End** | Top / Bottom |
| **Space** (file list) | Toggle selection |
| **a** (file list) | Select / Deselect all |
| **Ctrl+C** | Force exit |

---

## 🎚️ Compression Presets

| # | Name | Codec | CRF | Audio | Speed | Size |
|---|------|-------|-----|-------|-------|------|
| 1 | Best Size | libx265 | 28→36 | 64k→32k | 🐢 Slow | 🔽🔽🔽 Smallest |
| 2 | Small | libx265 | 30→38 | 48k→24k | 🐢 Slow | 🔽🔽 Small |
| 3 | Balanced | libx264 | 26→34 | 96k→48k | 🚶 Medium | 🔽 Medium |
| 4 | Fast | libx264 | 28→36 | 64k→32k | 🏃 Fast | 🔽 Slightly Small |
| 5 | Ultra Fast | libx264 | 30→38 | 48k→24k | ⚡ Fastest | 🔽 Least Reduction |

**Every preset tries multiple attempts** until the file is smaller than the original. If nothing works, **the original is kept** — never bigger.

---

## 🛡️ Safety Features

- ✅ **Output ALWAYS smaller** — or original copied
- ✅ **RAM check** — Preset warning if device RAM too low
- ✅ **3-tier confirmation** — For heavy presets on weak devices
- ✅ **Live RAM monitor** — Warns during compression if RAM drops
- ✅ **Safe input** — Ctrl+D / EOF handled gracefully
- ✅ **Duplicate name detection** — Warns about same-named files
- ✅ **Zoom-safe UI** — Terminal resize handled

---

## 📸 Screenshots

```
                ==================================================
                          ULTRA COMPRESSOR
                     by Musaddiq Shah.am  |  v3.0.0
                ==================================================

                +--------------------------------------------+
                |                 MAIN MENU                  |
                +--------------------------------------------+

                        Up/Down: Navigate  |  Enter: Select

                      > 1. Compress specific files
                        2. Compress FULL FOLDER
                        3. Extract AUDIO from videos (VIDEO to MP3)
                        4. Quit
```

---

## 🐛 Troubleshooting

### `No media files found`
- Make sure the folder contains `.mp4`, `.mp3`, `.jpg`, etc.
- Check `pwd` and `ls` to confirm current directory.

### `ffmpeg: command not found`
```bash
pkg install ffmpeg -y
```

### `Permission denied` on `/sdcard`
```bash
termux-setup-storage
```
Then accept the Android permission popup.

### App crashes / freezes
- Your device may not have enough RAM for the chosen preset
- Try **Preset 3, 4, or 5** (lighter)
- Close other apps

### Terminal UI looks broken
- Zoom out a bit (pinch on Termux)
- Minimum terminal size: **40 cols × 10 rows**

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature-name`
3. Commit: `git commit -m "Add feature"`
4. Push: `git push origin feature-name`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) file.

---

## 👤 Author

**Musaddiq Shah.am**

- GitHub: [@your-username](https://github.com/your-username)
- Built for the Termux community ❤️

---

## 🙏 Acknowledgements

- [FFmpeg](https://ffmpeg.org/) — the engine behind compression
- [Termux](https://termux.dev/) — Linux environment for Android
- [Python curses](https://docs.python.org/3/library/curses.html) — TUI framework

---

⭐ **If this tool helped you, give it a star!**
