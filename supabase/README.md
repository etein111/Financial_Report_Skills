# supabase/

本地 Supabase 开发环境。

## 目录结构

```
supabase/
├── config.toml                # Supabase 本地配置
├── seed.sql                   # 基础种子数据（随 db reset 自动加载）
├── SUPABASE_STANDARDS.md      # Supabase 开发规范
├── migrations/                # Schema 迁移文件（按编号顺序执行）
│   ├── 000_bootstrap          #   扩展、基础类型
│   ├── 010_reference_tables   #   字典表（rating, region, sector…）
│   ├── 020_core_tables        #   核心业务表（analyst, coverage, report…）
│   ├── 030_functions_triggers #   表级函数和触发器
│   ├── 040_security           #   RLS 策略
│   ├── 045_analyst_functions  #   分析师相关 RPC
│   ├── 050_template_functions #   模板相关 RPC
│   ├── 055_storage_policies   #   Storage 访问策略
│   ├── 056_template_path      #   模板路径前缀函数
│   ├── 060_coverage_functions #   覆盖相关 RPC
│   ├── 070_draft_report       #   报告草稿 RPC
│   └── 080_submit_report      #   报告提交 RPC
├── tests/
│   └── test_data.sql          # 测试数据（手工导入，不随 reset 自动加载）
├── seeds/                     # （预留）
├── snippets/                  # 常用 SQL 片段
├── push_supabase_com.py       # 推送到 Supabase Cloud 的脚本
└── push_zeabur_com.py         # 推送到 Zeabur 的脚本
```
