"""Headless stage comps. No camera, no window, no audio device.

Writes 1440×900 PNGs to artifacts/previews/. The OS title bar is not part of
the canvas; HighGUI would draw it from the ASCII caption in src/theme.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.demo import fake_hand  # noqa: E402
from src.fretboard import Fretboard  # noqa: E402
from src.overlay import CANVAS_H, CANVAS_W, Overlay  # noqa: E402
from src.song_player import SongPlayer  # noqa: E402
from src.strum_detector import StrumState  # noqa: E402

OUT = ROOT / 'artifacts' / 'previews'
FRAME = (540, 960)


def stage_frame(seed: int, warmth: float = 0.15) -> np.ndarray:
    """Dim blue-grey room plate with a soft key light and fine grain."""
    h, w = FRAME
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    image = np.zeros((h, w, 3), np.float32)
    image[..., 0] = 34
    image[..., 1] = 30
    image[..., 2] = 26
    key_x = (xx - w * 0.38) / (w * 0.48)
    key_y = (yy - h * 0.40) / (h * 0.46)
    key = np.exp(-(key_x * key_x + key_y * key_y) * 1.35)
    image[..., 0] += key * 28
    image[..., 1] += key * 24
    image[..., 2] += key * (18 + 22 * warmth)
    fill_x = (xx - w * 0.78) / (w * 0.40)
    fill_y = (yy - h * 0.62) / (h * 0.42)
    fill = np.exp(-(fill_x * fill_x * 1.4 + fill_y * fill_y))
    image[..., 0] += fill * 10
    image[..., 1] += fill * 12
    image[..., 2] += fill * 8
    floor = np.clip((yy - h * 0.72) / (h * 0.28), 0, 1)[..., None]
    image *= 1 - 0.28 * floor
    image += rng.normal(0, 2.4, image.shape)
    return np.clip(image, 0, 255).astype(np.uint8)


def _hands(chord_fingers: int, strum_on_line: bool) -> list:
    h, w = FRAME
    # Open or two-finger poses stay readable. A one-finger tuck crosses itself.
    fingers = chord_fingers if chord_fingers >= 2 else 5
    left = fake_hand(w * 0.32, h * 0.58, role='Left', finger_count=fingers)
    # Index sits on the strum lane for a hit; otherwise the hand rests above it.
    cy = h * (0.66 if strum_on_line else 0.56)
    right = fake_hand(w * 0.76, cy, role='Right', finger_count=5)
    return [left, right]


def _draw(overlay: Overlay, frame: np.ndarray, hands, **kwargs) -> np.ndarray:
    geom = Fretboard().update(hands, frame.shape[:2])
    return overlay.draw(frame, hands, geom, debug=False, fps=10, **kwargs)


def render_ui_previews(dest: Path = OUT) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    overlay = Overlay()
    paths: list[Path] = []

    waiting = SongPlayer()
    empty = _draw(
        overlay, np.zeros((*FRAME, 3), np.uint8), [],
        chord=None, strum_state=StrumState.IDLE, camera_off=True,
        song_player=waiting, confidence=0, last_event='',
    )
    paths.append(_write(dest / '01_empty_camera.png', empty))

    playing = SongPlayer()
    playing.state = 'playing'
    playing._elapsed_ms = playing.song.duration_seconds * 1000 * 0.40
    demo = _draw(
        overlay, stage_frame(2, warmth=0.2), _hands(2, False),
        chord='C', strum_state=StrumState.IDLE, demo=True,
        song_player=playing, confidence=0.86, last_event='', mode='chord',
    )
    paths.append(_write(dest / '02_playing_demo.png', demo))

    live = SongPlayer()
    live.select(1)
    gesture = _draw(
        overlay, stage_frame(7, warmth=0.05), _hands(1, True),
        chord='Am', strum_state=StrumState.TRIGGER, demo=False,
        song_player=live, confidence=0.91, last_event='strum', mode='chord',
    )
    paths.append(_write(dest / '03_gesture_chord.png', gesture))
    return paths


def _write(path: Path, image: np.ndarray) -> Path:
    if image.shape != (CANVAS_H, CANVAS_W, 3):
        raise RuntimeError(f'Unexpected canvas {image.shape} for {path.name}')
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f'Unable to write {path}')
    return path


def main() -> None:
    for path in render_ui_previews():
        print(path)


if __name__ == '__main__':
    main()
