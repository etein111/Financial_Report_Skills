"""工具函数。"""

from pathlib import Path

def get_project_root() -> Path:
    """获取项目根目录。"""
    return Path(__file__).parent.parent.parent

def get_templates_dir() -> Path:
    """获取 templates 目录。"""
    return get_project_root() / "templates"

def get_samples_dir() -> Path:
    """获取 samples 目录。"""
    return get_project_root() / "samples"

def find_elements_yaml(word_path: Path) -> Path | None:
    """查找与 Word 文件配对的 elements.yaml。

    规则：
    1. <word_name> elements.yaml
    2. 同目录下的 elements.yaml
    """
    word_dir = word_path.parent
    word_name = word_path.stem  # 不含扩展名

    # 规则 1: <name> elements.yaml
    candidates = [
        word_dir / f"{word_name} elements.yaml",
        word_dir / f"{word_name}_elements.yaml",
    ]

    # 规则 2: 目录下的 elements.yaml
    candidates.append(word_dir / "elements.yaml")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None
