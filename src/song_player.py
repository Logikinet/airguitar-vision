"""非阻塞吉他示范曲播放器：公共领域旋律 + 原创分解和弦伴奏。"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class NoteEvent:
    beat: float
    note: int
    velocity: float


@dataclass(frozen=True)
class Song:
    key: str
    title: str
    subtitle: str
    bpm: int
    beats: float
    events: tuple[NoteEvent, ...]

    @property
    def duration_seconds(self) -> float:
        return self.beats * 60.0 / self.bpm


class NoteOutput(Protocol):
    def note_on(self, midi_note: int, velocity: float = .8) -> None: ...


# 和弦低音及完整音阶。左手六手势逻辑保持不变；演示曲可用 Dm 等额外伴奏和弦。
VOICE = {
    'C':  (48, 55, 60, 64, 67),
    'G':  (43, 50, 55, 59, 67),
    'Am': (45, 52, 57, 60, 64),
    'F':  (41, 48, 53, 57, 65),
    'Dm': (50, 57, 62, 65, 69),
}


def _arrange(key: str, title: str, subtitle: str, bpm: int,
             melody: list[list[tuple[int, float]]], harmony: list[str]) -> Song:
    """Each melody bar occupies four beats. Counter-melody uses restrained picking.

    All MIDI notes fit bundled pluck_40..pluck_84.wav. The rhythm is evaluated
    against a monotonic clock, not `sleep`, keeping the camera loop responsive.
    """
    assert len(melody) == len(harmony)
    events: list[NoteEvent] = []
    for bar, (notes, chord_name) in enumerate(zip(melody, harmony)):
        offset = bar * 4.0
        tones = VOICE[chord_name]
        # 适当错开的向下扫弦 + 轻柔的分解和弦，不抢主旋律。
        for j, n in enumerate(tones[:4]):
            events.append(NoteEvent(offset + j * .045, n, .20 if j else .32))
        for shift, n in ((1., tones[2]), (1.5, tones[3]), (2., tones[1]),
                         (2.5, tones[3]), (3., tones[2]), (3.5, tones[-1])):
            events.append(NoteEvent(offset + shift, n, .18))
        t = offset
        for pitch, duration in notes:
            events.append(NoteEvent(t + .015, pitch, .88))
            t += duration
        assert abs(t - (offset + 4.)) < 1e-6, (title, bar, t)
    events.sort(key=lambda e: e.beat)
    return Song(key, title, subtitle, bpm, len(melody) * 4., tuple(events))


TWINKLE = _arrange(
    'twinkle', '小星星', '经典旋律 · 吉他指弹改编', 112,
    [
        [(72, 1), (72, 1), (79, 1), (79, 1)],
        [(81, 1), (81, 1), (79, 2)],
        [(77, 1), (77, 1), (76, 1), (76, 1)],
        [(74, 1), (74, 1), (72, 2)],
        [(79, 1), (79, 1), (77, 1), (77, 1)],
        [(76, 1), (76, 1), (74, 2)],
        [(79, 1), (79, 1), (77, 1), (77, 1)],
        [(76, 1), (76, 1), (74, 2)],
        [(72, 1), (72, 1), (79, 1), (79, 1)],
        [(81, 1), (81, 1), (79, 2)],
        [(77, 1), (77, 1), (76, 1), (76, 1)],
        [(74, 1), (74, 1), (72, 2)],
    ],
    ['C', 'Am', 'F', 'C', 'G', 'G', 'Am', 'G', 'C', 'Am', 'F', 'C'],
)
ODE_TO_JOY = _arrange(
    'ode', '欢乐颂', '贝多芬主题 · 吉他独奏改编', 104,
    [
        [(76, 1), (76, 1), (77, 1), (79, 1)],
        [(79, 1), (77, 1), (76, 1), (74, 1)],
        [(72, 1), (72, 1), (74, 1), (76, 1)],
        [(76, 1.5), (74, .5), (74, 2)],
        [(76, 1), (76, 1), (77, 1), (79, 1)],
        [(79, 1), (77, 1), (76, 1), (74, 1)],
        [(72, 1), (72, 1), (74, 1), (76, 1)],
        [(74, 1.5), (72, .5), (72, 2)],
    ],
    ['C', 'G', 'C', 'G', 'Am', 'F', 'G', 'C'],
)
SONGS: tuple[Song, ...] = (TWINKLE, ODE_TO_JOY)


class SongPlayer:
    """按时间戳增量发送音符。不使用线程或阻塞等待。

    Callbacks are performed only from update(); selecting tracks and pausing are
    safe even if no sound card exists (useful for simulated classroom demos).
    """
    def __init__(self, songs: tuple[Song, ...] = SONGS):
        if not songs:
            raise ValueError('At least one song is required')
        self.songs = songs
        self.selected = 0
        self.state = 'stopped'  # stopped / playing / paused
        self._start_ms = 0
        self._pause_at_ms = 0
        self._cursor = 0
        self._elapsed_ms = 0

    @property
    def song(self) -> Song:
        return self.songs[self.selected]

    @property
    def progress(self) -> float:
        return max(0., min(1., self._elapsed_ms / (self.song.duration_seconds * 1000)))

    @property
    def elapsed_seconds(self) -> float:
        return self._elapsed_ms / 1000

    def select(self, index: int) -> None:
        if not 0 <= index < len(self.songs):
            raise IndexError(index)
        self.selected = index
        self.stop()

    def stop(self) -> None:
        self.state = 'stopped'
        self._cursor = 0
        self._elapsed_ms = 0
        self._start_ms = 0
        self._pause_at_ms = 0

    def play_pause(self, now_ms: int) -> None:
        if self.state == 'playing':
            self.state = 'paused'
            self._pause_at_ms = now_ms
        elif self.state == 'paused':
            self._start_ms += now_ms - self._pause_at_ms
            self.state = 'playing'
        else:
            self._start_ms = now_ms
            self._cursor = 0
            self._elapsed_ms = 0
            self.state = 'playing'

    def update(self, now_ms: int, audio: NoteOutput) -> None:
        if self.state != 'playing':
            return
        self._elapsed_ms = max(0, now_ms - self._start_ms)
        beat = self._elapsed_ms / 1000 * self.song.bpm / 60
        events = self.song.events
        while self._cursor < len(events) and events[self._cursor].beat <= beat:
            e = events[self._cursor]
            audio.note_on(e.note, e.velocity)
            self._cursor += 1
        if beat >= self.song.beats + .6:
            self.stop()

    @property
    def current_bar(self) -> int:
        if self.state == 'stopped':
            return 0
        beat = self._elapsed_ms / 1000 * self.song.bpm / 60
        return min(int(beat // 4) + 1, int(self.song.beats / 4))

    @property
    def playing(self) -> bool:
        return self.state == 'playing'
