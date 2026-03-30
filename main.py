"""AmbiLight app: live screen accent colors preview."""

import hashlib
import time

import cv2

from app.core.image_analysator import ImageAnalysator, ROWS, COLS
from app.core.screen_reader import ScreenReader
from app.core.utils import draw_colors, show_image, show_live
from app.core.server import create_websocket_client, build_frame_packet, build_brightness_packet, CODE
from app.core.optimizations import optimize_colors
from app.core.server import NUM_LEDS
FPS = 60
_FRAME_TIME = 1.0 / FPS


def _hash_prepared_colors(colors: list[tuple[int, int, int]]) -> str:
    """Stable short fingerprint so you can see when the frame payload would differ."""
    h = hashlib.sha256()
    for r, g, b in colors:
        h.update(bytes((r & 0xFF, g & 0xFF, b & 0xFF)))
    return h.hexdigest()[:16]


def run_live() -> None:
    """Capture screen, split into grid, show accent colors; update live until 'q' or ESC."""
    window_name = "AmbiLight"
    print('Creating websocket client')
    ws = create_websocket_client()
    print('Sending brightness packet')
    ws.send(build_brightness_packet(150), CODE)
    with ScreenReader(save_folder="bin") as reader:
        analysator = ImageAnalysator()
        try:
            previous_colors: list[tuple[int, int, int]] = []
            last_hash: str | None = None
            while True:
                frame_start = time.perf_counter()
                frame = reader.get_image()
                colors = analysator.analyse(frame)
                # print('Colors:', colors)
                prepared_color = optimize_colors(previous_colors, colors) if previous_colors else colors
                packet = build_frame_packet(prepared_color)
                previous_colors = colors
                color_hash = _hash_prepared_colors(prepared_color)
                changed = last_hash is not None and color_hash != last_hash
                if changed:
                    ws.send(packet, CODE)
                    print('Color packet sent', color_hash)
                last_hash = color_hash
                preview = draw_colors(prepared_color, (COLS, ROWS))
                key = show_live(window_name, preview, delay_ms=1)
                if key in (ord("q"), ord("Q"), 27):  # q, Q, ESC
                    break
                elapsed = time.perf_counter() - frame_start
                sleep_remaining = _FRAME_TIME - elapsed
                if sleep_remaining > 0:
                    time.sleep(sleep_remaining)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            ws.close()
            print('Closing window')
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
    run_live()


if __name__ == "__main__":
    main()
