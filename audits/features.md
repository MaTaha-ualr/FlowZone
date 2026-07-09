# FlowZone Production Feature Plan

**Updated:** 2026-07-08  
**Purpose:** Consolidate the audit reports into a production roadmap.  
**Sources reviewed:** `FlowZone_Frontend_Audit_Report.md`, `FlowZone_Comprehensive_Audit_Report.md`, `flowzone_competitive_research_report.md`, and the duplicate DOCX audit.  
**Verification rule:** audit suggestions were checked against the current codebase before being added here.

This is the product roadmap. The audit reports explain defects; this file explains what FlowZone needs to become a credible production product for at-risk youth, mentors, case workers, and program administrators.

---

## Current Verified State

Some audit findings are correct, some are partly stale, and some became more specific after checking the code.

| Area | Current Code State | Roadmap Implication |
|---|---|---|
| Crisis resources | `frontend/src/components/CrisisSupport.tsx` and `frontend/src/lib/crisis.ts` now provide static 988, Crisis Text Line, and 911 resources. The app imports the provider and Get Help button. | Static crisis help is started. Production still needs backend safety events, mentor escalation, mandatory reporting, and follow-up workflows. |
| Admin authorization | `require_admin()` in `app/core/security.py` returns any authenticated user. Role enum currently supports `youth` and `mentor`, not `admin`. | Add real RBAC before any admin endpoint is production-exposed. |
| Demo mode | `APP_DEMO_MODE=true` accepts `X-User-ID` impersonation. No code-level production guard blocks it. | Add production guard, startup warning, and optional demo secret header. |
| Mentor notes | Mentor roster/dashboard reads are role-checked, but `POST /api/v1/mentors/notes` accepts any authenticated user and trusts submitted `mentor_id` / `mentor_name`. | Enforce mentor role and derive mentor identity from auth, not request body. |
| Document access | Document upload/list validates `user_id` against `current_user.id`. The older audit claim that ownership is missing is stale. | Keep ownership checks. Add upload size, MIME/type, scanning, and safer streaming. |
| Google Drive | Connect/callback exist, but sync returns 501 and OAuth state is static. | Hide or label Drive sync until real OAuth state, token storage, and sync are implemented. |
| WebSocket auth | WebSocket token is passed in the URL query string. | Replace with a safer browser-compatible strategy, such as short-lived WS tokens or secure cookie flow. |
| Trust history/vouches | Backend routes exist for trust history and vouches. Frontend still has mock/fallback areas. | Wire the UI to real endpoints and remove false success/fake data. |
| Decay/expiration | Credit decay and vouch expiration functions exist but only run from a manual admin endpoint. | Add scheduled jobs or managed worker. |
| Rate limiting | Concurrency guard has a lock; rate limiter uses in-memory lists with no lock and no distributed backend. | Use locking/Redis for production and key limits by authenticated user. |
| Sanitization/moderation | User input is scanned for PII/prompt injection/extreme language, but PII is flagged, not removed. AI output moderation is not present. | Add youth-safe content moderation, redaction policy, and human review workflow. |
| Frontend voice | `Voice.tsx` uses real recording/transcription/TTS. FlowQuest inline mic still simulates voice messages. | Reuse Voice flow inside FlowQuest or remove the fake mic from production. |
| Frontend validation | Local Node 16 blocks Vite 7 and ESLint 9. Docker uses Node 20. | Standardize local/CI Node 20.19+ or 22.12+. |

---

## Product North Star

FlowZone should feel like a calm, credible support system, not a surveillance tool, class project, or gamified scoreboard.

The production product must:

1. Keep youth safe during crisis, disclosure, or escalation.
2. Use real data for scores, rewards, badges, alerts, transcripts, and reports.
3. Explain privacy plainly: who can see what, why, and for how long.
4. Give mentors and case workers actionable context without overexposing youth.
5. Provide evidence-based wellness tools, not only AI chat.
6. Work reliably on mobile, with accessible controls and no dead buttons.
7. Treat demo mode and mock data as non-production-only.

---

## Frontend-Only vs Full-Stack Rule

