# Session Notes

## 1. 本次会话目标

本次会话主要完成了三件事：

1. 安装并启用 `superpowers` skills。
2. 基于项目背景文档，对 `neoskills` 的 report 类 skills 进行头脑风暴和边界收敛。
3. 将已经确认的结论同步回文档，形成后续新 session 可直接承接的设计上下文。

## 2. 已完成的环境操作

### 2.1 superpowers 安装

已按上游安装说明完成：

- 克隆仓库到 `/home/jjh/.codex/superpowers`
- 创建符号链接 `/home/jjh/.agents/skills/superpowers -> /home/jjh/.codex/superpowers/skills`

说明：

- 该步骤已验证成功。
- 如需在新 session 中使用相关 skills，通常重启 Codex CLI 后即可重新发现。

## 3. 本次阅读和参考的文档

本次主要基于以下文档进行讨论：

- `/mnt/c/_code/neoskills/docs/platform.md`
- `/mnt/c/_code/neoskills/docs/skills-report.md`
- `/mnt/c/_code/neoskills/docs/workbench-req.md`
- `/mnt/c/_code/neoskills/docs/README.md`

其中：

- `platform.md` 用于理解完整平台背景、角色、架构和阶段规划。
- `workbench-req.md` 用于理解工作台承接的能力范围。
- `skills-report.md` 是当前最核心的需求与设计主文档。

## 4. 已确认的核心定位

### 4.1 neoskills 的定位

`neoskills` 不是完整工作台，而是工作台中的业务能力集合。

它主要承载：

- 模板制作与维护能力
- 报告草稿解析能力
- 报告要素提取能力
- 标准报告生成能力

工作台本身：

- 第一阶段由 `opencode` 临时承担
- 后续由 `neospace` 承接

### 4.2 当前 MVP 的重心

MVP 重点不是完整自动化流水线，而是：

- 让 Editor 通过与 Agent 对话维护模板和提取规则
- 跑通“草稿 -> 抽取 -> 人工确认 -> 标准报告生成”的最小闭环

明确的优先级判断是：

- 优先保证模板维护和报告生产闭环可用
- 暂时不追求过度抽象
- 暂时不为未来复杂度提前设计大量中间层

## 5. 已确认的模板维护策略

### 5.1 模板维护方式

模板维护采用：

- 纯对话交互
- 默认先预览后确认
- 若用户明确要求“直接应用”，则允许跳过确认

业务侧不需要：

- 手工修改中间 DSL
- 手工维护复杂结构定义
- 手工在本地编辑模板后再回传

系统负责：

- 修改 `schema.yaml`
- 修改 `template.docx`
- 更新必要的模板元数据

### 5.2 关于中间表示的结论

本次讨论过是否引入“中间表示”或独立模板 DSL，最终结论是不采用。

原因：

- 当前模板复杂度不高
- 模板制作频率低
- 实际操作者是 Editor，而不是大量非技术业务人员同时维护
- 当前阶段优先简化系统设计

因此，当前方向为：

- 直接维护正式模板资产
- 不额外引入需要业务理解的新抽象层

### 5.3 模板定位方式

模板修改时，系统支持两类定位方式：

- 语义锚点
  例如“插到免责声明前”“放在投资要点后”
- 结构定位
  例如“放到第 3 个二级标题下”

最终结论是二者都支持，但当前阶段不为此引入额外复杂目录或中间模型。

## 6. 已确认的目录结构

### 6.1 最终采用的顶层结构

本次反复讨论后，最终收敛为：

```text
/skills/
/templates/
/reports/
```

不采用的目录概念：

- `workspace/`
- `templates-workspace/`
- `jobs/`
- `versions/`

原因：

- 这些概念在第一版会明显增加结构复杂度
- 当前模板修改频率低
- 当前无需保留模板修改历史
- 当前无需按任务系统组织模板修改过程

### 6.2 各目录职责

#### `skills/`

只存放符合 Agent Skills Open Standard 的 skills 插件。

不存放：

- 正式模板
- 运行态数据
- 报告产物

#### `templates/`

