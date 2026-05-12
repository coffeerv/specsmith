# SpecSmith Web (PoC)

A minimal React + Vite frontend whose primary job is to demo the inspectable provenance trail returned by `POST /specify`.

Design and scope are defined in [`../docs/specsmith-web-frontend-poc.md`](../docs/specsmith-web-frontend-poc.md). When this code and that brief disagree, the code wins.

## Prereqs

- Node 20+
- A running SpecSmith backend (see the repo-root README).

## Install and run

```bash
cd web
npm install
npm run dev
```

The dev server starts on `http://localhost:5173` and calls the backend at the URL set in `VITE_SPECSMITH_API_BASE_URL` (defaults to `http://localhost:8000`). Copy `.env.example` to `.env.local` to override.

## Scripts

- `npm run dev` — Vite dev server with HMR
- `npm run build` — type-check and build to `dist/`
- `npm run preview` — preview the production build
- `npm test` — run Vitest unit tests once
- `npm run test:watch` — Vitest in watch mode

## What this frontend does (and doesn't)

It does: compose a SpecScript, attach screenshots, submit to `/specify`, render the returned spec and trace, cross-link findings to the trace entry that produced them, expose the full critique prompt under its trace row.

It does not: persist runs, share links, authenticate users, stream per-node progress, or ship a dark mode. Those are deferred.
