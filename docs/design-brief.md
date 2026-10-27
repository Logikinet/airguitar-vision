# AirGuitar Vision — UI design brief

Showcase build. Canvas stays **1440×900**. Render with OpenCV + NumPy; Chinese text only through Pillow. The Windows screenshot fails three shipped-product tests: the native title is mojibake, icon slots are tofu (music note, play triangle, stop square, arrow), and the camera is a flat grey field with stroked debug boxes inside cramped cards.

North star: a dark performance stage. Chrome recedes; the camera is the hero; one accent carries “live”.

## Skills applied

Use the vendored docs only: `design-skills/ui-taste.md`, `design-skills/impeccable.md`, `design-skills/hallmark.md`. Do not `npx` those packages. The UI is an OpenCV canvas, so there is no DOM for Impeccable `detect`, Hallmark `sloplint`, or a ui-taste image-to-HTML pass. Apply the rules below by hand.

- **ui-taste.** This brief outranks the skill. Extend this system; do not start a second one. Image-first comps do not apply.
- **Impeccable.** The anti-pattern list is a ship gate (the 62-rule intent, checked on the PNG).
- **Hallmark.** Floor never ships. Reflex tells are banned. Finish nits do not block a frame.
- **huashu bans** in `design-kb.md` §1.4 sit in the same gate. huashu itself is not vendored here.

`design-kb.md` has no air-guitar, fretboard, or camera-HUD teardown, and no desktop music-tool competitor study. The References section stays binding. KB §7 taste sites (Dark Design, Design Spells, Mobbin, Minimal Gallery, Refero, Typewolf, Godly, and the rest of that list) are looking notes, not layout specs.

## Hard constraints

Floor:

- Text against its own fill is ≥4.5:1. `muted` on `surface` is the weak pair (~5.8:1). Ban gray or `muted` on `accent`, `success`, `warning`, or `danger` fills. Text on accent is `on-accent`.
- Reduced motion: no travel and no scale. State color may change in one frame.
- Draw only values the app already has. Do not invent fps, confidence, or duration.
- No mojibake, no tofu, no emoji.

Banned, with no exception granted in this file (Impeccable, Hallmark reflex, huashu):

- Inter, Arial, Roboto, or system-ui. The “Modern Dark Cinema” row pairs Inter/Inter; ignore that pair.
- Purple-to-blue fills, mesh or aurora gradients, neon bloom, plasma purple.
- Pure `#000000` or untinted gray as a surface.
- Nested cards, a card around one number, a left color-bar card, an icon tile over every heading.
- Bounce, elastic, or overshoot easing.
- An eyebrow over every title, tracked all-caps labels, one recolored word in a title.
- Middot chains (`A · B · C`), a trailing arrow on a button, `01` / `02` / `03` on items that are not a sequence.
- Emoji icons, drawn faces, empty placeholder frames.

Whitespace is composition. Leave it empty.

## References

**Spotify desktop** (Kombai / Open Design token captures). Canvas `#121212`, card `#181818`, raised `#282828`, text `#FFFFFF` / `#B3B3B3`. One voltage, `#1ED760`, almost only on play. 8px grid, 4px micro-steps. Cards lift by a lighter fill, not a drop shadow. Bottom now-playing bar holds transport, a thin progress track, and tabular time.

**Yousician** (song screen, play mode, Guitar World and support notes). The lesson surface is a hero notation stage with a bottom transport and loop range. Hits read green, misses red, then a score. Falling notes use blue for the left hand and a second hue for the right. Finger colors stay inside the lesson, never as chrome. Take the stage, the hit/miss pair, and the bottom bar. Keep this app on a dark commercial shell.

**Fender Play** (2022 lesson redesign; video-player help). The lesson page minimizes buttons so video and tab own the frame. Transport sits on a bottom gradient over the picture: play/pause, scrubber, chapter ticks. Completion is green. Path navigation uses one brand red. Our brand accent stays stage teal; red is reserved for danger.

**Rocksmith+** (noteway, Ubisoft color-preset and HUD notes). The dark noteway is the product. String lanes, a phrase banner, and miss marks are instrument HUD. Players can thin the HUD. Zone guides here should look like that lane language: soft bands, a play line, corner ticks. Full rectangles read as debug.

**Logic Pro** (control bar, Apple playback guide). A charcoal control bar, an LCD for position, a playhead, and an inspector rail. Yellow means a special state (solo), not decoration. Our bottom strip is that LCD.

## Colour

KB Cinema and `design-skills/colors-music-dark.tsv` / `styles-music-dark.tsv`, reconciled:

