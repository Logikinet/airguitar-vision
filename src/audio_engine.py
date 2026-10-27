"""Pygame polyphonic WAV playback with frame-safe queued down/up strums."""
from __future__ import annotations
import heapq
import os
import time
from pathlib import Path
from . import config

class AudioEngine:
    def __init__(self, backend: str = "pygame", asset_dir: str | Path = config.ASSET_DIR,
                 *, muted: bool = False) -> None:
        self.muted = muted
        self._mixer = None
        self._cache: dict[int, object] = {}
        self._scheduled: list[tuple[float, int, int, float]] = []
        self._sequence = 0
        self._asset_dir = Path(asset_dir)
        if muted:
            return
        if backend != "pygame":
            raise ValueError("Supported audio backend: pygame")
        try:
            import pygame
            os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
            self._mixer = pygame.mixer
        except Exception as exc:
            print(f"[audio] No audio output available ({exc}); continuing muted. Fix output device to hear sound.")
            self.muted = True

    def note_on(self, midi_note: int, velocity: float = .8) -> None:
        if self.muted:
            return
        note = int(midi_note)
        if not 40 <= note <= 84:
            return
        if note not in self._cache:
            path = self._asset_dir / f"pluck_{note}.wav"
            if not path.is_file():
                print(f"[audio] Missing bundled WAV: {path}")
                return
            self._cache[note] = self._mixer.Sound(str(path))
        channel = self._mixer.find_channel(force=True)
        if channel is not None:
            channel.set_volume(max(0., min(1., float(velocity))))
            channel.play(self._cache[note])

    def chord_on(self, midi_notes: list[int], velocity: float = .8,
                 direction: str = "down") -> None:
        """Queue notes in order 12ms apart without blocking the video thread."""
        notes = sorted(set(midi_notes), reverse=(direction == "up"))
        now = time.monotonic()
        for i, note in enumerate(notes):
            self._sequence += 1
            heapq.heappush(self._scheduled, (now + i * .012, self._sequence, note, velocity))
        self.update()

    def update(self) -> None:
        now = time.monotonic()
        while self._scheduled and self._scheduled[0][0] <= now:
            _, _, note, velocity = heapq.heappop(self._scheduled)
            self.note_on(note, velocity)

    def all_notes_off(self) -> None:
        self._scheduled.clear()
        if self._mixer is not None:
            self._mixer.stop()

    def close(self) -> None:
        self.all_notes_off()
        if self._mixer is not None:
            self._mixer.quit()
