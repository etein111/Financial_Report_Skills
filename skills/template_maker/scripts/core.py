"""Template Maker 核心编排器。"""

from pathlib import Path
import yaml
from .parser import WordStructureAnalyzer
from .schema_gen import SchemaGenerator
from .template_builder import TemplateBuilder
from .router_mgr import RouterManager
from .validator import TemplateValidator
from .utils import get_templates_dir

class TemplateMaker:
    """模板制作编排器。"""

    def __init__(self, project_root: Path):
        """初始化。

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root
        self.templates_dir = get_templates_dir()
        self.router_path = self.templates_dir / "router.yaml"

        self.parser = WordStructureAnalyzer()
        self.schema_gen = SchemaGenerator()
        self.builder = TemplateBuilder()
        self.validator = TemplateValidator()

    def create_template(
        self,
        name: str,
        word_path: Path,
        elements_path: Path | None = None,
    ) -> dict:
        """创建模板。

        Args:
            name: 模板名称
            word_path: Word 样本路径
            elements_path: elements.yaml 路径（可选）

        Returns:
            结果字典
        """
        # 1. 检测 elements.yaml
        if elements_path is None:
            from .utils import find_elements_yaml
            elements_path = find_elements_yaml(word_path)

        if not elements_path or not elements_path.exists():
            return {
                "status": "error",
                "message": "找不到 elements.yaml"
            }

        # 2. 创建模板目录
        template_dir = self.templates_dir / name
        template_dir.mkdir(parents=True, exist_ok=True)

        # 3. 分析 Word 文档
        word_structure = self.parser.analyze(word_path)

        # 4. 生成 schema
        elements = yaml.safe_load(elements_path.read_text())
        schema = self.schema_gen.generate(elements, template_name=name)

        # 保存 schema.yaml
        schema_path = template_dir / "schema.yaml"
        schema_path.write_text(yaml.dump(schema, allow_unicode=True, sort_keys=False))

        # 5. 生成 template.docx
        # 简化版本：暂时复制
        from shutil import copy
        template_path = template_dir / "template.docx"
        copy(word_path, template_path)

        # 6. 生成 meta.yaml
        meta = {
            "name": name,
            "display_name": f"{name} 模板",
            "version": "1.0.0",
            "status": "active",
            "sample_source": str(word_path),
        }
        meta_path = template_dir / "meta.yaml"
        meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))

        # 7. 更新 router.yaml
        router_mgr = RouterManager(self.router_path)
        router_mgr.add_mapping("company", name)

        return {
            "status": "success",
            "template_dir": str(template_dir),
            "fields_count": len(schema.get("fields", {})),
        }
