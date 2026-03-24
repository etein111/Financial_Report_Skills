---
name: template-admin
description: 模板配置管家 - 创建、更新、验证报告模板
triggers:
  - command: "设为{type}报告模板"
    action: create_template
  - command: "更新模板"
    action: update_template
  - command: "验证模板"
    action: validate_template
dependencies:
  - skill: rule-manager
inputs:
  - name: word_file
    type: file
    required: true
  - name: elements_file
    type: file
    required: false
  - name: report_type
    type: string
    required: true
outputs:
  - name: success
    type: boolean
  - name: placeholders
    type: array
  - name: message
    type: string
---

## 功能说明

### 创建模板 (create_template)
1. 解析 Word 文档结构
2. 识别动态内容区域
3. 生成带占位符的模板
4. 执行闭环验证
5. 保存到 templates/{type}/

### 更新模板 (update_template)
1. 解析新上传的 Word
2. 识别新增/删除的占位符
3. 更新模板文件
4. 同步更新 schema.yaml (如有必要)

### 验证模板 (validate_template)
1. 用 elements.yaml 重新渲染
2. 比对原文件
3. 报告差异
