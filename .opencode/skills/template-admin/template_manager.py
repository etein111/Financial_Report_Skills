"""模板管理器"""
import os
import shutil
from typing import Dict, Any, Optional, List
from parser import WordParser
from placeholder_detector import PlaceholderDetector
from validator import TemplateValidator


class TemplateManager:
    """模板的创建、更新、验证"""
    
    TEMPLATES_DIR = ".opencode/templates"
    
    def __init__(self):
        self.validator = TemplateValidator()
        self.detector = PlaceholderDetector()
    
    def create_template(self, word_file: str, elements_file: Optional[str],
                       report_type: str) -> Dict[str, Any]:
        """创建模板
        
        步骤:
        1. 解析 Word
        2. 生成占位符模板
        3. 闭环验证
        4. 保存
        """
        # 1. 解析 Word
        parser = WordParser(word_file)
        structure = parser.parse_structure()
        
        # 2. 加载要素
        elements = self._load_elements(elements_file) if elements_file else {}
        
        # 3. 检测/生成占位符
        placeholders = self._detect_placeholders(structure, elements)
        
        # 4. 创建模板目录
        template_dir = os.path.join(self.TEMPLATES_DIR, report_type)
        os.makedirs(template_dir, exist_ok=True)
        
        # 5. 复制并处理模板
        template_path = os.path.join(template_dir, "template.docx")
        shutil.copy2(word_file, template_path)
        
        # 6. 验证
        validation = self.validator.validate(
            word_file, template_path, elements
        )
        
        return {
            'success': validation['passed'],
            'template_path': template_path,
            'placeholders': placeholders,
            'validation': validation,
            'message': '模板创建成功' if validation['passed'] else '模板创建成功，但有差异需检查'
        }
    
    def update_template(self, new_word_file: str, report_type: str) -> Dict[str, Any]:
        """更新模板"""
        template_dir = os.path.join(self.TEMPLATES_DIR, report_type)
        template_path = os.path.join(template_dir, "template.docx")
        
        # 备份旧模板
        backup_path = template_path + '.backup'
        shutil.copy2(template_path, backup_path)
        
        # 更新
        shutil.copy2(new_word_file, template_path)
        
        # 检测新增占位符
        parser = WordParser(template_path)
        structure = parser.parse_structure()
        new_placeholders = self.detector.detect_from_content(str(structure))
        
        return {
            'success': True,
            'template_path': template_path,
            'new_placeholders': new_placeholders,
            'message': '模板更新成功'
        }
    
    def _load_elements(self, elements_file: str) -> Dict:
        """加载要素文件"""
        import yaml
        with open(elements_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _detect_placeholders(self, structure: Dict, elements: Dict) -> List[str]:
        """检测占位符"""
        placeholders = set()
        
        # 从已有占位符检测
        for para in structure.get('paragraphs', []):
            found = self.detector.detect_from_content(para['text'])
            placeholders.update(found)
        
        # 从要素生成
        for key in elements.keys():
            placeholders.add("{{" + key + "}}")
        
        return list(placeholders)
