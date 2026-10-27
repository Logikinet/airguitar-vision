#!/bin/sh
# Encode artifacts/demo_frames/%05d.png to docs/demo.mp4.
# H.264, yuv420p, 10 fps, 1280x720, CRF 23, faststart. No audio.
set -eu
cd "$(dirname "$0")/.."
mkdir -p docs
ffmpeg -y \
  -hide_banner \
  -loglevel error \
  -framerate 10 \
  -start_number 1 \
  -i artifacts/demo_frames/%05d.png \
  -an \
  -c:v libx264 \
  -pix_fmt yuv420p \
  -preset medium \
  -crf 23 \
  -r 10 \
  -vf "scale=1280:720:flags=lanczos,format=yuv420p" \
  -movflags +faststart \
  docs/demo.mp4
