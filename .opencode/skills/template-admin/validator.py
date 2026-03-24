"""闭环验证器"""
from docx import Document
from typing import Dict, Any, List
from docxtpl import DocxTemplate
import os


class TemplateValidator:
    """模板闭环验证"""
    
    def __init__(self):
        self.differences: List[Dict] = []
    
    def validate(self, original_file: str, template_file: str, 
                 elements: Dict) -> Dict[str, Any]:
        """执行闭环验证
        
        1. 用 elements.yaml 渲染模板
        2. 与原文件比对
        3. 返回差异报告
        """
        # 1. 渲染模板
        rendered_file = self._render_template(template_file, elements)
        
        # 2. 比对
        differences = self._compare_files(original_file, rendered_file)
        
        # 3. 返回结果
        return {
            'passed': len(differences) == 0,
            'differences': differences,
            'rendered_file': rendered_file
        }
    
    def _render_template(self, template_path: str, elements: Dict) -> str:
        """渲染模板"""
        doc = DocxTemplate(template_path)
        doc.render(elements)
        
        output_path = template_path.replace('.docx', '_rendered.docx')
        doc.save(output_path)
        
        return output_path
    
    def _compare_files(self, file1: str, file2: str) -> List[Dict]:
        """比对两个文件"""
        differences = []
        
        doc1 = Document(file1)
        doc2 = Document(file2)
        
        # 比对段落
        paras1 = [p.text.strip() for p in doc1.paragraphs if p.text.strip()]
        paras2 = [p.text.strip() for p in doc2.paragraphs if p.text.strip()]
        
        if paras1 != paras2:
            differences.append({
                'type': 'paragraphs',
                'count1': len(paras1),
                'count2': len(paras2),
                'message': '段落数量不一致'
            })
        
        # 比对表格
        tables1 = doc1.tables
        tables2 = doc2.tables
        
        if len(tables1) != len(tables2):
            differences.append({
                'type': 'tables',
                'count1': len(tables1),
                'count2': len(tables2),
                'message': '表格数量不一致'
            })
        
        return differences
