"""Schema 生成器（提示词包装）。"""

from typing import Dict, Any

class SchemaGenerator:
    """从 elements.yaml 生成 schema.yaml。"""

    def generate(self, elements: Dict[str, Any]) -> Dict[str, Any]:
        """生成 schema。

        Args:
            elements: elements.yaml 的内容

        Returns:
            schema 字典
        """
        fields = {}

        for name, value in elements.items():
            fields[name] = self._infer_field(name, value)

        return {"fields": fields}

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
