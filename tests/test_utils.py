"""Tests for app.core.utils."""

import numpy as np
import pytest

from app.core.utils import draw_colors, show_image, show_live


class TestDrawColors:
    """draw_colors(colors, dims)."""

    def test_output_shape(self) -> None:
        cols, rows = 3, 2
        colors = [(0, 0, 0)] * (cols * rows)
        image = draw_colors(colors, (cols, rows))
        assert image.shape == (rows * 100, cols * 100, 3)
        assert image.dtype == np.uint8

    def test_single_color_fills_first_cell(self) -> None:
        color = (40, 100, 200)  # BGR
        image = draw_colors([color], (2, 2))
        # First 100x100 block should be that color
        block = image[0:100, 0:100]
        assert np.all(block == color)

    def test_colors_placed_row_major(self) -> None:
        # (cols, rows) = (2, 2) -> 4 cells: (0,0), (1,0), (0,1), (1,1)
        colors = [
            (1, 0, 0),   # top-left
            (2, 0, 0),   # top-right
            (3, 0, 0),   # bottom-left
            (4, 0, 0),   # bottom-right
        ]
        image = draw_colors(colors, (2, 2))
        # Check center of each 100x100 cell
        assert image[50, 50, 0] == 1
        assert image[50, 150, 0] == 2
        assert image[150, 50, 0] == 3
        assert image[150, 150, 0] == 4

    def test_fewer_colors_than_slots_allowed(self) -> None:
        image = draw_colors([(0, 0, 0), (255, 255, 255)], (2, 2))
        assert image.shape == (200, 200, 3)

    def test_empty_colors_all_black(self) -> None:
        image = draw_colors([], (2, 2))
        assert image.shape == (200, 200, 3)
        np.testing.assert_array_equal(image, 0)

    def test_raises_when_more_colors_than_slots(self) -> None:
        with pytest.raises(ValueError, match="More colors provided than grid slots"):
            draw_colors([(0, 0, 0)] * 5, (2, 2))


class TestShowImage:
    """show_image(image) - mocked to avoid opening windows."""

    def test_calls_cv2_imshow_waitkey_destroy(self) -> None:
        from unittest.mock import patch, MagicMock
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        with patch("app.core.utils.cv2") as mock_cv2:
            mock_cv2.waitKey.return_value = ord("q")
            show_image(img)
            mock_cv2.imshow.assert_called_once()
            mock_cv2.waitKey.assert_called_once()
            mock_cv2.destroyAllWindows.assert_called_once()

    def test_accepts_bgr_array(self) -> None:
        from unittest.mock import patch
        img = np.random.randint(0, 255, (10, 20, 3), dtype=np.uint8)
        with patch("app.core.utils.cv2") as mock_cv2:
            mock_cv2.waitKey.return_value = 27
            show_image(img)
            args = mock_cv2.imshow.call_args[0]
            assert args[0] == "Screen"
            np.testing.assert_array_equal(args[1], img)


class TestShowLive:
    """show_live(name, image, delay_ms) - mocked to avoid opening windows."""

    def test_calls_imshow_with_name_and_image(self) -> None:
        from unittest.mock import patch
        img = np.zeros((30, 40, 3), dtype=np.uint8)
        with patch("app.core.utils.cv2") as mock_cv2:
            mock_cv2.waitKey.return_value = -1
            show_live("AmbiLight", img)
            mock_cv2.imshow.assert_called_once_with("AmbiLight", img)

    def test_calls_waitkey_with_delay_and_returns_its_value(self) -> None:
        from unittest.mock import patch
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        with patch("app.core.utils.cv2") as mock_cv2:
            mock_cv2.waitKey.return_value = ord("q")
            result = show_live("Preview", img, delay_ms=5)
            mock_cv2.waitKey.assert_called_once_with(5)
            assert result == ord("q")

    def test_returns_negative_one_when_no_key_pressed(self) -> None:
        from unittest.mock import patch
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        with patch("app.core.utils.cv2") as mock_cv2:
            mock_cv2.waitKey.return_value = -1
            result = show_live("Win", img)
            assert result == -1

    def test_default_delay_is_one(self) -> None:
        from unittest.mock import patch
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        with patch("app.core.utils.cv2") as mock_cv2:
            mock_cv2.waitKey.return_value = -1
            show_live("Win", img)
            mock_cv2.waitKey.assert_called_once_with(1)