| Feature Type | Frontend Only Is Okay? | Backend Needed? |
|---|---:|---:|
| Visual redesign, spacing, typography, component polish | Yes | No |
| Static resource panel such as national crisis lines | Yes | Optional managed resources later |
| Error boundaries, 404 page, skeletons, empty states | Yes | No |
| Local-only dark/light preference | Yes | No |
| Synced user preferences | No | Yes |
| Trust score, vouches, badges, streaks, rewards | No | Yes |
| Crisis escalation, safety events, mandatory reporting | No | Yes |
| Mentor/case-worker alerts and notes | No | Yes |
| Session transcripts, summaries, deletion, export | No | Yes |
| Notifications, reminders, SMS/email/push | No | Yes |
| Consent, account deletion, privacy settings | No | Yes |
| Admin review, audit trails, compliance logs | No | Yes |

Do not ship frontend-only placeholders for backend-owned behavior. If a backend contract is missing, the UI must say unavailable, demo-only, or not render the feature.

---

## Design And Experience System

The current dark/gold/neon look can be retained, but production needs a calmer, more systematic palette and a clearer visual language.

### Design Principles

- Mobile first. Youth workflows must be complete on a phone.
- Calm under stress. Storm, red Safe Harbor, and crisis screens should reduce motion and visual noise.
- High contrast. Target WCAG AA minimum.
- No surveillance framing. Avoid language like "they watch" or UI that feels punitive.
- Youth views should be simple and focused. Mentor/case-worker views can be denser.
- Every repeated pattern should use the design system, not page-local inline colors.

### Recommended Semantic Palette

| Token | Use | Dark Value | Light Value |
|---|---|---:|---:|
| `color-bg` | App background | `#080A0F` | `#F7F8FA` |
| `color-surface` | Cards and panels | `#11141B` | `#FFFFFF` |
| `color-surface-soft` | Secondary surfaces | `#171B24` | `#EEF1F5` |
| `color-border` | Borders | `#2A3140` | `#D8DEE8` |
| `color-text` | Primary text | `#F4F7FA` | `#111827` |
| `color-text-muted` | Secondary text | `#A7B0BF` | `#5B6472` |
| `color-primary` | Primary actions | `#D4AF37` | `#8A6500` |
| `color-primary-soft` | Primary subtle bg | `#2B2410` | `#FFF4CC` |
| `color-info` | Guidance and links | `#4DB6E8` | `#006D9C` |
| `color-success` | Safe/complete | `#31C48D` | `#057A55` |
| `color-warning` | Caution/yellow | `#F6AD3C` | `#9A5B00` |
| `color-danger` | Crisis/red | `#F05252` | `#C81E1E` |

### Required Design Work

| Feature | Frontend Work | Backend Work | Done When |
|---|---|---|---|
| Shared design tokens | Move colors, radius, shadows, typography to Tailwind/CSS variables. | None | New pages do not define local color objects. |
| Dark/light mode | Add light variables, theme toggle, system preference, reduced motion. | Optional preference endpoint. | Theme works without contrast regressions. |
| Crisis visual state | Create calm, high-contrast red/yellow Safe Harbor panels. | Safety event data later. | Red/yellow states always show action and context. |
| Image policy | Replace missing tier/mentor assets and optimize large PNGs. | Optional asset management. | No broken images; large assets have WebP/AVIF variants. |
| Layout system | Add normal, full-bleed, and immersive route layouts. | None | Pages do not use negative margins to escape layout. |

---

## Production Feature Backlog

### 1. Security, Access Control, And Platform Hardening