存放正式模板资产，是系统认可的“模板真相”。

#### `reports/`

按每篇报告组织处理现场和产物，便于 Editor 检查。

### 6.3 `templates/` 的组织方式

第一层按“模板名”组织，而不是按报告类型、业务线或团队组织。

示意：

```text
/templates/
  router.yaml
  /common/
    schema.yaml
    template.docx
    meta.yaml
```

关于命名的结论：

- 不强行引入技术化的 `template_id` 术语
- 业务上主要仍按“报告类型”理解
- 但底层允许多个报告类型映射到同一个模板
- 例如 `macro`、`quant` 可以共用 `common`

### 6.4 `router.yaml` 的定位

`router.yaml` 负责：

- 报告类型到模板名的静态映射

明确不做：

- 关键词路由
- 作者路由
- 语言路由
- 复杂优先级匹配

也就是说，第一版只支持静态映射。

### 6.5 `reports/` 的组织方式

`reports/` 下按报告名建目录，而不是按 job_id 建目录。

理由：

- Editor 关心的是“哪篇报告”
- 人工检查和查找时，按报告名更自然
- 当前无需引入任务系统抽象

目录名应尽量规整：

- 去掉无用前缀
- 去掉无用后缀
- 保留足够可识别的业务名称

### 6.6 `reports/<report_name>/` 的文件结构

已确认第一版采用如下结构：

```text
/reports/
  /<report_name>/
    draft.docx
    elements.yaml
    abstract.docx
    body.docx
    assets/
    output.docx
    output.pdf
    meta.yaml
```

含义：

- `draft.docx`：原始草稿
- `elements.yaml`：结构化要素
- `abstract.docx`：摘要 Word 片段
- `body.docx`：正文 Word 片段
- `assets/`：图表、截图、复杂表格裁剪结果等
- `output.docx`：标准输出 Word
- `output.pdf`：标准输出 PDF
- `meta.yaml`：该报告的基础元数据

## 7. 已确认的文档处理路线

### 7.1 第一版不采用 Markdown 中间层

这是本次非常重要的结论之一。

最终决定：

- 第一版不将 `abstract` 和 `body` 转成 Markdown
- 而是直接保留为可打开的 Word 片段文件

原因：

- `Word -> Markdown` 转换问题多
- 样式和结构容易丢失
- 图表、表格、复杂内容在 Markdown 中表达困难
- 后续再从 Markdown 拼回标准 Word 也很麻烦

因此第一版路线是：

- 直接从草稿抽出 `abstract.docx`
- 直接从草稿抽出 `body.docx`
- 最终通过模板和 Word 片段拼装生成标准 Word

### 7.2 Word 片段的要求

`abstract.docx` 和 `body.docx` 应该是：

- 完整可打开的独立 Word 文件
- 便于 Editor 直接检查

而不是仅供程序消费的内部片段格式。

## 8. 两个 skills 的边界与职责

### 8.1 划分原则

两个 skills 的边界最终按“写权限边界”划分，而不是按模糊的功能感受划分。

这条原则已确认。

### 8.2 `template-maker`

`template-maker` 只负责写 `templates/`。

职责包括：

- 创建模板
- 维护 `template.docx`
- 维护 `schema.yaml`
- 维护模板 `meta.yaml`
- 维护 `router.yaml`
- 在模板修改后执行一次最小渲染验证

不负责：

- 处理单篇报告
- 写 `reports/`
- 管理报告中间产物

### 8.3 `report-maker`

`report-maker` 只负责写 `reports/`。

职责包括：

- 接收草稿
- 识别报告类型
- 根据 `router.yaml` 选择模板
- 创建 `reports/<report_name>/`
- 抽取 `elements.yaml`
- 生成 `abstract.docx`
- 生成 `body.docx`
- 提取 `assets/`
- 接受 Editor 的修正与补充
- 渲染 `output.docx`
- 渲染 `output.pdf`
- 更新报告自己的 `meta.yaml`

不负责：

- 修改正式模板
- 修改 `schema.yaml`
- 修改 `router.yaml`
- 修改模板目录下的正式资产

