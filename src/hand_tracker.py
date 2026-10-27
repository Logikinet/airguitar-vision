"""MediaPipe Hand Landmarker Tasks adapter with optional old-solutions fallback.

The Tasks API is preferred. Its official .task model is downloaded once on
first start if absent. The old Solutions fallback is only used if installed.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import time
import urllib.request
import numpy as np
import cv2
from . import config

@dataclass
class HandResult:
    handedness: str  # "Left" or "Right", camera image is selfie-mirrored
    landmarks: list[tuple[float, float, float]]
    score: float


def ensure_model(path: Path = config.MODEL_PATH, *, download: bool = True) -> Path:
    """Resolve bundled/downloaded official Hand Landmarker model atomically."""
    path = Path(path)
    if path.is_file() and path.stat().st_size > 100_000:
        return path
    if not download:
        raise FileNotFoundError(f"No Hand Landmarker model: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".part")
    try:
        print("[model] Downloading Google's official MediaPipe hand_landmarker.task (once)...")
        with urllib.request.urlopen(config.MODEL_URL, timeout=35) as resp, open(temp, "wb") as out:
            while block := resp.read(1024 * 256):
                out.write(block)
        if temp.stat().st_size < 100_000:
            raise RuntimeError("Incomplete model download")
        temp.replace(path)
    except Exception as exc:
        temp.unlink(missing_ok=True)
        raise RuntimeError("Could not download MediaPipe hand model. Connect to the internet, "
                           "run: python tools/download_model.py, or manually save "
                           f"{config.MODEL_URL} as {path}.") from exc
    return path

class HandTracker:
    def __init__(self, max_num_hands: int = 2, model_complexity: int = 0,
                 model_path: Path = config.MODEL_PATH) -> None:
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError("MediaPipe is not installed. Run: python -m pip install -r requirements.txt") from exc
        self._mp = mp
        self._backend = ""
        self._model = None
        self._legacy = None
        self._last_timestamp = -1
        model_path = Path(model_path)
        try:
            # Some older environments have Solutions but no internet. Prefer
            # Tasks if the model is present or can be fetched successfully.
            ensure_model(model_path)
            options = mp.tasks.vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_hands=max_num_hands,
                min_hand_detection_confidence=config.MP_MIN_DETECTION_CONF,
                min_hand_presence_confidence=config.MP_MIN_DETECTION_CONF,
                min_tracking_confidence=config.MP_MIN_TRACKING_CONF,
            )
            self._model = mp.tasks.vision.HandLandmarker.create_from_options(options)
            self._backend = "tasks"
        except (RuntimeError, FileNotFoundError, AttributeError) as exc:
            if not hasattr(mp, "solutions") or not hasattr(mp.solutions, "hands"):
                raise RuntimeError("MediaPipe Tasks could not start: " + str(exc)) from exc
            print("[model] Tasks unavailable; using compatible bundled MediaPipe Hands model.")
            self._legacy = mp.solutions.hands.Hands(
                static_image_mode=False, max_num_hands=max_num_hands,
                model_complexity=model_complexity,
                min_detection_confidence=config.MP_MIN_DETECTION_CONF,
                min_tracking_confidence=config.MP_MIN_TRACKING_CONF,
            )
            self._backend = "solutions"

    def process(self, frame_bgr: np.ndarray, now_ms: int | None = None) -> list[HandResult]:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        if self._backend == "tasks":
            rgb = np.ascontiguousarray(rgb)
            mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
            stamp = int(time.monotonic_ns() // 1_000_000) if now_ms is None else int(now_ms)
            stamp = max(stamp, self._last_timestamp + 1)
            self._last_timestamp = stamp
            result = self._model.detect_for_video(mp_image, stamp)
            return [HandResult(
                handedness=group[0].category_name,
                score=float(group[0].score),
                landmarks=[(p.x * w, p.y * h, p.z * w) for p in landmark_list],
            ) for landmark_list, group in zip(result.hand_landmarks, result.handedness) if group]
        result = self._legacy.process(rgb)
        if not result.multi_hand_landmarks or not result.multi_handedness:
            return []
        return [HandResult(
            handedness=hd.classification[0].label,
            score=float(hd.classification[0].score),
            landmarks=[(p.x * w, p.y * h, p.z * w) for p in landmarks.landmark],
        ) for landmarks, hd in zip(result.multi_hand_landmarks, result.multi_handedness)]

    def close(self) -> None:
        for obj in (self._model, self._legacy):
            if obj is not None:
                obj.close()
