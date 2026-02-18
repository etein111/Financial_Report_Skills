# Claude Code 精美界面 UI 技术栈安装指南

本指南介绍 4 个核心 UI 工具，以及完整安装方法。这些工具组合可以让 Claude Code 自动生成现代、专业级 SaaS 界面（类似 Linear / Stripe / Vercel）。

适用于：

- Next.js App Router 项目
- Claude Code 自动生成 UI
- SaaS Dashboard / 管理后台

---

# 概览

需要安装以下 4 个核心组件：

| 工具 | 类型 | 作用 |
|---|---|---|
| Tailwind CSS | 样式系统 | 提供布局、颜色、间距、响应式能力 |
| shadcn/ui | UI 组件库 | 提供专业 SaaS 风格组件 |
| lucide-react | 图标库 | 提供现代 SVG 图标 |
| next-themes | 主题系统 | 提供 Dark Mode 支持 |

---

# 前提条件

确保你在 Next.js 项目根目录：

```bash
cd your-nextjs-project
```

确保存在：

```
package.json
app/
```

---

# 1. Tailwind CSS（现代样式系统）

## 安装

```bash
pnpm add -D tailwindcss postcss autoprefixer
pnpm dlx tailwindcss init -p
```

## 安装后生成

```
tailwind.config.js
postcss.config.js
```

## 作用

Tailwind CSS 提供：

- 响应式设计（responsive design）
- 间距系统（spacing system）
- 颜色系统（color system）
- Flexbox 和 Grid 布局
- 现代 UI 样式基础

Claude Code 默认优先使用 Tailwind。

---

# 2. shadcn/ui（核心 UI 组件库）

## 初始化

```bash
pnpm dlx shadcn-ui@latest init
```

推荐选项：

```
TypeScript: Yes
App Router: Yes
Tailwind CSS: Yes
Components directory: components/ui
```

## 安装常用组件

```bash
pnpm dlx shadcn-ui@latest add button card dialog input form table dropdown-menu
```

## 安装后生成

```
components/ui/button.tsx
components/ui/card.tsx
components/ui/dialog.tsx
components/ui/input.tsx
components/ui/form.tsx
components/ui/table.tsx
components/ui/dropdown-menu.tsx
```

## 作用

提供现代 SaaS UI 组件：

- Button
- Card
- Dialog（Modal）
- Form
- Table
- Dropdown Menu

特点：

- 专业视觉效果
- 正确间距和布局
- 正确交互行为
- 高可访问性（accessibility）

Claude Code 会自动优先使用这些组件。

---

# 3. lucide-react（现代图标库）

## 安装

```bash
pnpm add lucide-react
```

## 作用

提供现代 SVG 图标：

- Sidebar 图标
- Toolbar 图标
- 按钮图标
- 状态图标

## 使用示例

```tsx
import { User } from "lucide-react"

<User className="w-4 h-4" />
```

Claude Code 会自动使用 lucide-react 生成图标。

---

# 4. next-themes（Dark Mode 主题系统）

## 安装

```bash
pnpm add next-themes
```

## 作用

提供主题支持：

- Dark Mode
- Light Mode
- 自动检测系统主题
- 主题切换

现代 SaaS 应用标准功能。

---

# 一次性完整安装命令（推荐）

可直接复制执行：

```bash
pnpm add -D tailwindcss postcss autoprefixer
pnpm dlx tailwindcss init -p

pnpm dlx shadcn-ui@latest init
pnpm dlx shadcn-ui@latest add button card dialog input form table dropdown-menu

pnpm add lucide-react
pnpm add next-themes
```

---

# 安装完成后的项目结构

```
app/
components/
  ui/
    button.tsx
    card.tsx
    dialog.tsx
lib/
styles/
tailwind.config.js
postcss.config.js
package.json
```

---

# Claude Code 如何使用这些工具

Claude Code 会自动使用：

- Tailwind CSS → 生成样式
- shadcn/ui → 生成组件
- lucide-react → 添加图标
- next-themes → 支持 Dark Mode

Claude Code 可以自动生成：

- Dashboard
- Sidebar
- Navbar
- Forms
- Tables
- 管理后台界面

---

# 总结

必须安装：

```
Tailwind CSS
shadcn/ui
lucide-react
next-themes
```

这是 Claude Code 自动生成精美界面的基础技术栈。

