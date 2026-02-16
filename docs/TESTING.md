# Testing & Verification

目标：让"测试/验收/诊断"可重复、可清理、不污染目录、不对云端数据造成不可控副作用。

## 目录结构原则

**核心原则：所有不交付的代码都不能放 `web/` 目录下**

```
web/                      # 只包含交付代码
  ├── app/
  ├── components/
  ├── domain/
  ├── features/
  ├── lib/
  └── 配置文件

tests/                    # 所有测试代码
  ├── e2e/
  ├── scripts/
  └── playwright.config.ts

scripts/                  # 开发/运维脚本
supabase/                 # 数据库相关
docs/                     # 项目文档
temp/                     # 临时输出（不提交）
```

## 临时文件规范

- 所有测试/验收产生的临时文件，只允许写到仓库根目录 `temp/`。
- 输出文件名带时间戳，避免覆盖：`<tool>-<yyyyMMdd-HHmmss>.<ext>`
- 任何脚本不得在源码目录写入 `*.out`、`*.log`、`*.tmp` 等文件。

## 测试运行

### E2E 测试
```bash
cd tests
pnpm exec playwright test
```

### 验收脚本
```powershell
cd tests
node scripts/verify/verify-db-admin-and-rls.mjs
```

## 云端库副作用控制

- 能用 **只读** 验证就只读
- 需要写入验证时，优先在事务内执行并 `ROLLBACK`
- 或创建带 `__test__` 前缀的临时数据，并确保 `finally` 清理

