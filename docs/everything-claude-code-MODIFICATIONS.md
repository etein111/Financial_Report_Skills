# Everything Claude Code - Local Modifications

> Source: https://github.com/affaan-m/everything-claude-code
> Local path: `~/.claude/plugins/marketplaces/everything-claude-code/`

This file tracks local modifications to the plugin. If the plugin is updated, these changes may be overwritten and need to be re-applied.

## Modifications

### 1. Removed Dev Server Blocker Hook

**File:** `hooks/hooks.json`

**Change:** Deleted the PreToolUse hook that blocks dev server commands (`pnpm dev`, `npm run dev`, etc.)

**Reason:** Allow AI to start web dev servers directly. The original hook blocked all dev server commands including those wrapped in tmux, which prevented AI from managing development servers.

**Date:** 2026-02-17

---

### 2. Whitelist OpenSpec Spec Files in Doc Creation Hook

**File:** `hooks/hooks.json`

**Change:** Added `openspec\/changes\/.*\/specs\/.*\/spec` to the whitelist pattern in the md/txt file creation blocker hook.

**Reason:** OpenSpec change specs are legitimate documentation files that should be allowed.

**Date:** 2026-02-16 (estimated)

---

### 3. Whitelist docs Directory in Doc Creation Hook

**File:** `hooks/hooks.json`

**Change:** Added `docs\/.*` to the whitelist pattern.

**Reason:** Allow documentation files in the project's docs directory.

**Date:** 2026-02-17

---


## How to Re-apply After Plugin Update

1. Remove the dev server blocker hook (search for "Block dev servers outside tmux")

2. Update the md/txt file creation hook pattern to include:
   - `openspec\/changes\/.*\/specs\/.*\/spec`
   - `docs\/.*`

Or simply restore from this file's recorded changes.
