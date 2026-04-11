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

## SKILL.md 创建与修改规范

创建新 skill 或修改已有 skill 的 `SKILL.md` 时，**必须调用 `skill-creator`**，不得手动编写。

**原因**：`SKILL.md` 是 Claude Code 可调用的 skill 文件，需要符合 frontmatter 格式、描述规范和触发语义。`skill-creator` 能确保这些一致性。

**适用场景**：
- 新建 skill（创建 `SKILL.md`）
- 修改 skill 的触发描述、接口说明或使用流程

## 待定
增量修改skills可以考虑superpowers:writing-skills
