# Design QA — v5.0.0-alpha.3

## Comparison contract

- Source truth: `C:\Users\31795\.codex\generated_images\01a022bd-7794-7f20-a859-96ad33344392\exec-1250ece5-4cd3-4dca-8cf4-7d789bb470de.png`
- Source dimensions: `1670 × 942` (16:9)
- Implementation: `frontend/src/views/RoomHomeView.vue` at `http://127.0.0.1:5174/`
- Implementation capture: Codex in-app browser capture from the `studentTab4` rendered state, `1280 × 720` CSS viewport, after a successful non-crisis chat message.
- Teacher implementation: `frontend/src/views/AdminView.vue` at `http://127.0.0.1:5174/admin`
- Reference state: original pixel-art bedroom remains visible; dark translucent right-side action drawer is open; “做一个小行动” is selected; summary, one action, three decision buttons and the help link are visible.
- Rendered state: same room, navigation, pet and daily card remain in place; chat closes only after a successful safe response; the action drawer opens on the right with the same information hierarchy and working controls.

## Combined visual comparison

The selected source image and the rendered in-app-browser capture were inspected together at matching 16:9 states. The implementation preserves the source composition: the room remains the primary visual anchor, the drawer occupies the right third without replacing the room, and the dark glass surface, mint action color, compact type scale and quiet borders match the existing liquid-glass system. The implementation intentionally retains the current production room background and existing bottom navigation instead of recreating either asset.

## Interaction and accessibility checks

- Student core path: enter room → open chat → submit a safe concern → drawer opens → switch need → cycle action → open help-card flow.
- Crisis path: `需要立即协助` responses do not open the ordinary action drawer.
- Summary can be edited and saved; “愿意试试” and the help card persist on the device.
- Drawer uses an `aside` landmark, labelled heading, labelled close button, fieldset/legend and live feedback region.
- Keyboard focus indicators inherit the existing button/input focus system; reduced-motion media query disables drawer transition.
- Mobile breakpoint changes the drawer to an inset bottom sheet, stacks choice/action controls and caps height at 75vh.
- Teacher core path: permission-gated student selection → execute work order → inspect pipeline/evidence/conflict/decision → confirm tasks.
- Browser console: no warnings or errors in the tested student and teacher states.
- Desktop visual captures were produced from the live student drawer and teacher workbench states; focus entry, Escape close/return and the visible help-card path were exercised in the same browser session.

## Issue history

1. P1 — business UI exposed development/competition labels and seeded labels such as “演示/合成”. Fixed by replacing business copy and sanitizing display names without changing source records.
2. P1 — student need selector initially did not change the delivered action. Fixed by mapping each need to a distinct next step and defaulting to the selected reference state “做一个小行动”.
3. P1 — help flow only changed transient UI. Fixed by generating a persistent help card containing the chosen trusted adult and only the summary the student explicitly agreed to share.
4. P1 — secondary drawer text could fall below AA contrast over bright room areas. Fixed with a darker near-opaque glass surface and higher-opacity secondary text.
5. P1 — administrator direct work-product IDs changed on each refresh, losing confirmed task state. Fixed by reusing the same audited snapshot cutoff within the current day; the regression test waits across the former one-second boundary.
6. P1 — family-harm phrases and older crisis evidence could be missed. Fixed by extending household-person rules and appending all urgent records from the authorized 30-day scope even when ordinary display rows exceed 50.
7. P1 — reusing an administrator snapshot could hide a crisis signal that arrived later the same day. Fixed with an incremental SafetyGate; a new urgent signal creates a microsecond-unique safety revision and does not inherit prior ordinary-task confirmations.
8. P1 — an approved ordinary-teacher snapshot could hide a crisis signal that arrived after approval. Fixed with a redacted safety revision: urgent actions override immediately, while post-approval original text remains unavailable until a new approval.
9. P1 — household harm rules were too narrow for tool-based assault, coerced sexual contact and confinement. Fixed with category-level patterns and direct regression cases across the shared student/teacher SafetyGate.
10. P2 — initial build output was locked by a running preview audio file. Verified the same Vite production build in an isolated output directory instead; no source or user asset was removed.

## Final result

`passed`

- Visual P0: 0
- Visual P1: 0
- Visual P2: 0
