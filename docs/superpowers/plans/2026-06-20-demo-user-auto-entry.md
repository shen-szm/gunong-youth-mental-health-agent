# Demo User Auto Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let ordinary visitors enter the application automatically as one persistent demo user while preserving `/login` for teacher authentication.

**Architecture:** The backend exposes an idempotent demo-session endpoint that finds or creates a fixed non-teacher user. The frontend store requests that session when no local identity exists, and an async router guard initializes it for every route except `/login`; `App.vue` renders only routed pages so the login screen is no longer an implicit fallback.

**Tech Stack:** Vue 3, Pinia, Vue Router, Axios, FastAPI, SQLAlchemy, Python unittest, Node.js test runner

---

### Task 1: Define backend demo-session behavior

**Files:**
- Create: `backend/tests/test_demo_session.py`
- Modify: `backend/api/user.py`

- [ ] **Step 1: Write the failing backend test**

Create an in-memory SQLite test that calls `get_demo_session(db)` twice and asserts:

```python
self.assertEqual(first["user_id"], second["user_id"])
self.assertEqual(first["nickname"], "演示访客")
self.assertFalse(first["is_admin"])
self.assertEqual(db.query(User).filter(User.username == "demo_guest").count(), 1)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
& '.\backend\venv\Scripts\python.exe' -m unittest backend.tests.test_demo_session -v
```

Expected: FAIL because `get_demo_session` does not exist.

- [ ] **Step 3: Implement the endpoint**

Add `POST /api/user/demo-session` through a `get_demo_session(db)` function. Query `demo_guest`; if missing, create it with nickname `演示访客`, a generated unusable internal password hash, no plaintext password, and `is_admin=0`. Always force `is_admin=0` before returning the login-compatible payload.

- [ ] **Step 4: Run the backend test and verify GREEN**

Run the unittest command again.

Expected: one test passes.

### Task 2: Define frontend automatic-entry wiring

**Files:**
- Create: `frontend/tests/demo-auto-entry.test.mjs`
- Modify: `frontend/src/api/user.js`
- Modify: `frontend/src/stores/user.js`
- Modify: `frontend/src/router.js`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Write the failing frontend regression test**

The Node test must assert:

```text
user API exports createDemoSession()
store exports ensureDemoSession()
ensureDemoSession preserves an existing user
router guard awaits ensureDemoSession() outside /login
/login bypasses demo initialization
App.vue no longer imports or directly renders LoginView
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
node --test frontend/tests/demo-auto-entry.test.mjs
```

Expected: FAIL because automatic demo initialization is absent.

- [ ] **Step 3: Implement the frontend flow**

Add `createDemoSession()` to `api/user.js`. Add a deduplicated async `ensureDemoSession()` action to the user store that preserves existing identities and stores the returned demo identity through `login()`.

Replace the router guard with async behavior:

```javascript
if (to.path === "/login") return true
if (!userStore.isLoggedIn) {
  try {
    await userStore.ensureDemoSession()
  } catch {
    return "/login"
  }
}
return true
```

Remove the direct `LoginView` fallback from `App.vue`; render the router view normally.

- [ ] **Step 4: Run the frontend test and verify GREEN**

Run the Node test command again.

Expected: all frontend auto-entry assertions pass.

### Task 3: Verify compatibility

**Files:**
- Verify only

- [ ] **Step 1: Run all focused regression tests**

Run:

```powershell
node --test frontend/tests/demo-auto-entry.test.mjs frontend/tests/teacher-portal-labels.test.mjs
& '.\backend\venv\Scripts\python.exe' -m unittest backend.tests.test_demo_session -v
```

- [ ] **Step 2: Build the frontend**

Run `npm.cmd run build` from `frontend`.

- [ ] **Step 3: Compile changed backend code**

Run:

```powershell
& '.\backend\venv\Scripts\python.exe' -m py_compile backend\api\user.py
```

- [ ] **Step 4: Review and commit**

Run:

```powershell
git diff --check
git status --short
git diff
```

Confirm `/login`, teacher login routing, `is_admin`, and `/admin` remain unchanged, then commit the implementation.
