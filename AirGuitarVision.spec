"""Onefile build; native libraries/models extract together under sys._MEIPASS."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH)
model = root / 'assets' / 'hand_landmarker.task'
if not model.is_file() or model.stat().st_size < 100_000:
    raise RuntimeError('Run python tools/download_model.py before building')

# Include Tasks native libraries plus legacy Solutions graphs/models for fallback.
mp_data, mp_binaries, mp_imports = collect_all('mediapipe')
# The standard cv2 hook collects OpenCV DLLs, config and package data.
a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    binaries=mp_binaries,
    datas=[(str(root / 'assets'), 'assets')] + mp_data,
    hiddenimports=mp_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
# Try onefile first; CI must pass --selftest before publishing the executable.
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='AirGuitarVision',
    debug=False,
    strip=False,
    upx=False,
    console=True,  # Match start_windows.bat and retain useful diagnostic logs.
)
