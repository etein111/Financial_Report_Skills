"""模板验证函数。"""

from pathlib import Path
from docxtpl import DocxTemplate
import yaml
from typing import Tuple


def validate_template(template_path: Path, elements_path: Path) -> Tuple[bool, str]:
    """用 elements.yaml 验证模板。

    Args:
        template_path: template.docx 路径
        elements_path: elements.yaml 路径

    Returns:
        (是否通过, 消息)
    """
    try:
        # 加载 elements
        elements = yaml.safe_load(elements_path.read_text())

        # 加载模板
        template = DocxTemplate(template_path)

        # 渲染测试（不保存）
        # 简化版本：只检查能加载
        template.render(elements)

        return True, "验证通过"

    except Exception as e:
        return False, f"验证失败：{str(e)}"