Stage fills are **tinted deep blue-grey**, the Cinema rule (avoid pure `#000`, surfaces stay apart by lightness). OLED Dark Mode (`#000000`, `#121212`, neon `#39FF14`, `#BF00FF`) and the Video Streaming background `#000000` are out: they smear, and the neons are chrome. Music Streaming and Theater (`#0F0F23`, primary `#1E1B4B`, secondary `#4338CA`, border `#312E81`) and the Cinema accent `#5E6AD2` are indigo UI. Ban them for window fills, borders, and gradients.

One chrome accent, stage teal, carries play, the playhead, and focus. Streaming play-green `#22C55E` and Spotify `#1ED760` inform `success` only (camera live, chord lock, cooldown), the same job as Yousician hit-green. Fret and strum are a second, high-contrast HUD pair so they read on a moving frame: blue corner ticks, amber play line. They are not a gradient and they are not chrome.

OpenCV tuples are **BGR** `uint8`. Pillow `ImageDraw` needs RGB: reverse the tuple. Do not pass hex strings into `cv2`.

| Token | Hex | BGR | Use |
|---|---|---|---|
| bg | `#0E1116` | `(22, 17, 14)` | Window fill. Blue-grey, not `#000` |
| surface | `#161C24` | `(36, 28, 22)` | Header, cards, bottom strip |
| elevated | `#1E2733` | `(51, 39, 30)` | Wells, secondary buttons, idle chips |
| border | `#314052` | `(82, 64, 49)` | 1px edge. Tinted, not 8% white (that hairline dies on a still) |
| text | `#F4F7FB` | `(251, 247, 244)` | Titles, values |
| text-2 | `#B7C3D0` | `(208, 195, 183)` | Body, subtitles |
| muted | `#8A97A6` | `(166, 151, 138)` | Captions, hints, ≥13px, on `bg` / `surface` only |
| accent | `#3EE0C2` | `(194, 224, 62)` | Primary button, playhead, focus |
| accent-soft | `#14342E` | `(46, 52, 20)` | Selected chip fill |
| on-accent | `#06211C` | `(28, 33, 6)` | Label on accent fill |
| success | `#3DDC97` | `(151, 220, 61)` | Camera live, chord lock, cooldown |
| warning | `#F0B429` | `(41, 180, 240)` | Strum hit, muted audio |
| danger | `#F07178` | `(120, 113, 240)` | No camera, confidence &lt; 0.35 |
| fret-tint | `#163A66` | `(102, 58, 22)` | Left zone, blend α 0.22 |
| fret-edge | `#8EB7E8` | `(232, 183, 142)` | Corner ticks only. High contrast on the frame |
| strum-tint | `#3A3420` | `(32, 52, 58)` | Right lane, blend α 0.22 |
| strum-line | `#E8C45A` | `(90, 196, 232)` | 2px play line. High contrast on the frame |
| hand-l | `#7EB6FF` | `(255, 182, 126)` | Left-hand skeleton |
| hand-r | `#7EE0B8` | `(184, 224, 126)` | Right-hand skeleton |
| track | `#2A3848` | `(72, 56, 42)` | Progress gutter |

Alpha blends: `cv2.addWeighted(tint, a, frame, 1-a, 0)`. The photo scrim is the only pure black: `(0,0,0)` at α 0.55, 72px tall, vertical gradient (row `i` uses `0.55 * (1 - i/72)`). It is a read veil, not a surface token.

## Type

