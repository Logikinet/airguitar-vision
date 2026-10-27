"""pytest 根配置：确保 `src` 包可被导入（repo 根加入 sys.path）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
