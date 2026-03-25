# 项目结构说明

## 目录组织

```
neoskills/
├── docs/                   # 项目文档（需求、设计）
├── skills/                 # Skills 实现
│   └── template_maker/     # template_maker skill
│       ├── SKILL.md        # Skill 主文档
│       ├── scripts/        # 可执行脚本
│       ├── samples/        # 测试样本文件
│       └── references/     # 参考文档（可选）
├── templates/              # 生产模板（由 skill 生成）
├── tests/                  # 测试代码（如果需要）
├── .claude/                # Claude Code 配置
├── .gitignore              # Git 忽略规则
├── AGENTS.md               # AI 编程助手指导
├── CODING_STANDARDS.md     # 代码规范
├── CODE_REVIEW_CHECKLIST.md # 代码审查清单
└── README.md               # 项目说明
```

## 临时文件位置规则

**❌ 不要在项目根目录创建临时文件夹：**
- `*-workspace/`
- `test-results/`
- `eval-results/`
- `venv/`（如果已有 `.venv/`）

**✅ 临时文件应该放在：**
1. **系统临时目录** (`/tmp/` 或 `$TMPDIR`)
2. **用户主目录下的临时空间** (`~/tmp/`)
3. **专门的开发工作区** (可选: `../neoskills-dev/`)

## Skill 评估规范

当使用 skill-creator 评估 skill 时：

```bash
# 方案 1: 使用系统临时目录（推荐）
WORKSPACE=/tmp/neoskills-eval-$(date +%s)

# 方案 2: 使用项目外的开发目录
WORKSPACE=../neoskills-dev/eval-$(date +%s)

# 运行评估
mkdir -p "$WORKSPACE"
# ... 运行测试 ...
# 评估完成后可选：rm -rf "$WORKSPACE"
```

## Skill 目录结构规范

每个 skill 目录应该遵循以下结构：

```
skills/<skill_name>/
├── SKILL.md              # Skill 主文档
├── scripts/              # 可执行脚本
├── fixtures/             # 测试样本（输入文件）
├── tests/                # 测试相关
│   ├── expected/         # 预期输出（版本控制）
│   ├── output/           # 临时输出（.gitignore）
│   └── README.md         # 测试说明
└── references/           # 参考文档（可选）
```

**关键原则：**
- `fixtures/` - 固定测试输入，**被 Git 追踪**
- `tests/expected/` - 预期输出，**被 Git 追踪**
- `tests/output/` - 临时测试输出，**不被 Git 追踪**

## Git 提交前检查

```bash
# 检查是否有临时文件被追踪
git status

# 如果发现临时文件，先清理
git clean -fd

# 更新 .gitignore（如果需要）
# 然后再提交
```

## 常见错误

| 错误 | 影响 | 修复 |
|------|------|------|
| 评估输出在项目根目录 | 污染项目结构 | 使用 `/tmp/` 或 `.gitignore` |
| venv 和 .venv 同时存在 | 混淆 | 删除 venv，使用 .venv |
| 测试模板和生产模板混在一起 | 不清楚哪个是正式的 | 测试模板加 `test_` 前缀，已在 .gitignore 中排除 |
| 子代理输出文件 (*.output) 留在项目 | 占用空间 | 已在 .gitignore 中排除 |

## .gitignore 更新记录

重要更新会记录在这里，方便追踪。

**2024-03-24**: 添加评估工作区和虚拟环境目录的忽略规则。
