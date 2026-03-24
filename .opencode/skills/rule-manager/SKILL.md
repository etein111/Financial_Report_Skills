---
name: rule-manager
description: 规则管理器 - 对话式更新提取规则
triggers:
  - command: "增加{field}字段"
    action: add_field
  - command: "修改{field}字段"
    action: modify_field
  - command: "删除{field}字段"
    action: delete_field
dependencies: []
inputs:
  - name: feedback
    type: string
    required: true
  - name: report_type
    type: string
    required: true
outputs:
  - name: updated
    type: boolean
  - name: changes
    type: array
  - name: template_prompt
    type: string
---

## 功能说明

### 增加字段 (add_field)
1. 解析反馈中的字段名
2. 在 schema.yaml 中添加字段定义
3. 生成模板更新提示

### 修改字段 (modify_field)
1. 解析反馈中的修改内容
2. 更新 schema.yaml
3. 生成模板更新提示

### 删除字段 (delete_field)
1. 从 schema.yaml 中移除字段
2. 记录变更
