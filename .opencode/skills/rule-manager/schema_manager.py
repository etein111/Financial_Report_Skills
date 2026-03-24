"""Schema 管理器"""
import yaml
import os
from typing import Dict, List, Any, Optional


class SchemaManager:
    """管理 schema.yaml 文件"""
    
    DEFAULT_SCHEMA_PATH = ".opencode/config/schema.yaml"
    
    def __init__(self, schema_path: Optional[str] = None):
        self.schema_path = schema_path or self.DEFAULT_SCHEMA_PATH
        self.schema = self._load()
    
    def _load(self) -> Dict:
        """加载 schema"""
        if not os.path.exists(self.schema_path):
            return {'company': {}, 'sector': {}, 'common': {}}
        
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _save(self):
        """保存 schema"""
        with open(self.schema_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.schema, f, allow_unicode=True, default_flow_style=False)
    
    def add_field(self, report_type: str, field_name: str, 
                  description: str = "") -> bool:
        """添加字段"""
        if report_type not in self.schema:
            self.schema[report_type] = {
                'required_fields': [],
                'extraction_prompts': {}
            }
        
        if 'required_fields' not in self.schema[report_type]:
            self.schema[report_type]['required_fields'] = []
        if 'extraction_prompts' not in self.schema[report_type]:
            self.schema[report_type]['extraction_prompts'] = {}
        
        # 添加到必填字段
        if field_name not in self.schema[report_type]['required_fields']:
            self.schema[report_type]['required_fields'].append(field_name)
        
        # 添加提取提示
        self.schema[report_type]['extraction_prompts'][field_name] = description
        
        self._save()
        return True
    
    def modify_field(self, report_type: str, field_name: str,
                    new_description: str = "") -> bool:
        """修改字段"""
        if report_type not in self.schema:
            return False
        
        if field_name in self.schema[report_type].get('extraction_prompts', {}):
            self.schema[report_type]['extraction_prompts'][field_name] = new_description
            self._save()
            return True
        
        return False
    
    def delete_field(self, report_type: str, field_name: str) -> bool:
        """删除字段"""
        if report_type not in self.schema:
            return False
        
        # 从必填字段中移除
        if 'required_fields' in self.schema[report_type]:
            if field_name in self.schema[report_type]['required_fields']:
                self.schema[report_type]['required_fields'].remove(field_name)
        
        # 从提取提示中移除
        if 'extraction_prompts' in self.schema[report_type]:
            if field_name in self.schema[report_type]['extraction_prompts']:
                del self.schema[report_type]['extraction_prompts'][field_name]
        
        self._save()
        return True
    
    def get_schema(self, report_type: str) -> Dict:
        """获取指定类型的 schema"""
        return self.schema.get(report_type, {})
    
    def list_report_types(self) -> List[str]:
        """列出所有报告类型"""
        return list(self.schema.keys())
