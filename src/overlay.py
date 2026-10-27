"""1440×900 stage. Camera is the hero; chrome uses one teal accent.

Chinese strings go through Pillow and a CJK face. Icons are vector shapes.
cv2.putText and emoji/symbol codepoints are not used.
"""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw

from . import config
from .fretboard import Fretboard, FretboardGeom
from .hand_tracker import HandResult
from .song_player import SONGS, SongPlayer
from .strum_detector import StrumState
from .theme import (
    CANVAS_H,
    CANVAS_W,
    CARD_CHORDS,
    CARD_CONTROL,
    CARD_SONGS,
    CHORD_CELL,
    CHORD_GAP,
    CHORD_ORIGIN,
    HEADER,
    HERO,
    MODE_BTN,
    ODE_BTN,
    PLAY_BTN,
    STOP_BTN,
    STRIP,
    TWINKLE_BTN,
    bgr,
    load_cjk_fonts,
    rgb,
    xyxy,
)

CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
)
_FINGERTIPS = (4, 8, 12, 16, 20)
_SCRIM_H = 72
_HERO_MASK: np.ndarray | None = None
_VIGNETTE: dict[tuple[int, int, bool], np.ndarray] = {}


def _vignette(h: int, w: int, inverted: bool) -> np.ndarray:
    key = (h, w, inverted)
    cached = _VIGNETTE.get(key)
    if cached is not None:
        return cached
    yy, xx = np.mgrid[0:h, 0:w]
    nx = (xx - w / 2) / (w / 2)
    ny = (yy - h / 2) / (h / 2)
    radius = np.clip(np.sqrt(nx * nx + ny * ny), 0, 1.4)
    if inverted:
        field = 0.85 + 0.15 * (1 - radius)
    else:
        field = np.clip(1 - 0.42 * np.power(radius, 1.7), 0.62, 1)
    field = field.astype(np.float32)
    _VIGNETTE[key] = field
    return field


def _hero_mask(w: int, h: int, radius: int = 12) -> np.ndarray:
    global _HERO_MASK
    if _HERO_MASK is not None and _HERO_MASK.shape == (h, w):
        return _HERO_MASK
    scale = 4
    image = Image.new('L', (w * scale, h * scale), 0)
    ImageDraw.Draw(image).rounded_rectangle(
        (0, 0, w * scale - 1, h * scale - 1), radius=radius * scale, fill=255,
    )
    image = image.resize((w, h), Image.Resampling.LANCZOS)
    _HERO_MASK = np.asarray(image).astype(np.float32) / 255.0
    return _HERO_MASK


def _cover(frame: np.ndarray, tw: int, th: int) -> tuple[np.ndarray, float, float, float]:
    """Center-crop scale. Returns hero BGR plus (scale, crop_x, crop_y) in source pixels."""
    sh, sw = frame.shape[:2]
    scale = max(tw / sw, th / sh)
    nw = max(tw, int(round(sw * scale)))
    nh = max(th, int(round(sh * scale)))
    interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
    resized = cv2.resize(frame, (nw, nh), interpolation=interp)
    crop_x = (nw - tw) // 2
    crop_y = (nh - th) // 2
    return resized[crop_y:crop_y + th, crop_x:crop_x + tw], scale, crop_x / scale, crop_y / scale


def _map_point(px: float, py: float, scale: float, crop_x: float, crop_y: float) -> tuple[float, float]:
    return px * scale - crop_x * scale, py * scale - crop_y * scale


def _roi_box(roi: tuple[float, float, float, float], sw: int, sh: int,
             scale: float, crop_x: float, crop_y: float) -> tuple[float, float, float, float]:
    x, y, w, h = roi
    x0, y0 = _map_point(x * sw, y * sh, scale, crop_x, crop_y)
    x1, y1 = _map_point((x + w) * sw, (y + h) * sh, scale, crop_x, crop_y)
    return x0, y0, x1, y1


def _blend_color(image: np.ndarray, mask: np.ndarray, color: tuple[int, int, int], alpha: float) -> None:
    if alpha <= 0:
        return
    weight = mask.astype(np.float32) * alpha
    base = image.astype(np.float32)
    tint = np.array(color, np.float32)
    image[:] = np.clip(base * (1 - weight[..., None]) + tint * weight[..., None], 0, 255).astype(np.uint8)


