# Skill 标准

## Skill 目录结构规范

每个 skill 目录应该遵循以下结构：

```
skills/<skill_name>/
├── SKILL.md              # Skill 主文档
├── scripts/              # 可执行脚本
├── tests/                # 测试相关
│   ├── fixtures/         # 测试样本（输入文件）
│   ├── expected/         # 预期输出（版本控制）
│   ├── output/           # 临时输出（.gitignore）
│   └── README.md         # 测试说明
└── references/           # 参考文档（可选）
```

**关键原则：**
- `tests/fixtures/` - 固定测试输入，**被 Git 追踪**
- `tests/expected/` - 预期输出，**被 Git 追踪**
- `tests/output/` - 临时测试输出，**不被 Git 追踪**
