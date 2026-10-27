"""Build-time script: generate independent original plucked-string synthesized WAVs."""
from pathlib import Path
import wave
import numpy as np

folder=Path('assets');folder.mkdir(exist_ok=True)
sr=22050
for midi in range(40,85):
    f=440.0 * 2**((midi-69)/12)
    size=max(2,round(sr/f))
    rng=np.random.default_rng(2026+midi)
    ring=rng.uniform(-1,1,size).astype(np.float64)
    result=np.empty(int(sr*1.16))
    # Karplus-Strong plucked-string synthesis: physical-model inspired.
    # slight phase-dependent damping and short attack keep notes distinct.
    pointer=0
    decay=.991 if midi<58 else .987
    for i in range(len(result)):
        nxt=(pointer+1)%size
        current=ring[pointer]
        ring[pointer] = decay * (.499*current+.501*ring[nxt])
        result[i]=current
        pointer=nxt
    times=np.arange(len(result))/sr
    env=np.exp(-times*(1.9+max(0,midi-60)*.025))
    env*=np.minimum(1.,times/.003+.06)
    result*=env
    peak=np.max(np.abs(result))
    out=(result/max(.001,peak)*25000).astype(np.int16)
    with wave.open(str(folder/f'pluck_{midi}.wav'),'wb') as wf:
        wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(sr)
        wf.writeframes(out.tobytes())
print('Generated 45 original 22050-Hz mono plucked-string WAV files')
