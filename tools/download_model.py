"""Download official Google Hand Landmarker task bundle on a connected machine."""
from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src import config
from src.hand_tracker import ensure_model

def main():
    print('Source:',config.MODEL_URL)
    dest=ensure_model(config.MODEL_PATH)
    print('Saved:',dest,'size:',dest.stat().st_size,'bytes')
    print('You may copy this file to another offline computer in the assets folder.')

if __name__=='__main__':main()
