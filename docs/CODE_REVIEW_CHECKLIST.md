# 代码审查检查清单

使用此清单审查代码，确保符合项目规范。

## 快速检查（5分钟）

### 代码结构
- [ ] 文件是否超过 500 行？（超过则拆分）
- [ ] 模块职责是否单一？（一个模块只做一件事）
- [ ] 是否有不必要的导入？（删除未使用的 import）

### 函数设计
- [ ] 函数是否超过 50 行？（超过则拆分）
- [ ] 函数参数是否超过 5 个？（超过则使用数据类）
- [ ] 函数名是否清晰表达意图？

### I/O 操作
- [ ] 是否在循环中执行 I/O？（改为批量操作）
- [ ] 是否混合了逻辑和 I/O？（分离为纯函数和 I/O 函数）
- [ ] 文件操作是否有错误处理？

## 详细检查（15分钟）

### 1. 数据结构设计

**扁平化检查**
- [ ] YAML/JSON 结构是否超过 2 层嵌套？
- [ ] 是否有不必要的顶层键（fields、items、data）？
- [ ] 能否用 `type` 字段替代顶层键？

**示例检查**
```yaml
# ❌ 嵌套结构
fields:
  company: ...

# ✅ 扁平结构
company: ...
```

### 2. 函数式编程

**纯函数检查**
- [ ] 函数是否修改了传入的参数？
- [ ] 相同输入是否总是产生相同输出？
- [ ] 是否有隐藏的副作用（I/O、全局状态）？

**I/O 分离检查**
- [ ] 是否有独立的 load/save 函数？
- [ ] 业务逻辑函数是否不直接执行 I/O？
- [ ] 批量操作是否只执行一次 I/O？

**示例检查**
```python
# ❌ 混合 I/O 和逻辑
def update_item(path, id, value):
    data = load(path)      # I/O
    data[id] = value       # 逻辑
    save(path, data)       # I/O

# ✅ I/O 分离
def update_item(data, id, value):
    new_data = data.copy()
    new_data[id] = value   # 纯逻辑
    return new_data

# 使用时
data = load(path)
data = update_item(data, id, value)
save(path, data)          # 一次 I/O
```

### 3. 模块组织

**内聚性检查**
- [ ] 模块内的函数是否操作相同的数据类型？
- [ ] 模块名是否反映其职责？
- [ ] 是否有函数应该移到其他模块？

**模块拆分检查**
```
文档分析 → document.py
模板操作 → template.py
数据管理 → schema.py / router.py
验证逻辑 → validate.py
```

### 4. 冗余代码检查

**包装函数检查**
- [ ] 是否只是转发调用，没有额外逻辑？
- [ ] 能否直接使用标准库？

**重复代码检查**
- [ ] 是否有多个函数做类似的事？
- [ ] 能否合并或提取公共逻辑？

**示例检查**
```python
# ❌ 无意义的包装
def backup_file(src, dst):
    return shutil.copy2(src, dst)

# ✅ 直接使用
shutil.copy2(src, dst)
```

### 5. 命名规范

**函数命名**
- [ ] 是否使用具体动词（update、load、save、find、replace）？
- [ ] 是否避免使用模糊的词（handle、process、do）？
- [ ] 是否避免使用 get/set（除非确实是 getter/setter）？

**常量命名**
- [ ] 默认值常量是否使用 DEFAULT_ 前缀？
- [ ] 类型常量是否使用 Type 后缀？

**示例检查**
```python
# ❌ 模糊命名
def handle_data(data):
    pass

def process_item(item):
    pass

# ✅ 清晰命名
def validate_schema(schema):
    pass

def render_template(template, context):
    pass
```

### 6. 错误处理

**异常检查**
- [ ] 是否有适当的错误处理？
- [ ] 错误消息是否清晰？
- [ ] 是否避免捕获所有异常（裸 except）？

**验证检查**
- [ ] 是否验证输入参数？
- [ ] 是否处理边界情况（空值、None）？

**示例检查**
```python
# ❌ 不好的错误处理
def process(path):
    data = load(path)  # 可能失败
    return data

# ✅ 好的错误处理
def process(path):
    if not Path(path).exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    data = load(path)
    return data
```

## 常见问题速查

| 问题 | 检查项 | 解决方案 |
|------|--------|---------|
| 循环慢 | 循环中有 I/O | 改为批量操作 |
| 内存高 | 创建大量临时对象 | 使用生成器 |
| 难测试 | 函数有副作用 | 分离 I/O 和逻辑 |
| 难维护 | 模块职责不清 | 按职责拆分 |
| 难理解 | 命名模糊 | 重命名函数/变量 |
| Bug 多 | 缺少错误处理 | 添加验证和异常处理 |

## 审查流程

1. **静态分析**（2分钟）
   - 运行 linter（ruff、black）
   - 检查代码风格

2. **快速检查**（5分钟）
   - 使用快速检查清单

3. **详细检查**（15分钟）
   - 使用详细检查清单
   - 标记需要修改的地方

4. **讨论修改**（10分钟）
   - 与作者讨论发现的问题
   - 确认修改优先级

5. **验证修改**（5分钟）
   - 确认所有问题已修复
   - 运行测试

## 审查优先级

**必须修复（阻塞性）**
- 安全漏洞
- 功能错误
- 性能问题（循环 I/O）
- 缺少错误处理

**应该修复（重要性）**
- 代码重复
- 模块职责不清
- 命名模糊
- 数据结构嵌套过深

**可以考虑（优化性）**
- 代码风格
- 注释不足
- 变量名过长
- 可以简化的逻辑

## 工具支持

### Python 静态分析
```bash
# 代码风格检查
ruff check .

# 代码格式化
ruff format .

# 类型检查
mypy .
```

### Git Hooks
在 `.git/hooks/pre-commit` 中添加：
```bash
#!/bin/bash
# 运行静态检查
ruff check .
if [ $? -ne 0 ]; then
    echo "代码检查失败，请修复后再提交"
    exit 1
fi
```
