"""Recognize six easy symbolic left-hand gestures or one selected fret cell."""
from __future__ import annotations
from collections import Counter, deque
from math import hypot
from typing import Optional
from . import config
from .config import ChordId, FingerShape
from .fretboard import Fretboard, FretboardGeom
from .hand_tracker import HandResult

FINGERS = ((5,6,8), (9,10,12), (13,14,16), (17,18,20))  # MCP/PIP/TIP

def _distance(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return hypot(a[0] - b[0], a[1] - b[1])

def extended_fingers(hand: HandResult) -> tuple[bool, bool, bool, bool, bool]:
    """Determine digits from normalized palm-relative geometry, independent of rotation.

    Thumb is measured relative to the pinky knuckle, the other four
    against their PIP-to-MCP distances. A conservative threshold limits
    accidental chord changes from a single bent finger.
    """
    if len(hand.landmarks) < 21:
        return (False,) * 5
    p = hand.landmarks
    palm = max(1., _distance(p[0], p[9]))
    # Thumb straight when tip protrudes away from the pinky base AND its MCP.
    thumb = (_distance(p[4], p[17]) > _distance(p[3], p[17]) + palm * .16 and
             _distance(p[4], p[2]) > _distance(p[3], p[2]) * 1.12)
    fingers = []
    for mcp, pip, tip in FINGERS:
        outward = _distance(p[tip], p[mcp]) > _distance(p[pip], p[mcp]) * 1.45
        raised = _distance(p[tip], p[0]) > _distance(p[pip], p[0]) + palm * .09
        fingers.append(bool(outward and raised))
    return (bool(thumb), *fingers)

def finger_count_gesture(hand: HandResult) -> Optional[int]:
    thumb, index, middle, ring, pinky = extended_fingers(hand)
    digits = (index, middle, ring, pinky)
    # Count 1..4 uses the leading consecutive fingers, never arbitrary subsets.
    if thumb:
        return 5 if all(digits) else None
    if all(not v for v in digits):
        return 0
    for n in (1, 2, 3, 4):
        if digits == (True,) * n + (False,) * (4 - n):
            return n
    return None

class ChordMapper:
    def __init__(self, templates: dict[ChordId, FingerShape] | None = None,
                 vote_window: int = config.VOTE_WINDOW) -> None:
        if vote_window < 3:
            raise ValueError("vote_window must be >= 3")
        self._templates = templates if templates is not None else config.CHORD_TEMPLATES
        self._history: deque[Optional[str]] = deque(maxlen=vote_window)
        self._stable: Optional[str] = None
        self._cells: deque[Optional[tuple[int,int]]] = deque(maxlen=vote_window)
        self._stable_cell: Optional[tuple[int, int]] = None

    def gesture(self, hand: HandResult) -> tuple[Optional[str], float, Optional[int]]:
        idx = finger_count_gesture(hand)
        return (config.GESTURE_TO_CHORD.get(idx), float(hand.score) if idx is not None else 0., idx)

    def fingertips_to_shape(self, left_hand: HandResult, geom: FretboardGeom,
                            fretboard: Fretboard) -> FingerShape:
        def cell(i: int) -> Optional[tuple[int, int]]:
            p = left_hand.landmarks[i]
            return fretboard.point_to_cell((p[0], p[1]), geom)
        return FingerShape(index=cell(8), middle=cell(12), ring=cell(16), pinky=cell(20))

    def match(self, shape: FingerShape) -> tuple[Optional[ChordId], float]:
        """Legacy grid-template API: not used for approved Plan A chord mode."""
        # Symbolic CHORD_TEMPLATES are intentionally empty; do not manufacture
        # confidence from them. The production classifier is gesture().
        return None, 0.

    def update_filtered(self, chord: Optional[ChordId]) -> Optional[ChordId]:
        self._history.append(chord)
        counts = Counter(self._history)
        candidate, count = counts.most_common(1)[0]
        needed = max(config.VOTE_MIN_COUNT, len(self._history) // 2 + 1)
        if count >= needed and (candidate == self._stable or count >= needed):
            self._stable = candidate
        # Dropout is intentional: no detected left hand must eventually mute.
        return self._stable

    def update_cell(self, cell: Optional[tuple[int, int]]) -> Optional[tuple[int, int]]:
        self._cells.append(cell)
        candidate, count = Counter(self._cells).most_common(1)[0]
        needed = max(config.VOTE_MIN_COUNT, len(self._cells) // 2 + 1)
        if count >= needed:
            self._stable_cell = candidate
        return self._stable_cell

    def cells_to_notes(self, cells: list[tuple[int, int]], mode: str = "single") -> list[int]:
        notes = [config.OPEN_STRING_MIDI[s] + f for s, f in cells
                 if 0 <= s < config.N_STRINGS and 0 <= f <= config.N_FRETS]
        return notes[:1] if mode == "single" else list(dict.fromkeys(notes))

    def reset(self) -> None:
        self._history.clear()
        self._cells.clear()
        self._stable = None
        self._stable_cell = None
