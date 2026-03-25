@docs/README.md

# AGENTS.md

AI 编程助手的统一指导文件。Claude Code 和 Codex 共享此配置。

## 文档索引

## 语言偏好

- 默认使用中文与用户沟通，思考过程也使用中文
- 产出的文档、说明、计划与总结默认使用中文
- 仅在用户明确要求时切换语言

## 沟通原则

向用户提问澄清需求或做决策时，避免只抛问题，必须同时给出：
- 推荐选项（默认）
- 关键考量/取舍
- 不确定时的默认决策

## 编码原则

### Python 项目

- **使用 uv 作为包管理工具**：优先使用 `uv` 而非 `pip` 或 `poetry` 进行依赖管理和项目初始化
- 安装依赖：`uv pip install <package>` 或 `uv sync`
- 创建项目：`uv init` 或 `uv venv`

- **优先使用函数式编程**：
  - **使用纯函数代替类方法**：优先定义独立的函数，而不是将所有逻辑封装在类中
  - **函数应该无副作用**：相同输入始终产生相同输出，不依赖外部状态
  - **避免可变状态**：不要在函数内部修改传入的可变对象（如列表、字典），而是返回新对象
  - **组合优于继承**：通过组合小函数来构建复杂功能，而不是通过类的继承
  - **工具函数独立存在**：将功能拆分为独立的工具函数，便于 AI（Claude）按需调用

  **详细规范**：参见 [CODING_STANDARDS.md](./docs/CODING_STANDARDS.md)
  **审查清单**：参见 [CODE_REVIEW_CHECKLIST.md](./docs/CODE_REVIEW_CHECKLIST.md)

  **核心原则**：
  - **I/O 分离**：读写操作应该是独立的、显式的函数
  - **批量操作**：支持批量修改，避免循环中的 I/O
  - **扁平化结构**：数据结构优先扁平，不超过 2 层嵌套
  - **删除冗余**：删除无意义的包装函数和重复代码
  - **默认值常量化**：默认值定义为模块级常量

  **示例**：

  ```python
  # ✅ 推荐：I/O 分离 + 批量操作
  def load_data(path) -> dict:
      """纯 I/O"""
      return yaml.safe_load(Path(path).read_text())

  def update_item(data: dict, key: str, value) -> dict:
      """纯函数：返回新对象"""
      new_data = data.copy()
      new_data[key] = value
      return new_data

  def save_data(path: str, data: dict) -> None:
      """纯 I/O"""
      Path(path).write_text(yaml.dump(data))

  # 使用：批量修改，一次 I/O
  data = load_data("config.yaml")
  data = update_item(data, "key1", "value1")
  data = update_item(data, "key2", "value2")
  data = update_item(data, "key3", "value3")
  save_data("config.yaml", data)  # 一次写入
      doc.save(output_path)
      return {"success": True}

  # ❌ 避免：面向对象风格（过度封装）
  class DocumentProcessor:
      def __init__(self, doc_path):
          self.doc_path = doc_path
          self.doc = Document(doc_path)

      def find_content(self, search_text):
          # 依赖 self.state
          pass

      def replace_content(self, old, new):
          # 修改 self.state
          pass
  ```

  **理由**：
  - AI（Claude）可以直接调用单个函数，无需初始化类实例
  - 函数更容易测试和维护
  - 无副作用的函数可以安全地重试、并行执行
  - 符合 Unix 哲学："做好一件事"的小工具组合

### Skills 开发

- **严格遵循 Anthropic Agent Skills Open Standard**：所有 skill 必须符合官方标准规范
  - 官方文档：[agentskills.io](https://agentskills.io/home)
  - 官方仓库：[github.com/anthropics/skills](https://github.com/anthropics/skills)
  - 完整指南：[The Complete Guide to Building Skills for Claude (PDF)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)
  - **必需**：SKILL.md 必须包含 YAML frontmatter（name 和 description 字段）
  - **标准结构**：代码文件放在 `scripts/` 子目录，SKILL.md 在根目录

- **Skill 命名规范**：
  - **目录名和模块名必须使用下划线分隔**（如 `template_maker`、`report_maker`）
  - **禁止使用连字符**（如 `template-maker`），因为 Python 模块名不能包含连字符
  - 这确保了 skill 可以被正确导入：`from skills.template_maker.scripts.core import ...`

- **使用 skill-creator skill 开发新技能**：
  - 在创建或修改 skill 之前，**必须先调用** skill-creator skill
  - 使用 `init_skill.py` 脚本初始化正确的目录结构
  - 使用 `package_skill.py` 脚本验证和打包 skill
  - 参考 skill-creator 的设计模式和最佳实践

---
