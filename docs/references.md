# 官方资料与开源参考（2026-10）

1. Google AI Edge, Hand landmarks detection guide (Python): https://developers.google.com/mediapipe/solutions/vision/hand_landmarker/python ，官方 Tasks 初始化及 `detect_for_video` 说明。文档镜像：https://developers.google.cn/edge/mediapipe/solutions/vision/hand_landmarker/python
2. MediaPipe HandLandmarker Python API: https://developers.google.com/edge/api/mediapipe/python/mp/tasks/vision/HandLandmarker ，逐帧时间戳、检测模式与对象释放。
3. GitHub: Agneya Pathare, **agneya-1402/AirGuitar**: https://github.com/agneya-1402/AirGuitar 。开源项目采用 OpenCV + MediaPipe + Pygame、左手数字手势选和弦、右手扫弦的交互模式；借鉴其**架构/交互思路**。本项目未拷贝其源码或媒体文件，自己实现了指板、状态机、滤波、可视化和合成 WAV。
4. Original course design documents: `docs/original_architecture/` （用户提供的项目原始设计）。

**注意**：如需直接复制开源仓库的具体代码或音频素材，必须逐项遵守其 LICENSE 和媒体授权。当前交付项目未嵌入这些第三方代码或声音。
