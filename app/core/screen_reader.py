"""Screen capture with save-to-file and in-memory image support."""

from pathlib import Path
from datetime import datetime

import mss
import numpy as np
import cv2


class ScreenReader:
    """Captures the screen and provides save-to-folder or in-memory image."""

    def __init__(self, save_folder: str | Path = "bin"):
        self.save_folder = Path(save_folder)
        self.save_folder.mkdir(parents=True, exist_ok=True)
        self._sct = mss.mss()

    def get_image(self) -> np.ndarray:
        """
        Capture the primary monitor and return it as a numpy array (BGR, OpenCV-compatible).

        Returns:
            np.ndarray: Image in BGR format, shape (height, width, 3).
        """
        monitor = self._sct.monitors[0]  # primary monitor (all monitors: 0 = combined)
        screenshot = self._sct.grab(monitor)
        # mss returns BGRA; convert to BGR numpy array for OpenCV
        frame = np.array(screenshot)
        frame = frame[:, :, :3]  # drop alpha
        return frame

    def save_to_folder(self, filename: str | None = None) -> Path:
        """
        Capture the screen and save the image to the configured folder.

        Args:
            filename: Optional filename. If not given, uses a timestamp.

        Returns:
            Path: Path to the saved file.
        """
        frame = self.get_image()
        if filename is None:
            filename = f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = self.save_folder / filename
        cv2.imwrite(str(path), frame)
        return path

    def close(self) -> None:
        """Release the mss instance."""
        self._sct.close()

    def __enter__(self) -> "ScreenReader":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