These are production gates. They should happen before broad pilot use.

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| Real RBAC/admin role | Admin budget/model endpoints are sensitive. | Hide admin nav unless authorized. | Add `admin` role or permission model; enforce in `require_admin`. | Youth/mentor tokens cannot access admin routes. |
| Demo mode production guard | `X-User-ID` impersonation is dangerous outside local pilots. | Show demo banner when active. | Block demo mode in `APP_ENV=production`; require secret header in staging. | Production cannot start with unsafe demo auth. |
| Mentor note authorization | Notes can change trust score and Safe Harbor. | No client-supplied mentor identity. | Require mentor role; derive mentor id/name from token; add vouch limits. | Youth cannot create mentor notes or award themselves points. |
| Password reset | Users need recovery without staff intervention. | Forgot/reset password UI. | Reset tokens, expiry, email/SMS delivery. | Password reset works end to end. |
| Token refresh/session warning | Users should not be silently kicked out. | Expiry warning, router-safe logout. | Refresh endpoint or explicit short-session policy. | Session expiry is predictable and tested. |
| Account lockout/rate limit | Protect auth endpoints from brute force. | Friendly locked/try-later states. | Failed login tracking, lockout/backoff. | Repeated login failure is rate-limited. |
| Upload validation | Prevent memory exhaustion and unsafe files. | Show allowed file types/size. | Size limit, MIME allowlist, streaming, malware scan hook. | Oversized/unsupported files are rejected before ingestion. |
| Safer WebSocket auth | Query tokens leak into logs/history. | Request short-lived WS token before connect. | WS token endpoint or secure-cookie strategy. | Long-lived JWT is not placed in URL. |
| Production rate limiting | Current rate limiter is in-memory. | Surface retry-after errors. | Redis/lock-backed limiter keyed to authenticated user. | Limits survive multi-worker deploys. |
| Secret/config validation | Default secret and wildcard CORS are unsafe in production. | None | Startup validation for `APP_SECRET_KEY`, CORS, demo mode, debug. | Unsafe production config fails fast. |

### 2. Safety, Crisis, And Mandatory Reporting

Static help resources exist. The missing production feature is the safety operating system behind them.

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| Get Help completion | Youth need immediate help from any screen. | Keep global Get Help; add context-aware entry points in Storm, FlowQuest, red/yellow Safe Harbor. | Optional managed resource list. | Crisis resources are one click/tap away and tested on mobile. |
| Safety event model | Crisis events need persistence. | Show submitted/escalated state. | `SafetyEvent` model with source, severity, trigger, user, session, status. | Every crisis/mask/red event can be reviewed. |
| Safe Harbor escalation | Red/yellow must do something, not only display color. | Add action panels and mentor alert status. | Create/transition safety events; alert mentors/case workers. | Red Safe Harbor creates a trackable alert. |
| Mandatory reporting workflow | Abuse/neglect/imminent danger disclosures require action. | Mentor reporting wizard and templates. | Jurisdiction/configurable reporting records, supervisor notification, audit log. | Mentor can document report decisions and follow-up. |
| Human review queue | AI alone should not own safety decisions. | Mentor/case-worker alert inbox. | Alert assignment, acknowledgement, resolution, timestamps. | Alerts have owners and SLA state. |
| Post-crisis follow-up | Safety does not end after the hotline panel. | Follow-up checklist and next safe step UI. | Follow-up tasks, reminders, status history. | Crisis events have next-step tracking. |
| Quick exit/privacy affordance | Trauma-informed apps often need quick hide/exit. | Add optional quick-exit behavior and privacy copy. | None unless audited. | Youth can leave sensitive screens quickly. |

### 3. AI Safety And Youth-Appropriate Content

FlowZone uses LLMs. Production needs guardrails before and after model calls.

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| Input crisis classifier | Self-harm, violence, abuse, grooming, and danger need detection. | Show safety card when triggered. | Classifier/moderation layer before normal response flow. | High-risk text creates a safety event. |
| Output moderation | AI responses must be appropriate for youth. | Show fallback response if blocked. | Post-process AI output for self-harm, legal/medical overreach, unsafe advice. | Unsafe response is blocked or rewritten. |
| PII redaction policy | Current sanitizer flags PII but stores text unchanged. | Explain privacy and redaction clearly. | Decide flag vs redact by data type; store flags and redacted version. | PII handling is intentional and test-covered. |
| Not-therapy boundary | Prevent misleading mental-health claims. | Plain-language disclaimer in auth, chat, crisis, profile. | System prompts and policy checks. | App never presents itself as a therapist/emergency service. |
| Human escalation from AI | AI should route serious issues to humans. | Show "mentor notified" or "talk to someone" states. | Link moderation results to alert workflow. | Serious events are not silently handled by chatbot only. |

### 4. Youth Onboarding And Plain-Language Setup

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| First-run onboarding | New users should understand the app before seeing scores. | Short walkthrough after register. | Store onboarding completion. | New users see purpose, privacy, and next step. |
| Replace "Strategic Intake" language | Current copy can feel institutional. | Rename to "Your Setup" or "Getting to Know You". | Preserve API if answer schema stays. | Youth-friendly copy tested with target users. |
| Character explanation | Character assignment should feel transparent. | Explain why a character was assigned and how to change later. | Store preference/change history if editable. | Youth understands character routing. |
| Easy Read mode | Literacy levels vary. | Simpler copy toggle and lower reading level. | Optional preference storage. | Major flows have plain-language alternatives. |
| Language/i18n foundation | Non-native English users need access. | Set up i18n structure. | Optional localized managed content. | UI strings can be translated without rewrites. |

