# 一页摘要：基于手部关键点的空气吉他交互系统

| 项 | 内容 |
|---|---|
| 题目 | 基于手部关键点的空气吉他交互系统 |
| 英文 | Air Guitar Interaction System Based on Hand Landmark Detection |
| 方向 | 计算机视觉 + 人机交互（本科课设，非毕设） |
| 工期 | 建议 10 天核心路径（可扩到 2–3 周） |

## 效果（Demo 长什么样）

摄像头画面上叠加虚拟 **6 弦 × N 品位**琴颈与双手骨架。  
**左手**指尖落入网格 → 识别当前品位或匹配和弦（Am / C / D / Em / G / F）。  
**右手**快速扫过琴颈线 → 触发一次发声；HUD 显示和弦名与扫弦状态。  
可开关调试层；可切换「和弦模式 / 单音模式」。

## 技术要点

- **视觉**：Python 3.10+ · OpenCV · MediaPipe Hands（现成模型，不重训）  
- **交互**：固定 ROI（或腕连线）虚拟琴颈；左手模板匹配；右手扫弦状态机（IDLE→APPROACH→TRIGGER→COOLDOWN）  
- **音频**：pygame 预录 wav / MIDI / FluidSynth 任选  
- **结构**：单进程实时循环；模块分文件；不上 Web/Electron  

## 模块列表

| 模块 | 一句话 |
|---|---|
| `camera` | 采集与分辨率 |
| `hand_tracker` | MediaPipe 双手 21 点 |
| `fretboard` | 6×N 网格与点→(弦,品) |
| `chord_mapper` | 指型→六和弦 + 帧滤波 |
| `strum_detector` | 穿线+速度+冷却状态机 |
| `audio_engine` | note/chord 发声 |
| `overlay` | 网格 / 骨架 / HUD |
| `config` | 阈值与快捷键 |
| `main` | 主循环组装 |

## 明确不做

真吉他品格识别 · 自训手部模型 · 账号云端 · 第一期手机/鸿蒙 App。

## 2 分钟演示脚本

1. 开程序：骨架 + 虚拟琴颈（10s）  
2. 左手 Am，口播和弦名（10s）  
3. 右慢扫 / 快扫看力度（20s）  
4. 切单音模式扫两下（15s）  
5. 关调试层弹 Am–C–G–Em（40s）  
6. 收束：关键点 → 网格 → 状态机（15s）

## 文档包

- `COURSE_PLAN.md` — 任务书  
- `ARCHITECTURE.md` — 完整架构契约  
- `HANDOFF_FOR_CLAUDE.md` — 可粘贴给 AI 生成设计+骨架  
- `ONE_PAGER.md` — 本页  

**本包只提供思路与架构，不包含产品实现。**
