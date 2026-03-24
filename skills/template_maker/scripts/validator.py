"""模板验证器。"""

from pathlib import Path
from docxtpl import DocxTemplate
import yaml

class TemplateValidator:
    """验证模板可用性。"""

    def validate(self, template_path: Path, elements_path: Path) -> tuple[bool, str]:
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
