"""Centralized configuration for the Air Guitar course project.

All coordinates are relative to a mirrored (selfie) camera frame unless noted.
Adjust thresholds here after inspecting the on-screen debug information.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Optional

PROJECT_DIR = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
ASSET_DIR = PROJECT_DIR / "assets"
MODEL_PATH = ASSET_DIR / "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)

ChordId = str
@dataclass(frozen=True)
class FingerShape:
    index: Optional[tuple[int, int]] = None
    middle: Optional[tuple[int, int]] = None
    ring: Optional[tuple[int, int]] = None
    pinky: Optional[tuple[int, int]] = None

    def as_cells(self) -> list[tuple[int, int]]:
        return [v for v in (self.index, self.middle, self.ring, self.pinky) if v is not None]

CAMERA_ID = 0
FRAME_WIDTH = 960
FRAME_HEIGHT = 540
TARGET_FPS = 30
MIRROR_CAMERA = True  # Mirror the live webcam preview like a selfie.
# The supplied project was observed to receive reversed Left/Right labels on
# the target live-webcam/MediaPipe setup. Correct the role map by default for
# the live webcam; press H to toggle if a different camera labels correctly.
DEFAULT_HAND_ROLE_SWAP = True
MP_MAX_HANDS = 2
MP_MODEL_COMPLEXITY = 0
MP_MIN_DETECTION_CONF = .55
MP_MIN_TRACKING_CONF = .52

FRETBOARD_MODE = "fixed_roi"
N_STRINGS = 6
N_FRETS = 4
# normalized ROI, intentionally LEFT of the separate RIGHT-hand strum zone
FRETBOARD_ROI = (.085, .42, .48, .40)
STRUM_ROI = (.665, .34, .29, .48)
OPEN_STRING_MIDI = [40, 45, 50, 55, 59, 64]  # E2,A2,D3,G3,B3,E4
STRING_NAMES = ["E2", "A2", "D3", "G3", "B3", "E4"]

V_TH = .22                # minimum normal crossing speed, in pixels / ms at 540p
APPROACH_MARGIN = 48.0    # pixels at 540p, scaled by frame height
COOLDOWN_MS = 180
APPROACH_TIMEOUT_MS = 420
MAX_FRAME_GAP_MS = 180     # prevent spurious events after missed detections
MAX_TIP_JUMP_PX = 165.0   # at 540p

VOTE_WINDOW = 5
VOTE_MIN_COUNT = 3
# Gesture mappings are deliberately symbolic, not literal guitar fingerings.
# States: 0=fist, 1=index, 2=V, 3=three, 4=four, 5=open palm.
GESTURE_TO_CHORD = {0: "Em", 1: "Am", 2: "C", 3: "D", 4: "G", 5: "F"}
CHORD_ORDER = ["Em", "Am", "C", "D", "G", "F"]
GESTURE_LABELS = ["FIST", "INDEX", "V SIGN", "THREE", "FOUR", "OPEN"]
# Legacy symbolic template names retained for compatibility with the original architecture.
CHORD_TEMPLATES = {name: FingerShape() for name in CHORD_ORDER}
CHORD_NOTES = {
    "Em": [40, 47, 52, 55, 59, 64],
    "Am": [45, 52, 57, 60, 64],
    "C": [48, 52, 55, 60, 64],
    "D": [50, 57, 62, 66],
    "G": [43, 47, 50, 55, 59, 67],
    "F": [41, 48, 53, 57, 60, 65],
}

AUDIO_BACKEND = "pygame"
DEBUG_OVERLAY = True
KEYS = {
    "quit_q": ord("q"), "quit_esc": 27,
    "toggle_debug": ord("d"), "toggle_mode": ord("m"),
    "silence": ord("s"), "toggle_hands": ord("h"),
    "strum": 32, "reset_override": ord("0"),
}
