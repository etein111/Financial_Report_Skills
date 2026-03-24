"""占位符检测器"""
import re
from typing import Dict, List, Any, Set
from parser import WordParser


class PlaceholderDetector:
    """检测并生成占位符"""
    
    # 已知的动态字段模式
    KNOWN_FIELDS = {
        'ticker': r'\d{3,4}\s*HK|\w+\s*US',
        'company_name': r'[A-Z][a-z]+(\s+[A-Z][a-z]+)*',
        'rating': r'OUTPERFORM|NEUTRAL|UNDERPERFORM|BUY|SELL|HOLD',
        'target_price': r'\$?\d+\.?\d*',
        'report_date': r'\d{1,2}\s+\w+\s+\d{4}',
        'title': r'.+',
    }
    
    def __init__(self):
        self.detected_placeholders: Set[str] = set()
    
    def detect_from_content(self, content: str) -> List[str]:
        """从内容中检测可能的占位符"""
        placeholders = []
        
        # 模式1: 已有占位符格式 {{xxx}}
        matches = re.findall(r'\{\{([a-z_]+)\}\}', content, re.IGNORECASE)
        placeholders.extend(matches)
        
        # 模式2: [xxx] 格式
        matches = re.findall(r'\[([a-z_]+)\]', content, re.IGNORECASE)
        placeholders.extend(matches)
        
        # 模式3: <xxx> 格式
        matches = re.findall(r'<([a-z_]+)>', content, re.IGNORECASE)
        placeholders.extend(matches)
        
        return list(set(placeholders))
    
    def generate_template(self, parser: WordParser, elements: Dict) -> tuple:
        """生成带占位符的模板
        
        Args:
            parser: WordParser 实例
            elements: 要素字典 {field: value}
            
        Returns:
            (模板文件路径, 占位符列表)
        """
        # 分析文档结构，找出可替换的区域
        structure = parser.parse_structure()
        
        # 生成占位符映射
        placeholders = self._generate_placeholder_mapping(elements)
        
        # TODO: 创建新模板文件，替换内容为占位符
        
        return ("template.docx", list(placeholders.keys()))
    
    def _generate_placeholder_mapping(self, elements: Dict) -> Dict[str, str]:
        """生成占位符映射"""
        placeholders = {}
        for key, value in elements.items():
            placeholder = "{{" + key + "}}"
            placeholders[placeholder] = str(value)
        return placeholders
    
    def infer_placeholder_name(self, content: str) -> str:
        """从内容推断占位符名称"""
        content = content.strip()
        
        # 尝试匹配已知模式
        for field, pattern in self.KNOWN_FIELDS.items():
            if re.match(pattern, content, re.IGNORECASE):
                return field
        
        # 无法推断，使用通用名称
        return "unknown_field"