### 5. Core Wellness Toolkit

Competitive research shows FlowZone is unique in mentor coordination but lacks standard evidence-based wellness tools.

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| Grounding/breathing tools | Immediate anxiety support; low implementation cost. | Build short guided tools, timers, reduced-motion option. | Store completion only if it affects trust score. | User can complete a reset without chat. |
| Trauma-informed CBT library | Generic CBT is not enough for this audience. | Exercise library for thoughts, traps, court anxiety, anger, grief. | Content model/progress records if assigned/tracked. | Exercises are age-appropriate and reviewable. |
| Journaling | Competitors use thought journals and prompts. | Private journal and mentor-assigned prompt UI. | Journal model, visibility rules, optional mentor prompts. | Youth knows which journal entries are private/shared. |
| Sleep support for unstable environments | Foster/group-home youth may need short, practical sleep tools. | Short audio/text routines, sleep diary. | Optional sleep log endpoint. | Sleep tools do not assume a quiet home. |
| Emotion check-ins | Vibe Check should become a real daily wellness signal. | Already started; add already-checked-in-today state. | Daily check-in status/history endpoint. | Duplicate check-ins are handled clearly. |
| Personalized next steps | Youth need useful suggestions after check-ins. | Recommended exercise/action cards. | Recommendation rules based on vibe/history. | Recommendations come from real state, not random UI. |

### 6. Dashboard And Daily Youth Experience

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| Real activity feed | Dashboard fake data destroys trust. | Replace `genActivities()`. | Add activity feed endpoint. | Every item maps to a backend event. |
| Real trust chart | Trust trends must be explainable. | Use trust history endpoint. | Existing history may need richer event reasons. | Chart matches backend data. |
| Active session controls | Users need control of FlowQuest sessions. | Wire resume/end states and errors. | Existing end endpoint. | END button updates UI correctly. |
| Tactical reset | Button currently needs real behavior. | Build reset flow or disable until ready. | Store completion if score-affecting. | No dead controls remain. |
| Daily plan | Youth need a simple "what now?" screen. | Show today: check-in, reset, session, task. | Activity/task/check-in endpoints. | Dashboard gives one clear next step. |

### 7. FlowQuest, Voice, And Conversation History

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| Stable WebSocket lifecycle | Current dependency loop can reconnect on message changes. | Split socket lifecycle from polling. | Existing WS may be enough. | New messages do not recreate sockets. |
| Manual reconnect | Users need actionable connection states. | Add reconnect button/status copy. | Existing WS may be enough. | Disconnected state is clear and recoverable. |
| Real transcript drawer | Session history currently maps messages to empty arrays. | Fetch chat history on detail open. | Existing endpoint exists. | Drawer shows real messages. |
| Voice in FlowQuest | Inline mic is simulated. | Reuse `Voice.tsx` capture/transcribe/send path or remove mic. | Existing voice endpoints. | No fake voice messages in production. |
| Conversation deletion clarity | Session deletion affects transcripts but not trust history. | Explain before delete. | Existing delete endpoint; audit event later. | User knows what is deleted and retained. |
| Conversation summaries | Mentors/youth need digestible context. | Show summaries where allowed. | Existing summarizer can be expanded. | Long sessions have safe, permissioned summaries. |

### 8. Trust, Rewards, Badges, And Meaningful Gamification

Gamification should support engagement, not pretend to be clinical treatment.

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| Transparent trust details | Youth need to understand score changes. | Replace mock formula/history with real event data. | Rich trust history with component deltas/reasons. | Every visible score has a traceable reason. |
| Real vouch history | Hardcoded Coach Ray content must go. | Use vouches/rewards endpoints. | Existing vouch route may need display fields. | Vouches are real and permissioned. |
| Honest redemption | Current frontend can show success after API failure. | Remove false success fallback. | Return clear failure details. | Score changes only after backend success. |
| Badge engine | Profile badges are static. | Earned/locked/in-progress badge UI. | Achievement rules and event processing. | Badges represent real behavior. |
| Mentor recognition | Youth want positive feedback. | Shout-outs/recognition cards. | Mentor recognition events with limits/audit. | Encouragement is real and safe. |
| Purposeful streaks | Streaks should not punish vulnerable users. | Add compassionate streak recovery copy. | Streak rules and missed-day handling. | Streaks motivate without shame. |

