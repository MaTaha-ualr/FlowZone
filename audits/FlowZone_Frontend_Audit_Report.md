# FlowZone Frontend Audit Report

**Audit date:** 2026-07-08  
**Scope:** `frontend/src`, frontend config, public assets, and frontend-facing backend route availability  
**Mode:** Markdown-only correction pass. No source-code implementation changes are included here.  
**Tech stack observed:** React 19, TypeScript, Vite 7, Tailwind CSS 3.4, shadcn-style UI components, React Router 7, Framer Motion, Recharts.

This report replaces the earlier draft with findings verified against the current repository. Items that were overstated or factually wrong were removed or corrected. The remaining items are intended to be tangible implementation candidates for the next phase.

Companion roadmap: [`features.md`](features.md) defines the production feature plan, design direction, backend contracts, and release order.

---

## Verification Performed

Commands run from `frontend/`:

- `npm ci`: completed, but reported engine warnings because the current local Node is `v16.15.1`.
- `npm run build`: TypeScript completed, then Vite failed because Vite 7 requires Node `20.19+` or `22.12+`.
- `npm run lint`: failed before linting source files because ESLint 9 needs newer Node APIs such as `structuredClone`.
- `npm audit --omit=dev`: reported 3 production dependency advisories: `lodash` high severity and `react-router` / `react-router-dom` low severity.

Important environment finding: local validation is currently blocked by Node 16. The frontend dependency set requires a newer Node runtime, and the Dockerfile already uses `node:20-slim` for the frontend build stage.

---

## Corrections To The Previous Draft

The earlier report contained several useful findings, but some claims were inaccurate:

- `Dashboard.tsx` mock chart/activity data is not regenerated on every render. It is generated once per component mount via `useMemo(..., [])`. It is still fake and changes after remounts.
- `TrustDetail.tsx` history is not regenerated on every render. It regenerates on mount and when the selected time range changes. It is still fake/random data.
- The Navbar route issue is not a `/flow` versus `/flowquest` false positive. The real issue is that desktop route matching handles nested routes, while the mobile menu only checks exact paths.
- `Documents.tsx` search is not doing live filtering on every keystroke. It only searches on Enter or button click, so a debounce bug is not present.
- `Voice.tsx` is not fake voice recording. It uses `MediaRecorder`, `transcribeVoice`, `sendChatMessage`, and `synthesizeVoice`. The fake voice behavior exists in `FlowQuest.tsx` only.
- The deployment finding "no frontend Dockerfile" was misleading. The root `Dockerfile` already has a frontend builder stage and copies `frontend/dist` into the runtime image.
- `src/pages/Navbar.tsx` was the wrong path. Navbar lives at `frontend/src/components/Navbar.tsx`.

---

## Priority 0: Blockers And Safety-Critical Gaps

| # | File / Area | Verified Finding | Recommended Change |
|---|---|---|---|
| P0.1 | `frontend/package.json`, local Node | Local build and lint are blocked on Node `v16.15.1`. Vite 7 requires Node `20.19+` or `22.12+`; ESLint 9 also requires newer Node APIs. | Standardize on Node 20.19+ or Node 22.12+ in local docs, CI, and developer setup. Keep Docker's Node 20 stage, but make local setup match it. |
| P0.2 | `frontend/src/main.tsx` | No React error boundary wraps the app. A render/runtime exception can take the whole UI to a blank screen. | Add an app-level error boundary around `App`, plus route/feature-level fallback boundaries for high-risk flows such as FlowQuest and Voice. |
| P0.3 | Youth safety UI | No visible 988 / Crisis Text Line / emergency support affordance exists in the main navigation, dashboard, Vibe Check storm state, FlowQuest, or Safe Harbor UI. | Add persistent, plain-language crisis help access. At minimum include 988, Crisis Text Line 741741, emergency guidance, and an escalation path for mentors/case workers. |
| P0.4 | `frontend/src/pages/FlowQuest.tsx` | WebSocket setup depends on `connectWebSocket`, `pollMessages`, `sessionId`, and `wsStatus`. `pollMessages` depends on `messages.length`, so message changes can recreate the socket and polling interval. | Split socket lifecycle from message polling. Store latest message count in a ref or use a dedicated WebSocket hook. Avoid closing/reopening the socket due to message-count changes. |
| P0.5 | `frontend/src/pages/TrustDetail.tsx` | `AnimatedCount` schedules `requestAnimationFrame` and calls `setDisplay` inside `useMemo`. This is a render-phase side effect and the returned cleanup is ignored. | Replace the `useMemo` block with `useEffect`, include cleanup, and avoid scheduling new animation loops during render. |

