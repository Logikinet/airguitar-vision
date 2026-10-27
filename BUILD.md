# Windows exe

The `build-windows` GitHub Actions workflow runs on pushes, pull requests and
manual dispatch. It uses x64 Python 3.11, installs the pinned runtime/build
dependencies, runs pytest, downloads the official hand model, and builds
`AirGuitarVision.spec`. It tests `AirGuitarVision.exe --selftest` from outside
the source folder before uploading `airguitar-vision-windows`.
The English runner image has no Microsoft YaHei, SimHei, or SimSun. Before
pytest the job saves Source Han Sans CN (OFL) as
`%LOCALAPPDATA%\Microsoft\Windows\Fonts\simhei.ttf` when none of the system
fonts are present. `Overlay` checks that per-user path after the system fonts.

Download that artifact from the workflow run's **Artifacts** section and extract
`AirGuitarVision.exe`. Python is not needed on the destination PC. This is a
console-enabled **onefile** build: WAVs, MediaPipe data/native libraries and the
Tasks model extract into a temporary directory at startup. First launch can be
slow. No runtime model download is needed. Windows CI validates the actual exe;
Linux source tests cannot certify the Windows bundle.

For a local Windows build with Python 3.11:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-build.txt
python -m pytest -q
python tools/download_model.py
python -m PyInstaller --noconfirm --clean AirGuitarVision.spec
.\dist\AirGuitarVision.exe --selftest
```

The self-test loads all WAVs, Chinese UI fonts and the hand model, performs a
blank-frame detection and exits without opening a camera or playing sound.
The normal launch and existing CLI options are unchanged. Chinese system fonts
(Microsoft YaHei/SimHei) must be installed, as for the source app.

The executable is unsigned. For a build you trust, Windows SmartScreen may
require **More info → Run anyway**. Enable **Settings → Privacy & security →
Camera → Let desktop apps access your camera** for normal camera use.
