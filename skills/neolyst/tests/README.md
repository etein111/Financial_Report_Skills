# neolyst tests

集成测试，连接联调 Supabase 环境执行。

## 目录说明

- `fixtures/` — 固定测试输入文件（被 Git 追踪）
- `expected/` — 预期输出（被 Git 追踪）
- `output/` — 临时测试输出（不被 Git 追踪，见 .gitignore）

## 运行测试

```bash
export NEOLYST_TEST_URL=http://127.0.0.1:54321
export NEOLYST_TEST_ANON_KEY=...
export NEOLYST_TEST_EMAIL=your_email@example.com
export NEOLYST_TEST_PASSWORD=your_password
uv run pytest skills/neolyst/tests/ -v
```
