"""Tests for app.core.image_analysator."""

import numpy as np
import pytest

from app.core.image_analysator import (
    COLS,
    PERIM_LED_COUNT,
    ROWS,
    ImageAnalysator,
)


@pytest.fixture
def analysator() -> ImageAnalysator:
    return ImageAnalysator()


@pytest.fixture
def sample_image() -> np.ndarray:
    """BGR image 60x100x3."""
    return np.zeros((60, 100, 3), dtype=np.uint8)


class TestSplitImageByGrid:
    """split_image(image, rows, cols)."""

    def test_returns_correct_number_of_tiles(
        self, analysator: ImageAnalysator, sample_image: np.ndarray
    ) -> None:
        tiles = analysator.split_image(sample_image, 3, 4)
        assert len(tiles) == 3 * 4

    def test_tiles_cover_full_image(
        self, analysator: ImageAnalysator, sample_image: np.ndarray
    ) -> None:
        tiles = analysator.split_image(sample_image, 3, 4)
        total_pixels = sum(t.size for t in tiles)
        assert total_pixels == sample_image.size

    def test_tile_shapes_consistent(
        self, analysator: ImageAnalysator, sample_image: np.ndarray
    ) -> None:
        # 60x100 split 3x4 -> tile_h=20, tile_w=25
        tiles = analysator.split_image(sample_image, 3, 4)
        assert all(t.ndim == 3 and t.shape[2] == 3 for t in tiles)
        # First 11 tiles 20x25, last tile may be 20x25 (100/4=25)
        heights = {t.shape[0] for t in tiles}
        widths = {t.shape[1] for t in tiles}
        assert heights <= {20, 21}  # 60//3=20, remainder possible on last row
        assert widths <= {25, 26}   # 100//4=25, remainder on last col

    def test_single_tile_returns_whole_image(
        self, analysator: ImageAnalysator, sample_image: np.ndarray
    ) -> None:
        tiles = analysator.split_image(sample_image, 1, 1)
        assert len(tiles) == 1
        np.testing.assert_array_equal(tiles[0], sample_image)

    def test_tiles_are_copies_not_views(
        self, analysator: ImageAnalysator, sample_image: np.ndarray
    ) -> None:
        tiles = analysator.split_image(sample_image, 2, 2)
        for t in tiles:
            t[0, 0, 0] = 255
        assert sample_image[0, 0, 0] == 0

    def test_row_major_order(
        self, analysator: ImageAnalysator
    ) -> None:
        # Image where each quadrant has a unique mean so we can check order
        img = np.zeros((40, 40, 3), dtype=np.uint8)
        img[0:20, 0:20] = [1, 0, 0]   # top-left
        img[0:20, 20:40] = [2, 0, 0]  # top-right
        img[20:40, 0:20] = [3, 0, 0]  # bottom-left
        img[20:40, 20:40] = [4, 0, 0] # bottom-right
        tiles = analysator.split_image(img, 2, 2)
        assert tiles[0][0, 0, 0] == 1  # top-left
        assert tiles[1][0, 0, 0] == 2  # top-right
        assert tiles[2][0, 0, 0] == 3  # bottom-left
        assert tiles[3][0, 0, 0] == 4  # bottom-right


class TestSplitImageByAmount:
    """split_image(image, amount)."""

    def test_amount_four_gives_four_tiles(
        self, analysator: ImageAnalysator, sample_image: np.ndarray
    ) -> None:
        tiles = analysator.split_image(sample_image, 4)
        assert len(tiles) == 4

    def test_amount_six_gives_six_tiles(
        self, analysator: ImageAnalysator, sample_image: np.ndarray
    ) -> None:
        tiles = analysator.split_image(sample_image, 6)
        assert len(tiles) == 6

    def test_amount_five_gives_at_least_five_tiles(
        self, analysator: ImageAnalysator, sample_image: np.ndarray
    ) -> None:
        tiles = analysator.split_image(sample_image, 5)
        assert len(tiles) >= 5

    def test_amount_one_gives_one_tile(
        self, analysator: ImageAnalysator, sample_image: np.ndarray
    ) -> None:
        tiles = analysator.split_image(sample_image, 1)
        assert len(tiles) == 1
        np.testing.assert_array_equal(tiles[0], sample_image)


class TestGetAccentColor:
    """get_accent_color(image)."""

    def test_uniform_image_returns_that_color(
        self, analysator: ImageAnalysator
    ) -> None:
        img = np.full((10, 10, 3), [40, 80, 120], dtype=np.uint8)
        color = analysator.get_accent_color(img)
        np.testing.assert_array_almost_equal(color, [40, 80, 120])

    def test_half_black_half_white_returns_mid_gray(
        self, analysator: ImageAnalysator
    ) -> None:
        img = np.zeros((2, 2, 3), dtype=np.uint8)
        img[0, :] = [0, 0, 0]
        img[1, :] = [255, 255, 255]
        color = analysator.get_accent_color(img)
        np.testing.assert_array_almost_equal(color, [127.5, 127.5, 127.5])


class TestAnalyse:
    """analyse(image) returns RGB per tile."""

    def test_uniform_bgr_image_yields_rgb_tuples(
        self, analysator: ImageAnalysator
    ) -> None:
        # OpenCV BGR: B=10, G=20, R=30 -> RGB (30, 20, 10)
        img = np.full((60, 100, 3), [10, 20, 30], dtype=np.uint8)
        colors = analysator.analyse(img)
        assert len(colors) == ROWS * COLS
        assert all(c == (30, 20, 10) for c in colors)


class TestSplitImagePerimeter:
    """split_image_perimeter — edge strips."""

    def test_tile_count_matches_sum_of_edges(
        self, analysator: ImageAnalysator
    ) -> None:
        img = np.zeros((120, 200, 3), dtype=np.uint8)
        nl, nt, nr, nb = 2, 5, 3, 4
        tiles = analysator.split_image_perimeter(
            img, n_left=nl, n_top=nt, n_right=nr, n_bottom=nb
        )
        assert len(tiles) == nl + nt + nr + nb

    def test_defaults_yield_perim_led_count(
        self, analysator: ImageAnalysator
    ) -> None:
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        tiles = analysator.split_image_perimeter(img)
        assert len(tiles) == PERIM_LED_COUNT == 260

    def test_each_tile_is_bgr_and_non_empty(
        self, analysator: ImageAnalysator
    ) -> None:
        img = np.full((50, 80, 3), [1, 2, 3], dtype=np.uint8)
        tiles = analysator.split_image_perimeter(
            img, n_left=2, n_top=2, n_right=2, n_bottom=2
        )
        for t in tiles:
            assert t.ndim == 3 and t.shape[2] == 3
            assert t.size > 0