### 9. Documents, RAG, Court, And Probation Support

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| Upload progress and validation | Large uploads need feedback and safe limits. | Progress/cancel UI, allowed type copy. | Size/type limits, streaming, scan hook. | Uploads cannot exhaust memory. |
| Document status timeline | Users need to know processing state. | Pending/processing/verified/failed timeline. | Status/error fields if missing. | Failed extraction has recovery action. |
| Court/probation reminders | Differentiator for justice-involved youth. | Court date, probation tasks, prep tools. | Court/probation event model and reminders. | Youth can see and prepare for requirements. |
| Progress reports | Case workers/courts may need summaries. | Export/report UI for authorized roles. | Report generation, redaction, audit log. | Reports are permissioned and reproducible. |
| Search quality | RAG results need context and trust. | Source snippets, tags, filters. | Metadata/source refs and permissions. | User knows why result appeared. |
| Google Drive completion | Sync is currently stubbed. | Hide until real or show "coming soon". | Real OAuth state, token storage, sync job. | Drive sync does not expose unfinished behavior. |

### 10. Mentor, Case Worker, Guardian, And Family Workflows

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| Mentor roster polish | Existing roster is a foundation. | Improve filters, sorting, risk priority, empty states. | Existing endpoint plus alert/activity data. | Mentor can quickly prioritize youth. |
| Youth detail workspace | Mentors need one place for context. | Tabs for profile, sessions, notes, alerts, documents, trends. | Relationship/permission checks and richer data. | Mentor can act without hunting through pages. |
| Case worker dashboard | Competitive research identifies this as a differentiator. | Caseload dashboard and report tools. | Case-worker role, assignments, alerts, reports. | Case worker can manage multiple youth. |
| Guardian/parent portal | Needed only after consent and visibility rules. | Limited view of approved data. | Guardian relationships, consent, permissions. | Guardians see only allowed information. |
| Family communication | Long-term support feature. | Secure family messages/activities. | Family accounts, moderation, consent, audit. | Communication cannot bypass safety rules. |
| Mandatory reporter tools | Mentors/case workers need compliant workflows. | Reporting templates and supervisor escalation. | Reporting records and jurisdiction config. | Required reports are documented. |

### 11. Privacy, Consent, Data Rights, And Compliance

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| Privacy policy and terms | Required before real youth use. | Link before registration and in profile/nav. | Static first; version tracking later. | User can review before account creation. |
| "Who can see my data?" | Trust depends on visibility clarity. | Data visibility page and inline callouts. | Visibility rules endpoint or documented matrix. | Youth can tell who sees transcripts, scores, docs, notes. |
| Multi-party consent | Youth, guardians, courts, mentors may all be involved. | Age-aware assent/consent UX. | Consent records with version, actor, timestamp. | Consent can be audited. |
| COPPA/FERPA/KOSA readiness | Minors and school data require care. | Default privacy settings and clear notices. | Data minimization, retention, deletion, audit, school data controls. | Compliance requirements are mapped and implemented. |
| Data export | Users/programs may need records. | Export request/download UI. | Export endpoint with redaction and permissions. | Allowed data can be exported. |
| Deletion/retention | Soft-delete exists, but policy is unclear. | Account/data deletion UI with explanation. | Retention policy, deletion jobs, audit events. | Users know what is deleted and retained. |
| Audit trail | Sensitive youth data access must be traceable. | Admin/mentor views only if needed. | Audit event model for access, edits, exports, alerts. | Staff actions can be reviewed. |

### 12. Notifications, Peer Support, And Long-Term Engagement

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| Reminder preferences | Youth should control nudges. | Preference UI. | Preference storage. | Users can turn reminders on/off. |
| Check-in reminders | Streak systems need support. | Opt-in UI and in-app notification view. | Notification scheduler/provider. | Reminders respect user settings. |
| Mentor nudges | Mentors need safe follow-up. | Nudge templates. | Rate-limited notification endpoint and audit. | Nudges are logged and not spammy. |
| Moderated peer support | Competitive gap, but high risk. | Topic groups, no DMs/downvotes, safety copy. | Moderation, queue, reporting, mentor visibility. | Peer support cannot become unmonitored messaging. |
| Family wellness activities | Protective factor for some youth. | Shared activities where consent allows. | Family role, permissions, audit. | Family tools are opt-in and safe. |

