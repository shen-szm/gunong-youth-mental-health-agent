# V4.3 Engagement Loop Design

## Background

The current product already provides a public room entry, hidden teacher login, guided onboarding target highlights, chat, tree hole, healing, report, and profile panels. Version 4.2.5 improved onboarding by telling users exactly which room target to click and removed distracting mini tools.

V4.3 should move the product from "users can explore the room" to "users understand the core value quickly and have a reason to return daily." The scope is intentionally lightweight: improve activation and daily return behavior without introducing new backend services or rebuilding existing modules.

## Product Goal

V4.3 creates a light dual loop:

1. First-time activation loop: guide a new user through one meaningful chat experience, then show a small emotional takeaway and direct them to the tree hole for resonance.
2. Daily return loop: give returning users a simple daily task, a lightweight mood check-in, and a non-punitive companionship streak.

Success means a new visitor can complete the first meaningful experience without guessing, and a returning visitor sees a clear next action every day.

## Recommended Release Type

Release version: `4.3.0`.

Reason: this is a feature-level update that adds product loops and daily engagement logic, not a minor copy or styling patch.

## First-Time Activation Loop

### Entry

When the user enters the room and has not completed the current first-run guide version, the first-run card remains the primary visible guidance.

The guide should tell the user what to do and why:

- Step 1: click the computer to start a first confession.
- Step 2: send one sentence in the chat panel.
- Step 3: after the assistant replies, show a small "today's mood card."
- Step 4: guide the user to the tree hole to see similar feelings.

### Chat Prompt

When a first-run user opens chat and has not sent the first message, the input prompt should be more explicit:

> 把今天最想说的一句话丢给我

The prompt should reduce blank-page hesitation and make the expected action concrete.

### Completion Rule

The first-run experience is complete only after the user sends the first message and receives the assistant response. Merely clicking a target should not mark the full experience complete.

After completion, the app stores the guide completion version locally so the same guide does not repeatedly interrupt the user.

### Mood Card

After the first successful chat response, show a lightweight mood card with:

- emotion keyword or a fallback label;
- one warm summary sentence;
- one small action suggestion;
- a button that opens the tree hole panel.

This card should not require new backend support. It can derive content from the returned emotion value and the user's sent text.

## Daily Return Loop

### Daily Card Structure

For users who have already completed the first-run guide, the home engagement card becomes a daily return card with three parts:

1. Today's small task
   - Examples: say the most tiring thing today, write one sentence to comfort yourself, visit the tree hole for resonance.
2. Mood check-in
   - Options: 很累, 有点烦, 还可以, 轻松, 开心.
3. Companionship streak
   - Example: 你已经陪自己 3 天了.

The card should keep the current room visually clean and not cover primary hot zones.

### Tone

The return loop must avoid pressure. It should not use failure states such as "断签" or "任务失败."

Recommended language:

- "今天也给自己留一分钟。"
- "你已经陪自己 3 天了。"
- "不需要表现很好，只要说出来一点。"

### Local Persistence

Use local storage for V4.3:

- today's check-in value;
- today's task completion state;
- companionship streak count;
- last active date;
- last generated mood card;
- first-run completion version.

This keeps implementation risk low and avoids backend migration.

## Room Interaction Priority

The room should remain the central navigation surface. V4.3 should keep the priority clear:

1. Computer: main confession/chat entry.
2. Tree hole: resonance entry.
3. Healing: relaxation content.
4. Report: stage summary.
5. Profile: personal records and settings.

Only one recommended action should be visually emphasized at a time. This prevents the room from feeling like a dashboard full of competing tools.

## Data Flow

### First-Run Flow

1. User enters room.
2. App checks first-run completion version in local storage.
3. If incomplete, display first-run guide.
4. User clicks computer.
5. Chat panel opens with first-run prompt.
6. User sends first message through existing chat API.
7. Existing assistant response is appended.
8. App generates local mood card.
9. App marks first-run completion version.
10. Card invites user to open tree hole.

### Daily Flow

1. User enters room.
2. App checks local daily state by date.
3. If no check-in today, show mood check-in options.
4. User selects a mood.
5. App updates today's local state and companionship streak.
6. Daily card updates to show completion and next suggested action.

## Error Handling

- If chat API fails, do not mark the first-run loop complete.
- If local storage is unavailable, keep the UI usable and treat the session as temporary.
- If the assistant response has no emotion field, use a neutral fallback for the mood card.
- If date parsing fails, reset only the daily state and do not clear chat data.

## Testing Plan

Add or update frontend tests for:

- package and changelog version are `4.3.0`;
- first-run completion requires sending a message, not just clicking a hot zone;
- first-run chat prompt contains the explicit one-sentence instruction;
- mood card is generated after a successful first chat response;
- daily return card includes task, mood check-in, and companionship streak;
- daily persistence keys are date-scoped and local-only;
- existing hidden public login and teacher portal behavior remains unchanged;
- removed mini tools remain absent.

Run the existing test suite and production build before deployment.

## Out of Scope

V4.3 will not include:

- teacher dashboard redesign;
- backend risk detection;
- tree hole community rewrite;
- room decoration growth system;
- full achievement system;
- backend persistence for daily check-ins.

These should be considered for V4.4 or V5.0 after the activation and return loops are validated.
