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

测试入口不会直接读取 `skills/neolyst/neolyst.yaml`。`conftest.py` 会在 pytest 启动时执行以下映射：

- `NEOLYST_TEST_URL` -> `NEOLYST_URL`
- `NEOLYST_TEST_ANON_KEY` -> `NEOLYST_ANON_KEY`

因此，本地联调必须显式提供以上 4 个 `NEOLYST_TEST_*` 环境变量，不能依赖 yaml 默认值。
