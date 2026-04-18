# Report Maker 自动化回归测试

本目录包含 `report_maker` skill 的自动化回归测试。

---

## 使用方式

### 方式一：直接运行脚本（推荐）

```bash
cd D:/yechuan/work/Finance_AI/neoskills
python skills/report_maker/test_automation/scripts/run_e2e_test.py
```

### 方式二：通过 CC 提示词

1. CC 读取 `TEST_PROMPT.md`
2. CC 按照提示词中的步骤执行测试
3. 测试完成后 CC 输出验证报告

---

## 目录结构

```
test_automation/
├── TEST_PROMPT.md               # CC 读取的提示词（含完整步骤）
├── README.md                    # 本文件
├── scripts/
│   ├── run_e2e_test.py          # 独立运行脚本（主入口）
│   └── extract_test_values.py   # 提取预期值工具
└── test_env/
    └── expected/                # 预期值对照
```

---

## 测试用例：威胜控股公司覆盖报告

| 项目 | 值 |
|------|-----|
| 草稿 | `inbox/samples/company/0402威胜控股（3393.HK）首次覆盖：配网投资与AI算力双轮驱动，能源计量龙头再启航.docx` |
| 报告类型 | `company` |
| ticker | `3393.HK` |
| 评级 | `跑赢大市` |
| 目标价 | `40.94` |

### 预期输出特征

| 内容 | 预期值 |
|------|--------|
| abstract 字符数 | ~832 |
| abstract 段落数 | 8 |
| body 段落数 | 272 |
| body 表格数 | 26 |
| english_summary 段落数 | 19 |
| 最终报告段落数 | 270-290 |
| 最终报告表格数 | 26-30 |

---

## 验证标准

测试通过需满足：
1. ✅ 第一阶段成功提取 abstract/body/english_summary
2. ✅ elements.yaml 字段正确
3. ✅ 第二阶段渲染成功
4. ✅ 最终报告无 `{{}}` 占位符残留
5. ✅ 段落/表格数量在预期范围内

---

## 输出位置

测试输出统一写入：`reports/test_output/`

最终报告：`reports/test_output/test_report_output.docx`
