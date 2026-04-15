
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

### neoskill

* 独立 Skills 架构：每个 Skill 保持单一职责，通过事件和消息解耦.
* 自然语言编排流程 ：支持串行、并行、条件分支等执行模式
* 自然语言配置：通过自然语言对话修改配置文件。

#### report_maker skill

* 模板机制。过自然语言或 YAML 配置即可新增模板或提取字段

#### neolyst skill

* 一致性逻辑下沉到 Supabase：业务数据一致性、状态流转、关系维护通过Skills接口执行.

### neospace

* neopace通过独立可编排的Skills 实现报告的自动化编辑与审核等工作。
* 工作台仓库，Skills 的运行载体，负责人机协作，session流对接。

## 代码库划分

### neolyst

* neolyst-web，主要用于应对监管合规检查。

### neoport

* 外部发布系统仓库。
* neoport-web
* neoport-db
* Publish Worker 进程。

### neoskills
  
* neolyst-db数据库：唯一事实源，所有数据库实例以此为准。
* 各种skills：neolyst，report_maker, template_maker, compliance.

### neospace

* neospace。