# Neoskills 代码规范

本文档总结项目开发中的最佳实践和设计原则，确保代码质量和一致性。

## 核心原则

### 1. 函数式编程优先

#### 原则
- **纯函数**：相同输入 → 相同输出，无副作用
- **I/O 分离**：读写操作应该是独立的、显式的函数
- **不可变性**：不要修改传入的可变对象，返回新对象
- **批量操作**：支持批量修改，避免循环中的 I/O

#### 示例

**❌ 错误：每次操作都读写文件**
```python
def add_router_mapping(router_path, report_type, template_name):
    data = load_router(router_path)      # 读文件
    data["mappings"][report_type] = template_name
    save_router(router_path, data)      # 写文件

# 调用3次 = 3次读 + 3次写
add_router_mapping(path, "company", "common")
add_router_mapping(path, "macro", "common")
add_router_mapping(path, "strategy", "common")
```

**✅ 正确：分离逻辑和 I/O**
```python
def update_mapping(data, report_type, template_name):
    """纯函数：返回新数据"""
    new_data = data.copy()
    new_data.setdefault("mappings", {})[report_type] = template_name
    return new_data

# 调用3次 = 1次读 + 1次写
data = load_router(path)
data = update_mapping(data, "company", "common")
data = update_mapping(data, "macro", "common")
data = update_mapping(data, "strategy", "common")
save_router(path, data)
```

#### 检查清单
- [ ] 函数是否修改了传入的参数？
- [ ] 函数是否隐式执行 I/O（读写文件、网络请求）？
- [ ] 批量操作是否会导致多次 I/O？

### 2. 扁平化数据结构

#### 原则
- **扁平优于嵌套**：能用扁平结构就不要嵌套
- **用字段区分类型**：用 `type` 字段而非顶层键
- **减少层级**：YAML/JSON 结构尽量不超过 2 层

#### 示例

**❌ 错误：人为分离导致嵌套**
```yaml
# 不必要的嵌套
fields:
  company:
    description: 公司名称
    format: 西锐飞机
  ticker:
    description: 股票代码
    format: 2507.HK

extraction_rules:
  abstract:
    description: 报告摘要
    scope: 首页右侧
  body:
    description: 报告正文
    scope: 从首页之后
```

**✅ 正确：扁平化，用 type 区分**
```yaml
# 扁平化结构
company:
  description: 公司名称
  format: 西锐飞机

ticker:
  description: 股票代码
  format: 2507.HK

abstract:
  type: fragment
  description: 报告摘要
  scope: 首页右侧

body:
  type: fragment
  description: 报告正文
  scope: 从首页之后
```

#### 检查清单
- [ ] 是否有不必要的顶层键（fields、items、data）？
- [ ] 结构是否超过 2 层嵌套？
- [ ] 能否用 `type` 字段替代顶层键？

### 3. 模块高内聚低耦合

#### 原则
- **单一职责**：一个模块只做一件事
- **按数据类型分**：操作相同数据类型的函数放一起
- **按操作对象分**：document.py 操作 Document，schema.py 操作 dict
- **命名反映职责**：模块名要清晰表达其职责

#### 示例

**❌ 错误：tools.py 包含所有函数**
```python
# tools.py (25KB, 30+ 函数)
def find_content_location(): pass   # 文档分析
def replace_field_value(): pass      # 模板操作
def generate_schema(): pass          # Schema 生成
def load_router(): pass              # 路由管理
# ... 26 更多函数
```

**✅ 正确：按职责拆分**
```python
# document.py (文档分析)
def find_content_location(): pass
def get_document_structure(): pass

# template.py (模板操作)
def replace_field_value(): pass
def replace_abstract(): pass

# schema.py (Schema 管理)
def generate_schema(): pass
def update_field(): pass

# router.py (路由管理)
def load_router(): pass
def update_mapping(): pass
```

#### 模块拆分指南

| 操作对象 | 模块名 | 典型函数 |
|---------|--------|---------|
| Word 文档结构 | document.py | find_content, get_structure |
| Word 文档内容 | template.py | replace_field, replace_body |
| Schema 数据 | schema.py | generate_schema, update_field |
| 路由配置 | router.py | load_router, update_mapping |
| 验证逻辑 | validate.py | validate_template |

#### 检查清单
- [ ] 模块是否超过 500 行？
- [ ] 模块内的函数是否操作不同的数据类型？
- [ ] 模块名是否清晰表达职责？

### 4. 删除冗余代码

#### 原则
- **包装不等于抽象**：如果只是转发调用，没有额外逻辑，删除它
- **避免重复**：两个函数做类似的事，合并它们
- **用现有工具**：不要重新发明轮子

