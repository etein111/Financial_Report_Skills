# 前端视觉一致性规范

用于约束后续功能开发不偏离既有页面视觉基线。该规范基于已落地 change 的共同结论整理：
- `ui-prototype-core-pages`
- `auth-and-users-mvp`
- `region-and-analyst-management`
- 当前 `web/components/ui/*` 与 `web/app/login|desktop|users`

## 1. 适用范围

- 适用于 `web/` 下所有页面与业务组件（`app/*`、`features/*/components/*`）。
- 新功能默认复用现有 UI 基础组件，不允许自行定义第二套视觉系统。
- 偏离本规范的改动，必须先在 OpenSpec proposal 明确说明并获批准。

## 2. 视觉基线（硬约束）

### 2.1 总体风格

- 风格方向固定为：深色、专业、简洁、科技感。
- UI 文案默认英文。
- 不允许按功能模块随意切换为浅色主题或引入冲突色板。

### 2.2 全局背景与文本

- 页面主背景：`linear-gradient(to bottom, #0c1221 0%, #09090b 50%, #020617 100%)`。
- 主文字：`text-zinc-100` / `#fafafa`。
- 次文字：`text-zinc-400`。
- 表单自动填充必须保持深色输入框视觉（禁止出现浏览器默认黄底）。

### 2.3 设计 token（统一）

- 卡片/弹窗圆角：`rounded-[12px]`。
- 输入框圆角：`rounded-[8px]`。
- 按钮圆角：`rounded-[6px]`。
- 默认边框：`border border-white/10`。
- Hover 边框：`border-white/20`。
- 焦点态：`focus-visible:ring-2 focus-visible:ring-blue-500/60`。
- 动画时长基线：`duration-200`。

## 3. 页面级一致性约束

### 3.1 Login 页

- 必须保留粒子背景（`ParticleField`）与居中登录卡片结构。
- 标题/副标题保持：
  - `The Future is Now`
  - `Research Report Management System`
- 登录、忘记密码交互使用统一 `Button` / `Input` / `Modal`。

### 3.2 Desktop 页

- 保持 Desktop-as-Launcher 契约：
  - 功能卡片新标签页打开。
  - 功能页不在页面内实现“返回 Desktop”主导航。
- 保持两组分区结构：`Reports` / `Data Management`。
- Admin-only 能力仅 Admin 可见。

### 3.3 管理列表页（Users / Regions / Analyst Info / 后续同类页面）

- 页面骨架统一：Header + 搜索区 + 列表区 + 分页区。
- 列表操作统一使用 `Modal` / `ConfirmModal` 做创建、编辑、危险操作确认。
- 状态展示统一使用 `Badge`，主操作统一使用 `Button`。

## 4. 组件复用规则（强制）

- 按钮必须复用 `web/components/ui/button.tsx`。
- 输入框必须复用 `web/components/ui/input.tsx`。
- 卡片容器必须复用 `web/components/ui/card.tsx`。
- 弹窗必须复用 `web/components/ui/modal.tsx` / `web/components/ui/confirm-modal.tsx`。
- 分页必须复用 `web/components/ui/pagination.tsx`。
- 业务组件允许加 `className` 微调，但不得改变基础组件的核心视觉 token。

## 5. 禁止项（防视觉漂移）

- 禁止在业务页面直接写与基线冲突的圆角、边框、阴影、按钮色板。
- 禁止新增“平行按钮体系/平行输入框体系/平行弹窗体系”。
- 禁止页面间出现不同主背景体系（例如 A 页渐变、B 页纯浅色）。
- 禁止未评审即引入新的全局字体与全局颜色变量。
- 禁止用临时内联样式覆盖全局交互状态（focus/disabled/error）。

## 6. 开发执行清单（PR 自检）

- 是否复用了 `components/ui` 基础组件，而不是重复造轮子。
- 是否符合统一 token（6/8/12 圆角、white/10 边框、blue focus ring、200ms 过渡）。
- 是否保持了页面骨架一致性（Header/Filter/Table/Pagination）。
- 是否保留了 Desktop-as-Launcher 与权限可见性规则。
- 是否在移动端宽度下保持可读和可操作（按钮、表格、弹窗不破版）。
- 如有偏离，是否在 OpenSpec proposal 记录“偏离原因 + 替代方案 + 回收计划”。

## 7. 变更门禁

- 任何视觉基线调整，必须先更新本规范，再进入实现。
- Code Review 发现视觉漂移时，按 bug 处理，不作为“可接受风格差异”。
