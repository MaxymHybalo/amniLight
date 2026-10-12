# AmbiLight

Ambient light project.

## Setup

_Add setup instructions here._

## Usage

```powershell
python .\main.py
python .\main.py --mode audio
python .\main.py --mode image
```

`--mode audio` visualizes system audio (loopback) using `config/audio_viz.json`. `--mode image` samples the screen for ambilight colors. If you omit `--mode`, the default is `MODE` at the top of `main.py` (`audio` or `image`). Press `q` or ESC to quit.

## Tests

Run `python scripts/run_tests.py` to run tests

## License

_Add license information if needed._