def _round_mask(shape: tuple[int, int], box: tuple[float, float, float, float], radius: int,
                feather: float = 0) -> np.ndarray:
    h, w = shape
    mask = Image.new('L', (w, h), 0)
    x0, y0, x1, y1 = box
    ImageDraw.Draw(mask).rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=255)
    field = np.asarray(mask).astype(np.float32) / 255.0
    if feather > 0:
        field = cv2.GaussianBlur(field, (0, 0), feather)
        peak = float(field.max())
        if peak > 0:
            field = np.clip(field / peak, 0, 1)
    return field


def _apply_scrims(hero: np.ndarray) -> None:
    h = hero.shape[0]
    n = min(_SCRIM_H, h // 2)
    ramp = (0.55 * (1 - np.arange(n) / n)).astype(np.float32)
    view = hero.astype(np.float32)
    view[:n] *= (1 - ramp)[:, None, None]
    view[-n:] *= (1 - ramp[::-1])[:, None, None]
    hero[:] = np.clip(view, 0, 255).astype(np.uint8)


def _corner_ticks(hero: np.ndarray, box: tuple[float, float, float, float], color: tuple[int, int, int]) -> None:
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    arm, thick = 14, 2
    segments = (
        ((x0, y0), (x0 + arm, y0)), ((x0, y0), (x0, y0 + arm)),
        ((x1, y0), (x1 - arm, y0)), ((x1, y0), (x1, y0 + arm)),
        ((x0, y1), (x0 + arm, y1)), ((x0, y1), (x0, y1 - arm)),
        ((x1, y1), (x1 - arm, y1)), ((x1, y1), (x1, y1 - arm)),
    )
    for start, end in segments:
        cv2.line(hero, start, end, color, thick, cv2.LINE_AA)


def _hband(hero: np.ndarray, x0: int, x1: int, y: int, color: tuple[int, int, int], alpha: float, thick: int) -> None:
    if x1 <= x0 or thick <= 0:
        return
    y0 = max(0, y)
    y1 = min(hero.shape[0], y + thick)
    x0 = max(0, x0)
    x1 = min(hero.shape[1], x1)
    if y1 <= y0 or x1 <= x0:
        return
    band = hero[y0:y1, x0:x1].astype(np.float32)
    tint = np.array(color, np.float32)
    hero[y0:y1, x0:x1] = np.clip(band * (1 - alpha) + tint * alpha, 0, 255).astype(np.uint8)


def display_copy(text: str) -> str:
    """ASCII slash is the only separator. Middot chains are a banned pattern."""
    return text.replace(' · ', ' / ').replace('·', ' / ')


# Clear rows between the title's descender ink and the subtitle's ascender ink.
_TITLE_SUB_GAP = 8
_BRAND_TITLE = '空气吉他'
_BRAND_SUB = '计算机视觉 / 实时交互演奏台'


def _lockup_tops(title_font, sub_font, header: tuple[int, int, int, int],
                 min_gap: int = _TITLE_SUB_GAP) -> tuple[int, int]:
    """Top-left anchors so the two baselines clear by at least ``min_gap`` px.

    Ascent is the baseline under Pillow's top-left anchor. The painted
    descender is ``bbox.bottom - ascent`` and the painted ascender is
    ``ascent - bbox.top``. CJK em-boxes are taller than these glyphs, so
    the gap is the ink, not the full descent. ``min_gap`` stays in 6..8
    when the header cannot hold a larger one.
    """
    title_box = title_font.getbbox(_BRAND_TITLE)
    sub_box = sub_font.getbbox(_BRAND_SUB)
    title_ascent, title_descent = title_font.getmetrics()
    sub_ascent = sub_font.getmetrics()[0]
    # Painted ink first. Declared descent/ascent is only the fallback when a
    # face reports no glyph box (the em often includes blank leading).
    ink_descender = title_box[3] - title_ascent
    ink_ascender = sub_ascent - sub_box[1]
    title_descender = ink_descender if ink_descender > 0 else max(0, title_descent)
    sub_ascender = ink_ascender if ink_ascender > 0 else max(0, sub_ascent)
    hy, hh = header[1], header[3]
    pad = 3
    inner_top = hy + pad
    inner_bot = hy + hh - pad
    title_ink = title_box[3] - title_box[1]
    sub_ink = sub_box[3] - sub_box[1]
    room = inner_bot - inner_top
    gap = min_gap
    if title_ink + gap + sub_ink > room:
        gap = max(6, room - title_ink - sub_ink)
    slack = max(0, room - (title_ink + gap + sub_ink))
    ink_top = inner_top + slack // 2
    title_y = int(round(ink_top - title_box[1]))
    # sub baseline = title baseline + descender ink + gap + ascender ink
    title_baseline = title_y + title_ascent
    sub_baseline = title_baseline + title_descender + gap + sub_ascender
    sub_y = int(round(sub_baseline - sub_ascent))
    return title_y, sub_y


def _mmss(seconds: float) -> str:
    whole = max(0, int(seconds))
    return f'{whole // 60:02d}:{whole % 60:02d}'


class Overlay:
    def __init__(self) -> None:
        self.board = Fretboard()
        self.fonts, self.display = load_cjk_fonts()
        self.buttons: dict[str, tuple[int, int, int, int]] = {
            'mode': MODE_BTN,
            'twinkle': TWINKLE_BTN,
            'ode': ODE_BTN,
            'play_pause': PLAY_BTN,
            'stop': STOP_BTN,
        }
        self._place_header(camera='live', muted=False, fullscreen=False, fps=10)

    def hit_test(self, x: int, y: int) -> str | None:
        for name, (x0, y0, x1, y1) in self.buttons.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                return name
        return None

    def _font(self, size: int):
        return self.fonts[size]

    def _text_width(self, text: str, size: int) -> float:
        return float(self._font(size).getlength(text))

    def _place_header(self, *, camera: str, muted: bool, fullscreen: bool, fps: float) -> dict[str, tuple]:
        """Right cluster, vertically centered in the header. Returns draw specs."""
        audio = '已静音' if muted else '音频开'
        if camera == 'off':
            cam_label, cam_fill, cam_ink, cam_dot = '无摄像头', 'danger_fill', 'danger', 'danger'
        elif camera == 'demo':
            cam_label, cam_fill, cam_ink, cam_dot = '模拟演示', 'hit_fill', 'warning', 'warning'
        else:
            cam_label, cam_fill, cam_ink, cam_dot = '摄像头已连接', 'accent_soft', 'success', 'success'
        fps_label = f'{fps:.0f} fps'
        body = 16
        right = HEADER[0] + HEADER[2] - 16
        pill_h = 28
        y0 = HEADER[1] + (HEADER[3] - pill_h) // 2
        y1 = y0 + pill_h
        gap = 8

        def pill_w(label: str, dot: bool) -> int:
            extra = 12 if dot else 0
            return int(round(12 + extra + self._text_width(label, body) + 12))

        full_w = pill_w('全屏', False)
        full = (right - full_w, y0, right, y1)
        right = full[0] - gap
        audio_w = pill_w(audio, False)
        audio_box = (right - audio_w, y0, right, y1)
        right = audio_box[0] - gap
        fps_w = self._text_width(fps_label, 15)
        fps_x = right - fps_w
        right = int(round(fps_x)) - gap
        cam_w = pill_w(cam_label, True)
        cam = (right - cam_w, y0, right, y1)
        self.buttons['mute'] = audio_box
        self.buttons['fullscreen'] = full
        return {
            'camera': (cam, cam_label, cam_fill, cam_ink, cam_dot),
            'fps': (fps_x, fps_label, y0 + pill_h / 2),
            'audio': (audio_box, audio, muted),
            'full': (full, fullscreen),
        }

    def draw(self, frame: np.ndarray, hands: list[HandResult], geom: FretboardGeom,
             chord: Optional[str], strum_state: StrumState, debug: bool,
             *, mode: str = 'chord', active_cell: tuple[int, int] | None = None,
             fps: float = 0., confidence: float = 0., last_event: str = '',
             demo: bool = False, current_gesture: int | None = None,
             role_swap: bool = False, sound_muted: bool = False,
             song_player: SongPlayer | None = None, camera_off: bool = False,
             fullscreen: bool = False) -> np.ndarray:
        del debug, current_gesture  # scores and raw gesture ids stay off the stage
        if frame is None:
            camera_off = True
        hero_x, hero_y, hero_w, hero_h = HERO
        hero, mapped_hands = self._compose_hero(
            frame, hands, geom, strum_state, mode, active_cell, camera_off, role_swap, bool(last_event),
        )
        canvas = np.empty((CANVAS_H, CANVAS_W, 3), np.uint8)
        canvas[:] = bgr('bg')
        mask = _hero_mask(hero_w, hero_h)
        region = canvas[hero_y:hero_y + hero_h, hero_x:hero_x + hero_w]
        canvas[hero_y:hero_y + hero_h, hero_x:hero_x + hero_w] = (
            region * (1 - mask[..., None]) + hero * mask[..., None]
        ).astype(np.uint8)

        image = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
        pen = ImageDraw.Draw(image)
        camera = 'off' if camera_off else ('demo' if demo else 'live')
        header = self._place_header(camera=camera, muted=sound_muted, fullscreen=fullscreen, fps=fps)
        self._paint(pen, header, mapped_hands, chord, strum_state, mode, active_cell,
                    confidence, last_event, sound_muted, song_player, camera_off, fullscreen)
        return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)

    def _compose_hero(self, frame, hands, geom, strum_state, mode, active_cell,
                      camera_off, role_swap, hit, ) -> tuple[np.ndarray, list[tuple]]:
        hero_w, hero_h = HERO[2], HERO[3]
        mapped: list[tuple] = []
        if camera_off or frame is None or frame.size == 0:
            plate = np.empty((hero_h, hero_w, 3), np.float32)
            plate[:] = np.array(bgr('elevated'), np.float32)
            plate *= _vignette(hero_h, hero_w, True)[..., None]
            return np.clip(plate, 0, 255).astype(np.uint8), mapped

        source = frame
        if mode == 'single':
            source = frame.copy()
            self.board.draw_guide(source, geom, active_cell)
        hero, scale, crop_x, crop_y = _cover(source, hero_w, hero_h)
        hero = hero.astype(np.float32)
        hero *= _vignette(hero_h, hero_w, False)[..., None]
        hero = np.clip(hero, 0, 255).astype(np.uint8)
        sh, sw = frame.shape[:2]
        self._draw_zones(hero, sw, sh, scale, crop_x, crop_y, strum_state, hit)
        for hand in hands:
            label = hand.handedness
            if role_swap:
                label = 'Right' if label == 'Left' else 'Left'
            color = bgr('hand_l') if label == 'Left' else bgr('hand_r')
            points = []
            for px, py, _z in hand.landmarks:
                hx, hy = _map_point(px, py, scale, crop_x, crop_y)
                points.append((int(round(hx)), int(round(hy))))
            if len(points) < 21:
                continue
            for i, j in CONNECTIONS:
                cv2.line(hero, points[i], points[j], color, 2, cv2.LINE_AA)
            for index, point in enumerate(points):
                if index in _FINGERTIPS:
                    cv2.circle(hero, point, 4, color, -1, cv2.LINE_AA)
                else:
                    cv2.circle(hero, point, 2, bgr('text'), -1, cv2.LINE_AA)
            wrist = points[0]
            # Past the wrist, away from the palm, so the name does not sit on the joint.
            palm_x = sum(points[i][0] for i in (0, 5, 9, 13, 17)) / 5
            palm_y = sum(points[i][1] for i in (0, 5, 9, 13, 17)) / 5
            away_x, away_y = wrist[0] - palm_x, wrist[1] - palm_y
            norm = (away_x * away_x + away_y * away_y) ** 0.5
            if norm < 1:
                away_x, away_y = 0.0, 1.0
            else:
                away_x, away_y = away_x / norm, away_y / norm
            mapped.append((wrist[0] + HERO[0], wrist[1] + HERO[1], away_x, away_y, label))
        _apply_scrims(hero)
        return hero, mapped

    def _draw_zones(self, hero, sw, sh, scale, crop_x, crop_y, strum_state, hit) -> None:
        h, w = hero.shape[:2]
        margin = 12
        fx0, fy0, fx1, fy1 = _roi_box(config.FRETBOARD_ROI, sw, sh, scale, crop_x, crop_y)
        fx0, fy0 = max(margin, fx0), max(margin, fy0)
        fx1, fy1 = min(w - margin, fx1), min(h - margin, fy1)
        if fx1 - fx0 > 32 and fy1 - fy0 > 32:
            # Feather the wash so the zone is a lane, not a stroked debug plate.
            mask = _round_mask(hero.shape[:2], (fx0, fy0, fx1, fy1), 16, feather=18)
            _blend_color(hero, mask, bgr('fret_tint'), 0.22)
            _corner_ticks(hero, (fx0, fy0, fx1, fy1), bgr('fret_edge'))

        sx0, sy0, sx1, sy1 = _roi_box(config.STRUM_ROI, sw, sh, scale, crop_x, crop_y)
        sx0, sy0 = max(margin, sx0), max(margin, sy0)
        sx1, sy1 = min(w - 1 - margin, sx1), min(h - 1 - margin, sy1)
        if sx1 - sx0 > 48 and sy1 - sy0 > 24:
            _hband(hero, int(sx0), int(sx1), int(round(sy0)), bgr('strum_line'), 0.40, 1)
            _hband(hero, int(sx0), int(sx1), int(round(sy1)), bgr('strum_line'), 0.40, 1)
            if hit:
                line = bgr('warning')
            elif strum_state == StrumState.COOLDOWN:
                line = bgr('success')
            else:
                line = bgr('strum_line')
            y = int(round((sy0 + sy1) / 2))
            x_start = int(round(sx0)) + 16
            x_end = int(round(sx1)) - 16
            cv2.line(hero, (x_start, y), (x_end, y), line, 2, cv2.LINE_AA)
            cap = 6
            cv2.line(hero, (x_start, y - cap // 2), (x_start, y + cap // 2), line, 2, cv2.LINE_AA)
            cv2.line(hero, (x_end, y - cap // 2), (x_end, y + cap // 2), line, 2, cv2.LINE_AA)

    def _paint(self, pen, header, hands, chord, strum_state, mode, active_cell,
               confidence, last_event, sound_muted, song_player, camera_off, fullscreen) -> None:
        self._header(pen, header)
        self._hero_chrome(pen, hands, camera_off)
        self._strip(pen, chord, strum_state, mode, active_cell, confidence, last_event)
        self._control_card(pen, mode)
        self._chord_card(pen, chord, mode)
        self._song_card(pen, song_player)
        del sound_muted, fullscreen

    def _card(self, pen, box) -> None:
        pen.rounded_rectangle(xyxy(box), radius=12, fill=rgb('surface'), outline=rgb('border'), width=1)

    def _header(self, pen, header) -> None:
        pen.rounded_rectangle(xyxy(HEADER), radius=12, fill=rgb('surface'), outline=rgb('border'), width=1)
        mark = 36
        brand_y = HEADER[1] + (HEADER[3] - mark) // 2
        self._brand(pen, 40, brand_y)
        title_y, sub_y = _lockup_tops(self.display, self._font(15), HEADER)
        pen.text((88, title_y), _BRAND_TITLE, font=self.display, fill=rgb('text'))
        pen.text((88, sub_y), _BRAND_SUB, font=self._font(15), fill=rgb('text2'))
        cam, label, fill, ink, dot = header['camera']
        self._pill(pen, cam, fill, label, ink, dot=dot)
        fps_x, fps_label, fps_y = header['fps']
        pen.text((fps_x, fps_y), fps_label, font=self._font(15), fill=rgb('text2'), anchor='lm')
        audio_box, audio, muted = header['audio']
        if muted:
            self._pill(pen, audio_box, 'warning', audio, 'on_accent')
        else:
            self._pill(pen, audio_box, 'elevated', audio, 'text', outline='border')
        full_box, fullscreen = header['full']
        if fullscreen:
            self._pill(pen, full_box, 'accent_soft', '全屏', 'text', outline='accent')
        else:
            self._pill(pen, full_box, 'elevated', '全屏', 'text', outline='border')

    def _brand(self, pen, x: int, y: int) -> None:
        pen.rounded_rectangle((x, y, x + 36, y + 36), radius=8, fill=rgb('elevated'), outline=rgb('accent'), width=1)
        accent = rgb('accent')
        # Strings stop above the bridge. A 36px mark cannot hold a y+28 string
        # and a separate 200–340° arc without the strokes crossing.
        for dx in (10, 18):
            pen.line((x + dx, y + 8, x + dx, y + 24), fill=accent, width=2)
        pen.arc((x + 4, y + 26, x + 32, y + 34), start=200, end=340, fill=accent, width=2)

    def _pill(self, pen, rect, fill: str, text: str, ink: str, dot: str | None = None, outline: str | None = None) -> None:
        x0, y0, x1, y1 = rect
        radius = (y1 - y0) // 2
        kwargs = {'radius': radius, 'fill': rgb(fill)}
        if outline:
            kwargs['outline'] = rgb(outline)
            kwargs['width'] = 1
        pen.rounded_rectangle(rect, **kwargs)
        cy = (y0 + y1) / 2
        tx = x0 + 12
        if dot:
            pen.ellipse((tx, cy - 3, tx + 6, cy + 3), fill=rgb(dot))
            tx += 12
        pen.text((tx, cy), text, font=self._font(16), fill=rgb(ink), anchor='lm')

    def _hero_chrome(self, pen, hands, camera_off: bool) -> None:
        hx, hy, hw, hh = HERO
        pen.rounded_rectangle((hx, hy, hx + hw - 1, hy + hh - 1), radius=12, outline=rgb('border'), width=1)
        if camera_off:
            self._empty_state(pen)
            return
        self._pill(pen, (hx + 16, hy + 22, hx + 16 + self._pill_width('左手 / 和弦', True), hy + 50),
                   'surface', '左手 / 和弦', 'fret_edge', dot='fret_edge')
        right_label = '右手 / 扫弦'
        rw = self._pill_width(right_label, True)
        self._pill(pen, (hx + hw - 16 - rw, hy + 22, hx + hw - 16, hy + 50),
                   'surface', right_label, 'strum_line', dot='strum_line')
        pen.text((hx + 20, hy + hh - 36), '镜像预览 / 左手选和弦 / 右手穿过扫弦线',
                 font=self._font(13), fill=rgb('text'), anchor='lm')
        pill_h = 28
        # 30px from the wrist point to the pill edge. 12px left the label on the joint.
        clear = 30
        for wrist_x, wrist_y, away_x, away_y, label in hands:
            word = '左手' if label == 'Left' else '右手'
            ink = 'hand_l' if label == 'Left' else 'hand_r'
            width = self._pill_width(word, False)
            dist = clear + pill_h / 2
            cx = wrist_x + away_x * dist
            cy = wrist_y + away_y * dist
            x0 = int(round(min(max(cx - width / 2, hx + 16), hx + hw - width - 16)))
            y0 = int(round(min(max(cy - pill_h / 2, hy + 78), hy + hh - pill_h - 56)))
            self._pill(pen, (x0, y0, x0 + width, y0 + pill_h), 'surface', word, ink)

    def _pill_width(self, text: str, dot: bool) -> int:
        extra = 12 if dot else 0
        return int(round(12 + extra + self._text_width(text, 16) + 12))

    def _empty_state(self, pen) -> None:
        hx, hy, hw, hh = HERO
        cx = hx + hw / 2
        cy = hy + hh / 2 - 24
        body = (cx - 18, cy - 13, cx + 18, cy + 13)
        pen.rounded_rectangle(body, radius=4, outline=rgb('text2'), width=2)
        pen.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), outline=rgb('text2'), width=2)
        pen.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=rgb('text2'))
        pen.text((cx, body[3] + 20), '连接摄像头开始演奏', font=self.display, fill=rgb('text'), anchor='mt')
        # D toggles the debug overlay. Demo songs are the right-rail controls, not a key.
        pen.text((cx, body[3] + 64), '选择右侧示范曲可无摄像头预览',
                 font=self._font(15), fill=rgb('text2'), anchor='mt')

    def _strip(self, pen, chord, strum_state, mode, active_cell, confidence, last_event) -> None:
        self._card(pen, STRIP)
        x, y, w, h = STRIP
        splits = (x + w // 3, x + 2 * w // 3)
        for sx in splits:
            pen.line((sx, y + 20, sx, y + h - 20), fill=rgb('border'), width=1)
        columns = (x, splits[0], splits[1])
        if mode == 'chord':
            recognized = chord or '等待手势'
            locked = chord is not None
        else:
            if active_cell:
                recognized = f'第{active_cell[0] + 1}弦 / 第{active_cell[1]}品'
                locked = True
            else:
                recognized = '等待手势'
                locked = False
        if not locked:
            rec_color = 'text'
        elif confidence < 0.35:
            rec_color = 'danger'
        else:
            rec_color = 'success'
        if last_event:
            strum, strum_color = '检测到扫弦', 'warning'
        elif strum_state == StrumState.COOLDOWN:
            strum, strum_color = '冷却中', 'success'
        else:
            strum, strum_color = '准备就绪', 'text'
        rows = (
            ('演奏模式', '和弦演奏' if mode == 'chord' else '单音演奏', 'text', '按 M 切换'),
            ('当前识别', recognized, rec_color, f'置信度 {confidence:.2f}'),
            ('扫弦反馈', strum, strum_color, '空格拨弦 / H 校正左右手'),
        )
        caption_y = y + 32
        value_y = caption_y + 13 + 8
        hint_y = value_y + 22 + 8
        for cx, (caption, value, color, hint) in zip(columns, rows):
            left = cx + 20
            pen.text((left, caption_y), caption, font=self._font(13), fill=rgb('muted'))
            pen.text((left, value_y), value, font=self._font(22), fill=rgb(color))
            pen.text((left, hint_y), hint, font=self._font(13), fill=rgb('muted'))

    def _control_card(self, pen, mode: str) -> None:
        self._card(pen, CARD_CONTROL)
        x, y, _w, _h = CARD_CONTROL
        pen.text((x + 20, y + 20), '演奏控制', font=self._font(20), fill=rgb('text'))
        label = '和弦演奏' if mode == 'chord' else '单音演奏'
        self._button(pen, self.buttons['mode'], 'elevated', label, 'text', outline='border')
        pen.text((x + 20, MODE_BTN[3] + 8), '点击切换 / 按 M', font=self._font(13), fill=rgb('muted'))

    def _chord_card(self, pen, chord, mode: str) -> None:
        self._card(pen, CARD_CHORDS)
        x, y, _w, _h = CARD_CHORDS
        pen.text((x + 20, y + 20), '手势与和弦', font=self._font(20), fill=rgb('text'))
        cell_w, cell_h = CHORD_CELL
        origin_x, origin_y = CHORD_ORIGIN
        for index, name in enumerate(config.CHORD_ORDER):
            col, row = index % 3, index // 3
            x0 = origin_x + col * (cell_w + CHORD_GAP)
            y0 = origin_y + row * (cell_h + CHORD_GAP)
            rect = (x0, y0, x0 + cell_w, y0 + cell_h)
            chosen = mode == 'chord' and chord == name
            if chosen:
                pen.rounded_rectangle(rect, radius=8, fill=rgb('accent_soft'), outline=rgb('accent'), width=1)
            else:
                pen.rounded_rectangle(rect, radius=8, fill=rgb('elevated'), outline=rgb('border'), width=1)
            cy = (y0 + y0 + cell_h) / 2
            pen.text((x0 + 12, cy), f'{index}指', font=self._font(13),
                     fill=rgb('success' if chosen else 'muted'), anchor='lm')
            pen.text(((x0 + x0 + cell_w) / 2 + 8, cy), name, font=self._font(16),
                     fill=rgb('text'), anchor='mm')
        pen.text((x + 20, origin_y + 2 * cell_h + CHORD_GAP + 16),
                 '教学手势映射 / 不是真实按弦姿势', font=self._font(13), fill=rgb('muted'))

    def _song_card(self, pen, song_player: SongPlayer | None) -> None:
        self._card(pen, CARD_SONGS)
        x, y, _w, _h = CARD_SONGS
        pen.text((x + 20, y + 20), '示范曲', font=self._font(20), fill=rgb('text'))
        selected = song_player.selected if song_player else 0
        song = song_player.song if song_player else None
        for index, (key, label) in enumerate((('twinkle', '小星星'), ('ode', '欢乐颂'))):
            active = index == selected
            fill = 'accent_soft' if active else 'elevated'
            edge = 'accent' if active else 'border'
            ink = 'text' if active else 'text2'
            self._button(pen, self.buttons[key], fill, label, ink, outline=edge)
        title = song.title if song else '小星星'
        subtitle = display_copy(song.subtitle) if song else '经典旋律 / 吉他指弹改编'
        pen.text((x + 20, 640), title, font=self._font(22), fill=rgb('text'))
        pen.text((x + 20, 670), subtitle, font=self._font(13), fill=rgb('text2'))

        track = (x + 20, 744, x + CARD_SONGS[2] - 20, 750)
        progress = song_player.progress if song_player else 0.0
        self._progress(pen, track, progress)
        if song_player:
            elapsed = _mmss(song_player.elapsed_seconds)
            total = _mmss(song_player.song.duration_seconds)
            state = {'stopped': '待播放', 'playing': '正在弹奏', 'paused': '已暂停'}[song_player.state]
        else:
            elapsed, total, state = '00:00', _mmss(SONGS[0].duration_seconds), '待播放'
        state_fill = 'success' if state == '正在弹奏' else ('text2' if state == '已暂停' else 'muted')
        pen.text((x + 20, 766), state, font=self._font(13), fill=rgb(state_fill), anchor='lm')
        pen.text((x + CARD_SONGS[2] - 20, 766), f'{elapsed} / {total}',
                 font=self._font(15), fill=rgb('text2'), anchor='rm')

        playing = song_player is not None and song_player.state == 'playing'
        paused = song_player is not None and song_player.state == 'paused'
        if playing:
            play_label, icon = '暂停', 'pause'
        elif paused:
            play_label, icon = '继续', 'play'
        else:
            play_label, icon = '播放示范曲', 'play'
        self._button(pen, self.buttons['play_pause'], 'accent', play_label, 'on_accent', icon=icon, icon_fill='on_accent')
        self._button(pen, self.buttons['stop'], 'elevated', '停止', 'text', outline='border', icon='stop', icon_fill='text')
        pen.text((x + 20, 838), 'P 播放 / 暂停 / T 停止', font=self._font(13), fill=rgb('muted'))

    def _button(self, pen, rect, fill: str, text: str, ink: str,
                outline: str | None = None, icon: str | None = None, icon_fill: str | None = None) -> None:
        kwargs = {'radius': 8, 'fill': rgb(fill)}
        if outline:
            kwargs['outline'] = rgb(outline)
            kwargs['width'] = 1
        pen.rounded_rectangle(rect, **kwargs)
        x0, y0, x1, y1 = rect
        cy = (y0 + y1) / 2
        font = self._font(16)
        text_w = float(font.getlength(text))
        icon_w = 0
        gap = 0
        if icon == 'play':
            icon_w, icon_h, gap = 11, 13, 8
        elif icon == 'pause':
            icon_w, icon_h, gap = 10, 13, 8
        elif icon == 'stop':
            icon_w, icon_h, gap = 10, 10, 8
        total = icon_w + gap + text_w
        left = (x0 + x1) / 2 - total / 2
        if icon:
            self._icon(pen, icon, left, cy - icon_h / 2, rgb(icon_fill or ink))
            left += icon_w + gap
        pen.text((left, cy), text, font=font, fill=rgb(ink), anchor='lm')

    def _icon(self, pen, kind: str, x: float, y: float, fill) -> None:
        if kind == 'play':
            pen.polygon((x, y, x, y + 13, x + 11, y + 6.5), fill=fill)
        elif kind == 'pause':
            pen.rectangle((x, y, x + 3, y + 13), fill=fill)
            pen.rectangle((x + 7, y, x + 10, y + 13), fill=fill)
        elif kind == 'stop':
            pen.rounded_rectangle((x, y, x + 10, y + 10), radius=2, fill=fill)

    def _progress(self, pen, rect, progress: float) -> None:
        x0, y0, x1, y1 = rect
        pen.rounded_rectangle(rect, radius=3, fill=rgb('track'))
        progress = max(0.0, min(1.0, progress))
        head = x0 + (x1 - x0) * progress
        if progress > 0.004:
            pen.rounded_rectangle((x0, y0, max(x0 + 6, head), y1), radius=3, fill=rgb('accent'))
        radius = 5
        pen.ellipse((head - radius, (y0 + y1) / 2 - radius, head + radius, (y0 + y1) / 2 + radius), fill=rgb('accent'))
