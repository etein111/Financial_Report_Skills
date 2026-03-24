"""对话式反馈处理器"""
import re
from typing import Dict, List, Any, Optional
from schema_manager import SchemaManager


class FeedbackHandler:
    """处理用户反馈，更新规则"""
    
    def __init__(self):
        self.schema_manager = SchemaManager()
    
    def process(self, feedback: str, report_type: str = "common") -> Dict[str, Any]:
        """处理用户反馈
        
        识别反馈类型并执行相应操作
        """
        feedback = feedback.strip()
        
        # 识别操作类型
        if self._is_add_field(feedback):
            return self._handle_add_field(feedback, report_type)
        elif self._is_modify_field(feedback):
            return self._handle_modify_field(feedback, report_type)
        elif self._is_delete_field(feedback):
            return self._handle_delete_field(feedback, report_type)
        else:
            return {
                'success': False,
                'message': f'无法理解反馈: {feedback}'
            }
    
    def _is_add_field(self, text: str) -> bool:
        """是否添加字段"""
        patterns = [
            r'增加.*字段',
            r'添加.*字段',
            r'新增.*字段',
            r'加上.*字段',
        ]
        return any(re.search(p, text) for p in patterns)
    
    def _is_modify_field(self, text: str) -> bool:
        """是否修改字段"""
        patterns = [
            r'修改.*字段',
            r'调整.*字段',
            r'改变.*字段',
        ]
        return any(re.search(p, text) for p in patterns)
    
    def _is_delete_field(self, text: str) -> bool:
        """是否删除字段"""
        patterns = [
            r'删除.*字段',
            r'移除.*字段',
            r'去掉.*字段',
        ]
        return any(re.search(p, text) for p in patterns)
    
    def _extract_field_name(self, text: str) -> Optional[str]:
        """提引号内的字段名"""
        # 匹配 "xxx" 或 'xxx' 或「xxx」
        patterns = [
            r'["\']([^"\']+)["\']',  # "xxx" or 'xxx'
            r'[「『]([^」』]+)[」』]',  # 「xxx」
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                field = match.group(1)
                # 转换为下划线格式
                return self._to_underscore(field)
        
        return None
    
    def _to_underscore(self, text: str) -> str:
        """转换为下划线格式"""
        # 中文 -> 保留中文 or 直接用中文作为字段名
        # 英文 -> 转小写加下划线
        text = text.lower().strip()
        text = re.sub(r'[^\w\u4e00-\u9fff]', '_', text)
        text = re.sub(r'_+', '_', text)
        return text.strip('_')
    
    def _handle_add_field(self, feedback: str, report_type: str) -> Dict[str, Any]:
        """处理添加字段"""
        field_name = self._extract_field_name(feedback)
        
        if not field_name:
            return {
                'success': False,
                'message': '无法识别字段名，请使用引号包围字段名'
            }
        
        # 生成描述
        description = self._generate_description(feedback, field_name)
        
        # 更新 schema
        self.schema_manager.add_field(report_type, field_name, description)
        
        # 生成模板更新提示
        template_prompt = self._generate_template_prompt('add', field_name)
        
        return {
            'success': True,
            'action': 'add',
            'field_name': field_name,
            'description': description,
            'template_prompt': template_prompt,
            'changes': [f'在 {report_type} 类型中添加字段: {field_name}']
        }
    
    def _handle_modify_field(self, feedback: str, report_type: str) -> Dict[str, Any]:
        """处理修改字段"""
        field_name = self._extract_field_name(feedback)
        
        if not field_name:
            return {
                'success': False,
                'message': '无法识别字段名'
            }
        
        # 生成新描述
        description = self._generate_description(feedback, field_name)
        
        # 更新 schema
        self.schema_manager.modify_field(report_type, field_name, description)
        
        return {
            'success': True,
            'action': 'modify',
            'field_name': field_name,
            'description': description,
            'changes': [f'修改 {report_type} 类型字段: {field_name}']
        }
    
    def _handle_delete_field(self, feedback: str, report_type: str) -> Dict[str, Any]:
        """处理删除字段"""
        field_name = self._extract_field_name(feedback)
        
        if not field_name:
            return {
                'success': False,
                'message': '无法识别字段名'
            }
        
        # 删除
        self.schema_manager.delete_field(report_type, field_name)
        
        return {
            'success': True,
            'action': 'delete',
            'field_name': field_name,
            'changes': [f'删除 {report_type} 类型字段: {field_name}']
        }
    
    def _generate_description(self, feedback: str, field_name: str) -> str:
        """生成字段描述"""
        # 尝试从反馈中提取描述
        # 例如: "增加一个'风险提示'字段" -> "请提取风险提示"
        
        # 移除操作词，保留核心描述
        text = feedback
        for word in ['增加', '添加', '新增', '修改', '删除', '字段', '一个', '的']:
            text = text.replace(word, '')
        
        text = text.strip(' "\'')
        
        if text:
            return f"请提取{text}"
        
        return f"请提取{field_name}字段"
    
    def _generate_template_prompt(self, action: str, field_name: str) -> str:
        """生成模板更新提示"""
        if action == 'add':
            return (
                f"已增加'{field_name}'字段。\n\n"
                f"请下载当前的排版模板，在您希望显示该字段的段落输入占位符 "
                f"{{{{{field_name}}}}}，然后上传修改后的 Word 文件。"
            )
        return ""
