# NordiskaDownloader

A desktop GUI for [svtplay-dl](https://github.com/spaam/svtplay-dl), the command-line downloader for Nordic streaming services (SVT Play, TV4 Play and others). Paste a link, pick a quality, press Download.

Built with Python, [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) and Pillow. The logo (download arrow + Swedish cross) is drawn in code, so there are no image assets.

<!-- Add a screenshot after a successful download, then uncomment:
![NordiskaDownloader](docs/screenshot.png)
-->

## Features

- URL input with a Paste button and a target-folder picker
- Two quality presets: **Top (1080p+)** and **Medium (below 720p)**
- Live progress bar and ETA, parsed from svtplay-dl output
- Audio and video merged into one `.mp4` through ffmpeg
- Optional token field for services that require login
- Stop button, plus a log that shows the exact command that was run

## Requirements

- Windows 10/11 and Python 3.10+ (3.12 recommended)
- [ffmpeg](https://ffmpeg.org/) for merging audio and video

## Quick start

```powershell
winget install Gyan.FFmpeg      # once, then reopen the terminal
run.bat
```

`run.bat` creates a virtual environment, installs `requirements.txt` and starts the app.

Manual alternative:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python svtplay_gui.py
```

If ffmpeg is not installed system-wide, put `ffmpeg.exe` next to `svtplay_gui.py`. The log shows which ffmpeg was found.

## How it works

| Part | Approach |
|------|----------|
| UI | `customtkinter` with a custom Swedish-flag palette, card layout |
| Downloading | `subprocess.Popen` runs svtplay-dl in a background thread and streams stdout line by line |
| Thread safety | UI updates go through `self.after(0, ...)` |
| Progress | Regex over svtplay-dl's `[pos/total][====] ETA: ...` output |
| Tool discovery | Looks for svtplay-dl next to the app, in a local `.venv`, then on PATH; ffmpeg is added to the child process PATH |

## Notes from development

- CLI flags were checked against svtplay-dl's own `--help` and source, after guessed flags broke the first versions.
- Packaging with PyInstaller is not supported yet. svtplay-dl and ffmpeg have to travel with the exe, and the official cx_Freeze build depends on a matching `python3xx.dll`. Running from a venv is the reliable path.

## Known limitations

- Manually tested only; there are no automated tests yet
- Windows-first (paths and `CREATE_NO_WINDOW`)
- Quality presets map to svtplay-dl's `--resolution` operators, so "Medium" can pick 576p when available

## Disclaimer

For personal use with content you are entitled to access. Respect each service's terms and copyright law. This project is not affiliated with SVT, TV4 or the svtplay-dl project. svtplay-dl is MIT-licensed and installed as a separate dependency.

## Author

Ivan Kozyrev, [github.com/IvanK-9](https://github.com/IvanK-9)
