"""AmbiLight app: live screen accent colors preview."""

import cv2

from app.core.image_analysator import ImageAnalysator, ROWS, COLS
from app.core.screen_reader import ScreenReader
from app.core.utils import draw_colors, show_image, show_live


def run_live() -> None:
    """Capture screen, split into grid, show accent colors; update live until 'q' or ESC."""
    window_name = "AmbiLight"
    with ScreenReader(save_folder="bin") as reader:
        analysator = ImageAnalysator()
        while True:
            frame = reader.get_image()
            colors = analysator.analyse(frame)
            preview = draw_colors(colors, (COLS, ROWS))
            key = show_live(window_name, preview, delay_ms=1)
            if key in (ord("q"), ord("Q"), 27):  # q, Q, ESC
                break
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
