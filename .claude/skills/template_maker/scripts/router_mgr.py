"""Router.yaml 管理器。"""

import yaml
from pathlib import Path

class RouterManager:
    """管理 router.yaml 文件。"""

    def __init__(self, router_path: Path):
        """初始化。

        Args:
            router_path: router.yaml 文件路径
        """
        self.path = router_path
        self.data = self._load()

    def _load(self) -> dict:
        """加载 router.yaml。"""
        if not self.path.exists():
            return {"mappings": {}}

        return yaml.safe_load(self.path.read_text()) or {"mappings": {}}

    def add_mapping(self, report_type: str, template_name: str):
        """添加报告类型映射。

        Args:
            report_type: 报告类型（如：company, macro）
            template_name: 模板名称
        """
        self.data.setdefault("mappings", {})[report_type] = template_name
        self._save()

    def _save(self):
        """保存到文件。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(yaml.dump(self.data, allow_unicode=True, sort_keys=False))
