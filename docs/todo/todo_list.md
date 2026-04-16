  Windows 默认编码是 GBK — path.read_text() 和 path.write_text() 不指定 encoding 时用系统默认编码。中文项目必须显式
  encoding='utf-8'，否则在 Windows 上中文 YAML 会炸。


  neolyst_integration.py 里的 from skills.neolyst.scripts.connection import get_client 就是跨 skill 的 Python    
  层直接依赖，违反了架构原则。 

  命名规则？
