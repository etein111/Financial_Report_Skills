
## 待定内容

暂存无法确定归属的内容，后续逐步消化。

### Agent Skills 能力详解

#### Skills 分类

**数据维护**：Analyst Manager — 从 Excel 提取分析师信息，与 Neolyst 比对，确认差异后自动更新

**报告检查**：

| Skill | 功能 |
|-------|------|
| Report Field Checker | 按报告类型验证必填字段完整性 |
| File Completeness Checker | 验证 Word、Model 等文件齐全 |
| File Similarity Checker | 莱文斯坦距离比对文件名，相似度 < 60% 警告 |
| SFC Signature Validator | 从 SFC 官网查询牌照信息，自动填充 |

**审批流程**：

| Skill | 功能 |
|-------|------|
| Coverage Approval | 检查 Coverage 存在性，处理首次覆盖审批 |
| Chief Approval | 处理首席审批 |
| RQC Approval | 判断 RQC 触发（首次覆盖/评级调整/TP 变动 ≥ 30%） |

**内容生成**：

| Skill | 功能 |
|-------|------|
| Report Title Generator | 按规则自动生成标准标题 |
| Report Extractor | 从 Word 提取摘要和正文 |
| Stock Chart Generator | 从市场数据生成股价走势图和 Volume 柱状图 |
| Report Generator | 填充模板生成完整报告 |

**发布流程**：

| Skill | 功能 |
|-------|------|
| Report Submission | 提交前检查（RQC/Coverage/字段），通过后更新状态 |
| Translation | 报告翻译 |
| Auto Auditor | AI 自动审核合规性 |
| Publish Handler | Word → PDF，发送通知邮件，同步 Wind |
