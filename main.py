"""Air Guitar main program. See README.md for first-use and keyboard controls."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import time
from typing import Optional

import cv2
import os
import numpy as np
from src import config
from src.audio_engine import AudioEngine
from src.camera import Camera
from src.chord_mapper import ChordMapper
from src.demo import DemoScene
from src.fretboard import Fretboard
from src.hand_tracker import HandResult, HandTracker, ensure_model
from src.overlay import Overlay, CANVAS_W, CANVAS_H
from src.song_player import SongPlayer
from src.strum_detector import StrumDetector


def monotonic_ms() -> int:
    return time.monotonic_ns()//1_000_000


def pick_hand(hands: list[HandResult], handedness: str) -> Optional[HandResult]:
    return next((hand for hand in hands if hand.handedness == handedness), None)


def select_hand_roles(hands: list[HandResult], role_swap: bool = False) -> tuple[Optional[HandResult], Optional[HandResult]]:
    """Return (chord/single-note hand, strum hand) from detector labels.

    Some mirrored webcam pipelines report the handedness labels in reverse.
    ``role_swap`` normalizes that mapping without changing the actual landmarks.
    """
    chord_label = 'Right' if role_swap else 'Left'
    strum_label = 'Left' if role_swap else 'Right'
    return pick_hand(hands, chord_label), pick_hand(hands, strum_label)


def _index_fingertip(hand: Optional[HandResult]) -> Optional[tuple[float,float]]:
    return None if hand is None or len(hand.landmarks)<9 else tuple(hand.landmarks[8][:2])


def map_velocity(velocity: float) -> float:
    return min(1., max(.30, .3 + .8 * min(1.,max(0.,velocity-.12)/1.1)))


def fit_desktop_window() -> tuple[int, int]:
    """Keep the entire Chinese control panel visible on smaller Windows laptops."""
    if os.name == 'nt':
        try:
            import ctypes
            screen_w=ctypes.windll.user32.GetSystemMetrics(0)
            screen_h=ctypes.windll.user32.GetSystemMetrics(1)
            ratio=min(1.0,(screen_w-50)/CANVAS_W,(screen_h-105)/CANVAS_H)
            if ratio>0.2:
                return int(CANVAS_W*ratio),int(CANVAS_H*ratio)
        except Exception:
            pass
    return CANVAS_W,CANVAS_H


def parser() -> argparse.ArgumentParser:
    ap=argparse.ArgumentParser(description='MediaPipe + OpenCV Air Guitar')
    ap.add_argument('--demo', action='store_true',help='synthetic hands, no camera/MediaPipe needed')
    ap.add_argument('--camera',type=int,default=0,help='OpenCV camera index, default 0')
    ap.add_argument('--video',type=str,default=None, help='video file input (real MediaPipe detection)')
    ap.add_argument('--mute',action='store_true',help='disable pygame audio')
    ap.add_argument('--width',type=int,default=config.FRAME_WIDTH)
    ap.add_argument('--height',type=int,default=config.FRAME_HEIGHT)
    ap.add_argument('--smoke-test',action='store_true',help='render 1 demo frame and write artifacts/smoke_test.png, no UI')
    ap.add_argument('--selftest', action='store_true', help='verify bundled assets and tracking without camera/audio output')
    return ap


def selftest() -> None:
    """Exercise native dependencies and bundled resources without devices/network."""
    import mediapipe  # noqa: F401 -- verify the critical native module imports
    import pygame
    import wave

    # Validate every expected WAV, including the two prepared song previews.
    names = [f'pluck_{note}.wav' for note in range(40, 85)]
    names += ['demo_song_twinkle.wav', 'demo_song_ode.wav']
    for name in names:
        with wave.open(str(config.ASSET_DIR / name), 'rb') as sound:
            if sound.getnframes() == 0 or not sound.readframes(sound.getnframes()):
                raise RuntimeError(f'Empty bundled WAV: {name}')
    # Decode with the real audio backend, using SDL's dummy output device.
    previous_driver = os.environ.get('SDL_AUDIODRIVER')
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=1)
        for name in names:
            pygame.mixer.Sound(str(config.ASSET_DIR / name))
    finally:
        pygame.mixer.quit()
        if previous_driver is None:
            os.environ.pop('SDL_AUDIODRIVER', None)
        else:
            os.environ['SDL_AUDIODRIVER'] = previous_driver
    ensure_model(download=False)  # Missing bundle must fail, never download/fallback.
    tracker = HandTracker()
    try:
        if tracker._backend != 'tasks':
            raise RuntimeError('Bundled Tasks model failed to initialize')
        tracker.process(np.zeros((256, 256, 3), dtype=np.uint8), now_ms=0)
    finally:
        tracker.close()
    Overlay()  # Load Pillow and the same system Chinese fonts used by the UI.
    print('[OK] AirGuitarVision selftest: imports, WAVs, fonts, hand model')


def run(args: argparse.Namespace) -> None:
    if args.width<600 or args.height<400:
        raise ValueError('Use at least 600x400 resolution for HUD and tracking regions.')
    demo=args.demo or args.smoke_test
    camera: Camera|None=None
    tracker: HandTracker|None=None
    audio: AudioEngine|None=None
    if not demo:
        camera=Camera(args.camera,args.width,args.height,config.TARGET_FPS,
                      source=args.video if args.video else args.camera)
        try:
            tracker=HandTracker(config.MP_MAX_HANDS,config.MP_MODEL_COMPLEXITY)
        except Exception:
            camera.release()
            raise
    scene=DemoScene() if demo else None
    board=Fretboard()
    mapper=ChordMapper()
    strummer=StrumDetector(config.V_TH,config.COOLDOWN_MS,config.APPROACH_MARGIN)
    overlay=Overlay()
    song_player=SongPlayer()
    window_name="空气吉他 - 中文视觉演奏台"
    pending_actions: list[str] = []
    fullscreen=False
    if not args.smoke_test:
        cv2.namedWindow(window_name,cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name,*fit_desktop_window())
        def on_mouse(event:int,x:int,y:int,flags:int,param:object)->None:
            if event==cv2.EVENT_LBUTTONUP:
                action=overlay.hit_test(x,y)
                if action:pending_actions.append(action)
        cv2.setMouseCallback(window_name,on_mouse)
    # If --mute passed, never import pygame: makes offline smoke-tests reliable.
    audio=AudioEngine(muted=args.mute or args.smoke_test)
    # Use the corrected handedness mapping by default for the live webcam.
    # Synthetic demo hands already have canonical labels and must not be swapped.
    mode='chord'; debug=config.DEBUG_OVERLAY; swap=(config.DEFAULT_HAND_ROLE_SWAP and not demo and not bool(args.video))
    muted=audio.muted
    prev_tip=None;prev_ms=None; fps=0.;stable_chord=None;stable_cell=None
    event_label='';event_until=0; stale_tip_count=0
    override=None
    def reset_tracking():
        nonlocal prev_tip,prev_ms,stable_cell,stable_chord
        prev_tip=prev_ms=None
        stable_cell=stable_chord=None
        mapper.reset();strummer.reset()
    try:
        while True:
            start=monotonic_ms()
            if demo:
                frame,hands=scene.frame((args.height,args.width),start,mode)
                if scene.manual_chord is not None:
                    override=config.GESTURE_TO_CHORD[scene.manual_chord]
            else:
                ok,frame=camera.read()
                if not ok or frame is None:
                    print('[camera] End of input stream')
                    break
                hands=tracker.process(frame,start)
            h,w=frame.shape[:2]
            # Map the physical left hand to chord/single-note control and the
            # physical right hand to strumming. H toggles the handedness correction.
            left, right = select_hand_roles(hands, swap)
            geom=board.update(hands,(h,w))
            neck=board.neck_line(geom)
            # GESTURE (0..5 raised digits) for chords; INDEX finger for single notes.
            raw=None;confidence=0.;gesture_index=None
            if left is not None:
                raw,confidence,gesture_index=mapper.gesture(left)
            if mode=='chord':
                stable_chord=mapper.update_filtered(override if override else raw)
                active_notes=config.CHORD_NOTES.get(stable_chord,[]) if stable_chord else []
                stable_cell=None
            else:
                cell=board.point_to_cell(_index_fingertip(left),geom) if left else None
                stable_cell=mapper.update_cell(cell)
                active_notes=mapper.cells_to_notes([stable_cell]) if stable_cell else []
                stable_chord=None
            # A right-hand fingertip crossing the horizontal middle of the
            # dedicated strum ROI emits a velocity/dir event with cooldown.
            tip=_index_fingertip(right)
            dt=start-prev_ms if prev_ms is not None else 0
            vel=None
            if tip is not None and prev_tip is not None and 1<=dt<=config.MAX_FRAME_GAP_MS:
                if np.hypot(tip[0]-prev_tip[0],tip[1]-prev_tip[1]) < config.MAX_TIP_JUMP_PX*(h/540):
                    vel=((tip[0]-prev_tip[0])/dt,(tip[1]-prev_tip[1])/dt)
            event=strummer.update(tip,vel,neck,start)
            prev_tip=tip;prev_ms=start
            if event:
                event_label=f'{event.direction.upper()}  {event.velocity:.2f}px/ms'
                event_until=start+380
                # Playing a prepared track owns the output, but detection/video
                # continues uninterrupted while its notes are scheduled.
                if active_notes and song_player.state != 'playing':
                    if mode=='chord': audio.chord_on(active_notes,map_velocity(event.velocity),direction=event.direction)
                    else: audio.note_on(active_notes[0],map_velocity(event.velocity))
            song_player.update(start,audio)
            audio.update()
            # UI label Left/Right stays the detector's original labeling.
            frame=overlay.draw(frame,hands,geom,stable_chord,strummer.state,debug,
                               mode=mode,active_cell=stable_cell,fps=fps,confidence=confidence,
                               last_event=event_label if start<event_until else '',
                               demo=demo,current_gesture=gesture_index,role_swap=swap,sound_muted=muted,
                               song_player=song_player)
            if args.smoke_test:
                dest=config.PROJECT_DIR/'artifacts'/'smoke_test.png';dest.parent.mkdir(exist_ok=True)
                if not cv2.imwrite(str(dest),frame):raise RuntimeError('Unable to write smoke_test.png')
                print(f'[OK] Demo smoke test saved to: {dest}')
                break
            try:
                cv2.imshow(window_name,frame)
                key=cv2.waitKey(1)&0xFF
            except cv2.error as exc:
                raise RuntimeError('图形窗口打开失败，请在 Windows 桌面或 VS Code 中运行。') from exc
            if key in (ord('q'),27):break
            # Handle clicks as real UI commands. Keyboard aliases are retained.
            if key==ord('m'):pending_actions.append('mode')
            elif key==ord('h') and not demo:pending_actions.append('swap')
            elif key==ord('s'):pending_actions.append('mute')
            elif key==ord('f'):pending_actions.append('fullscreen')
            elif key==ord('p'):pending_actions.append('play_pause')
            elif key==ord('t'):pending_actions.append('stop')
            elif key==ord('n'):pending_actions.append('ode' if song_player.selected==0 else 'twinkle')
            elif key==ord('d'):debug=not debug
            elif key==ord(' ') and active_notes and song_player.state!='playing':
                if mode=='chord': audio.chord_on(active_notes,.85)
                else: audio.note_on(active_notes[0],.85)
                event_label='手动扫弦';event_until=start+400
            elif key==ord('0'):
                override=None
                if demo:scene.manual_chord=None
                reset_tracking()
            elif ord('1')<=key<=ord('6'):
                n=key-ord('1')
                override=config.GESTURE_TO_CHORD[n]
                if demo:scene.manual_chord=n
                reset_tracking()
            elif demo and key==ord('a'):
                scene.auto=not scene.auto
                if scene.auto:
                    scene.manual_chord=None;override=None
                else:
                    scene.manual_chord=0;override=None
                reset_tracking()
            elif demo and mode=='single':
                s,f=scene.cell
                if key==ord('j'):f=max(0,f-1)
                elif key==ord('l'):f=min(config.N_FRETS,f+1)
                elif key==ord('i'):s=max(0,s-1)
                elif key==ord('k'):s=min(config.N_STRINGS-1,s+1)
                scene.cell=(s,f)
            for action in pending_actions:
                if action=='mode':
                    mode='single' if mode=='chord' else 'chord'
                    reset_tracking()
                elif action=='swap' and not demo:
                    swap=not swap; reset_tracking()
                elif action=='mute':
                    if audio._mixer is None and not args.mute:
                        print('[音频] 无可用声音设备，请先运行 setup_windows.bat 并检查扬声器。')
                        muted=True
                    else:
                        muted=not muted
                        audio.muted=muted
                        if muted:audio.all_notes_off()
                elif action=='play_pause':
                    was_playing=song_player.state=='playing'
                    if song_player.state=='stopped':audio.all_notes_off()
                    song_player.play_pause(start)
                    if was_playing:audio.all_notes_off()
                elif action=='stop':
                    song_player.stop();audio.all_notes_off()
                elif action=='twinkle' or action=='ode':
                    song_player.select(0 if action=='twinkle' else 1)
                    audio.all_notes_off()
                elif action=='fullscreen':
                    fullscreen=not fullscreen
                    cv2.setWindowProperty(window_name,cv2.WND_PROP_FULLSCREEN,
                        cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL)
                    if not fullscreen:cv2.resizeWindow(window_name,*fit_desktop_window())
            pending_actions.clear()
            elapsed=max(1,monotonic_ms()-start)
            instantaneous=1000.0/elapsed
            fps=instantaneous if fps==0 else fps*.87+instantaneous*.13
            if demo:
                # Do not exhaust CPU in a generated live-preview scene.
                remaining=1000/config.TARGET_FPS-(monotonic_ms()-start)
                if remaining>0:time.sleep(remaining/1000)
    finally:
        if audio:audio.close()
        if tracker:tracker.close()
        if camera:camera.release()
        cv2.destroyAllWindows()


def main(argv: list[str]|None=None) -> int:
    args=parser().parse_args(argv)
    try:
        if args.selftest:
            selftest()
        else:
            run(args)
        return 0
    except (RuntimeError,ValueError,ImportError,OSError) as exc:
        print(f'\n[ERROR] {exc}\nTry: python main.py --demo (no camera/model required).\nSee README.md for setup.',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
