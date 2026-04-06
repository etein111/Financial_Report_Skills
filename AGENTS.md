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

## 文档协作规则

- 修改强耦合设计文档时，先整理“已确认决策清单”，再动文档。
- 每条已确认决策都要显式映射到受影响章节，按“决策 -> 章节”回填，不要按零散段落局部修补。
- 术语整理与行为规则修改分开处理；术语未稳定前，不要同步改接口语义。
- 跨文档修改后，至少回查主设计文档、架构文档和 live schema 快照三处，确认口径一致后再结束。

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

## 技术栈与工具库

### Word 文档操作

本项目涉及大量 Word 文档处理（模板生成、报告创建等），以下 Python 库按重要性和使用场景分类：

#### ✅ 核心库

| 库名 | 用途 | 安装 | 使用场景 |
|------|------|------|----------|
| **python-docx** | 创建、读取、修改 .docx 文件 | `uv pip install python-docx` | **最常用** - 基础文本、段落、表格、图片操作 |
| **docx2txt** | 提取 Word 文档纯文本 | `uv pip install docx2txt` | 文档分析、内容提取（复杂结构可读） |

**注意事项**：
- `python-docx` 的 `cell.text` **只返回直接段落的文本，不包括嵌套表格**
- 处理嵌套表格需要递归遍历 `cell.tables`
- 复杂结构建议用 `docx2txt` 先分析，再定位到 `python-docx` 操作

#### 📌 扩展/生态库

| 库名 | 用途 | 安装 | 使用场景 |
|------|------|------|----------|
| **docxtpl** | Jinja2 模板驱动的 Word 生成 | `uv pip install docxtpl` | 模板变量替换、循环、条件渲染 |
| **docxcompose** | 合并多个 Word 文档 | `uv pip install docxcompose` | 拼接报表、合并章节 |
| **docxedit** | 编辑 Word 文档且保留原有格式 | `uv pip install docxedit` | 复杂格式文档自动化处理 |
| **docx2python** | 提取复杂表格结构 | `uv pip install docx2python` | 嵌套表格、合并单元格的准确提取 |

#### 选择建议

| 任务 | 推荐库 | 理由 |
|------|--------|------|
| **创建模板** | `python-docx` | 精细控制文档结构 |
| **填充模板** | `docxtpl` | 支持循环、条件等高级功能 |
| **批量报告** | `docxtpl` + `python-docx` | 模板 + 精细调整 |
| **文档分析** | `docx2txt` | 可读性更好 |
| **合并文档** | `docxcompose` | 专为合并设计 |

#### 示例代码

**递归处理嵌套表格**（本项目常用）：

```python
from docx import Document

def replace_in_nested_tables(doc, old_text, new_text):
    """递归替换所有层级的表格文本"""
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                # 替换单元格段落
                for para in cell.paragraphs:
                    if old_text in para.text:
                        para.text = para.text.replace(old_text, new_text)

                # 递归处理嵌套表格
                for nested_table in cell.tables:
                    replace_in_nested_tables(nested_table, old_text, new_text)
```

---
