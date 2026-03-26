"""Pytest 配置文件。"""
import sys
from pathlib import Path

# 添加 scripts 目录到 Python 路径
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# 设置包路径以便支持相对导入
package_dir = Path(__file__).parent.parent
if str(package_dir) not in sys.path:
    sys.path.insert(0, str(package_dir))
