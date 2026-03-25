# report_maker 使用指南

## 概述

`report_maker` 是一个 Claude Code skill，用于处理分析师报告草稿并生成标准排版报告。

**核心能力**：
- 自动从 Word 草稿中提取结构化要素（如股票代码、公司名、评级、目标价等）
- 交互式确认提取结果，支持修正
- 基于模板自动渲染生成标准格式的 Word 和 PDF 报告

**原则**：
- **只写 reports/，不写 templates/** - report_maker 只处理报告，不修改模板
- **两阶段流程** - 先抽取确认，后渲染输出

---

## 使用场景

### 场景 1：处理新草稿

**适用情况**：分析师上传了一份新的报告草稿，需要生成标准排版报告。

**操作步骤**：

1. 上传草稿文件到工作目录
2. 告诉 Claude："这份草稿是 [报告类型] 报告，帮我处理"

**示例对话**：
```
你：我上传了一份公司报告草稿，报告类型是 company，帮我处理

Claude：好的，我来处理这份公司报告草稿。

[处理过程...]

报告类型: company
模板: company

提取的关键要素：
- ticker: 2507.HK
- company: 西锐飞机
- rating: OUTPERFORM
target_price: 86.72

请检查以上信息是否正确，如有错误请告诉我。
```

### 场景 2：修正提取的字段

**适用情况**：自动提取的结果有误，需要修正。

**操作步骤**：
直接告诉 Claude 哪个字段错了，应该是什么值。

**示例对话**：
```
你：ticker 应该是 700 HK，不是 2507.HK

Claude：好的，已更新 ticker 为 700 HK

其他字段保持不变，继续吗？
```

### 场景 3：生成最终报告

**适用情况**：要素确认无误，准备生成标准报告。

**操作步骤**：
告诉 Claude 确认并生成。

**示例对话**：
```
你：确认，继续生成

Claude：好的，开始渲染模板...

[渲染过程...]

✓ 报告生成成功！
- output.docx: reports/西锐飞机首次覆盖报告/output.docx
- output.pdf: reports/西锐飞机首次覆盖报告/output.pdf
```

---

## 支持的报告类型

| 报告类型 | 说明 | 使用的模板 |
|---------|------|------------|
| `company` | 公司覆盖报告（首次覆盖、深度分析等） | company |
| `sector` | 行业研究报告 | sector |
| `macro` | 宏观报告 | common |
| `strategy` | 策略报告 | common |
| `quantitative` | 量化报告 | common |
| `bond` | 债券报告 | common |
| `company_flash` | 公司快讯报告 | company_flash |
| `sector_flash` | 行业快讯报告 | sector_flash |

**注意**：
- 报告类型使用小写
- 如果指定了未定义的报告类型，会提示创建模板
- 多个报告类型可以共用一个模板（如 macro、strategy、quantitative、bond 都用 common）

---

## 目录结构

处理后的报告保存在 `reports/<report_name>/` 目录下：

```
reports/<report_name>/
├── draft.docx           # 原始草稿
├── elements.yaml        # 提取的要素（与 schema 一致）
├── abstract.docx        # 摘要片段
├── body.docx            # 正文片段
├── output.docx          # 最终 Word
└── output.pdf           # 最终 PDF
```

**文件说明**：
- **draft.docx** - 原始草稿的副本
- **elements.yaml** - 提取的所有字段，必须与 schema.yaml 严格一致
- **abstract.docx** - 从草稿中提取的摘要部分（Word 片段）
- **body.docx** - 从草稿中提取的正文部分（Word 片段）
- **output.docx** - 渲染后的标准格式报告
- **output.pdf** - 发布用的 PDF 版本

---

## 详细使用示例

### 示例 1：完整的报告处理流程

**步骤 1：上传并指定类型**

```
你：上传 draft.docx，这是一份公司报告

Claude：收到。请问报告类型是什么？
  可选：company, sector, macro, strategy, quantitative, bond

你：company
```

**步骤 2：自动提取要素**

```
Claude：正在提取要素...

提取结果：
- ticker: 2507.HK
- company: 西锐飞机
- rating: OUTPERFORM
- target_price: 86.72
- title: 首次覆盖：安全...
- a1_cn: 杨斌
- a1_email: harryyang@hfisec.com.hk
  ...（共 46 个字段）

请检查以上信息，如有错误请告诉我修正，或输入"确认"继续。
```

**步骤 3：确认并生成**

```
你：确认

Claude：好的，开始渲染...

✓ 报告生成成功！
- 位置：reports/西锐飞机首次覆盖报告/
- 文件：output.docx, output.pdf
```

### 示例 2：修正多个字段

```
你：ticker 改成 700 HK，rating 改成 HOLD

Claude：已更新：
- ticker: 700 HK ✓
- rating: HOLD ✓

确认生成吗？
```

### 示例 3：切换模板

```
你：这份报告应该用 common 模板

Claude：好的，切换到 common 模板...

注意：模板切换只能在确认阶段进行。
```

---

## 常见问题

### Q1：如何指定报告类型？

**A**：在对话中明确说明，例如：
- "这是一份公司报告"
- "报告类型是 sector"
- "macro 报告草稿"

### Q2：如何修正提取的字段？

**A**：直接告诉 Claude 需要修正的字段，例如：
- "ticker 应该是 700 HK"
- "rating 改成 HOLD"
- "target_price 改为 100"

### Q3：有些字段提取不到怎么办？

**A**：有两种方式：
1. 留空 - 直接回车，字段值将为空字符串
2. 补充 - 告诉 Claude 正确的值，例如：
  - "investment_thesis 是：公司具有强大的市场地位"

### Q4：可以跳过确认直接生成吗？

**A**：不建议。两阶段流程的关键就是人工确认环节，确保数据准确后再渲染。

### Q5：生成的报告在哪里？

**A**：保存在 `reports/<报告名>/` 目录下，包括：
- output.docx - Word 版本
- output.pdf - PDF 版本

### Q6：PDF 转换失败怎么办？

**A**：这通常是因为 LibreOffice 未安装。你可以：
1. 安装 LibreOffice
2. 或者只使用 output.docx

---

## 与 template_maker 的配合

`report_maker` 和 `template_maker` 是两个独立的 skills：

| 功能 | report_maker | template_maker |
|------|------------|---------------|
| **用途** | 处理报告 | 创建/维护模板 |
| **写权限** | 只写 reports/ | 只写 templates/ |
| **使用时机** | 日常报告处理 | 模板初始化/修改 |

**典型工作流**：

1. **初始阶段**（使用 template_maker）：
   ```
   创建 company 模板
   定义 schema.yaml
   创建 template.docx
   ```

2. **日常使用**（使用 report_maker）：
   ```
   上传草稿 → 提取要素 → 确认 → 生成报告
   ```

3. **模板维护**（使用 template_maker）：
   ```
   需要新增字段？告诉 template_maker
   需要调整模板？告诉 template_maker
   ```

---

## 最佳实践

### 1. 命名规范

报告名称会自动规范化：
- 去除常见前缀：`draft_`、`草稿_`、`final_`、`v2_` 等
- 去除常见后缀：`_draft`、`_final`、`_v2` 等
- 保留业务名称：`西锐飞机首次覆盖报告`

### 2. 批量处理

如果需要处理多份报告，建议：
- 每份报告独立处理，确保质量
- 使用相同的模板保证一致性

### 3. 质量控制

- **第一阶段必须确认** - 不要跳过
- **检查关键字段** - ticker、rating、target_price、analysts 等
- **验证输出** - 打开 output.docx 检查格式

---

## 错误处理

### 错误 1：报告类型未定义

**症状**：系统提示"报告类型未找到"

**解决方案**：
1. 检查 `templates/router.yaml` 配置
2. 使用 template_maker 创建对应模板
3. 或使用已存在的报告类型

### 错误 2：模板文件缺失

**症状**：系统提示"模板文件不存在"

**解决方案**：
1. 检查 `templates/<template_name>/template.docx` 是否存在
2. 使用 template_maker 重新生成模板

### 错误 3：要素提取失败

**症状**：系统提示"提取失败"

**解决方案**：
1. 检查草稿文件格式是否为 .docx
2. 检查草稿文件是否损坏
3. 尝试重新上传草稿

---

## 技巧和建议

### 技巧 1：提前准备

在处理报告前，建议：
- 确认报告类型正确
- 准备好草稿文件（格式正确）
- 了解该报告类型的字段定义

### 技巧 2：分批确认

如果字段很多（40+ 个），建议：
- 先确认关键字段（ticker、rating、target_price）
- 再确认其他字段
- 最后一次性确认

### 技巧 3：保存中间结果

每份报告处理完后，建议：
- 保存 `elements.yaml` 作为记录
- 保存 `output.docx` 和 `output.pdf` 作为发布版本
- 保留 `draft.docx` 作为原始记录

---

## 更新日志

**v1.0** (2026-03-26)
- 初始版本
- 支持基本的报告处理流程
- 支持 8 种报告类型
- 两阶段流程（抽取确认 → 渲染输出）