#### 示例

**❌ 错误：无意义的包装**
```python
def save_template_backup(doc_path, backup_path):
    """保存模板备份"""
    shutil.copy2(doc_path, backup_path)  # 只是转发
    return {"success": True}
```

**✅ 正确：直接使用 shutil.copy2**
```python
# 使用标准库
import shutil
shutil.copy2(doc_path, backup_path)

# 或者使用 Git 进行版本控制
```

**❌ 错误：逻辑重复**
```python
def add_schema_field(path, name, description, format):
    schema = load_schema(path)
    schema[name] = {"description": description}
    if format:
        schema[name]["format"] = format
    save_schema(path, schema)

def update_schema_field(path, name, description, format):
    schema = load_schema(path)
    if name in schema:
        schema[name]["description"] = description
    if format:
        schema[name]["format"] = format
    save_schema(path, schema)
```

**✅ 正确：合并为一个函数**
```python
def update_field(schema, name, description, format=None):
    """纯函数：返回新 schema"""
    new_schema = schema.copy()
    field_def = {"description": description}
    if format:
        field_def["format"] = format
    new_schema[name] = field_def
    return new_schema
```

#### 检查清单
- [ ] 这个函数是否只是转发调用？
- [ ] 是否有多个函数做类似的事？
- [ ] 是否可以用标准库替代？

### 5. 默认值应该是常量

#### 原则
- **定义常量**：默认值定义为模块级常量
- **避免硬编码**：不要在函数里写死默认值
- **支持覆盖**：用户配置应该覆盖默认值

#### 示例

**❌ 错误：函数内写死默认值**
```python
def generate_schema(elements):
    schema = {}
    for name, value in elements.items():
        schema[name] = {
            "description": name,  # 硬编码
            "type": "string"      # 硬编码
        }
    return schema
```

**✅ 正确：定义常量**
```python
DEFAULT_FIELD_TYPE = "string"

def generate_schema(elements):
    schema = {}
    for name, value in elements.items():
        schema[name] = {
            "description": name,
            "type": DEFAULT_FIELD_TYPE
        }
    return schema
```

#### 检查清单
- [ ] 默认值是否定义为常量？
- [ ] 常量名是否清晰（使用 DEFAULT_ 前缀）？
- [ ] 是否支持用户配置覆盖？

## 代码审查检查清单

在提交代码前，确保：

### 结构设计
- [ ] 数据结构是否扁平化（不超过 2 层嵌套）？
- [ ] 是否用 `type` 字段区分类型，而非顶层键？
- [ ] YAML/JSON 结构是否清晰简洁？

### 函数设计
- [ ] 函数是否为纯函数（相同输入 → 相同输出）？
- [ ] I/O 操作是否独立为单独的函数？
- [ ] 是否支持批量操作（避免循环 I/O）？
- [ ] 返回值是否是新对象，而非修改传入对象？

### 模块组织
- [ ] 模块是否按职责拆分（单一职责）？
- [ ] 模块内函数是否操作相同的数据类型？
- [ ] 模块名是否清晰反映职责？
- [ ] 模块是否超过 500 行？

### 代码质量
- [ ] 是否删除了冗余的包装函数？
- [ ] 是否合并了重复逻辑的函数？
- [ ] 是否使用了标准库而非重新实现？
- [ ] 默认值是否定义为常量？

### 命名规范
- [ ] 函数名是否清晰表达意图（update、load、save、find）？
- [ ] 是否避免使用 get/set（优先使用具体动词）？
- [ ] 常量是否使用 DEFAULT_ 前缀？
- [ ] 类型是否使用 Type 后缀（Config、Data）？

## 重构流程

当需要重构代码时：

1. **理解现状**
   - 画出函数调用关系图
   - 标记 I/O 操作和纯函数
   - 识别重复代码和冗余函数

2. **识别问题**
   - 哪些函数混合了 I/O 和逻辑？
   - 哪些模块职责不清晰？
   - 哪些数据结构可以扁平化？

3. **设计目标**
   - 理想状态是什么？
   - 需要哪些模块和函数？
   - 数据流应该是怎样的？

4. **小步重构**
   - 每次只重构一个模块
   - 保持向后兼容（如果需要）
   - 运行测试验证

5. **更新文档**
   - 更新 SKILL.md
   - 更新设计文档
   - 更新示例代码

## 参考资源

- [AGENTS.md](../AGENTS.md) - 项目级编程指导
- [函数式编程原则](https://docs.python.org/3/howto/functional.html)
- [Python 代码风格](https://peps.python.org/pep-0008/)
