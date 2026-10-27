"""Render public-domain guitar arrangements to preview WAV files without sound hardware."""
from __future__ import annotations
import sys
import wave
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.song_player import SONGS
from src import config


def render(song, output: Path) -> None:
    rate=22050
    n=int((song.duration_seconds + 1.4)*rate)
    mix=np.zeros(n,dtype=np.float64)
    sample_cache={}
    for e in song.events:
        if e.note not in sample_cache:
            with wave.open(str(config.ASSET_DIR/f'pluck_{e.note}.wav'),'rb') as f:
                if f.getframerate()!=rate or f.getnchannels()!=1 or f.getsampwidth()!=2:
                    raise ValueError('Unexpected instrument sample format')
                sample_cache[e.note]=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float64)/32768
        sound=sample_cache[e.note]
        start=int(round(e.beat*60/song.bpm*rate))
        count=min(len(sound),n-start)
        if count>0:
            mix[start:start+count]+=sound[:count]*e.velocity
    peak=max(float(np.max(np.abs(mix))),1e-8)
    mix=np.clip(mix*min(1.0,.91/peak),-1.,1.)
    output.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(output),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate)
        f.writeframes((mix*32767).astype('<i2').tobytes())
    print(f'{song.title}: {song.duration_seconds:.1f}s => {output}')

if __name__=='__main__':
    for s in SONGS:
        render(s,config.ASSET_DIR/f'demo_song_{s.key}.wav')