---

## Priority 1: Data Integrity And Functional Defects

| # | File / Area | Verified Finding | Recommended Change |
|---|---|---|---|
| P1.1 | `frontend/src/pages/Dashboard.tsx` | `genChartData()` uses `Math.random()` and `genActivities()` hardcodes recent events. The chart and activity feed are not connected to real history. | Use real endpoints. The backend already has `/api/v1/trust/{user_id}/history`; add or implement a real activity feed endpoint before using `getActivityFeed`. |
| P1.2 | `frontend/src/lib/api.ts`, backend routes | `getActivityFeed()` calls `/api/v1/users/{userId}/activity`, but no matching backend route exists in `app/api/routes/users.py`. | Either add the backend activity route or remove the API helper until the endpoint exists. |
| P1.3 | `frontend/src/pages/TrustDetail.tsx` | Trust history is random and local even though backend route `/api/v1/trust/{user_id}/history` exists. | Wire the page to the real trust history endpoint and preserve empty/error states when no history exists. |
| P1.4 | `frontend/src/pages/TrustDetail.tsx` | Vouch display uses hardcoded `mockVouches` even though `getVouches()` exists in `frontend/src/lib/api.ts`. | Fetch `/api/v1/trust/{user_id}/vouches`; do not show Coach Ray or hardcoded vouches unless explicitly in demo mode. |
| P1.5 | `frontend/src/pages/Rewards.tsx` | `handleRedeem()` catches redemption errors and still shows success, decrements local score, and adds a redeemed item. Failed API redemption is masked as success. | Only show success after the API succeeds. On failure, keep score unchanged and show an error. Demo fallback should be gated behind an explicit demo flag. |
| P1.6 | `frontend/src/pages/SessionHistory.tsx` | `historyFromApi()` always sets `messages: []`, so the transcript drawer cannot show real transcripts. | Fetch chat history when opening a session detail drawer, or extend the sessions endpoint to include transcript summaries/messages. |
| P1.7 | `frontend/src/pages/Dashboard.tsx` | Active session `END` button contains only a comment and never calls `endSession`. | Wire it to `endSession(session.id)`, refresh dashboard session state, and show loading/error feedback. |
| P1.8 | `frontend/src/pages/Dashboard.tsx` | `Run Tactical Reset` appears as a button but has no handler. | Implement the reset flow or render it as disabled/unavailable with clear copy. Do not show active controls that do nothing. |
| P1.9 | `frontend/src/pages/FlowQuest.tsx` | FlowQuest's inline mic records no audio and creates a simulated voice message/reply. | Either wire it to the same voice APIs as `Voice.tsx` or remove/label it as unavailable. |
| P1.10 | `frontend/src/context/AuthContext.tsx`, `frontend/src/lib/api.ts`, `app/api/routes/auth.py` | Auth stores only an access token in localStorage. There is no refresh endpoint or token refresh flow. A 401 clears localStorage and navigates to login. | Add a deliberate auth strategy: refresh tokens or short-session UX with warnings. If using 401 logout, clear in-memory auth state too and use router navigation. |
| P1.11 | `frontend/src/App.tsx` | No catch-all route exists. Unknown hash routes render an empty layout area. | Add a `*` route with a Not Found page and recovery links. |
| P1.12 | `frontend/src/pages/TrustDetail.tsx`, `frontend/src/pages/Rewards.tsx`, `frontend/public` | Tier images `/tier-watch.png`, `/tier-flex.png`, `/tier-vetted.png` are referenced but not present. Some references have fallback text; others do not. | Add the images, replace with generated badges/icons, or remove the image references consistently. |
| P1.13 | `frontend/src/pages/Rewards.tsx`, `frontend/public` | `/mentor-ray.jpg` is referenced but absent. A fallback appears, but the UI still assumes a specific mentor photo/name. | Use real mentor data, ship the asset, or make the mentor block data-driven/demo-gated. |
| P1.14 | `frontend/src/pages/Voice.tsx`, `frontend/tailwind.config.js` | `shadow-glow-gold` is used, but Tailwind defines `shadow-gold` and `shadow-glow-gold` is not configured. | Change the class to an existing shadow utility or add the exact utility to Tailwind config. |
| P1.15 | `frontend/src/App.css` | Default Vite CSS remains but is not imported. It is dead code and would break layout if imported. | Delete the file or replace it with intentional app CSS. |

