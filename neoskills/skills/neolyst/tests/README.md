# neolyst tests

集成测试，连接联调 Supabase 环境执行。

## 目录说明

- `fixtures/` — 固定测试输入文件（被 Git 追踪）
- `expected/` — 预期输出（被 Git 追踪）
- `output/` — 临时测试输出（不被 Git 追踪，见 .gitignore）

## 运行测试

首次使用，复制配置模板并按需修改：

```bash
cp skills/neolyst/tests/test_config.example.json skills/neolyst/tests/test_config.json
# 编辑 test_config.json，填入实际的 URL、anon_key、email、password
```

运行测试：

```bash
uv run pytest skills/neolyst/tests/ -v
```

测试配置统一从 `tests/test_config.json` 读取，不使用环境变量。
