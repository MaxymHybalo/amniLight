import math
from typing import overload

import numpy as np

COLS = 600
ROWS = 140

class ImageAnalysator:

    def __init__(self) -> None:
        pass

    def analyse(self, image: np.ndarray) -> list[tuple[int, int, int]]:
        """Split image into grid, return accent color (BGR int tuple) per tile."""
        tiles = self.split_image(image, ROWS, COLS)
        colors = []
        for tile in tiles:
            mean_bgr = self.get_accent_color(tile)
            colors.append(tuple(int(c) for c in mean_bgr))
        return colors

    def get_accent_color(self, image: np.ndarray) -> tuple[int, int, int]:
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
