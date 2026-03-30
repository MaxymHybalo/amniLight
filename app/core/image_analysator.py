import math
from typing import overload

import numpy as np

COLS = 36
ROWS = 5

# Perimeter LED layout: left → top → right → bottom (order matches concatenation below).
PERIM_LEFT = 18
PERIM_TOP = 72
PERIM_RIGHT = 18
PERIM_BOTTOM = 72
PERIM_LED_COUNT = PERIM_LEFT + PERIM_TOP + PERIM_RIGHT + PERIM_BOTTOM  # 260


def _segment_ranges(length: int, n: int) -> list[tuple[int, int]]:
    """Split [0, length) into n half-open spans; last span absorbs remainder."""
    if n <= 0:
        return []
    ranges: list[tuple[int, int]] = []
    for i in range(n):
        start = i * length // n
        end = length if i == n - 1 else (i + 1) * length // n
        ranges.append((start, end))
    return ranges


class ImageAnalysator:

    def __init__(self) -> None:
        pass

    def analyse(self, image: np.ndarray) -> list[tuple[int, int, int]]:
        """Split image into grid, return accent color (R, G, B) int tuple per tile."""
        tiles = self.split_image_perimeter(image)
        colors = []
        for tile in tiles:
            mean_bgr = self.get_accent_color(tile)
            b, g, r = mean_bgr[0], mean_bgr[1], mean_bgr[2]
            colors.append((int(r), int(g), int(b)))
        
        return colors

    def get_accent_color(self, image: np.ndarray) -> tuple[int, int, int]:
        """Mean color in image channel order (BGR for OpenCV frames)."""
        return image.mean(axis=(0, 1))

    @overload
    def split_image(self, image: np.ndarray, amount: int) -> list[np.ndarray]: ...
    @overload
    def split_image(self, image: np.ndarray, rows: int, cols: int) -> list[np.ndarray]: ...

    def split_image(
        self,
        image: np.ndarray,
        amount_or_rows: int,
        cols: int | None = None,
    ) -> list[np.ndarray]:
        """
        Split image into smaller tiles.

        Either pass a single amount (e.g. 4 → 2×2 grid) or (rows, cols) explicitly.

        Args:
            image: BGR image, shape (height, width, channels).
            amount_or_rows: Number of tiles, or number of rows if cols is given.
            cols: If given, amount_or_rows is rows and this is columns.

        Returns:
            List of sub-images (numpy arrays), row-major order.
        """
        if cols is not None:
            rows, cols = amount_or_rows, cols
        else:
            amount = amount_or_rows
            cols = math.ceil(math.sqrt(amount))
            rows = math.ceil(amount / cols)

        h, w = image.shape[:2]
        tile_h = h // rows
        tile_w = w // cols
        tiles: list[np.ndarray] = []

        for r in range(rows):
            for c in range(cols):
                y1, y2 = r * tile_h, (r + 1) * tile_h if r < rows - 1 else h
                x1, x2 = c * tile_w, (c + 1) * tile_w if c < cols - 1 else w
                tiles.append(image[y1:y2, x1:x2].copy())

        return tiles

    def split_image_perimeter(
        self,
        image: np.ndarray,
        n_left: int = PERIM_LEFT,
        n_top: int = PERIM_TOP,
        n_right: int = PERIM_RIGHT,
        n_bottom: int = PERIM_BOTTOM,
        strip_frac: float = 0.06,
    ) -> list[np.ndarray]:
        """
        Sample the screen border in strips for edge LEDs.

        Order: **left** (top→bottom), **top** (left→right), **right** (top→bottom),
        **bottom** (left→right). Total tiles = n_left + n_top + n_right + n_bottom.

        Each tile is a small rectangle along that edge (``strip_frac`` of min(h, w), at least 1px).

        Note:
            With default counts you get **260** tiles (30+100+30+100), not 180.
            Match ``NUM_LEDS`` in ``server.py`` to this count if you use this split for WS.
        """
        h, w = image.shape[:2]
        strip = max(1, int(min(h, w) * strip_frac))
        strip_w = min(strip, w)
        strip_h = min(strip, h)

        tiles: list[np.ndarray] = []

        for y0, y1 in _segment_ranges(h, n_left):
            tiles.append(image[y0:y1, 0:strip_w].copy())

        for x0, x1 in _segment_ranges(w, n_top):
            tiles.append(image[0:strip_h, x0:x1].copy())

        for y0, y1 in _segment_ranges(h, n_right):
            tiles.append(image[y0:y1, w - strip_w : w].copy())

        for x0, x1 in _segment_ranges(w, n_bottom):
            tiles.append(image[h - strip_h : h, x0:x1].copy())

        return tiles
