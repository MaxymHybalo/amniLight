"""AmbiLight app: live screen accent colors preview."""

from __future__ import annotations

import argparse
import hashlib
import time
from typing import Literal

import cv2

from app.core.audio_analysator import AudioAnalysator
from app.core.audio_config import DEFAULT_CONFIG_PATH, load_audio_viz_config
from app.core.image_analysator import COLS, ROWS, ImageAnalysator
from app.core.optimizations import optimize_colors, optimize_colors_audio_from_config
from app.core.screen_reader import ScreenReader
from app.core.server import CODE, build_brightness_packet, build_frame_packet, create_websocket_client
from app.core.utils import draw_colors, show_image, show_live

# Default when you run `python main.py` with no flags. CLI `--mode` overrides this.
MODE: Literal["image", "audio"] = "audio"

AUDIO_CONFIG = load_audio_viz_config()
FPS_IMAGE = 60


def _hash_prepared_colors(colors: list[tuple[int, int, int]]) -> str:
    """Stable short fingerprint so you can see when the frame payload would differ."""
    h = hashlib.sha256()
    for r, g, b in colors:
        h.update(bytes((r & 0xFF, g & 0xFF, b & 0xFF)))
    return h.hexdigest()[:16]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AmbiLight live LED preview")
    parser.add_argument(
        "--mode",
        choices=("image", "audio"),
        default=MODE,
        help="image = screen colors; audio = system-audio visualizer (default: %(default)s)",
    )
    return parser.parse_args()


def _make_analysator(mode: Literal["image", "audio"]):
    if mode == "audio":
        print(f"Loading audio config from {DEFAULT_CONFIG_PATH}")
        return AudioAnalysator.from_config(AUDIO_CONFIG)
    return ImageAnalysator()


def _next_colors(analysator, reader: ScreenReader) -> list[tuple[int, int, int]]:
    if isinstance(analysator, AudioAnalysator):
        return analysator.analyse()
    return analysator.analyse(reader.get_image())


def _prepare_colors(
    analysator,
    previous: list[tuple[int, int, int]],
    colors: list[tuple[int, int, int]],
) -> list[tuple[int, int, int]]:
    if not previous:
        return colors
    if isinstance(analysator, AudioAnalysator):
        return optimize_colors_audio_from_config(previous, colors, AUDIO_CONFIG.optimize)
    return optimize_colors(previous, colors)


def run_live(mode: Literal["image", "audio"] = MODE) -> None:
    """Capture screen or audio, show accent colors; update live until 'q' or ESC."""
    fps = AUDIO_CONFIG.fps if mode == "audio" else FPS_IMAGE
    frame_time = 1.0 / fps
    window_name = "AmbiLight"
    print(f"Mode: {mode} ({fps} fps)")
    print("Creating websocket client")
    ws = create_websocket_client()
    print("Sending brightness packet")
    ws.send(build_brightness_packet(100), CODE)
    with ScreenReader(save_folder="bin") as reader:
        analysator = _make_analysator(mode)
        try:
            previous_colors: list[tuple[int, int, int]] = []
            last_hash: str | None = None
            while True:
                frame_start = time.perf_counter()
                colors = _next_colors(analysator, reader)
                prepared_color = _prepare_colors(analysator, previous_colors, colors)
                packet = build_frame_packet(prepared_color)
                previous_colors = colors
                color_hash = _hash_prepared_colors(prepared_color)
                changed = last_hash is not None and color_hash != last_hash
                if changed:
                    ws.send(packet, CODE)
                    print("Color packet sent", color_hash)
                last_hash = color_hash
                preview = draw_colors(prepared_color, (COLS, ROWS))
                key = show_live(window_name, preview, delay_ms=1)
                if key in (ord("q"), ord("Q"), 27):  # q, Q, ESC
                    break
                elapsed = time.perf_counter() - frame_start
                sleep_remaining = frame_time - elapsed
                if sleep_remaining > 0:
                    time.sleep(sleep_remaining)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if hasattr(analysator, "close"):
                analysator.close()
            ws.close()
            print("Closing window")
    cv2.destroyAllWindows()


def run_once() -> None:
    """Single capture: screenshot → split → accent colors → show once (key to close)."""
    with ScreenReader(save_folder="bin") as reader:
        image = reader.get_image()
        analysator = ImageAnalysator()
        colors = analysator.analyse(image)
        preview = draw_colors(colors, (COLS, ROWS))
        show_image(preview)


def main() -> None:
    args = _parse_args()
    run_live(args.mode)


if __name__ == "__main__":
    main()
