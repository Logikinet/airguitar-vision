"""A no-camera/no-audio frame tests actual composition and bundled WAVs."""
import wave
import cv2
import numpy as np
from src import config
from src.demo import DemoScene
from src.fretboard import Fretboard
from src.overlay import Overlay, CANVAS_H, CANVAS_W
from src.strum_detector import StrumState
from main import map_velocity,main


def test_demo_renders_to_image(tmp_path):
    scene=DemoScene()
    frame,hands=scene.frame((540,960),1000,'chord')
    assert len(hands)==2
    geom=Fretboard().update(hands,frame.shape[:2])
    out=Overlay().draw(frame,hands,geom,'C',StrumState.IDLE,True,demo=True)
    assert out.shape==(CANVAS_H,CANVAS_W,3) and out.sum()>0
    assert cv2.imencode('.png',out)[0]


def test_smoke_test_without_camera():
    assert main(['--smoke-test'])==0
    assert (config.PROJECT_DIR/'artifacts'/'smoke_test.png').stat().st_size>1000


def test_velocity_clamped():
    assert .30<=map_velocity(0)<=1
    assert .30<=map_velocity(2)<=1


def test_wav_bank_is_complete():
    for note in range(40,85):
        path=config.ASSET_DIR/f'pluck_{note}.wav'
        assert path.is_file(), f'Missing sound: {path.name}'
        with wave.open(str(path)) as fp:
            assert fp.getnchannels()==1 and fp.getframerate()==22050 and fp.getnframes()>10000


def test_chord_notes_bank_range():
    for notes in config.CHORD_NOTES.values():
        assert 3<=len(notes)<=6
        assert all(40<=n<=84 for n in notes)
