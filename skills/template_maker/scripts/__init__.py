# template_maker skill
# Skill 目录名使用下划线以符合 Python 模块命名规范
# 同时也符合 Anthropic Skills 的命名要求

# 函数式模块
from . import router
from . import schema
from . import document
from . import template

__all__ = [
    'router',    # 路由管理函数模块
    'schema',    # Schema 操作函数模块
    'document',  # 文档分析函数模块
    'template',  # 模板操作函数模块
]
