"""Stage tokens, layout, and the ASCII HighGUI window title.

OpenCV tuples elsewhere are BGR. Pillow draws with the RGB tuples from ``rgb()``.
Coordinates are the 1440×900 brief: 8px grid, 4px micro steps.
"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import ImageFont

# HighGUI on Windows writes the caption through the ANSI API. A Chinese title
# becomes the mojibake in the shipped screenshot. Never pass non-ASCII text to
# namedWindow or setWindowTitle. A Unicode caption would be SetWindowTextW
# after this ASCII window already exists.
WINDOW_TITLE = 'AirGuitar Vision'

CANVAS_W, CANVAS_H = 1440, 900

# xywh. 64px tall: a 28px title plus a 15px subtitle need an 8px gap
# between descenders and ascenders, and the bar still ends 8px above the hero.
HEADER = (24, 16, 1392, 64)
HERO = (24, 88, 952, 644)
STRIP = (24, 748, 952, 128)
# 24px between rail cards. The chord card gives up empty space under its
# footnote so the mode and song hit targets stay on the same pixels.
CARD_CONTROL = (992, 88, 424, 156)
CARD_CHORDS = (992, 268, 424, 232)
CARD_SONGS = (992, 524, 424, 352)

PAD = 20
GAP = 16
MICRO = 8

# Rail controls. Header pills are measured from the label and stored on Overlay.
MODE_BTN = (1012, 148, 1396, 192)
TWINKLE_BTN = (1012, 580, 1200, 620)
ODE_BTN = (1208, 580, 1396, 620)
PLAY_BTN = (1012, 786, 1260, 830)
STOP_BTN = (1268, 786, 1396, 830)

CHORD_ORIGIN = (1013, 324)
CHORD_CELL = (122, 40)
CHORD_GAP = 8

_HEX = {
    'bg': '#0E1116',
    'surface': '#161C24',
    'elevated': '#1E2733',
    'border': '#314052',
    'text': '#F4F7FB',
    'text2': '#B7C3D0',
    'muted': '#8A97A6',
    'accent': '#3EE0C2',
    'accent_soft': '#14342E',
    'on_accent': '#06211C',
    'success': '#3DDC97',
    'warning': '#F0B429',
    'danger': '#F07178',
    'fret_tint': '#163A66',
    'fret_edge': '#8EB7E8',
    'strum_tint': '#3A3420',
    'strum_line': '#E8C45A',
    'hand_l': '#7EB6FF',
    'hand_r': '#7EE0B8',
    'track': '#2A3848',
    'hit_fill': '#3A3018',
    'danger_fill': '#3A2228',
}


def rgb(name: str) -> tuple[int, int, int]:
    value = _HEX[name]
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def bgr(name: str) -> tuple[int, int, int]:
    red, green, blue = rgb(name)
    return blue, green, red


def assert_ascii_window_title(title: str) -> str:
    """Reject any caption that HighGUI would encode as ANSI/GBK garbage."""
    if not isinstance(title, str) or title != title.strip() or not title:
        raise ValueError(f'OpenCV window title must be a non-empty ASCII string, got {title!r}')
    if not title.isascii() or any(ord(ch) < 32 for ch in title):
        raise ValueError(f'OpenCV window title must be printable ASCII, got {title!r}')
    return title


def xyxy(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x, y, w, h = box
    return x, y, x + w, y + h


_FONT_DIRS = (
    'C:/Windows/Fonts',
    '/usr/share/fonts/opentype/noto',
    '/usr/share/fonts/opentype/source-han-sans',
    '/usr/share/fonts/truetype/noto',
    '/System/Library/Fonts',
    '/usr/share/fonts/truetype/arphic',
)
_REGULAR_NAMES = (
    'msyh.ttc',
    'msyhbd.ttc',
    'NotoSansCJK-Regular.ttc',
    'SourceHanSansSC-Regular.otf',
    'simhei.ttf',
    'simsun.ttc',
    'gbsn00lp.ttf',
)
_BOLD_NAMES = (
    'msyhbd.ttc',
    'NotoSansCJK-Bold.ttc',
    'SourceHanSansSC-Bold.otf',
    'simhei.ttf',
)


def _font_dirs() -> list[Path]:
    dirs = [Path(item) for item in _FONT_DIRS]
    local = os.environ.get('LOCALAPPDATA')
    if local:
        dirs.append(Path(local) / 'Microsoft' / 'Windows' / 'Fonts')
    return dirs


def _find_named(names: tuple[str, ...]) -> str | None:
    for name in names:
        for folder in _font_dirs():
            path = folder / name
            if path.is_file():
                return str(path)
    return None


def _face_index(path: str) -> int:
    if not path.lower().endswith('.ttc'):
        return 0
    for index in range(16):
        try:
            face = ImageFont.truetype(path, 16, index=index)
        except OSError:
            break
        family = face.getname()[0]
        if family.endswith(' SC') or 'Sans SC' in family or family in ('Microsoft YaHei', 'SimHei', 'SimSun'):
            return index
    return 0


def load_cjk_fonts(sizes: tuple[int, ...] = (13, 15, 16, 20, 22, 28)) -> tuple[dict[int, ImageFont.FreeTypeFont], ImageFont.FreeTypeFont]:
    """One CJK family for every string. Display uses a bold file when one exists."""
    regular = _find_named(_REGULAR_NAMES)
    if regular is None:
        raise RuntimeError('未找到可显示中文的系统字体。请在 Windows 安装“微软雅黑”或“黑体”，再启动程序。')
    regular_index = _face_index(regular)
    fonts = {size: ImageFont.truetype(regular, size, index=regular_index) for size in sizes}
    bold_path = _find_named(_BOLD_NAMES)
    if bold_path is None:
        display = fonts.get(28) or ImageFont.truetype(regular, 28, index=regular_index)
    else:
        display = ImageFont.truetype(bold_path, 28, index=_face_index(bold_path))
    return fonts, display