### 13. Reliability, Observability, And Testing

| Feature | Why It Matters | Frontend Work | Backend Work | Done When |
|---|---|---|---|---|
| Node/tooling baseline | Current local Node blocks validation. | Document/use Node 20.19+ or 22.12+. | CI uses same runtime. | Build and lint run locally and in CI. |
| Error boundaries | No blank screens during crisis moments. | App/route/feature error boundaries. | Optional error reporting. | Component crash shows recovery UI. |
| Monitoring | Production issues must be visible. | Sentry or equivalent frontend reporting. | Backend error metrics/logging. | Errors include route/request id where safe. |
| E2E tests | Youth flows need regression coverage. | Tests for auth, Get Help, Vibe, FlowQuest, dashboard, rewards, documents. | API contract fixtures. | CI blocks broken core flows. |
| Backend security tests | Critical backend protections need tests. | None. | Tests for RBAC, demo guard, mentor notes, uploads, WS auth. | Known security regressions fail CI. |
| Performance budget | Mobile users may have slow devices/networks. | Bundle/image budgets, code splitting. | No backend needed. | Main flows meet load budget. |
| Accessibility checks | At-risk users may need assistive tech. | Labels, focus, live regions, skip links, reduced motion. | No backend needed. | axe/manual checks pass critical flows. |

---

## Backend Contracts Needed

The backend already has useful foundations: auth, profile, rainbow/rewards, vibe checks, sessions, chat, WebSocket, voice, trust, vouches, mentor roster/dashboard/notes, documents, and RAG search. These contracts are still needed or need hardening.

| Contract | Needed By | Suggested Shape / Notes |
|---|---|---|
| RBAC permissions | Admin, mentors, case workers, guardians | Add roles/permissions beyond `youth` and `mentor`; enforce in dependencies. |
| Safety events | Crisis, Safe Harbor, AI moderation | `POST /api/v1/safety/events`, `GET /api/v1/safety/events/{id}`. |
| Mentor/case-worker alert queue | Safety operations | `GET /api/v1/mentors/alerts`, acknowledge, assign, resolve. |
| Mandatory reporting records | Legal/safety workflow | Reporting record with jurisdiction, reason, reporter, status, timestamps. |
| Activity feed | Dashboard | `GET /api/v1/users/{id}/activity?limit=20` with typed events. |
| Daily check-in status/history | Dashboard, Vibe Check | `GET /api/v1/checkins/today`, `GET /api/v1/checkins/history`. |
| Wellness exercises | CBT, grounding, sleep | Exercise catalog, completion records, optional assignments. |
| Journals/prompts | Journaling, mentor assignments | Journal visibility rules: private, shared with mentor, reportable. |
| Achievement state | Badges/rewards | Earned/locked/in-progress badge list and unlock events. |
| Rich trust history | Trust page | Component deltas, event reason, source object, timestamp. |
| Password reset | Auth | Request reset, verify token, set password. |
| Refresh/session metadata | Auth | Refresh endpoint or explicit expiry response. |
| Preferences | Theme, reminders, accessibility | User preferences for notifications, theme, reduced motion, language. |
| Consent records | Compliance | Consent version, actor, youth/guardian/court role, timestamp. |
| Data export | Privacy/reporting | Export request/download with redaction and audit. |
| Audit events | Compliance/security | Access/edit/export/delete/admin/safety action logs. |
| Scheduled jobs | Trust economy | Run credit decay, vouch expiration, reminders, stale session cleanup. |
| Document upload hardening | Documents/RAG | File size/type validation, scanning hook, processing status/errors. |
| Court/probation records | Justice-specific feature | Court dates, probation requirements, completion evidence, reports. |

---

## Release Plan

### Release 0: Production Safety Gate

Goal: eliminate unsafe production conditions before expanding features.

- Standardize Node and CI so build/lint/tests run.
- Add real RBAC/admin authorization.
- Block demo mode in production.
- Enforce mentor role on note submission.
- Add upload size/type validation.
- Add error boundaries and 404.
- Fix FlowQuest WebSocket lifecycle.
- Remove false-success reward redemption.
- Keep existing Get Help UI, but add tests and context-aware entry points.

