# 交给 Claude（或同类助手）的完整提示词

> 用法：把下方「提示词正文」整段复制到新对话。  
> 目标：让对方生成 **架构设计文档 + 空源码骨架**（docstring + TODO），**不要**在本机替你写满业务逻辑、**不要**跑 MediaPipe Demo。  
> 配套阅读：同目录 `ARCHITECTURE.md`、`COURSE_PLAN.md`、`ONE_PAGER.md`。

---

## 提示词正文（从下一行复制到文末）

```text
你是课设架构师兼脚手架生成器。请为本科课设「基于手部关键点的空气吉他交互系统」产出可落地的设计文档与空代码骨架。只做架构与接口，不要实现算法细节，不要训练模型，不要引入 Web/Electron。

# 一句话产品

笔记本摄像头 + MediaPipe Hands → 虚拟 6 弦 × N 品位琴颈 → 左手指尖决定和弦/品位 → 右手扫弦触发发声 + HUD。可演示闭环即可。

# 硬约束

- Python 3.10+，单进程 OpenCV 窗口实时循环
- 视觉：opencv-python + mediapipe Hands（用现成 Hand Landmarker，禁止自训）
- 音频：pygame.mixer 预录 wav，或 mido，或 FluidSynth，三选一并在 README 写清
- 必须模块文件：
  src/camera.py
  src/hand_tracker.py
  src/fretboard.py
  src/chord_mapper.py
  src/strum_detector.py
  src/audio_engine.py
  src/overlay.py
  src/config.py
  以及根目录 main.py、requirements.txt、README.md
- 和弦第一期只做 6 个模板：Am, C, D, Em, G, F
- 扫弦必须用状态机：IDLE → APPROACH → TRIGGER → COOLDOWN，写清转移条件与 cooldown（建议 80–150ms）
- 琴颈默认 fixed_roi（实现快稳）；wrist_axis 可作为注释中的进阶选项
- N_FRETS 建议 4 或 5；N_STRINGS=6
- 不做：自定义手部模型训练、真吉他品格检测、账号云端、手机 App、第一期鸿蒙（可列为未来工作）
- 输出必须是「设计 + 骨架」，每个函数体用 `raise NotImplementedError` 或 `pass  # TODO:`，但签名、docstring、类型注解要完整

# 你必须先输出的文件

1) docs/design.md
   内容至少包括：
   - 目标与 Must/Should/Could
   - mermaid 模块图
   - 各模块职责表
   - 公共 API（与骨架一致）
   - 主循环伪代码
   - 扫弦状态机（状态图 + 转移表）
   - 和弦模板数据结构与 Am/C/D/Em/G/F 表（简化指型即可）
   - 数据流
   - config 旋钮列表与建议默认值
   - 风险与对策
   - D1–D10 里程碑：每天交付物、DoD、要改哪些文件
   - 明确 Out of Scope
   - 2 分钟演示脚本

2) 空骨架源码（可 import 的结构，逻辑 TODO）
   - main.py：组装对象 + while 循环框架 + 按键分支（q/Esc/d/m/s），循环内调用各模块但允许 NotImplemented
   - src/*.py：类与函数签名 + docstring + TODO
   - src/config.py：把阈值、ROI、模板字典、快捷键写成可改常量（模板可用占位坐标）
   - requirements.txt：opencv-python、mediapipe、numpy、pygame（或你选的音频库）
   - README.md：安装、运行、快捷键、环境光建议、非功能指标
   - tests/ 至少两个单测文件的空壳：
     tests/test_fretboard_geometry.py
     tests/test_strum_state_machine.py
     （用例名写好，断言 TODO）

# 接口契约（必须遵守，可微调命名但不可合并职责）

HandTracker.process(frame) -> list[HandResult]
Fretboard.update(hands, shape) -> FretboardGeom
Fretboard.point_to_cell(xy, geom) -> (string_id, fret_id) | None
Fretboard.neck_line(geom) -> (p1, p2)
ChordMapper.fingertips_to_shape(...) -> FingerShape
ChordMapper.match(shape) -> (chord_id|None, confidence)
ChordMapper.update_filtered(chord) -> chord_id|None
StrumDetector.update(tip_xy, tip_vel, neck_line, now_ms) -> StrumEvent|None
AudioEngine.note_on / chord_on / all_notes_off
Overlay.draw(frame, hands, geom, chord, strum_state, debug) -> frame

# 扫弦转移条件（写入 design.md，骨架里用枚举体现）

- IDLE → APPROACH：指尖进入琴颈线邻域且朝向线运动
- APPROACH → TRIGGER：有符号距离变号（穿越）且 |v| > V_TH → 产生 StrumEvent
- TRIGGER → COOLDOWN：立即进入
- COOLDOWN → IDLE：经过 cooldown_ms
- APPROACH → IDLE：离开邻域或超时

# 主循环数据流（写入 design.md）

Frame → Hands → Fretboard 几何
              → ChordMapper（左手）→ 稳定和弦 / MIDI notes
              → StrumDetector（右手）→ 可选 StrumEvent
              → 若有事件则 AudioEngine 发声
              → Overlay → imshow

# 里程碑（design.md 必须有表）

D1 摄像头+关键点 | D2 网格 | D3 (s,f) | D4 STRUM log | D5 空弦音
D6 六和弦 | D7 滤波+力度 | D8 HUD+快捷键 | D9 标定/评测 | D10 Demo+报告大纲

# 输出格式要求

- 先写 docs/design.md 全文
- 再按文件给出骨架代码（标明路径）
- 中文撰写 design.md 与 README；代码标识符英文
- 简洁具体，禁止空话与范围膨胀
- 不要生成 assets 二进制；在 README 说明需自备 6 个空弦 wav 或使用合成后端
- 不要写「已实现可运行的完整算法」；明确标注 TODO

验收标准（对你输出的检查清单）：
[ ] design.md 含 mermaid 模块图与状态机转移表
[ ] 每个必须模块文件存在且有类型注解签名
[ ] main.py 有完整循环骨架与按键
[ ] config 含 V_TH、COOLDOWN_MS、VOTE_WINDOW、六和弦模板占位
[ ] Out of Scope 写明
[ ] 无深度学习训练代码、无 Web UI
```

---

## 粘贴后建议你补充的一句（可选）

若接手方已读过 `ARCHITECTURE.md`，可在提示词末尾追加：

```text
请与下列架构契约对齐（若冲突以更具体、可测试的转移条件为准）：
（此处可粘贴 ARCHITECTURE.md 第 5–8 节摘要，或直接附件上传 ARCHITECTURE.md）
```

## 接手方交付后建议自检

1. `docs/design.md` 能否单独给老师当设计说明？  
2. `python -c "import main"` 或至少各 `src` 文件语法能通过（允许 NotImplemented）？  
3. 是否仍出现「真琴检测 / 训练模型 / Electron」等越界内容？有则删。  
4. 再按 D1→D10 自己填 TODO，**本 handoff 文档作者不负责实现与跑通。**
