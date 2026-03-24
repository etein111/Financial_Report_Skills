"""Pytest 配置文件。"""
import sys
from pathlib import Path

# 添加 scripts 目录到 Python 路径
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))
