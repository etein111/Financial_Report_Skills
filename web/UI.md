# UI 组件规范

> 约定 UI 组件的命名、结构、样式、可访问性及交互模式。
>
> 分层、依赖方向、触库规约（例如 `app → features → domain`、仅 `features/*/repo/*` 可触库）以 `LOGIC.md` 为准；本文不重复定义这些架构规则，避免两份文档漂移。
>
> 参考来源：
> - [React & TypeScript: 10 patterns for writing better code](https://blog.logrocket.com/react-typescript-10-patterns-writing-better-code/)
> - [React with TypeScript: Best Practices](https://www.sitepoint.com/react-with-typescript-best-practices/)
> - [Tailwind CSS Best Practices](https://dev.to/theodorusclarence/styling-best-practices-i-use-with-tailwindcss-mf0)

## 1. 命名规范

以下为推荐约定，优先保持一致性；确有必要时允许按语义选用更贴切的动词（例如 `open*`、`submit*`、`on*`、`handle*`）。

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件名 | PascalCase | `Button`, `UserProfile` |
| 文件名 | kebab-case | `button.tsx`, `user-profile.tsx` |
| Props 类型 | PascalCase + Props | `ButtonProps`, `ModalProps` |
| 变体类型 | PascalCase，语义化 | `ButtonVariant`, `BadgeTone` |
| 事件处理函数 | `handle/on/open/submit` + 动词 | `handleSubmit`, `onClose`, `openInvite` |
| 常量 | UPPER_SNAKE_CASE | `PAGE_SIZE`, `DEFAULT_TIMEOUT` |

## 2. 组件结构

### 2.1 文件内顺序

```typescript
// 1. "use client" 指令（如需要）
"use client";

// 2. 导入（React 在前，第三方在后，本地最后）
import * as React from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/cn";

// 3. 类型定义
export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  isLoading?: boolean;
};

// 4. 主组件
export function Button({
  className,
  variant = "primary",
  isLoading = false,
  ...props
}: ButtonProps) {
  // ...
}

// 5. 子组件（仅当被主组件独占使用时）
function Spinner() {
  // ...
}
```

### 2.2 单一职责

- 默认一个文件一个主组件（便于定位与 review）
- 子组件仅当被主组件独占使用时可放在同文件
- 可复用的子组件建议拆分为独立文件；原型/快速迭代期允许例外，但应避免在 `components/ui` 里堆砌杂物

```typescript
// ✅ 推荐：独立文件
// components/ui/pagination.tsx
export function Pagination() { ... }

// ❌ 避免：多个可复用组件在同一文件
// components/ui/misc.tsx
export function Pagination() { ... }
export function ConfirmModal() { ... }
```

### 2.3 Props 定义

Props 类型不做“必须 interface / 必须 type”的硬性规定，保持简单一致：
- **默认用 `type`**（更符合联合类型、组合类型的使用习惯）
- 需要 `extends`/声明合并时再用 `interface`

```typescript
// ✅ 推荐：默认用 type
export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

// ✅ 需要 extends/声明合并时可用 interface
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
```

**使用 discriminated unions 处理互斥 props**：

```typescript
// ✅ 推荐：discriminated union
type ButtonProps = {
  variant: "primary";
  primaryColor?: string;
} | {
  variant: "secondary";
  secondaryStyle?: "outline" | "solid";
};
```

**导出 Props 类型**（便于其他组件复用）：

```typescript
// ✅ 推荐：导出 Props
export type ButtonProps = { /* ... */ };
export type ButtonVariant = ...;
```

### 2.4 forwardRef 规范

```typescript
export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, ...props }, ref) => {
    return <input ref={ref} ... />;
  }
);

Input.displayName = "Input"; // 必须！便于调试
```

## 3. 样式规范

### 3.1 基本原则

- 使用 Tailwind CSS utility classes
- class 合并统一使用 `cn()` 工具函数
- UI 组件应支持 `className` 覆盖（尤其是 `components/ui/*`）
- 尽量避免使用 `@apply`（优先组件抽象）

```typescript
// ✅ 推荐：组件抽象
export function Button({ className, variant = "primary", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        // 1. 基础样式
        "inline-flex items-center justify-center rounded-[6px] px-4 py-2",
        // 2. 变体样式
        variant === "primary" && "bg-blue-600 text-white hover:bg-blue-700",
        variant === "secondary" && "bg-zinc-800 text-zinc-100 hover:bg-zinc-700",
        // 3. className 放最后，允许覆盖
        className,
      )}
      {...props}
    />
  );
}

// ❌ 避免：@apply
// .btn-primary { @apply bg-blue-600 text-white; }
```

### 3.2 类名组织顺序

以下为推荐组织顺序，非强制；以可读性与 diff 友好为先。

```typescript
className={cn(
  // 1. 布局（display, position）
  "inline-flex items-center justify-center",
  // 2. 尺寸（width, height, padding, margin）
  "w-full px-4 py-2",
  // 3. 边框与圆角
  "rounded-[6px] border border-white/10",
  // 4. 背景
  "bg-zinc-900",
  // 5. 文字
  "text-sm text-zinc-100",
  // 6. 效果（shadow, opacity, transition）
  "shadow-lg transition-colors duration-200",
  // 7. 状态（hover, focus, disabled）
  "hover:bg-zinc-700 focus:ring-2 focus:ring-blue-500",
  // 8. 条件样式
  isDisabled && "cursor-not-allowed opacity-50",
  // 9. 外部传入（放最后）
  className,
)}
```

### 3.3 间距处理

**优先考虑使用 `space-*`**（保持可读性，不为规则强行重构）：

```typescript
// ✅ 推荐：space-y
<div className="space-y-4">
  <p>Item 1</p>
  <p>Item 2</p>
  <p>Item 3</p>
</div>

// ❌ 避免：重复 margin
<div>
  <p className="mb-4">Item 1</p>
  <p className="mb-4">Item 2</p>
  <p className="mb-4">Item 3</p>
</div>
```

### 3.4 设计 Token

| 元素 | 约定 |
|------|------|
| 圆角 | 按钮 `rounded-[6px]`；输入框 `rounded-[8px]`；卡片/弹窗 `rounded-[12px]` |
| 边框 | `border border-white/10`（10% 白色透明） |
| 背景 | 主背景 `bg-zinc-900`；悬停 `hover:bg-zinc-700` |
| 文字 | 主文字 `text-zinc-100`；次要 `text-zinc-400` |
| 过渡 | `transition-colors duration-200`（200ms） |
| 焦点 | `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60` |

## 4. 可访问性

本节是建议基线。现有原型组件可能未完全覆盖（例如 `aria-busy`），后续逐步补齐即可。

| 元素 | 约定 | 示例 |
|------|------|------|
| 按钮 | 可点击区域尽量 ≥ 44px | `min-h-[44px] px-4 py-2` |
| 输入框 | 关联 label | `<label htmlFor={id}>` + `<input id={id}>` |
| 弹窗 | `role="dialog"`, `aria-modal="true"` | 支持 Escape 关闭 |
| Toast | `aria-live="polite"` | 屏幕阅读器播报 |
| 图标 | 纯装饰用 `aria-hidden="true"` | `<svg aria-hidden="true">` |
| 加载状态 | 建议设置 `aria-busy`，必要时使用 `aria-live` | `<button aria-busy={isLoading}>` |

## 5. 目录约定

```
web/components/
├── ui/                 # 基础 UI 组件（纯 UI，不触库）
└── particles/          # 视觉效果组件（纯 UI/动效）
```

**分层约束**：
- `components/*`：纯 UI 组件，不包含业务规则，不访问外部数据，不触 Supabase
- 业务 UI 推荐放在 `features/*/components/*`；整体分层/依赖方向/触库规约以 `LOGIC.md` 为准

> 过渡说明：当前原型阶段可能存在 `components/users/*` 等业务 UI；后续会迁移到 `features/users/components/*`，以与分层规范一致。

## 6. 现有组件（基线 API）

| 组件 | 路径 | 用途 | 核心 Props |
|------|------|------|------------|
| `Button` | `components/ui/button.tsx` | 统一按钮与 loading | `variant`, `isLoading` |
| `Input` | `components/ui/input.tsx` | 统一输入框/label/error | `label`, `error` |
| `Modal` | `components/ui/modal.tsx` | 统一弹窗容器 | `open`, `title`, `description`, `footer`, `onClose` |
| `ToastProvider`/`useToast` | `components/ui/toast.tsx` | 全局成功/失败反馈 | `toast.success()`, `toast.error()` |
| `Badge` | `components/ui/badge.tsx` | 权限/状态标签 | `tone` |
| `Card` | `components/ui/card.tsx` | 卡片容器 | 继承 `div` props |
| `Table`/`THead`/`TR`/`TH`/`TD` | `components/ui/table.tsx` | 统一表格外观 | 语义化子组件 |
| `ParticleField` | `components/particles/particle-field.tsx` | 粒子背景 | `particleCount` |

## 7. 交互模式

> 涉及鉴权、错误处理、Server Actions 的交互约定以 `LOGIC.md` 为准；本节只保留 UI 组件层面的使用约定，避免重复。

### 7.1 Modal 弹窗

- 内容放 `children`，底部按钮放 `footer`
- 危险操作（删除、Ban）必须二次确认
- 关闭统一走 `onClose`

### 7.2 表格

- 分页：默认 12 条/页
- 空态：展示明确的空态提示（例如 "No users found"）

## 8. 变更流程

1. **判断类型**：通用组件放 `components/ui`，业务组件放 feature 目录
2. **更新文档**：新增/修改组件后更新本文档的组件表格
3. **避免重复**：不要复制 Tailwind class，优先抽成组件或工具函数
4. **保持一致**：遵循现有命名和结构规范
