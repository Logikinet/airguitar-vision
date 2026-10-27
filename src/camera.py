"""Camera input and mirroring; a demo is provided separately in src/demo.py."""
from __future__ import annotations
from typing import Optional
import cv2
import numpy as np
from . import config

class Camera:
    def __init__(self, device_id: int, width: int, height: int, fps: int,
                 source: str | int | None = None) -> None:
        self.source = device_id if source is None else source
        backend = cv2.CAP_DSHOW if isinstance(self.source, int) and __import__("sys").platform == "win32" else cv2.CAP_ANY
        self._cap = cv2.VideoCapture(self.source, backend)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera/video source {self.source!r}. Check access permissions and --camera ID.")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._cap.set(cv2.CAP_PROP_FPS, fps)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def read(self) -> tuple[bool, Optional[np.ndarray]]:
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return False, None
        if config.MIRROR_CAMERA and isinstance(self.source, int):
            frame = cv2.flip(frame, 1)
        return True, frame

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
