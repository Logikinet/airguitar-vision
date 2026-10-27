"""Headless demo frames. No camera, no window, no audio device.

Writes 1440×900 PNGs to artifacts/demo_frames/%05d.png, then exits.
UI frames go through the same Overlay path as tools/render_ui_preview.py.
Synthetic hands are fake_hand poses from that helper, with the right hand
moved on Y so the index crosses the strum line.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# tools/ is not a package. The script directory is already on sys.path[0].
from render_ui_preview import FRAME, _draw, _hands, stage_frame  # noqa: E402

from src import config  # noqa: E402
from src.overlay import Overlay  # noqa: E402
from src.song_player import SongPlayer  # noqa: E402
from src.strum_detector import StrumState  # noqa: E402
from src.theme import CANVAS_H, CANVAS_W, bgr, load_cjk_fonts, rgb  # noqa: E402

OUT = ROOT / 'artifacts' / 'demo_frames'
FPS = 10
# Suggested beats: intro, empty camera, download card, playing demo,
# gesture card, chord + strum, end card. 52s is inside the 30–60s window.
TIMELINE = (
    ('intro', 0.0, 4.0),
    ('empty', 4.0, 12.0),
    ('download', 12.0, 16.0),
    ('playing', 16.0, 30.0),
    ('gestures', 30.0, 34.0),
    ('strum', 34.0, 48.0),
    ('end', 48.0, 52.0),
)
DEMO_LINE = '渲染界面演示 / Rendered UI demo — no camera on this machine'
RELEASE = 'https://github.com/Logikinet/airguitar-vision/releases/tag/v1.0.1'
# _hands places the right hand at these fractions of the frame height.
_CY_ABOVE = 0.56
_CY_ON_LINE = 0.66

_FONTS, _DISPLAY = load_cjk_fonts((16, 20, 22, 28, 36, 48))


def _font(size: int):
    if size == 28:
        return _DISPLAY
    face = _FONTS.get(size)
    if face is None:
        raise RuntimeError(f'No theme font cached for size {size}')
    return face


def _span_frames(t0: float, t1: float) -> int:
    return int(round(t1 * FPS)) - int(round(t0 * FPS))


def _check_timeline() -> int:
    if TIMELINE[0][1] != 0.0:
        raise RuntimeError('Timeline must start at 0')
    previous = 0.0
    total = 0
    for name, t0, t1 in TIMELINE:
        if t0 != previous or t1 <= t0:
            raise RuntimeError(f'Bad timeline segment {name}: {t0}..{t1}')
        total += _span_frames(t0, t1)
        previous = t1
    if total < int(30 * FPS) or total > int(60 * FPS):
        raise RuntimeError(f'Frame count {total} is outside 30–60s at {FPS} fps')
    return total


def _caption(lines: tuple[tuple[str, int, str], ...]) -> np.ndarray:
    """Full-canvas dark card. Colors and CJK faces come from src/theme.py."""
    canvas = np.empty((CANVAS_H, CANVAS_W, 3), np.uint8)
    canvas[:] = bgr('bg')
    image = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
    pen = ImageDraw.Draw(image)
    pen.rectangle((0, 0, CANVAS_W, 8), fill=rgb('accent'))
    pen.rectangle((0, CANVAS_H - 8, CANVAS_W, CANVAS_H), fill=rgb('accent'))
    gap = 16
    heights = []
    for text, size, _color in lines:
        if not text:
            heights.append(12)
            continue
        box = _font(size).getbbox(text)
        heights.append(box[3] - box[1])
    total_h = sum(heights) + gap * (len(lines) - 1)
    y = (CANVAS_H - total_h) / 2
    for (text, size, color), height in zip(lines, heights):
        if text:
            pen.text((CANVAS_W / 2, y), text, font=_font(size), fill=rgb(color), anchor='mt')
        y += height + gap
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def _cards() -> dict[str, np.ndarray]:
    return {
        'intro': _caption((
            ('空气吉他', 48, 'text'),
            ('AirGuitar Vision', 28, 'text2'),
            ('', 16, 'muted'),
            ('渲染界面演示', 36, 'accent'),
            (DEMO_LINE, 22, 'text'),
            ('', 16, 'muted'),
            ('MediaPipe + OpenCV', 20, 'muted'),
            ('左手手势和弦 / 右手扫弦', 20, 'text2'),
            ('示范曲  小星星 / 欢乐颂', 20, 'text2'),
        )),
        'download': _caption((
            ('下载与首次运行', 48, 'text'),
            ('Download and first launch', 28, 'text2'),
            ('', 16, 'muted'),
            (RELEASE, 20, 'accent'),
            ('未签名。SmartScreen：更多信息 → 仍要运行', 22, 'text'),
            ('Unsigned. SmartScreen: More info → Run anyway', 20, 'text2'),
            ('允许桌面应用使用摄像头', 22, 'text'),
            ('Allow camera access for desktop apps', 20, 'text2'),
            ('', 16, 'muted'),
            (DEMO_LINE, 20, 'muted'),
        )),
        'gestures': _caption((
            ('手势 0–5', 48, 'text'),
            ('Gestures 0–5', 28, 'text2'),
            ('', 16, 'muted'),
            ('0 Em     1 Am     2 C', 36, 'accent'),
            ('3 D      4 G      5 F', 36, 'accent'),
            ('', 16, 'muted'),
            ('象征性指法，不是真实按弦', 22, 'text'),
            ('Symbolic finger counts, not real fretting', 20, 'text2'),
            (DEMO_LINE, 20, 'muted'),
        )),
        'end': _caption((
            ('空气吉他', 48, 'text'),
            ('AirGuitar Vision', 28, 'text2'),
            ('', 16, 'muted'),
            ('渲染界面演示', 36, 'accent'),
            (DEMO_LINE, 22, 'text'),
            ('', 16, 'muted'),
            (RELEASE, 20, 'accent'),
            ('v1.0.1', 20, 'muted'),
        )),
    }


def _place_hands(chord_fingers: int, cy_frac: float) -> list:
    """Reuse _hands (fake_hand). Slide the right hand onto ``cy_frac``."""
    h, _w = FRAME
    baseline = _CY_ON_LINE if cy_frac >= (_CY_ABOVE + _CY_ON_LINE) / 2 else _CY_ABOVE
    hands = _hands(chord_fingers, strum_on_line=baseline == _CY_ON_LINE)
    dy = (cy_frac - baseline) * h
    right = hands[1]
    right.landmarks = [(x, y + dy, z) for x, y, z in right.landmarks]
    return hands


class _StrumAnim:
    """Downward crossings of the tuned strum line become a short TRIGGER."""

    def __init__(self) -> None:
        self.prev: float | None = None
        self.hold = 0
        self.cool = 0

    def step(self, cy: float) -> tuple[StrumState, str]:
        prev = self.prev
        self.prev = cy
        if self.hold > 0:
            self.hold -= 1
            return StrumState.TRIGGER, 'strum'
        if prev is not None and prev < _CY_ON_LINE <= cy:
            self.hold = 2
            self.cool = 5
            return StrumState.TRIGGER, 'strum'
        if self.cool > 0:
            self.cool -= 1
            return StrumState.COOLDOWN, ''
        if cy < _CY_ON_LINE and (_CY_ON_LINE - cy) <= 0.06:
            return StrumState.APPROACH, ''
        return StrumState.IDLE, ''


def _chord_at(local_s: float, span_s: float) -> tuple[str, int]:
    slot = span_s / len(config.CHORD_ORDER)
    index = min(len(config.CHORD_ORDER) - 1, int(local_s / slot))
    return config.CHORD_ORDER[index], index


def _gesture_cy(local_s: float, span_s: float) -> float:
    """One downstroke and return per chord, crossing the strum line."""
    slot = span_s / len(config.CHORD_ORDER)
    phase = (local_s % slot) / slot
    if phase < 0.15:
        return 0.50
    if phase < 0.55:
        return 0.50 + (0.80 - 0.50) * ((phase - 0.15) / 0.40)
    if phase < 0.75:
        return 0.80
    return 0.80 + (0.50 - 0.80) * ((phase - 0.75) / 0.25)


def _playing_cy(local_s: float) -> float:
    # Slow bob around the strum line so progress and the hand both move.
    return 0.64 + 0.14 * np.sin(2 * np.pi * local_s / 3.2)


def _assert_chord_map() -> None:
    for index, name in enumerate(config.CHORD_ORDER):
        if config.GESTURE_TO_CHORD[index] != name:
            raise RuntimeError(f'Gesture {index} is not {name}')


def _write_png(path: Path, image: np.ndarray) -> None:
    if image.shape != (CANVAS_H, CANVAS_W, 3):
        raise RuntimeError(f'Unexpected canvas {image.shape} for {path.name}')
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f'Unable to write {path}')


def _write_hold(out: Path, image: np.ndarray, index: int, count: int) -> int:
    first = out / f'{index:05d}.png'
    _write_png(first, image)
    blob = first.read_bytes()
    for step in range(1, count):
        (out / f'{index + step:05d}.png').write_bytes(blob)
    return index + count


def _write_run(out: Path, overlay: Overlay, plate: np.ndarray, player: SongPlayer,
               index: int, count: int, span_s: float, *, demo: bool, confidence: float,
               cy_fn, advance_song: bool) -> int:
    anim = _StrumAnim()
    for k in range(count):
        local = k / FPS
        chord, fingers = _chord_at(local, span_s)
        cy = float(cy_fn(local))
        state, event = anim.step(cy)
        if advance_song:
            player.state = 'playing'
            player._elapsed_ms = min(local, player.song.duration_seconds) * 1000
        frame = _draw(
            overlay, plate, _place_hands(fingers, cy),
            chord=chord, strum_state=state, demo=demo,
            song_player=player, confidence=confidence, last_event=event, mode='chord',
        )
        _write_png(out / f'{index:05d}.png', frame)
        index += 1
        done = index - 1
        if done % 50 == 0:
            print(f'  {done} frames', flush=True)
    return index


def render_demo_frames(dest: Path = OUT) -> int:
    total = _check_timeline()
    _assert_chord_map()
    dest.mkdir(parents=True, exist_ok=True)
    for old in dest.glob('*.png'):
        old.unlink()

    print(f'rendering {total} frames at {FPS} fps -> {dest}', flush=True)
    overlay = Overlay()
    cards = _cards()
    blank = np.zeros((*FRAME, 3), np.uint8)
    play_plate = stage_frame(2, warmth=0.2)
    live_plate = stage_frame(7, warmth=0.05)

    waiting = SongPlayer()
    playing = SongPlayer()
    gesture_song = SongPlayer()
    gesture_song.select(1)

    empty = _draw(
        overlay, blank, [],
        chord=None, strum_state=StrumState.IDLE, camera_off=True,
        song_player=waiting, confidence=0, last_event='',
    )

    spans = {name: _span_frames(t0, t1) for name, t0, t1 in TIMELINE}
    index = 1
    index = _write_hold(dest, cards['intro'], index, spans['intro'])
    index = _write_hold(dest, empty, index, spans['empty'])
    index = _write_hold(dest, cards['download'], index, spans['download'])
    index = _write_run(
        dest, overlay, play_plate, playing, index, spans['playing'], 14.0,
        demo=True, confidence=0.86, cy_fn=_playing_cy, advance_song=True,
    )
    index = _write_hold(dest, cards['gestures'], index, spans['gestures'])
    index = _write_run(
        dest, overlay, live_plate, gesture_song, index, spans['strum'], 14.0,
        demo=False, confidence=0.91,
        cy_fn=lambda local: _gesture_cy(local, 14.0), advance_song=False,
    )
    index = _write_hold(dest, cards['end'], index, spans['end'])

    written = index - 1
    on_disk = len(list(dest.glob('*.png')))
    if written != total or on_disk != total:
        raise RuntimeError(f'Expected {total} frames, wrote {written}, disk {on_disk}')
    return written


def main() -> None:
    count = render_demo_frames()
    print(f'frames {count}')
    print(f'fps {FPS}')


if __name__ == '__main__':
    main()