---

## Priority 2: Accessibility And UX Issues

| # | File / Area | Verified Finding | Recommended Change |
|---|---|---|---|
| P2.1 | `frontend/src/components/Layout.tsx`, `Navbar.tsx` | No skip-to-content link or `main` target exists for keyboard users. | Add a skip link and a focusable `main` landmark. |
| P2.2 | `frontend/src/components/Navbar.tsx` | Mobile menu button lacks `aria-label`, `aria-expanded`, `aria-controls`, and Escape-key close behavior. | Add accessible disclosure attributes and keyboard handling. |
| P2.3 | Multiple pages | Several icon-only buttons rely on icons or `title` only. Examples include menu, eye toggle, mic, send, close, refresh, delete, and replay controls. | Add `aria-label` for every icon-only button. Keep visible text where practical. |
| P2.4 | `frontend/src/pages/Register.tsx` | Most form fields use placeholders without associated labels. | Add visible or screen-reader-only labels with `htmlFor` / `id`. |
| P2.5 | `frontend/src/pages/Login.tsx` | Labels are visible but are not programmatically associated with inputs because there are no matching `id` / `htmlFor` pairs. | Add ids and `htmlFor` attributes. |
| P2.6 | `frontend/src/pages/Intake.tsx` | The range input has no accessible label and the displayed value is not tied to the input for assistive technology. | Add a label, `aria-valuetext`, and an associated output element. |
| P2.7 | `frontend/src/pages/FlowQuest.tsx` | Incoming chat messages have no live region, so screen readers are unlikely to announce new assistant/system messages. | Add an appropriate `aria-live` region for new messages/status changes. |
| P2.8 | `frontend/src/pages/TrustDetail.tsx` | Formula tokens are clickable `span` elements with no keyboard activation semantics. | Use buttons for interactive tokens or add role, tab index, and keyboard handlers. |
| P2.9 | `frontend/src/pages/FlowQuest.tsx` | Top-level `fixed inset-0` overlays the normal layout and hides the shared navbar. | Decide whether FlowQuest is intentionally immersive. If yes, provide equivalent navigation/escape controls and test mobile viewport behavior. |
| P2.10 | `frontend/src/pages/Profile.tsx` | Notification checkbox is hardcoded `checked` and `readOnly`. | Back it with user preference state/API, or render it as static status text. |
| P2.11 | `frontend/src/pages/VibeCheck.tsx`, `Dashboard.tsx` | Hover effects are implemented with `onMouseEnter`/`onMouseLeave` inline mutations and do not have equivalent focus styling. | Move hover/focus states into classes/CSS and include focus-visible states. |

---

## Priority 3: Performance, Maintainability, And Architecture

