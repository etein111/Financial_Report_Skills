"""Schema 生成器（提示词包装）。"""

from typing import Dict, Any

class SchemaGenerator:
    """从 elements.yaml 生成 schema.yaml。"""

    def generate(self, elements: Dict[str, Any], template_name: str = "") -> Dict[str, Any]:
        """生成 schema。

        Args:
            elements: elements.yaml 的内容
            template_name: 模板名称

        Returns:
            schema 字典
        """
        # 生成字段定义
        fields = {}
        for name, value in elements.items():
            if name not in ["analysts"]:  # 跳过复杂嵌套字段
                fields[name] = self._infer_field(name, value)

        # 构建完整 schema
        schema = {
            "name": template_name,
            "display_name": f"{template_name} 模板",
            "version": "1.0.0",
            "fields": fields,
            # 抽取规则（供 report-maker 使用）
            "extraction_rules": self._get_extraction_rules(),
        }

        return schema

    def _infer_field(self, name: str, value: Any) -> Dict[str, Any]:
        """推断字段定义。

        Args:
            name: 字段名
            value: 字段值

        Returns:
            字段定义字典
        """
        # 简化版本：基于字段名和值推断
        # 后续会用提示词增强
        field_def = {
            "description": self._get_description(name),
        }

        # 添加 format（如果有值）
        if value and value != "null":
            field_def["format"] = str(value)

        return field_def

    def _get_description(self, name: str) -> str:
        """获取字段描述。"""
        descriptions = {
            "report_date": "报告日期",
            "company": "公司名称",
            "ticker": "股票代码",
            "title": "报告标题",
            "rating": "评级",
            "target_price": "目标价",
            "current_price": "现价",
            "market_cap": "市值",
        }
        return descriptions.get(name, name)

    def _get_extraction_rules(self) -> Dict[str, Any]:
        """获取默认抽取规则。

        Returns:
            抽取规则字典
        """
        return {
            "abstract": {
                "description": "报告摘要部分",
                "scope": "从报告开头到第一个一级标题之前",
                "hints": [
                    "通常包含投资亮点、核心观点",
                    "长度约 200-500 字",
                    "不应包含表格和图表",
                ],
            },
            "body": {
                "description": "报告正文部分",
                "scope": "从第一个一级标题之后到报告结尾",
                "hints": [
                    "包含各章节详细内容",
                    "可能包含表格、图表引用",
                    "按原文结构保留段落和标题层级",
                ],
            },
        }
