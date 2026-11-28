# Public Entry Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make public entry bypass login, move teacher login to a hidden route, strengthen备案 visibility, and remove the handheld game window.

**Architecture:** Add a focused Node regression test that inspects Vue source for routing, style, and removed-entry invariants. Then make minimal source edits in `router.js`, `App.vue`, and `RoomHomeView.vue`.

**Tech Stack:** Vue 3, Vue Router, Node.js test runner, Vite

---

### Task 1: Regression test

**Files:**
- Create: `frontend/tests/public-entry-polish.test.mjs`

- [ ] Write a failing test asserting `/login` redirects to `/`, `/teacher-login` renders `LoginView`, `App.vue` treats `/teacher-login` as full-screen login, 小掌机/`ikk` is absent from `RoomHomeView.vue`, and备案样式 uses high contrast.
- [ ] Run `node --test frontend/tests/public-entry-polish.test.mjs`; expect failure.

### Task 2: Implementation

**Files:**
- Modify: `frontend/src/router.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/views/RoomHomeView.vue`

- [ ] Change route `/login` to redirect `/`.
- [ ] Add route `/teacher-login` for `LoginView`.
- [ ] Update router guard to bypass demo initialization only for `/teacher-login`.
- [ ] Update App login full-screen checks from `/login` to `/teacher-login`.
- [ ] Remove 小掌机 button, `ikk` mini app config, and `.ikk-bottom-mask`.
- [ ] Strengthen `.beian-footer` and children for contrast.
- [ ] Update teacher logout redirects from `/login` to `/teacher-login`.

### Task 3: Verification

- [ ] Run `node --test frontend/tests/public-entry-polish.test.mjs frontend/tests/demo-auto-entry.test.mjs frontend/tests/teacher-portal-labels.test.mjs`.
- [ ] Run `npm.cmd run build` from `frontend`.
- [ ] Run `git diff --check`.
- [ ] Review diff and commit.
