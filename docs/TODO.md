  Windows 默认编码是 GBK — path.read_text() 和 path.write_text() 不指定 encoding 时用系统默认编码。中文项目必须显式
  encoding='utf-8'，否则在 Windows 上中文 YAML 会炸。


  neolyst_integration.py 里的 from skills.neolyst.scripts.connection import get_client 就是跨 skill 的 Python    
  层直接依赖，违反了架构原则。 

  命名规则？

  1. renderer.py 对同一文件 8-10 次完整 zip 读写 — 需要重构 modify_docx_xml 支持批量操作
  2. splitter.py 中 extract_body/extract_english_summary 的 ~200 行重复 — 需要提取通用启发式提取函数
  3. renderer.py 导入 17 个私有函数 — 需要重新设计模块间 API 边界
  4. yfinance 对同一 ticker 重复请求 — 需要在渲染流程中共享数据
  