### Release 1: Safe Youth MVP

Goal: a youth can use the app safely with real data.

- Add safety event backend and mentor alert queue.
- Add storm/red Safe Harbor action panels.
- Wire dashboard trust chart/activity to real APIs.
- Wire active session END.
- Wire real transcript drawer.
- Replace FlowQuest fake mic with real voice flow or remove it.
- Add key accessibility fixes: labels, live regions, skip link, icon labels.

### Release 2: Trustworthy Gamification And Daily Use

Goal: scores, rewards, badges, and streaks become real.

- Rich trust history.
- Real vouch history.
- Achievement/badge engine.
- Tactical reset flow.
- Daily check-in state and reminders foundation.
- Mentor recognition/shout-outs with limits and audit.
- Remove hardcoded Coach Ray/demo content.

### Release 3: Evidence-Based Wellness Toolkit

Goal: FlowZone becomes more than chat and scores.

- Grounding/breathing tools.
- Trauma-informed CBT exercise library.
- Journaling with privacy controls and optional mentor prompts.
- Sleep support for unstable environments.
- Personalized next-step recommendations.
- Plain-language/Easy Read mode.

### Release 4: Compliance And Data Rights

Goal: youth data handling is explicit, auditable, and legally defensible.

- Privacy policy, terms, and "Who can see my data?" page.
- Multi-party consent records.
- Account deletion/deactivation UX backed by retention policy.
- Data export.
- Audit events for sensitive access/actions.
- COPPA/FERPA/KOSA compliance mapping.

### Release 5: Mentor, Case Worker, And Program Operations

Goal: professional users can coordinate care and document outcomes.

- Youth detail workspace.
- Case worker dashboard.
- Mandatory reporting workflow.
- Court/probation reminders and reports.
- Program analytics that do not expose unnecessary youth data.

### Release 6: Long-Term Differentiators

Goal: build defensible product depth after safety and compliance are stable.

- Moderated peer support with no DMs/downvotes.
- Family communication and shared activities.
- Multi-language support.
- Offline support for selected resources.
- Wearable integrations only if privacy/consent model is ready.
- AI personalization only after moderation/audit systems are mature.

---

## Product Quality Bar

A feature is not production-ready unless all of these are true:

- It uses real backend data or is explicitly demo-only.
- It has loading, empty, error, and retry states.
- It works on mobile and desktop.
- It supports keyboard and screen readers.
- It has safe copy that does not imply surveillance, judgment, or therapy replacement.
- It does not expose unauthorized data.
- It has backend permission checks where data is sensitive.
- It has audit/retention behavior if it touches youth safety, privacy, reports, or staff actions.
- It has a test plan.
- It is represented in the design system, not one-off inline styling.

---

## Stale Or Corrected Audit Items

Do not carry these forward as written:

- "No crisis intervention UI" is now partly stale. Static Get Help UI exists. Backend escalation and operational safety workflows are still missing.
- "Document access lacks auth" is stale. The current document routes check `user_id` against `current_user.id`. Upload validation is still missing.
- "Voice recording is fake" is only true for the inline FlowQuest mic. `Voice.tsx` uses real browser recording and voice APIs.
- "Session timeout is never used" is partly stale. Start/resume checks a timeout window, but there is no background cleanup, warning UI, or scheduled enforcement.
- "Dashboard mock data regenerates on every render" is overstated. It is generated on mount, but it is still fake and must be replaced.

---

## Open Product Decisions

These need owner decisions before implementation:

1. Who can see youth transcripts: youth only, mentors, case workers, guardians, admins?
2. What exact workflow happens after Storm or red Safe Harbor?
3. Which staff roles exist: mentor, case worker, guardian, admin, supervisor?
4. Are rewards real-world permissions, in-app recognition, or both?
5. What is the retention policy for chats, voice transcripts, documents, safety events, and deleted accounts?
6. What jurisdictions or programs define mandatory reporting requirements?
7. Which notification channels are allowed: in-app, email, SMS, push?
8. Is demo mode allowed outside local development?
9. Should light mode ship in the first production release or after the safety MVP?
10. Will peer support be part of the product, or intentionally excluded for safety?

