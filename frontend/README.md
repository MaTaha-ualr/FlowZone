# FlowZone Frontend

## Trust Engine & Gamified Support Framework

The official React frontend for the FlowZone backend — a multi-model AI chatbot platform with adaptive characters, trust scoring, and gamified workflows for high-risk youth (ages 12-18).

---

## Tech Stack

- **React 19** + TypeScript
- **Vite 7.2.4**
- **Tailwind CSS v3.4.19** + shadcn/ui
- **Framer Motion** — animations
- **Recharts** — data visualization
- **Lucide React** — icons
- **date-fns** — date formatting

---

## Backend API

This frontend connects to the FlowZone FastAPI backend:

**Deployed**: served from the same Railway FastAPI service.

**OpenAPI Docs**: `/docs` on the deployed service

---

## Pages (14 Total)

| Page | Route | Description |
|------|-------|-------------|
| Landing | `/` | Cinematic hero, persona showcase, Trust Engine formula |
| Login | `/login` | JWT authentication |
| Register | `/register` | Account creation with youth/mentor roles |
| Strategic Intake | `/intake` | 5-question onboarding flow |
| Dashboard | `/dashboard` | Youth hub — trust score, streak, quick actions |
| Vibe Check | `/vibe-check` | Interactive mood selector with character assignment |
| FlowQuest | `/flowquest/:sessionId` | WebSocket chat with AI characters |
| Session History | `/sessions` | Past FlowQuest logs |
| Trust Detail | `/trust` | Full formula breakdown (C + W + H + R + M - P) / T |
| Rewards | `/rewards` | Vouch store with tier gating |
| Profile | `/profile` | Player stats, Rainbow Circle, badges |
| Documents | `/documents` | RAG document vault with search |
| Voice | `/voice` | STT + TTS interface |
| Mentor Dashboard | `/mentor/dashboard` | Coach Ray's youth roster |
| Mentor Notes | `/mentor/notes/:userId` | Per-youth journal |

---

## Quick Start

```bash
# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

---

## Connecting to Your Backend

Set the `VITE_API_URL` environment variable:

```bash
# .env file
VITE_API_URL=https://your-backend-url.com
```

If not set, browser requests use the same origin as the frontend. Use `VITE_API_URL=http://localhost:8000` only for local Vite development against a local FastAPI server.

---

## Deployment

The built `dist/` folder is a static site ready for any host:

- **Vercel**: `vercel --prod`
- **Netlify**: Drag `dist/` folder to Netlify Drop
- **GitHub Pages**: Push `dist/` to `gh-pages` branch
- **Railway**: Connect repo, set build command to `npm run build`
- **AWS S3**: Upload `dist/` contents to S3 bucket

---

## FlowZone Terminology

Consistent language throughout the app:
- **FlowQuest** — chat session (not "chat")
- **Strategic Intake** — 5-question onboarding (not "onboarding")
- **Trust Engine** — scoring system (not "gamification")
- **Safe Harbor** — status levels (not "status")
- **The Dump** — voice/text vent (not "message")
- **Tactical Action** — action items (not "task")
- **Vibe Check** — mood selector (not "mood check")
- **Vouch** — redeemable rewards (not "reward")
- **Mask** — detected inconsistency (not "lie")
- **Character** — AI voice (not "AI personality")

---

## Target Personas

All content references the 5 test personas:

1. **Marcus Cole** — 15, JJ, Memphis, basketball goal, GPA 1.8
2. **Aaliyah Jenkins** — 16, JJ, defending sibling, grade collapse
3. **Jordan Rivera** — 14, at-risk, non-binary, poetry writer
4. **DeShawn Mitchell** — 15, at-risk, grieving brother, star athlete
5. **Kaya Thompson** — 14, foster, 3rd home, positive masking

---

## License

MIT — Built for high-risk youth everywhere.
