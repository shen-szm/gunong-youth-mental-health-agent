# Teacher Portal Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace user-visible administrator terminology with teacher terminology while preserving all internal permission fields, routes, APIs, and account compatibility.

**Architecture:** Add a lightweight Node regression test that reads the affected source files and verifies required teacher-facing strings and forbidden administrator-facing strings. Then make minimal string-only edits in Vue templates/scripts and FastAPI response/prompt text, leaving identifiers and paths unchanged.

**Tech Stack:** Vue 3, JavaScript, Node.js built-in test runner, FastAPI, Python

---

### Task 1: Add teacher-facing terminology regression test

**Files:**
- Create: `frontend/tests/teacher-portal-labels.test.mjs`

- [ ] **Step 1: Write the failing test**

Create a Node test that loads the affected frontend and backend files, asserts the required teacher-facing phrases, rejects user-visible administrator phrases, and confirms `/admin`, `/api/admin`, `is_admin`, and `isAdmin` remain present.

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/teacher-portal-labels.test.mjs`

Expected: FAIL because the current UI and API messages still contain administrator-facing terminology.

- [ ] **Step 3: Commit the failing regression test**

Run:

```powershell
git add frontend/tests/teacher-portal-labels.test.mjs
git commit -m "test: define teacher portal terminology"
```

### Task 2: Update frontend visible terminology

**Files:**
- Modify: `frontend/src/views/RoomHomeView.vue`
- Modify: `frontend/src/views/ProfileView.vue`
- Modify: `frontend/src/views/AdminView.vue`

- [ ] **Step 1: Replace role and entry labels**

Apply these visible mappings:

```text
管理员 -> 教师
管理后台 -> 教师端
设管理 -> 设为教师
取消管理 -> 取消教师
设置管理员 -> 设置教师
请用管理员账号登录 -> 请用教师账号登录
```

Keep internal names such as `isAdmin`, `toggleAdmin`, `/admin`, `/api/admin`, and CSS class names unchanged.

- [ ] **Step 2: Run the terminology test**

Run: `node --test frontend/tests/teacher-portal-labels.test.mjs`

Expected: still FAIL until backend user-visible messages are updated.

### Task 3: Update backend visible terminology

**Files:**
- Modify: `backend/api/admin.py`
- Modify: `backend/api/user.py`

- [ ] **Step 1: Replace response and AI prompt terminology**

Apply these visible mappings:

```text
需要管理员权限 -> 需要教师权限
设为管理员 -> 设为教师
取消管理员 -> 取消教师
联系管理员重置 -> 联系教师重置
给管理者的建议 -> 给教师的建议
```

Keep module names, functions, fields, route prefixes, and internal comments unchanged.

- [ ] **Step 2: Run the terminology test**

Run: `node --test frontend/tests/teacher-portal-labels.test.mjs`

Expected: PASS.

### Task 4: Verify compatibility and builds

**Files:**
- Verify only

- [ ] **Step 1: Verify frontend production build**

Run: `npm.cmd run build` from `frontend`.

Expected: Vite exits with code 0.

- [ ] **Step 2: Verify backend syntax**

Run:

```powershell
& '.\backend\venv\Scripts\python.exe' -m py_compile backend\api\admin.py backend\api\user.py
```

Expected: exit code 0 with no output.

- [ ] **Step 3: Verify internal compatibility names**

Run:

```powershell
rg -n 'is_admin|isAdmin|/admin|/api/admin' frontend/src backend/api
```

Expected: internal permission fields and routes are still present.

- [ ] **Step 4: Review diff and commit**

Run:

```powershell
git diff --check
git diff -- frontend/src/views/RoomHomeView.vue frontend/src/views/ProfileView.vue frontend/src/views/AdminView.vue backend/api/admin.py backend/api/user.py frontend/tests/teacher-portal-labels.test.mjs
git add frontend/src/views/RoomHomeView.vue frontend/src/views/ProfileView.vue frontend/src/views/AdminView.vue backend/api/admin.py backend/api/user.py
git commit -m "feat: present admin tools as teacher portal"
```
