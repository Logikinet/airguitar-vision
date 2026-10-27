"""Deterministic fake tracker used ONLY for --demo (not AI recognition)."""
from __future__ import annotations
import math
import numpy as np
from .hand_tracker import HandResult
from . import config

# Approximate finger coordinates for a static upright palm centered at (x,y).
def fake_hand(cx: float, cy: float, *, role: str, finger_count: int = 5) -> HandResult:
    palm = [
        (0, 68), (-37, 48), (-58, 22), (-65, -8), (-73, -32),
        (-28, 10), (-34, -24), (-34, -57), (-35, -82),
        (-4, 4), (-5, -34), (-5, -70), (-5, -96),
        (20, 8), (20, -30), (21, -61), (22, -85),
        (40, 19), (44, -15), (48, -45), (51, -69),
    ]
    # Keep proximal joints; tuck last two finger joints when bent.
    digits = [8, 12, 16, 20]
    v = list(palm)
    for fi, tip in enumerate(digits):
        if fi >= min(4, finger_count):
            m = tip - 3; pip = tip - 2
            x0,y0 = v[m]
            v[pip] = (x0 + 3, y0 + 16)
            v[tip - 1] = (x0 + 7, y0 + 30)
            v[tip] = (x0 + 3, y0 + 21)
    if finger_count < 5:
        v[4] = (-20, 39)
    # right hand has all fingers spread, and a visible fingertip at index #8
    if role == 'Right':
        v[4] = (-73, -32)
    return HandResult(role, [(cx+x,cy+y,0.) for x,y in v], .99)


class DemoScene:
    """A synthetic loop that exercises REAL mapping/strum/audio state machines."""
    def __init__(self):
        self.start_ms: int | None = None
        self.manual_chord: int | None = None
        self.auto = True
        self.cell = (2, 2)

    def frame(self, shape: tuple[int,int], now_ms: int, mode: str) -> tuple[np.ndarray,list[HandResult]]:
        h,w = shape
        if self.start_ms is None:
            self.start_ms = now_ms
        t = (now_ms-self.start_ms)/1000
        stage = int(t//3.6) % 6
        idx = stage if self.manual_chord is None else self.manual_chord
        frame = np.zeros((h,w,3), dtype=np.uint8)
        # Camera-like gradient for a pleasant, predictable offline demonstration.
        frame[...,0] = np.linspace(27,45,w,dtype=np.uint8)[None,:]
        frame[...,1] = np.linspace(34,46,h,dtype=np.uint8)[:,None]
        frame[...,2] = 38
        if mode == 'chord':
            left = fake_hand(w*.25, h*.37, role='Left', finger_count=idx)
        else:
            # The fingertip must sit inside the grid; exact placement not affected by
            # other synthetic hand points.
            left = fake_hand(w*.30, h*.55, role='Left',finger_count=1)
            cell_s,cell_f = self.cell
            x,y,rw,rh=config.FRETBOARD_ROI
            px=(x+(cell_f+.5)*rw/(config.N_FRETS+1))*w
            py=(y+(cell_s+.5)*rh/config.N_STRINGS)*h
            dx=px-left.landmarks[8][0]; dy=py-left.landmarks[8][1]
            left.landmarks=[(xx+dx,yy+dy,zz) for xx,yy,zz in left.landmarks]
        x,y,rw,rh=config.STRUM_ROI
        phase=(t*2.0)%2.0
        # Right index makes periodic down/up crossings, margin and velocity
        # are consistent with the live detector.
        move=math.sin(t*math.pi*1.55)*.27
        right=fake_hand((x+rw*.48)*w,(y+rh*.5 + move)*h + 82, role='Right',finger_count=5)
        return frame,[left,right]
