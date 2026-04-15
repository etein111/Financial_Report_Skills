# 分析师投研报告平台 NeoPlatform Overview

# 目标与价值

## 价值

* AI驱动研究生产力的质变。
  目标是将99%的工作交给AI自动化，自动化程度不够没有意义。
* 人从"操作者"转向"监督者"。
  通过渐进式自动化，。人工角色不再是排版和对数的工人，而是规则的制定者、生产过程的监督者与最终结果的确认者。

## 目标

* 自动化生产报告
  初期通过AI自动化报告规范性编辑，后期分析师观点驱动AI生产报告。
* 业务主导的自我进化
  Editor和SA通过自然语言与AI对话，自动沉淀业务经验。无需研发介入即可持续优化自动编辑和审核逻辑，使系统能力随业务经验持续增长。
* 合规风险自动拦截
  将合规检查（SFC 牌照、Stock List、利益披露、评级变动等）通过机器初筛与高亮提示，大幅降低人为疏漏风险。

# 业务

## 业务角色

* 分析师（Analyst）
  在微信里发送草稿和指令给编辑，后期直接与 AI Agent 协作。
* 合规人员（SA）
  在工作台查看系统初筛结果，完成审批和发布。
* 编辑（Editor）
  通过工作台与AI写作前期负责手动操作和教系统规则，后期负责维护系统和处理异常。
  初期平台没有设置这个角色，只有一个编辑，用SA的身份操作。
  后面进展快的话可以一步到位，直接过渡到分析师直接接入AI工作台自助工作，编辑只是AI的监督者，可能不需要这个角色。
* 系统管理员 (Admin)
  拥有所有平台权限，包括管理用户权限、行业分类等基础设置等。
* 买方机构（Customer）
  在外部发布系统查看报告。

## 核心工作流(todo)

### 报告编辑(todo)

1. 任务接收
   分析师通过微信发送草稿与指令。
2. AI 预处理
   AI自动解析并生成报告保存在neolyst-db，Editor核对修改。
3. 确认入库
   Editor处理好报告，会自动在neolyst-db，状态标记为"待审核"。

### 审批发布(todo)

1. 自动初筛
   SA 登录工作台调用审核功能，系统高亮合规风险点。
2. 人工决断
   SA 确认后下达发布指令。
3. 异步发布
   系统修改 neolyst-db 状态为"已发布"，独立进程侦测后自动同步至 neoport-db。

# 产品设计原则

AI Native(todo)

## 渐进式自动化

* 人机协作
  AI自动处理标编辑与合规工作；AI处理不好的特例由人工兜底。
* 借助AI固化经验
  人工在兜底处理后，可通过对话将经验教给AI，转化为新的自动化规则（Skills），逐渐沉淀经验，提高自动化率。

## Skill为载体（todo）

  以skill为载体封装流程和规则
  按业务工作尽量拆成相互独立而内聚的skill
  灵活部署在任何Agent里

## AI自主学习（todo）

# 平台架构

## 子系统

* 企业微信前台
  面向分析师的协作入口，前台Agent负责
* Editor 工作台
  Eitor与AI协作生产。自动根据模板生成报告，写入 neolyst-db。
* SA 工作台
  SA与AI写作审核。执行合规检查，确认后发布neolyst-db中的报告。
* Neolyst-db
  内部核心数据库。存所有人员、权限、报告和审计信息。
* Neoport-db
  外部数据库。只存发给客户看的最终版报告供客户查阅，以及其他客户服务数据。
* 独立发布进程
  搬运工。自动把neolyst-db中的已发布报告传送到neoport-db。
* Neolyst- web
  内部网站，主要用于审计和辅助手工操作。
* Neoport-web
  外部网站，Custumer Portal,为客户提供查阅报告等服务。

## 子系统关系

```
 [SA]              [分析师]
   |                  |
   |                  v
   |             [企业微信前台]
   |                  |
   v                  v
[SA工作台]    [Editor工作台]
   |                  |
   |                  v
   +---------->[Neolyst-db]  ------> [Neolyst-web]
                     |
                     v
               [Neoport-db] ---------> [Neoport-web]
```

## 架构原则

### 内外分离

* 内部用户和外部用户分别管理。
* 内部数据和外部数据严格分离。
* 外部系统依赖内部系统，严禁反向依赖。

### 统一身份认证与权限

* 内部人员身份认证和权限统一由neolyst-db管理。
  不管使用网站还是工作台，都统一由neolyst-db来做身份验证和权限控制。
* 外部人员身份认证和权限统一由neoreport-db管理。

## 子系统

### neolyst-db

* Supabase Auth 承担认证、数据访问与数据权限兜底。
* Supabase PostgREST + RLS
* Supabase Storage（模板/报告文件）


## 代码库划分

### neolyst

* 含 neolyst-web 代码，主要用于应对监管合规检查。

### neoport

* 外部发布系统仓库。含 neoport-web、neoport-db 及 Publish Worker 进程。

### neoskills
  
* neolyst-db数据库唯一事实源。
* 各种skills：neolyst，report_maker, template_maker, compliance.

### neospace

* 工作台仓库。Skills 的运行载体，负责人机协作，session流对接。

# Plan

## Roadmap

### Phase1：业务启动 (MVP)

* 目标
  替换现有xn系统，先解决编辑排版工作量最大的问题。
* 做法
  开发neolyst-db，neolyst-web和几个skill：neolyst,report_maker, template_maker,compliance。
  用opencode充当临时工作台，挂载skills。
  Editor与AI工作台对话对话调用report_maker skill完成要素提取，用模板自动生成报告，自动提交报告。
  SA与工作台对话调用compliance skill，自动审核，手动批准发布。
  报告处理还是以Word格式为中心，保留word片段进行拼装与检查。

### Phase2：工作台成型

* 目标
  分析师通过微信把报告发给工作台，AI直接与分析师对话半自助处理报告，编辑补位，逐步完善自动化。
* 做法
  自研AI工作台neospace，分析师接入微信，微信机器人Agent转发工作session给AI工作台。
  AI工作台AI自动处理为主，人工补位为辅。
  报告处理以markdown格式为中心，标准化报告生产，降低报告排版的难度。
  平台以markdown格式为基础，有利于AI Native。
  
### Phase3：AI助理

* 目标
  分析师提观点，AI助理自动生成报告。
* 做法
  建立分析师AI记忆系统，沉淀分析师的经验与思考体系。
  建立金融数据库和知识库。
  AI基于这些基础设施，从分析师观点出发自动产生报告。
