"""工作流编排器 - 场景一"""
from typing import Dict, Any, Optional
from template_admin.template_manager import TemplateManager
from rule_manager.feedback_handler import FeedbackHandler


class TemplateWorkflowOrchestrator:
    """场景一: 模板制作与维护工作流"""
    
    def __init__(self):
        self.template_manager = TemplateManager()
        self.feedback_handler = FeedbackHandler()
    
    async def handle_create_template(self, word_file: str, 
                                     elements_file: Optional[str],
                                     report_type: str) -> Dict[str, Any]:
        """处理创建模板请求"""
        result = self.template_manager.create_template(
            word_file, elements_file, report_type
        )
        
        return {
            'type': 'template_created',
            'data': result,
            'message': self._format_create_message(result)
        }
    
    async def handle_update_template(self, word_file: str,
                                     report_type: str) -> Dict[str, Any]:
        """处理更新模板请求"""
        result = self.template_manager.update_template(
            word_file, report_type
        )
        
        return {
            'type': 'template_updated',
            'data': result,
            'message': self._format_update_message(result)
        }
    
    async def handle_feedback(self, feedback: str,
                             report_type: str = "common") -> Dict[str, Any]:
        """处理用户反馈"""
        result = self.feedback_handler.process(feedback, report_type)
        
        if result.get('success') and result.get('template_prompt'):
            return {
                'type': 'field_added',
                'data': result,
                'message': self._format_feedback_message(result)
            }
        
        return {
            'type': 'feedback_processed',
            'data': result,
            'message': result.get('message', '处理完成')
        }
    
    def _format_create_message(self, result: Dict) -> str:
        """格式化创建成功消息"""
        msg = "模板创建成功！\n\n"
        msg += f"检测到的占位符: {', '.join(result.get('placeholders', []))}\n\n"
        msg += "下一步: 您可以通过对话方式修改提取规则，\n"
        msg += '例如: "以后提取某类型报告时，增加一个\'风险提示\'字段"'
        return msg
    
    def _format_update_message(self, result: Dict) -> str:
        """格式化更新成功消息"""
        msg = "模板更新成功！\n\n"
        msg += f"新增占位符: {', '.join(result.get('new_placeholders', []))}"
        return msg
    
    def _format_feedback_message(self, result: Dict) -> str:
        """格式化反馈处理消息"""
        msg = f"已{result['action']}字段: {result['field_name']}\n\n"
        msg += result.get('template_prompt', '')
        return msg