One CJK face for every string, including digits. Load once with Pillow. Try, in order: `msyh.ttc`, `msyhbd.ttc`, `NotoSansCJK-Regular.ttc`, `SourceHanSansSC-Regular.otf`, `simhei.ttf`, then `%LOCALAPPDATA%\Microsoft\Windows\Fonts\` for the same names. Web pairs (Righteous, Poppins, Space Grotesk, Inter) do not ship this UI.

| Role | px | Weight | Sample |
|---|---|---|---|
| display | 28 | bold file if present, else regular | 空气吉他 |
| title | 20 | regular | 演奏控制 |
| body | 16 | regular | 双手交互 / 六和弦 |
| caption | 13 | regular | 按 M 切换和弦 / 单音 |
| value | 22 | regular | 和弦演奏 |
| mono | 15 | same face, tabular by drawing | 00:12 / 00:25 |

Body stays ≥16px and captions ≥13px (above the 14px / 12px floors). One scale only. Do not crop a glyph in a fixed box; shorten the copy.

`cv2.putText` is forbidden for any user-visible string. Never draw U+25B6, U+25A0, U+25CF, U+266A–U+266C, U+2192, U+2197, or emoji. Those are the tofu in the screenshot. Separators are ASCII ` / `. Ban `·` as a connector, even when the font has the glyph.

## Spacing

Base **8**, micro **4**. Window margin **24**. Card gap **16**. Card padding **20**. Header content inset **16**. Adjacent targets keep ≥8px between them.

| Radius | px | Where |
|---|---|---|
| card | 12 | Hero clip, rail cards, bottom strip. Cinema’s 16px is the web note; this canvas stays 12 so the 1440 frame stays dense. Fret zones stay 16 |
| control | 8 | Buttons, chord chips |
| pill | height/2 | Status and mode chips (h 28 → r 14) |
| progress | 3 | 6px track |
| tick | 0 | 2×14 focus brackets |

Primary and secondary buttons are 44px tall. Chord cells and song rows are 40px. Pills are 28px (desktop pointer, above the 24px minimum). No offset “shadow” rectangles. Elevation is `surface` on `bg`, plus a 1px `border`.

Draw order is the only z scale: frame, vignette, zone tint, skeletons, scrims, pills, chrome. No ad-hoc large z.

## Motion

Motion confirms a gesture. The loop is about 10 fps, so time is frames. Press darkens on the next frame (~100ms). A state crossfade is at most 2–3 frames (200–300ms). Ease-out only: Cinema `cubic-bezier(0.16, 1, 0.3, 1)`, no overshoot. Ban bounce and elastic. Strum feedback recolors the play line and the status cell, holds, then cooldown. Reduced motion snaps the color in one frame. No glow pulse.

## Layout (1440×900)

| Region | x, y, w, h |
|---|---|
| Header | 24, 16, 1392, 56 |
| Hero camera | 24, 88, 952, 644 |
| Bottom strip | 24, 748, 952, 128 |
| Rail | 992, 88, 424, 788 |

Hero width is 952/1440 = **66%**. Rail gap is 16. Bottom of the strip is y=876, leaving the 24px margin. Rail cards, gap 16:

1. 演奏控制 — 992, 88, 424, 156
2. 手势与和弦 — 992, 260, 424, 248
3. 示范曲 — 992, 524, 424, 352

Keep existing button ids; only the rectangles move.

## Components

**Header.** 36×36 brand mark at (40, 26), the one mark on the window. Display “空气吉他” at x=88, y=22. Subtitle “计算机视觉 / 实时交互演奏台” at y=50, `text-2`. That subtitle is the product line, not an eyebrow pattern. Right cluster, vertically centered: success pill (6px dot + “摄像头已连接” or warning “模拟演示”), mono “10 fps” in `text-2`, then pills “音频开” / “已静音” (warning fill when muted) and “全屏”. Pill h=28, pad-x=12, gap=8.

**Cards.** `surface` + 1px `border`, r=12, padding 20. Open with the title in `text` 20px. No label above the title. Hints sit under the control they describe, in `muted`. No nested box around a single value.

**Primary button.** h=44, r=8, fill `accent`, label `on-accent` 16px. Play triangle 11×13 drawn 8px left of the label, gap 8. Copy: “播放示范曲” / “暂停” / “继续”. Min width 168. No trailing arrow.

**Secondary button.** h=44, r=8, fill `elevated`, 1px `border`, label `text`. Stop is a 10×10 rounded rect icon plus “停止”. Song picks (“小星星”, “欢乐颂”) are secondary, h=40; the selected one uses `accent-soft` and a 1px `accent` edge.

**Chips.** Chord grid: 3 columns, gap 8, cell h=40, r=8, fill `elevated`. Index in `muted` caption, name in `text` 16px. Selected: fill `accent-soft`, 1px `accent`, index in `success`.

**Progress.** Track 6px, r=3, full inner width, fill `accent` to the playhead. A 10px `accent` disc sits on the playhead (Logic / Fender scrubber). Under it, state caption left (“待播放”, “正在弹奏”, “已暂停”) and mono “mm:ss / mm:ss” right. Playing state uses `success`.

**Status pills.** h=28, r=14. Live = `accent-soft` + `success` text. Hit = `warning` text on `#3A3018` BGR `(24, 48, 58)`. Danger = `#3A2228` BGR `(40, 34, 58)` + `danger` text. Never `muted` on these fills.

**Bottom strip.** One `surface` card, three equal columns, 1px `border` dividers inset 20px vertically. Each column: caption, then 22px value, then caption hint. Captions are the metric name, not a tracked label.

- 演奏模式 / 和弦演奏 or 单音演奏 / 按 M 切换
- 当前识别 / chord name or 等待手势 / 置信度 0.00 (value turns `danger` under 0.35, `success` when locked)
- 扫弦反馈 / 准备就绪, 检测到扫弦 (`warning`), or 冷却中 (`success`)