| # | File / Area | Verified Finding | Recommended Change |
|---|---|---|---|
| P3.1 | Page architecture | Large page files are carrying too many responsibilities: `FlowQuest.tsx` 1156 lines, `Dashboard.tsx` 778, `SessionHistory.tsx` 775, `Documents.tsx` 679, `TrustDetail.tsx` 633, `Rewards.tsx` 551, `Voice.tsx` 530. | Extract feature components by page domain, starting with FlowQuest, Dashboard, SessionHistory, Documents, and TrustDetail. |
| P3.2 | Multiple pages | Color token objects are duplicated in Dashboard, VibeCheck, TrustDetail, Rewards, and related files despite Tailwind theme tokens existing. | Use Tailwind theme tokens or a single shared TypeScript token map. |
| P3.3 | `FlowQuest.tsx`, `SessionHistory.tsx` | `HexAvatar` is duplicated. | Extract a shared avatar component. |
| P3.4 | `frontend/src/App.tsx` | All pages are eagerly imported. There is no route-level code splitting. | Use `React.lazy` and `Suspense` for non-critical routes after an error boundary exists. |
| P3.5 | `frontend/public` | Character PNGs are about 1.6-1.9 MB each and vibe PNGs are about 1.3-1.6 MB each. The vibe PNGs are not used by `VibeCheck.tsx`, which uses emojis. | Convert large raster assets to appropriately sized WebP/AVIF variants, lazy-load non-critical images, and remove unused vibe images if not part of the product direction. |
| P3.6 | `frontend/src/lib/api.ts`, page response parsing | API responses are often cast through `Record<string, unknown>` and manually normalized. Zod is already installed. | Add runtime schemas for key API contracts, especially auth, sessions, trust, rewards, documents, and chat. |
| P3.7 | `frontend/src/lib/api.ts` | `useApi` has no caching, request dedupe, stale/retry policy, or cancellation. | Consider TanStack Query or a small internal wrapper with caching and cancellation for repeated dashboard/profile/trust calls. |
| P3.8 | `frontend/src/pages/Voice.tsx` | Cleanup effect intentionally omits `stream` from dependencies; if unmount happens while recording, the cleanup closure can hold the initial `null` stream. | Store the active stream in a ref or make cleanup dependency-safe so tracks always stop. |
| P3.9 | `frontend/src/pages/FlowQuest.tsx` | Comment says `src/lib/api.ts` does not exist, but the file exists and is imported. | Remove the stale comment and keep local helpers named as response normalizers instead of API helpers. |
| P3.10 | `frontend/src/pages/Home.tsx`, `Voice.tsx` | Negative margin layout breakout patterns couple pages to `Layout` padding. | Add an explicit full-bleed layout option instead of using negative margins. |
| P3.11 | Navigation | Back links are inconsistent. Some pages label a link as Dashboard but route to `/`. | Standardize page back targets and labels. |
| P3.12 | Toasts | `sonner` and `components/ui/sonner.tsx` exist, but no `Toaster` is mounted and no `toast()` calls exist. | Mount the toaster once and use it for non-blocking success/error feedback. |

---

## Product, Privacy, And Youth-Specific Gaps

These are not all code defects, but they should be resolved before treating the frontend as production-ready for at-risk youth.

| # | Area | Verified Gap | Recommended Change |
|---|---|---|---|
| Y1 | Crisis support | No visible crisis resources or "get help now" path. | Add persistent crisis support, especially in Vibe Check storm state, Safe Harbor red/yellow states, FlowQuest, and Dashboard. |
| Y2 | Privacy/terms | No visible privacy policy, terms, data visibility explanation, or "who can see my data" UI. | Add plain-language privacy/visibility pages and link them from auth, profile, documents, and navigation. |
| Y3 | Consent | Registration accepts youth accounts but has no visible guardian/consent flow or age-appropriate explanation. | Add a jurisdiction-aware consent strategy and plain-language consent copy. |
| Y4 | Stakeholder access | Mentor pages exist, but no parent/guardian/probation/case-worker portal is visible despite user fields such as `has_probation` and `has_case_worker`. | Define the intended stakeholder roles and data boundaries before adding UI. |
| Y5 | Language | Some phrases may undermine trust: "They watch. You flex. You get vetted.", "Strategic Intake", "The Dump", and surveillance-adjacent wording. | Test copy with actual users and mentors. Prefer clearer, less surveillance-coded language. |
| Y6 | Gamification | Profile badges are static; TrustDetail/Rewards contain hardcoded Coach Ray/demo language; progress celebrations are limited. | Make achievements and mentor/vouch content data-driven, with clear earned/locked states. |
| Y7 | Account control | No visible password reset, account deletion UI, MFA, or session timeout warning. Backend has soft-delete user route but the frontend does not expose account deletion. | Add account recovery and control flows appropriate to the risk profile. |

---

## Implementation Order For Next Phase

1. Upgrade local/CI Node to match the frontend toolchain and rerun `npm run build`, `npm run lint`, and `npm audit --omit=dev`.
2. Add error boundaries and a 404 route.
3. Add crisis help UI and Safe Harbor escalation affordances.
4. Fix the highest-risk runtime defects: FlowQuest socket lifecycle, TrustDetail `AnimatedCount`, Rewards false-success redemption, Dashboard END button.
5. Replace fake trust/history/vouch/dashboard data with real endpoints or explicit demo-mode gates.
6. Address the missing assets or remove the broken image references.
7. Add the accessibility fixes for forms, icon buttons, live regions, skip link, and keyboard interaction.
8. Extract the largest page files after behavior is stabilized.

---

## Audit Workspace State

- `frontend/node_modules/` was temporarily installed by `npm ci` for verification and then removed after the audit.
- No source files were intentionally changed during this audit pass except this Markdown report.
