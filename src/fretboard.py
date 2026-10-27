"""Six horizontal strings and five columns (open + frets 1..4)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import cv2
import numpy as np
from . import config
from .hand_tracker import HandResult

@dataclass
class FretboardGeom:
    origin: tuple[float, float]
    axis_u: tuple[float, float]  # vertical, across strings
    axis_v: tuple[float, float]  # horizontal, along fret direction
    n_strings: int
    n_frets: int
    string_spacing: float
    fret_spacing: float

class Fretboard:
    def __init__(self, mode: str = "fixed_roi") -> None:
        if mode != "fixed_roi":
            raise ValueError("Only fixed_roi is implemented")
        self.mode = mode

    def update(self, hands: list[HandResult], frame_shape: tuple[int, int]) -> FretboardGeom:
        h, w = frame_shape
        x, y, rw, rh = config.FRETBOARD_ROI
        return FretboardGeom(
            origin=(x * w, y * h), axis_u=(0., 1.), axis_v=(1., 0.),
            n_strings=config.N_STRINGS, n_frets=config.N_FRETS,
            string_spacing=rh * h / config.N_STRINGS,
            fret_spacing=rw * w / (config.N_FRETS + 1),
        )

    def point_to_cell(self, xy: tuple[float, float], geom: FretboardGeom) -> Optional[tuple[int, int]]:
        dx, dy = xy[0] - geom.origin[0], xy[1] - geom.origin[1]
        u = dx * geom.axis_u[0] + dy * geom.axis_u[1]
        v = dx * geom.axis_v[0] + dy * geom.axis_v[1]
        if not (0 <= u < geom.string_spacing * geom.n_strings and
                0 <= v < geom.fret_spacing * (geom.n_frets + 1)):
            return None
        return (int(u // geom.string_spacing), int(v // geom.fret_spacing))

    def cell_center(self, cell: tuple[int, int], geom: FretboardGeom) -> tuple[int, int]:
        s, f = cell
        u = (s + .5) * geom.string_spacing
        v = (f + .5) * geom.fret_spacing
        return (int(geom.origin[0] + geom.axis_u[0] * u + geom.axis_v[0] * v),
                int(geom.origin[1] + geom.axis_u[1] * u + geom.axis_v[1] * v))

    def neck_line(self, geom: FretboardGeom) -> tuple[tuple[float, float], tuple[float, float]]:
        """Horizontal strum reference line, confined to the separate right-hand ROI.

        This replaces the original ill-oriented fret-boundary segment.
        """
        # Infer screen dimensions from proportional fixed ROI geometry.
        h = geom.string_spacing * geom.n_strings / config.FRETBOARD_ROI[3]
        w = geom.fret_spacing * (geom.n_frets + 1) / config.FRETBOARD_ROI[2]
        x, y, rw, rh = config.STRUM_ROI
        cy = (y + rh / 2) * h
        return ((x * w, cy), ((x + rw) * w, cy))

    def draw_guide(self, frame: np.ndarray, geom: FretboardGeom,
                   active_cell: Optional[tuple[int, int]] = None) -> None:
        """Single-note lanes. Labels are drawn by the overlay with the CJK face.

        No closed debug slab and no Hershey text. The active cell is a soft fill.
        """
        x0, y0 = map(int, geom.origin)
        x1 = int(x0 + geom.fret_spacing * (geom.n_frets + 1))
        y1 = int(y0 + geom.string_spacing * geom.n_strings)
        if active_cell is not None:
            s, f = active_cell
            shade = frame.copy()
            a = (int(x0 + f * geom.fret_spacing), int(y0 + s * geom.string_spacing))
            b = (int(x0 + (f + 1) * geom.fret_spacing), int(y0 + (s + 1) * geom.string_spacing))
            cv2.rectangle(shade, a, b, (151, 220, 61), -1)
            cv2.addWeighted(shade, .28, frame, .72, 0, frame)
        fret_bgr = (82, 64, 49)
        string_bgr = (232, 183, 142)
        for f in range(geom.n_frets + 2):
            xx = int(x0 + f * geom.fret_spacing)
            cv2.line(frame, (xx, y0), (xx, y1), fret_bgr, 1, cv2.LINE_AA)
        for s in range(geom.n_strings):
            yy = int(y0 + (s + .5) * geom.string_spacing)
            cv2.line(frame, (x0, yy), (x1, yy), string_bgr, 1, cv2.LINE_AA)
