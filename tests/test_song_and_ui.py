"""中文可点击 UI 与两首示范曲的节奏回归测试。"""
import wave
from src import config
from src.song_player import SONGS, SongPlayer
from src.overlay import Overlay, CANVAS_W, CANVAS_H


class FakeAudio:
    def __init__(self):self.notes=[]
    def note_on(self,note,velocity=.8):self.notes.append((note,velocity))


def test_public_domain_songs_are_musically_arranged():
    assert len(SONGS)==2
    assert [s.title for s in SONGS]==['小星星','欢乐颂']
    for song in SONGS:
        assert 15<song.duration_seconds<35
        assert len(song.events)>80
        assert all(40<=e.note<=84 for e in song.events)
        assert list(song.events)==sorted(song.events,key=lambda e:e.beat)
        assert len(set(e.note for e in song.events))>=10


def test_play_pause_resume_stop_uses_monotonic_clock():
    p=SongPlayer();a=FakeAudio()
    p.play_pause(1000)
    p.update(1000,a)
    assert p.state=='playing' and len(a.notes)>=1
    p.update(3000,a)
    before=len(a.notes)
    elapsed=p.elapsed_seconds
    p.play_pause(3000)
    p.update(9000,a)
    assert len(a.notes)==before and p.elapsed_seconds==elapsed
    assert p.state=='paused'
    p.play_pause(9000)
    p.update(9200,a)
    assert p.elapsed_seconds==2.2 and len(a.notes)>=before
    p.stop()
    assert p.progress==0 and p.current_bar==0 and p.state=='stopped'


def test_song_finishes_and_can_replay():
    p=SongPlayer();a=FakeAudio()
    p.select(1)
    p.play_pause(0)
    p.update(100000,a)
    assert p.state=='stopped'
    assert len(a.notes)==len(SONGS[1].events)
    p.play_pause(105000)
    p.update(105000,a)
    assert p.state=='playing'


def test_live_ui_mouse_buttons_and_font_available():
    o=Overlay()
    for name in ('play_pause', 'stop', 'twinkle', 'ode', 'mode', 'mute', 'fullscreen'):
        x0, y0, x1, y1 = o.buttons[name]
        assert o.hit_test((x0 + x1) // 2, (y0 + y1) // 2) == name
    # Hero center is the camera, not a control.
    assert o.hit_test(24 + 476, 88 + 322) is None
    assert CANVAS_W == 1440 and CANVAS_H == 900


def test_window_title_is_ascii_only():
    import inspect
    from main import WINDOW_TITLE, run, set_ascii_window_caption
    from src.theme import assert_ascii_window_title
    assert assert_ascii_window_title(WINDOW_TITLE) == 'AirGuitar Vision'
    assert WINDOW_TITLE.isascii()
    source = inspect.getsource(run)
    assert 'namedWindow' in source and 'WINDOW_TITLE' in source
    assert '空气吉他 - 中文视觉演奏台' not in source
    assert 'setWindowTitle' not in source
    caption = inspect.getsource(set_ascii_window_caption)
    assert 'SetWindowTextW' in caption and 'cv2.namedWindow' not in caption
    try:
        assert_ascii_window_title('空气吉他')
    except ValueError:
        return
    raise AssertionError('Chinese window titles must be rejected')


def test_song_previews_are_real_wav_files():
    for song in SONGS:
        file=config.ASSET_DIR/f'demo_song_{song.key}.wav'
        assert file.is_file()
        with wave.open(str(file),'rb') as w:
            assert w.getframerate()==22050 and w.getnchannels()==1
            assert w.getnframes()>w.getframerate()*15
