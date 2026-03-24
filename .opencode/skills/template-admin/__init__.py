"""Template Admin Skill - 模板配置管家"""
from .parser import WordParser
from .placeholder_detector import PlaceholderDetector
from .validator import TemplateValidator
from .template_manager import TemplateManager

__all__ = [
    'WordParser',
    'PlaceholderDetector', 
    'TemplateValidator',
    'TemplateManager'
]
