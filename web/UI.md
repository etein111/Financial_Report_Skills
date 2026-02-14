# UI 组件规范

> 目的：约定 UI 组件的命名、结构、样式、可访问性及交互模式，确保实现一致。
>
> 参考来源：[React + TypeScript Style Guide](https://react-typescript-style-guide.com/)、[LogRocket - React TypeScript Patterns](https://blog.logrocket.com/react-typescript-10-patterns-writing-better-code/)、[Tailwind CSS Best Practices](https://dev.to/theodorusclarence/styling-best-practices-i-use-with-tailwindcss-mf0)

## 1. 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件名 | PascalCase | `Button`, `UserProfile` |
| 文件名 | kebab-case | `button.tsx`, `user-profile.tsx` |
| Props 接口 | PascalCase + Props | `ButtonProps`, `ModalProps` |
| 变体类型 | PascalCase，语义化 | `ButtonVariant`, `BadgeTone` |
| 事件处理函数 | handle + 动词 | `handleSubmit`, `handleClose` |
| 常量 | UPPER_SNAKE_CASE | `PAGE_SIZE`, `MAX_RETRIES` |

## 2. Props 定义规范

### 2.1 使用 interface（推荐）

```typescript
// ✅ 推荐：使用 interface，便于扩展和继承
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  isLoading?: boolean;
}

// ✅ 扩展示例
export interface IconButtonProps extends ButtonProps {
  icon: React.ReactNode;
  label: string;
}
```

### 2.2 变体类型使用 type（联合类型）

```typescript
// ✅ 联合类型使用 type
export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
export type BadgeTone = "zinc" | "blue" | "amber" | "green" | "red";
export type UserStatus = "active" | "inactive" | "banned";
```

### 2.3 必填与可选

```typescript
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;        // 可选
  error?: string;        // 可选
  // 继承的 type、placeholder 等均为可选
}

export interface ModalProps {
  open: boolean;         // 必填
  onClose: () => void;   // 必填
  title?: string;        // 可选
  children: React.ReactNode;  // 必填
}
```

### 2.4 工具类型

```typescript
// Pick - 选取部分属性
type UserPreview = Pick<User, "id" | "name" | "email">;

// Omit - 排除部分属性
type UserWithoutPassword = Omit<User, "password">;

// Partial - 所有属性可选
type PartialUser = Partial<User>;
```

## 3. 组件结构规范

### 3.1 文件内顺序

```typescript
// 1. "use client" 指令（如需要）
"use client";

// 2. 导入（分组：React → 外部库 → 内部模块 → 类型）
import * as React from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";

// 3. 类型定义（先变体类型，后 Props 接口）
export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  isLoading?: boolean;
}

// 4. 辅助函数（如样式映射）
const variantStyles: Record<ButtonVariant, string> = {
  primary: "bg-blue-600 text-white hover:bg-blue-700",
  secondary: "border border-white/10 bg-zinc-800 text-zinc-100 hover:bg-zinc-700",
  danger: "bg-red-600 text-white hover:bg-red-700",
  ghost: "bg-transparent text-zinc-200 hover:bg-white/5",
};

// 5. 主组件
export function Button({
  className,
  variant = "primary",
  isLoading = false,
  disabled,
  children,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || isLoading;

  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[6px] px-4 py-2",
        "text-sm font-medium transition-colors duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60",
        isDisabled && "cursor-not-allowed opacity-50",
        variantStyles[variant],
        className,
      )}
      disabled={isDisabled}
      {...props}
    >
      {isLoading ? <Spinner /> : null}
      {children}
    </button>
  );
}

// 6. 子组件（仅当被主组件独占使用时）
function Spinner() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4 animate-spin text-current"
      viewBox="0 0 24 24"
      fill="none"
    >
      {/* ... */}
    </svg>
  );
}
```

### 3.2 单一职责

- **一个文件一个主组件**
- 子组件仅当被主组件独占使用时可放在同文件
- 可复用的子组件应拆分为独立文件
- 工具函数应放 `lib/` 目录

### 3.3 forwardRef 规范

```typescript
export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => {
    const inputId = id ?? React.useId();

    return (
      <div className="space-y-1">
        {label ? <label htmlFor={inputId}>{label}</label> : null}
        <input
          ref={ref}
          id={inputId}
          className={cn("base-styles", error && "error-styles", className)}
          {...props}
        />
        {error ? <p className="text-xs text-red-500">{error}</p> : null}
      </div>
    );
  },
);

Input.displayName = "Input"; // 必须设置
```

## 4. 样式规范

### 4.1 基本约定

- 使用 **Tailwind CSS**，避免内联 style
- class 合并统一使用 `cn()` 工具函数
- 所有组件必须支持 `className` 覆盖

### 4.2 cn() 使用模式

```typescript
// ✅ 推荐：基础样式 + 条件样式 + 用户覆盖
<button
  className={cn(
    // 1. 基础样式（不变化的）
    "inline-flex items-center justify-center gap-2 rounded-[6px] px-4 py-2",
    "text-sm font-medium transition-colors duration-200",

    // 2. 条件样式（状态/变体相关）
    isDisabled && "cursor-not-allowed opacity-50",
    variant === "primary" && "bg-blue-600 text-white hover:bg-blue-700",

    // 3. 用户覆盖（放最后）
    className,
  )}
>
```

### 4.3 避免使用 @apply

```typescript
// ❌ 避免：使用 @apply 抽取到 CSS
.button {
  @apply inline-flex items-center justify-center rounded-[6px] px-4 py-2;
}

// ✅ 推荐：抽取到组件或样式映射
const buttonBase = "inline-flex items-center justify-center rounded-[6px] px-4 py-2";

// 或使用 Record 映射
const variantStyles: Record<ButtonVariant, string> = {
  primary: "bg-blue-600 text-white hover:bg-blue-700",
  // ...
};
```

### 4.4 设计 Token

| 元素 | 约定 |
|------|------|
| 圆角 | 按钮/输入框 `rounded-[6px]` 或 `rounded-[8px]`；卡片/弹窗 `rounded-[12px]` |
| 边框 | `border border-white/10`（10% 白色透明） |
| 背景 | 主背景 `bg-zinc-900`；悬停 `hover:bg-zinc-700` 或 `hover:bg-zinc-800` |
| 文字 | 主文字 `text-zinc-100`；次要 `text-zinc-300` 或 `text-zinc-400` |
| 过渡 | `transition-colors duration-200`（200ms） |
| 焦点 | `focus:ring-2 focus:ring-blue-500/50` 或 `focus-visible:ring-2` |

### 4.5 响应式

```typescript
// ✅ 移动优先
<div className="text-sm md:text-base lg:text-lg">

// ✅ 响应式隐藏/显示
<div className="hidden md:block">
<div className="block md:hidden">
```

## 5. 可访问性

| 元素 | 要求 |
|------|------|
| 按钮 | 必须有可点击区域（最小 44px） |
| 输入框 | 必须关联 label（通过 `id` 或 `aria-labelledby`） |
| 弹窗 | `role="dialog"`, `aria-modal="true"`, 支持 Escape 关闭 |
| Toast | `aria-live="polite"` |
| 图标 | 纯装饰用 `aria-hidden="true"` |
| 加载状态 | 使用 `aria-busy` 或 `aria-live` |

```typescript
// ✅ Modal 可访问性示例
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby={titleId}
  aria-describedby={descriptionId}
>
  <h2 id={titleId}>{title}</h2>
  <p id={descriptionId}>{description}</p>
</div>
```

## 6. 目录约定

```
web/components/
├── ui/                 # 基础 UI 组件（无业务逻辑）
│   ├── button.tsx
│   ├── input.tsx
│   ├── modal.tsx
│   ├── toast.tsx
│   ├── badge.tsx
│   ├── card.tsx
│   └── table.tsx
├── <feature>/          # 业务组件
│   └── users/
│       ├── users-page.tsx
│       ├── user-card.tsx
│       └── user-form.tsx
└── particles/          # 视觉效果组件
    └── particle-field.tsx
```

分层约束：
- `components/ui/*`：只做展示与交互，不包含业务逻辑，不访问外部服务
- `components/<feature>/*`：可包含业务 UI 状态与交互

## 7. 现有组件（冻结 API）

| 组件 | 路径 | 用途 | 核心 Props |
|------|------|------|------------|
| `Button` | `ui/button.tsx` | 统一按钮与 loading | `variant`, `isLoading` |
| `Input` | `ui/input.tsx` | 统一输入框/label/error | `label`, `error` |
| `Modal` | `ui/modal.tsx` | 统一弹窗容器 | `open`, `title`, `description`, `footer`, `onClose` |
| `ToastProvider`/`useToast` | `ui/toast.tsx` | 全局成功/失败反馈 | `toast.success()`, `toast.error()` |
| `Badge` | `ui/badge.tsx` | 权限/状态标签 | `tone` |
| `Card` | `ui/card.tsx` | 卡片容器 | 继承 `div` props |
| `Table`/`THead`/`TR`/`TH`/`TD` | `ui/table.tsx` | 统一表格外观 | 语义化子组件 |

## 8. 交互模式

### 8.1 表单校验

- 必填与格式校验在提交前完成
- 错误提示使用 `Input` 组件的 `error` prop
- 异步提交失败使用 `toast.error()`

```typescript
// ✅ 校验模式
function handleSubmit(e: React.FormEvent) {
  e.preventDefault();

  const errors: { email?: string; name?: string } = {};

  if (!email.trim()) errors.email = "Email is required";
  else if (!isValidEmail(email)) errors.email = "Invalid email format";

  setErrors(errors);
  if (Object.keys(errors).length) return;

  // 提交逻辑...
}
```

### 8.2 Toast 反馈

```typescript
toast.success("Operation succeeded.", { title: "Success" });
toast.error("Operation failed.", { title: "Error" });
```

- 任何改变数据状态的操作必须有反馈
- 默认 success 3s，error 5s

### 8.3 Modal 弹窗

- 内容放 `children`，底部按钮放 `footer`
- 危险操作（删除、Ban）必须二次确认
- 关闭统一走 `onClose`

```typescript
// ✅ 确认弹窗模式
<ConfirmModal
  open={deleteOpen}
  title="Delete user?"
  description="This action cannot be undone."
  onClose={() => setDeleteOpen(false)}
  onConfirm={handleDelete}
  confirmLabel="Delete"
  confirmTone="danger"
/>
```

### 8.4 表格

- 分页：默认 12 条/页
- 空态：展示 "No results found" 提示

```typescript
// ✅ 空态处理
{items.length === 0 ? (
  <tr>
    <td colSpan={5} className="py-10 text-center text-zinc-400">
      No results found
    </td>
  </tr>
) : (
  items.map(item => <ItemRow key={item.id} item={item} />)
)}
```

## 9. 变更流程

1. **判断是否通用组件**：是则放 `components/ui`，否则放 feature 目录
2. **新增/修改组件后**：更新本文档的组件表格
3. **避免复制 Tailwind class**：优先抽成组件或工具函数
4. **保持 API 稳定**：修改现有组件 API 需同步更新所有使用方
