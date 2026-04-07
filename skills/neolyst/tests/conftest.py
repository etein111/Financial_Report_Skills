"""Pytest 配置文件 - neolyst skill 测试。"""
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径，支持 `from skills.neolyst.scripts import ...`
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
