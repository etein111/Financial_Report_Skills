# report_maker 部署文档

本文档介绍如何部署和配置 `report_maker` skill。

## 环境要求

- Python 3.8 或更高版本
- Claude Code 或兼容的 AI 编程助手
- 可选：LibreOffice（用于 PDF 转换）

## 部署步骤

### 1. 确认环境

```bash
# 检查 Python 版本
python --version  # 应该是 3.8+

# 检查 uv 是否已安装（推荐使用 uv）
which uv
```

### 2. 安装依赖

```bash
# 使用 uv 安装（推荐）
uv pip install python-docx docxtpl

# 或使用 pip
pip install python-docx docxtpl
```

### 3. 验证 skill 文件

```bash
# 检查 skill 文件是否存在
ls -la skills/report_maker/SKILL.md

# 检查脚本模块
ls -la skills/report_maker/scripts/
```

应该看到：
- `common.py` - 通用工具函数
- `extractor.py` - LLM 要素提取
- `splitter.py` - 摘要/正文拆分
- `renderer.py` - 模板渲染

### 4. 运行测试

```bash
# 运行所有测试
pytest skills/report_maker/tests/ -v

# 预期输出: 所有测试通过
# ============================== 84 passed in X.XX s ==============================
```

### 5. 配置模板路由

编辑 `templates/router.yaml`，配置报告类型到模板的映射：

```yaml
mappings:
  company: company
  sector: sector
  macro: common
  strategy: common
  quantitative: common
  bond: common
```

### 6. 准备模板目录

确保以下目录结构存在：

```
templates/
├── router.yaml
├── company/
│   ├── schema.yaml
│   └── template.docx
├── sector/
│   ├── schema.yaml
│   └── template.docx
└── common/
    ├── schema.yaml
    └── template.docx
```

### 7. 创建 reports 目录

```bash
# 创建报告输出目录
mkdir -p reports/
```

### 8. 测试完整流程

在 Claude Code 中测试：

```
我上传了一份公司报告草稿 draft.docx，报告类型是 company，帮我处理
```

预期行为：
1. 系统识别报告类型为 `company`
2. 从 router.yaml 获取模板名 `company`
3. 加载 schema.yaml
4. 提取要素并展示
5. 等待用户确认
6. 生成标准报告

## 可选：安装 LibreOffice

如果需要 PDF 转换功能：

### Windows

1. 下载 LibreOffice: https://www.libreoffice.org/download/download/
2. 安装到默认路径
3. 验证安装：
   ```powershell
   & "C:\Program Files\LibreOffice\program\soffice.exe" --version
   ```

### Linux

```bash
# Ubuntu/Debian
sudo apt-get install libreoffice

# Fedora/RHEL
sudo dnf install libreoffice

# 验证安装
libreoffice --version
```

### macOS

```bash
# 使用 Homebrew
brew install --cask libreoffice

# 验证安装
/libreoffice --version
```

## 故障排除

### 问题 1: Skill 未触发

**症状**: 上传报告后没有自动触发 report_maker skill

**解决方案**:
1. 检查 `skills/report_maker/SKILL.md` 是否存在
2. 确认 SKILL.md 中的 description 清楚描述了使用场景
3. 尝试明确指定："使用 report_maker 处理这份报告"

### 问题 2: 模板未找到

**症状**: 错误信息 "模板未找到"

**解决方案**:
1. 检查 `templates/router.yaml` 是否存在
2. 验证报告类型在 router.yaml 中有对应映射
3. 确认模板目录存在：`templates/<template_name>/template.docx`

### 问题 3: Schema 加载失败

**症状**: 错误信息 "schema.yaml 未找到"

**解决方案**:
1. 检查 `templates/<template_name>/schema.yaml` 是否存在
2. 验证 YAML 格式是否正确
3. 运行测试验证：`pytest skills/report_maker/tests/test_common.py -v`

### 问题 4: 依赖未安装

**症状**: "No module named 'docx'" 或类似错误

**解决方案**:
```bash
# 重新安装依赖
uv pip install --force-reinstall python-docx docxtpl

# 或使用 pip
pip install --force-reinstall python-docx docxtpl
```

### 问题 5: PDF 转换失败

**症状**: "LibreOffice 未找到，跳过 PDF 转换"

**解决方案**:
1. **方案 A**: 安装 LibreOffice（见上文）
2. **方案 B**: 跳过 PDF 转换，只生成 Word 文档
   - report_maker 会生成 `output.docx`
   - 可以手动转换为 PDF

### 问题 6: 测试失败

**症状**: `pytest` 运行失败

**解决方案**:
```bash
# 检查 Python 版本
python --version

# 重新安装依赖
uv pip install -e .

# 运行单个测试文件调试
pytest skills/report_maker/tests/test_common.py -v
```

### 问题 7: 权限错误

**症状**: 无法写入 reports/ 目录

**解决方案**:
```bash
# 检查目录权限
ls -la reports/

# 修改权限
chmod 755 reports/

# 或创建新的报告目录
mkdir -p /path/to/reports
```

## 验证部署

运行以下命令验证部署成功：

```bash
# 1. 检查 Python 环境
python --version

# 2. 检查依赖
python -c "import docx; import docxtpl; print('依赖 OK')"

# 3. 运行测试
pytest skills/report_maker/tests/ -v

# 4. 检查 skill 文件
ls -l skills/report_maker/SKILL.md
ls -l skills/report_maker/scripts/*.py

# 5. 检查模板
ls -l templates/router.yaml
ls -l templates/company/schema.yaml

# 6. 检查输出目录
ls -ld reports/
```

## 配置文件示例

### router.yaml

```yaml
mappings:
  company: company
  sector: sector
  macro: common
  strategy: common
  quantitative: common
  bond: common
  company_flash: company
  sector_flash: sector
```

### company/schema.yaml

```yaml
company:
  type: string
  description: 公司名称
  format: "腾讯控股"

ticker:
  type: string
  description: 股票代码
  format: "0700.HK"

title:
  type: string
  description: 报告标题
  format: "首次覆盖：..."

rating:
  type: string
  description: 投资评级
  format: "OUTPERFORM"

# ... 更多字段定义
```

## 性能优化建议

1. **使用 uv 代替 pip**: uv 安装包更快
2. **缓存模板**: 首次渲染后缓存结果
3. **并行处理**: 多份报告可以并行处理
4. **LibreOffice 后台服务**: 如果频繁转换 PDF，考虑启动 LibreOffice 后台服务

## 安全注意事项

1. **输入验证**: report_maker 会验证用户输入
2. **路径安全**: 使用 Path 对象防止路径遍历攻击
3. **权限控制**: reports/ 目录应该有适当的写权限
4. **敏感信息**: 不要在 elements.yaml 中存储敏感信息

## 日志和调试

启用详细日志：

```python
# 在使用 report_maker 时，可以查看详细日志
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 更新和维护

### 更新 skill

```bash
# 拉取最新代码
git pull

# 重新安装依赖
uv pip install --force-reinstall python-docx docxtpl

# 运行测试验证
pytest skills/report_maker/tests/ -v
```

### 备份配置

```bash
# 备份模板目录
cp -r templates/ templates.backup/

# 备份重要报告
cp -r reports/ reports.backup/
```

## 联系支持

如遇到问题：
1. 检查本文档的故障排除部分
2. 运行测试获取详细错误信息
3. 查看 GitHub Issues（如果项目有公开仓库）
