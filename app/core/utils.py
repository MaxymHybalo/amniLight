import cv2
import numpy as np

PREVIEW_CELL_SIZE = 5


def show_image(image: np.ndarray) -> None:
    cv2.imshow("Screen", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def show_live(name: str, image: np.ndarray, delay_ms: int = 1) -> int:
    """
    Show image in a window and wait briefly. Returns the key code if a key was pressed, else -1.
    Use for live-updating preview; exit loop when key is ord('q') or 27 (ESC).
    """
    cv2.imshow(name, image)
    return cv2.waitKey(delay_ms)


def draw_colors(colors: list[tuple[int, int, int]], dims: tuple[int, int]) -> np.ndarray:
    """
    Draws colors into a grid of passed dimensions.

    :param colors: List of BGR (int, int, int) color triples.
    :param dims: (cols, rows) - how many colors per row and how many rows.
    :return: np.ndarray of the composed image.
    """
    cols, rows = dims
    if len(colors) > cols * rows:
        raise ValueError("More colors provided than grid slots available.")
    square_size = PREVIEW_CELL_SIZE
    image = np.zeros((rows * square_size, cols * square_size, 3), dtype=np.uint8)
    for idx, color in enumerate(colors):
        col = idx % cols
        row = idx // cols
        top_left = (col * square_size, row * square_size)
        bottom_right = ((col + 1) * square_size, (row + 1) * square_size)
        cv2.rectangle(image, top_left, bottom_right, color, -1)
    return image