## Icons

Draw shapes with `cv2` (lineType `LINE_AA`) or Pillow `polygon` / `ellipse`. No icon font.

- **Brand mark** 36×36, r=8, fill `elevated`, 1px `accent`. Two vertical strings inset 10px and 18px, 2px `accent`, from y+8 to y+28. A 2px arc (ellipse, start 200°, end 340°) as the bridge. This replaces “♫”.
- **Play** filled triangle points `(0,0) (0,13) (11,6.5)` in `on-accent`.
- **Pause** two rects 3×13, gap 4.
- **Stop** round-rect 10×10, r=2.
- **Camera** for empty state: body r=4 rect 36×26, lens circle r=6, small dot r=2. Stroke 2px `text-2`.

## Camera hero

Clip the frame to the hero rect with a rounded mask, r=12, then a 1px `border`. Scale with cover (center-crop), not stretch.

**Vignette** after cover-fit, before UI:

```python
yy, xx = np.mgrid[0:h, 0:w]
nx = (xx - w/2) / (w/2); ny = (yy - h/2) / (h/2)
r = np.clip(np.sqrt(nx*nx + ny*ny), 0, 1.4)
vig = np.clip(1 - 0.42 * np.power(r, 1.7), 0.62, 1)
frame = (frame.astype(np.float32) * vig[..., None]).astype(np.uint8)
```

Top and bottom scrims sit under the zone pills and the hint line.

**Fret zone** (existing left ROI, chord mode keeps the face clear of the string grid): rounded tint, r=16, `fret-tint` α 0.22. Four open corner ticks, 14×2, `fret-edge`. No closed rectangle. Pill “左手 / 和弦” on the scrim.

**Strum zone:** horizontal band only. Top and bottom 1px at 40% `strum-line`. Center line 2px `strum-line`, inset 16px; `success` during cooldown. 6px end caps. Pill “右手 / 扫弦” on the top scrim, right side. The yellow box in the screenshot goes away.

Hint on the bottom scrim, caption, `text`: “镜像预览 / 左手选和弦 / 右手穿过扫弦线”.

**Empty state** (no device, before demo): fill `elevated`, same vignette math inverted so the center is lighter (`0.85 + 0.15*(1-r)`). Camera glyph centered, 24px above middle. Title “等待摄像头”. Caption “连接摄像头，或按 D 进入演示”. No laptop line-art on a flat grey plate.

Skeletons: `hand-l` / `hand-r`, thickness 2, fingertip r=4, other joints r=2 in `text`. Labels are pills (“左手”, “右手”), not floating debug text.

## Window title

`cv2.namedWindow("AirGuitar Vision", cv2.WINDOW_NORMAL)`.

On Windows, HighGUI sets the caption with the ANSI API, so a Chinese Python string becomes the mojibake in the screenshot. The title string is ASCII only. If a Unicode caption is ever required, set it after the window exists:

```python
hwnd = ctypes.windll.user32.FindWindowW(None, "AirGuitar Vision")
ctypes.windll.user32.SetWindowTextW(hwnd, "AirGuitar Vision")
```

`FindWindowW` matches the ASCII title already created. Do not pass Chinese into `namedWindow` or `setWindowTitle`.

## Acceptance (preview PNGs)

Shoot 1440×900 PNGs that include the OS title bar.

1. Title bar reads `AirGuitar Vision` exactly. No replacement characters, no GBK garbage.
2. Zero tofu: brand, play, pause, stop, camera, fullscreen, mute. Zoom to 200% and look for empty boxes.
3. Hero is 952px wide, clipped at r=12, with vignette. Empty state and a live (or demo) frame are both shot. Neither is flat `#808080` with a hard rectangle.
4. Fret and strum read as HUD: tint, ticks or lane, pills. Ticks and the play line stay high-contrast on the frame. No full yellow or blue debug stroke.
5. Rail cards show 20px padding and 16px gaps. Titles have no eyebrow. No caption collides with a button.
6. Bottom strip is one card, three columns. Values are 22px and readable.
7. Primary play button is accent fill with a drawn triangle and dark text. Progress shown at 0 and at about 40%, with the playhead disc.
8. Selected chord chip, success camera pill, and warning strum-hit state are each visible in some frame.
9. All Chinese strings use the CJK font. ASCII ` / ` separators. No emoji, no middot chains, no Inter.
10. Surfaces are the blue-grey tokens, not `#000` and not an indigo or purple gradient. No gray text on accent, success, warning, or danger.
11. A still is pitch-screenshot worthy: it can sit beside Fender Play or Spotify without looking like a course demo.