### 8.4 抽取能力归属

讨论过是否为“从草稿中抽取 elements/摘要/正文”单独再建一个第三 skill。

最终结论是：

- 第一版不新增第三个 skill
- 该能力归属 `report-maker`

原因：

- 从业务视角看，这仍然是“处理一篇报告”的同一个动作
- 如果拆成第三个 skill，会增加使用复杂度
- 会让 `reports/` 的写边界分裂
- 第一版应保持结构最简

## 9. `report-maker` 的流程设计

### 9.1 两阶段流程

`report-maker` 明确采用两阶段流程：

#### 第一阶段：抽取与确认

负责：

- 接收草稿
- 识别报告类型
- 路由模板
- 抽取要素
- 生成 `elements.yaml`
- 生成 `abstract.docx`
- 生成 `body.docx`
- 生成 `assets/`
- 生成供 Editor 检查的结果摘要

然后暂停，等待 Editor 确认和修正。

#### 第二阶段：渲染与输出

在确认完成后继续：

- 更新已修正的数据或片段
- 调用模板渲染
- 生成 `output.docx`
- 转换 `output.pdf`
- 更新报告 `meta.yaml`

### 9.2 模板切换规则

这一点已明确确认：

- 只允许在确认阶段切换模板
- 一旦进入最终渲染阶段，不再支持切换模板

换句话说：

- 可在第一阶段改模板
- 不在第二阶段改模板

## 10. 关于交互方式的结论

对于两个 skill 的对外使用方式，最终倾向为：

- 每个 skill 作为一个主 skill 存在
- 依靠自然语言理解当前操作意图
- 不额外拆成多个显式命令入口

即：

- `template-maker` 自己理解“创建模板 / 改字段 / 改模板 / 改路由”
- `report-maker` 自己理解“抽取 / 修正 / 继续生成”

原因：

- 更符合业务使用心智
- 减少技能入口复杂度

## 11. 已更新的文档

本次会话中，已经将主要结论同步到以下文档：

- `/mnt/c/_code/neoskills/docs/platform.md`
- `/mnt/c/_code/neoskills/docs/skills-report.md`

另外新增了：

- `/mnt/c/_code/neoskills/SESSION_PROMPT.md`
- `/mnt/c/_code/neoskills/SESSION_NOTES.md`

## 12. 当前文档状态判断

`skills-report.md` 现在已经可以作为后续新 session 的主上下文文档。

如果重新开 session，建议读取顺序为：

1. `docs/skills-report.md`
2. `docs/platform.md`
3. `docs/workbench-req.md`

其中：

- `skills-report.md` 为主文档
- 另外两份为背景补充

## 13. 尚未展开但已预留的后续话题

后续仍需继续讨论但本次尚未展开到细节的内容包括：

1. `router.yaml` 的字段设计
2. `schema.yaml` 的字段设计
3. 模板 `meta.yaml` 的字段设计
4. 报告 `meta.yaml` 的字段设计
5. `template-maker` 和 `report-maker` 的 `SKILL.md` 具体写法
6. 抽取、渲染、验证流程在实现层面的脚本拆分方式

## 14. 推荐的新 Session 提示方式

如果开启新 session，建议使用根目录的：

- `/mnt/c/_code/neoskills/SESSION_PROMPT.md`

该文件已写好可直接复用的提示词模板。

## 15. 总结

本次会话已经完成的最关键工作不是代码实现，而是把第一版设计边界收紧并写清楚。尤其是以下几点已经基本定稿：

- 顶层目录只保留 `skills/`、`templates/`、`reports/`
- 第一版不引入 `workspace/jobs/versions`
- `templates/` 按模板名组织
- `reports/` 按报告名组织
- 第一版不采用 Markdown 中间层
- 抽取能力并入 `report-maker`
- `template-maker` 只写模板资产，`report-maker` 只写报告产物
- `report-maker` 采用“抽取确认 -> 渲染输出”的两阶段流程

这套结论已经足以支持下一轮继续细化 YAML 结构或开始编写实际 skills 文档。
