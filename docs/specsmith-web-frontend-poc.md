# SpecSmith — Web Frontend PoC

> Implementation brief in Spec Kit shape. Single-file handoff with compressed Spec / Plan / Tasks structure. This document defines a minimal React + Vite frontend whose primary job is to demo the inspectable provenance trail produced by `POST /specify`.

> **Status: not yet implemented.** This document is the source of truth for the initial build. When the code lands and diverges, the code wins and this file should be updated or annotated like its sibling brief in [`docs/specsmith-provenance-trail-poc.md`](specsmith-provenance-trail-poc.md).

This brief intentionally does not introduce a second Constitution. The project's principles are defined once in the provenance-trail brief and apply transitively here: scope discipline, additive changes, trace as a first-class artifact, and the structural separation of deterministic vs. probabilistic findings. The frontend exists to make those principles legible to a human looking at the screen.

## Implementation map

| Section in this brief | Authoritative implementation (once built) |
|---|---|
| Vite app shell, dev server, build config | `web/` (new directory at repo root) |
| Type bindings for `/specify` response | `web/src/types/specsmith.ts` |
| API client | `web/src/api/specify.ts` |
| Layout primitives (Row, Pill, Field, Section, Dropdown, Skeleton, Button) | `web/src/components/primitives/` |
| Trace column | `web/src/components/trace/` |
| Spec column | `web/src/components/spec/` |
| Input column | `web/src/components/input/` |
| Templates registry | `web/src/templates/` |
| Cross-linking state (hovered / pinned finding ↔ trace row) | `web/src/state/linking.ts` |
| Backend addition: `RuleFinding.produced_by_node` | [`models/trace.py`](../models/trace.py), validator call sites |

---

## Audience and intent

The intended viewer is a technical audience. The frontend should read as a thoughtful internal developer tool — restrained, type-driven, observability-flavored — not as a generic AI product. Specifically, it must avoid the visual shorthand that has come to signal "AI demo": gradient hero sections, glassmorphism, purple-to-pink palettes, emoji-as-icons, sparkle-decorated CTAs, oversized rounded cards floating on tinted backgrounds. It must also avoid the opposite failure mode of an enterprise portal designed by committee.

Reference aesthetics: Linear (restraint, single accent, tight type scale), Honeycomb / Datadog APM (trace row visual language, status dots, monospace for IDs and durations), Stripe Dashboard (structured-data presentation, quiet section headers).

---

## Spec

### What we are building

A single-page React application served from `web/` that lets a user:

1. Compose or paste a SpecScript, optionally attach screenshot(s), and submit it to `POST /specify`.
2. Read the returned spec in a rendered form, with deterministic `RuleFinding` and probabilistic `CritiqueFinding` items visually distinguishable.
3. Inspect the trace returned alongside the spec: per-node timing, status, input hash, output keys, model, and (for the `critique` node) the full prompt text.
4. Cross-link findings to the trace entry that produced them.
5. Load any of the README examples as a one-click template.

The frontend is a thin client. All orchestration, validation, and LLM work remains in the existing FastAPI backend. The frontend introduces no persistence and no auth.

### Outcomes

After this work is complete, the following must be true:

1. Running `npm run dev` inside `web/` starts a Vite dev server that talks to a local SpecSmith backend at `http://localhost:8000`.
2. A user can submit a SpecScript with zero, one, or multiple image attachments and receive a rendered spec plus a rendered trace.
3. Each of the three SpecScript variants shown in the README (text-only, single screenshot, multi-screenshot) is available as a one-click template in a `Template ▾` dropdown.
4. The trace column shows exactly the entries returned by the backend, in execution order, with timing, status, input hash, and output keys.
5. The `critique` trace row, when expanded, shows the full prompt text recorded under `prompts`.
6. Hovering a `CritiqueFinding` highlights the `critique` trace row (and vice versa). Hovering a `RuleFinding` highlights the trace row of the node that produced it (and vice versa).
7. A `Rendered / JSON` toggle in the Spec column header switches between a structured render and a copy-able JSON dump of the spec. The choice persists in `localStorage`.
8. If `TraceEntry.token_usage` is populated, the trace table shows an `in / out` column. If null across all entries, the column is omitted entirely.
9. The page renders without layout shift on initial load (fonts self-hosted, skeleton rows match real row dimensions).
10. The page passes WCAG 2.2 AA for the audited primary path: load templates, submit, read results, expand trace rows, toggle JSON.

### Out of scope

Do not build:

- Authentication, accounts, or any identity surface.
- Persistence of runs (no `localStorage` of history, no IndexedDB, no backend storage).
- Sharing or permalink URLs (`/runs/:id` etc.).
- Streaming or per-node progress over SSE/WebSocket.
- Dark mode (light only for this PoC; tokens authored so dark is a later swap).
- A "Re-run with edits" affordance (deferred to a later phase).
- A SpecScript syntax-aware editor (CodeMirror, Monaco). A styled `<textarea>` is sufficient.
- A component library (MUI, Chakra, Ant, Radix-themed, shadcn). Hand-roll the ~8 primitives needed.
- A markdown renderer. The spec is a structured object.
- A syntax highlighter (Prism, Shiki, Highlight.js). Prompt text is rendered as `<pre>` with mono font.
- A router. There is one screen.
- A state management library (Redux, Zustand, Jotai, etc.). React state and a small context for cross-linking is enough.
- Analytics, error reporting integrations, feature flags.
- A "Copy as cURL" affordance.
- Per-node live streaming UI. The trace arrives whole; do not fake progressive reveal.

### Functional requirements

#### FR-1. Single screen, three-column layout above a defined breakpoint

The page consists of one top bar and three primary regions: Input (left, ~32%), Spec (middle, ~40%), Trace (right, ~28%). Below 1100px viewport width, the Trace region collapses behind a tab adjacent to "Spec" within the middle region. The Input region remains visible at all viewport widths supported (≥768px).

#### FR-2. SpecScript input

The Input region exposes:

- A multi-line text field for the SpecScript, rendered in IBM Plex Mono.
- A file input accepting `image/*`, supporting multiple files, with each selection shown as a removable pill.
- An optional `target` selector (`PRD`, `Tech Spec`, `GitHub Spec`) reflecting the existing template set in [`templates/`](../templates/).
- A `Generate` button that submits the form.

The form must support submitting with only a SpecScript, only files, or both, mirroring the backend's tolerance.

#### FR-3. Template dropdown

A `Template ▾` dropdown at the top of the Input region offers at least the following entries, sourced from the README:

- `Blank`
- `Text-only PRD`
- `Single screenshot PRD`
- `Multi-screenshot PRD`

Selecting a template populates the SpecScript textarea verbatim. Templates that expect attachments show an inline hint instructing the user to attach the expected number of images; the frontend does not pre-attach fake files.

#### FR-4. Submission and loading state

When the user clicks `Generate`:

- The button becomes disabled and its label changes to `Generating…`.
- A 2px indeterminate progress bar appears under the top bar.
- The Spec and Trace regions render skeleton content matching the eventual output shape: the Trace region renders six greyed rows with node names already filled in (`ingest, classify, extract, critique, revise, render`).
- An elapsed timer ticks in the Trace region header (`elapsed 4.2s`).
- The frontend does not fake per-node progress; skeleton rows resolve to real rows together when the response lands.

#### FR-5. Spec rendering

The Spec region renders the response's `spec` object as structured sections. At minimum: `title`, `type`, top-level prose blocks (e.g. goals, acceptance, metrics, NFRs as present), and a `Findings` section that groups by `kind`.

`RuleFinding` and `CritiqueFinding` items render with distinct visual treatment so a reader can tell deterministic from probabilistic at a glance: differing left-edge color (validator vs. critique), a `kind` pill, and either `rule_id` or `critique_prompt_id` shown in mono.

Severity (`info`, `warn`, `error`) is conveyed by a small leading dot, not by a colored background.

#### FR-6. Spec view toggle

The Spec region header includes a segmented `Rendered / JSON` toggle. The JSON view shows the entire `spec` object pretty-printed with two-space indentation, in IBM Plex Mono, with a single `Copy` button that uses `navigator.clipboard.writeText`. The user's choice persists across page loads in `localStorage` under a single key.

#### FR-7. Trace rendering

The Trace region renders one row per entry in `trace.entries`, in returned order. Each row shows, at minimum:

- A status dot.
- The node name in mono.
- Duration in mono, right-aligned (`240ms`, `2.1s`, `12,148ms` — choose a single unit policy and apply it consistently).
- The first 8 characters of `input_hash`, click-to-copy.
- The list of `output_keys` as a small secondary label.
- A chevron indicating expandability.

The region header shows total duration summed across entries and run ID (`6 nodes · 3.44s total · run a3f9…`).

#### FR-8. Trace row expansion

Clicking a row expands it inline (pushes subsequent rows down — no modal, no side drawer). The expanded panel shows:

- A key-value block: full `input_hash` with copy affordance, `output_keys`, `entry_id`, `model` (or `null`), `token_usage` (or `null`).
- If `prompts` is non-empty: a heading `Prompts` followed by, for each prompt, the `prompt_id` in mono and the full `prompt_text` in a monospace block with CSS-counter line numbers and a `Copy` button.

Only one row may be expanded at a time. Clicking the active row again collapses it. The expansion state is keyboard-accessible (Enter / Space toggle, arrow keys move focus between rows).

#### FR-9. Token usage column visibility

If any entry in `trace.entries` has a non-null `token_usage` with at least one numeric value, the trace table shows an additional `tok in / out` column for all rows. Entries with `token_usage: null` render an empty cell in that column. If all entries have `token_usage: null`, the column is omitted entirely; no `—` dashes are shown.

#### FR-10. Finding ↔ trace cross-linking

Hovering a finding in the Spec region applies an accent-blue 2px left border and a subtle background tint to the matching trace row, and vice versa. Cross-linking rules:

- `CritiqueFinding` links to the trace entry whose `prompts` includes a `PromptTrace.prompt_id` equal to the finding's `critique_prompt_id`. Today this is always the `critique` entry.
- `RuleFinding` links to the trace entry whose `node` equals the finding's `produced_by_node` (new backend field — see AD-7).

Clicking a finding or trace row toggles a pinned link that survives mouse-out and is dismissed with `Escape` or by clicking the pinned element again. Only one pinned link exists at a time.

#### FR-11. Error state

If `POST /specify` returns a non-2xx response, the Spec region shows a single-line error with the HTTP status and the response detail (when present), and the run ID in mono if the response included one. Any partial trace returned in the error body is still rendered in the Trace region. The page does not show a generic spinner without resolution; the loading state must terminate in either success or a visible error within the request lifetime.

#### FR-12. Input persistence across submissions

A successful or failed submission must not clear the SpecScript textarea, the `target` selector, or the attached file pills. The user may edit any of these and click `Generate` again to submit a fresh run. The previous response is replaced atomically on the next success; partial UI state (expanded trace row, pinned cross-link, JSON toggle) is reset on submission.

This is a frontend-only behavior. The backend remains stateless; each submission is an independent `/specify` call. No graph-topology change, no refinement node, no continuity of run state across submissions.

#### FR-13. Backend reachability

The frontend reads the backend base URL from `import.meta.env.VITE_SPECSMITH_API_BASE_URL`, defaulting to `http://localhost:8000` when unset. Requests use `fetch` with `multipart/form-data`. CORS is already permissive in the backend (`allow_origins=["*"]`), so no proxy is required for local development.

### Non-functional requirements

#### NFR-1. Stack minimalism

Runtime dependencies must be limited to: `react`, `react-dom`, `vite` (dev), `typescript` (dev), `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono`, and at most one additional small utility (e.g. `clsx`) if and only if it removes meaningful duplication. No router, no component library, no markdown renderer, no syntax highlighter, no state management library, no CSS-in-JS runtime, no icon library. Plain CSS (or CSS Modules) only.

Total production runtime dependencies must be ≤ 10 entries in `package.json` `dependencies`. Production bundle (uncompressed JS + CSS, excluding fonts) should be under 200KB; gzipped under 80KB. These are budgets, not asserts — exceeding them requires a written justification in the PR description.

#### NFR-2. Typography

UI text uses IBM Plex Sans. Technical content — SpecScript editor, hashes, run IDs, durations, node names, prompt text, JSON dumps — uses IBM Plex Mono. Both fonts are self-hosted via `@fontsource/*` packages, latin subset only, woff2 only. Tabular numerals (`font-feature-settings: "tnum"`) are enabled globally so timing and token columns align.

Body size 14.5–15px (Plex has a smaller x-height than Inter; do not use 14px without testing). Line-height 1.45 for body. Weights used: 400, 500, 600. Weight 700 is not used. Letter-spacing: 0 for body, +0.02em for ALL CAPS labels, -0.005em for the page title.

#### NFR-3. Color and surface

Light mode only for this PoC. Background `#FAFAFA`. Surface `#FFFFFF` on the three primary regions. Borders `#E5E5E7` at 1px hairline. Text primary near-black; secondary at ~60% opacity of primary. A single accent (a restrained blue, around `#2563EB`) is used only for the primary CTA, the active trace row, the cross-linking border, and focus rings. Status dots (8px) use green / amber / red without fills behind them. No drop shadows except a single soft shadow under the expanded trace row's content. No gradients anywhere.

Color tokens must be authored as semantic CSS variables (e.g. `--surface-1`, `--text-primary`, `--accent`, `--border-hairline`) so a future dark-mode pass is a stylesheet swap rather than a refactor.

#### NFR-4. Spacing and radius

Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 px. Border radii: 4–6px (no 8+). The three primary regions are separated by 1px hairlines, not by gaps.

#### NFR-5. Accessibility

The audited primary path (load template, submit, read spec, expand a trace row, toggle JSON) must pass WCAG 2.2 AA. Specifically:

- All interactive elements are real `<button>`, `<a>`, or `<input>` elements with associated labels.
- A visible focus ring (accent blue, 2px) is present on all focusable elements.
- Trace rows are keyboard-operable: focus moves via Tab, expansion toggles via Enter or Space, arrow keys move focus between rows when one row is focused.
- Color is not the sole signal for severity or for the rule-vs-critique distinction (icon shape, pill text, or position carries the same information).
- `prefers-reduced-motion` is honored: the elapsed-timer counter still ticks but skeleton shimmer and tint fades are disabled.
- The accent blue meets 4.5:1 contrast against `#FFFFFF` (verify with the chosen exact hex).

#### NFR-6. Performance budget

First contentful paint under 1s on a mid-range laptop on local dev. No layout shift during font load (fonts are self-hosted with `font-display: swap` and the layout reserves space using metric-matched fallbacks if needed). The trace table must handle 20 entries without perceptible jank, though the current backend emits exactly 6.

#### NFR-7. Build and tooling

The build is a standard Vite + React + TypeScript setup. Lint via `eslint` with `@typescript-eslint` and React rules; format via `prettier`. The frontend lives entirely under `web/`. No changes to the existing Python `requirements.txt`. The repo root `README.md` gains a short section pointing to `web/README.md` for frontend setup; `web/README.md` documents `npm install`, `npm run dev`, `npm run build`, and the `VITE_SPECSMITH_API_BASE_URL` environment variable.

#### NFR-8. No new external services at runtime

The frontend talks to the local SpecSmith backend only. It does not load fonts, scripts, analytics, or any other asset from a third-party origin at runtime. Fonts are bundled via the `@fontsource/*` packages, served from the same origin as the app.

---

## Plan

### Architecture decisions

#### AD-1. Vite + React + TypeScript, no framework

The frontend is a Vite SPA. No Next.js, no Remix, no SSR. There is no benefit to server rendering for a tool whose only useful state is the result of a user-initiated `POST`. TypeScript is on from the start because the response shape is structured enough that types pay for themselves on the first refactor.

#### AD-2. Single screen, three columns

The layout is one screen, three columns, fixed at the breakpoint defined in FR-1. The trace column is a peer of the spec column, not a hidden debug drawer. This is a deliberate UX choice: the inspectable provenance trail is the project's differentiator, and burying it would defeat the demo's purpose.

#### AD-3. No component library

The interaction surface is small enough that a component library would cost more in bundle size, theming friction, and visual conformity than it saves. The team will hand-roll a small primitives set (Button, Field, Pill, Row, Section, Dropdown, Skeleton, Banner) in plain CSS (or CSS Modules). If accessibility primitives become genuinely difficult to implement (focus traps, popover positioning), the team may add `@radix-ui/react-*` for those specific primitives only, not as a full library import.

#### AD-4. Hand-rolled trace and spec rendering

The Trace and Spec views are bespoke components, not driven by a generic JSON-tree renderer. The shapes are known and small enough that a custom renderer is shorter, faster, and reads better than configuring `react-json-view` or similar.

#### AD-5. Light mode first, semantic tokens

All color is authored as semantic CSS variables on `:root`. A future dark-mode pass adds a `[data-theme="dark"]` block that overrides token values. No component reads raw hex codes; all reads go through tokens. Dark mode is not shipped in this PoC.

#### AD-6. Cross-linking via discriminator-aware mapping

The frontend computes the mapping from finding to trace entry at render time, deterministically:

- For `CritiqueFinding`, scan `trace.entries` for the entry whose `prompts` includes a `prompt_id` equal to the finding's `critique_prompt_id`.
- For `RuleFinding`, scan `trace.entries` for the entry whose `node` equals the finding's `produced_by_node`.

The mapping is held in a small `Map<findingKey, entryId>` computed once per response and consumed by both the Spec and Trace columns. Hover and pinned-link state lives in a small React context, not a state library.

#### AD-7. Backend addition: `RuleFinding.produced_by_node`

To enable rule-finding cross-linking (FR-10), `RuleFinding` gains an optional `produced_by_node: NodeName` field. The validators that currently produce rule findings are called from inside specific graph nodes; the call sites populate `produced_by_node` with the name of the enclosing node. Older clients that ignore this field are unaffected. This is the only backend change introduced by the frontend brief, and it is justified by the UX cost of shipping rule findings as un-linked second-class citizens.

This change is additive and consistent with the existing brief's Constitution principle 3 (existing patterns preserved, additive changes).

#### AD-8. Templates as static module, not API

The three (or more) example SpecScripts are shipped as a static TypeScript module in `web/src/templates/`. They are not fetched from the backend, and the backend does not gain a `/templates` endpoint. This keeps the frontend reachable without the backend running for cold load and avoids coupling the demo's surface to backend state.

#### AD-9. State and loading discipline

There is no global state store. Form state is local to the input column. Response state (`{ spec, trace }`) lives in a single React state at the page level and is passed down. Cross-linking hover/pinned state lives in a small context provider scoped to the response. There is no router.

The loading state is binary at the level of the request (`idle | submitting | success | error`). Per-node progress is not simulated. The skeleton trace rows use the statically known pipeline order (`ingest, classify, extract, critique, revise, render`) so the wait reads as structured rather than as a generic spinner.

#### AD-10. JSON view via `JSON.stringify`, not a library

The Spec column's JSON view is `JSON.stringify(spec, null, 2)` rendered inside a `<pre>` with mono font. No syntax highlighter is installed. The same applies to prompt text in expanded trace rows: it is rendered with `white-space: pre-wrap` and CSS-counter line numbers, not via a code highlighter.

#### AD-11. Backend base URL from env, no proxy

The Vite dev server does not proxy `/specify`. The frontend reads `VITE_SPECSMITH_API_BASE_URL` at build time and calls the backend directly. This is acceptable because the backend already permits all origins in CORS. If that policy tightens, a Vite proxy can be added without code changes.

#### AD-12. Type binding strategy

The frontend defines TypeScript types that mirror the Pydantic models in [`models/trace.py`](../models/trace.py) and [`models/spec.py`](../models/spec.py) by hand, in `web/src/types/specsmith.ts`. No code generator is introduced for this PoC. The hand-written types are short enough that the maintenance cost is lower than the cost of adding `openapi-typescript` or similar to the build pipeline.

If and when the response shape grows, that decision should be revisited.

---

## Data contracts

### `/specify` response (consumed)

The frontend treats the existing response shape as canonical:

```ts
type NodeName =
  | "ingest"
  | "classify"
  | "extract"
  | "critique"
  | "revise"
  | "render";

type Severity = "info" | "warn" | "error";

type PromptTrace = { prompt_id: string; prompt_text: string };

type TraceEntry = {
  entry_id: string;
  run_id: string;
  node: NodeName;
  started_at: string;
  ended_at: string;
  duration_ms: number;
  input_hash: string;
  output_keys: string[];
  model: string | null;
  token_usage: Record<string, number> | null;
  prompts: PromptTrace[];
  status: "success";
};

type RuleFinding = {
  kind: "rule";
  rule_id: string;
  severity: Severity;
  target_field: string | null;
  message: string;
  produced_by_node?: NodeName;  // added by AD-7
};

type CritiqueFinding = {
  kind: "critique";
  critique_prompt_id: string;
  model: string;
  severity: Severity;
  target_field: string | null;
  message: string;
};

type Finding = RuleFinding | CritiqueFinding;

type Spec = {
  title?: string;
  type?: string;
  findings: Finding[];
  [key: string]: unknown;
};

type SpecifyResponse = {
  target: string;
  spec: Spec;
  trace: { run_id: string; entries: TraceEntry[] };
};
```

The frontend treats unknown spec fields as renderable prose blocks; it does not error on extra keys.

### Backend change introduced

`RuleFinding` gains an optional field:

```python
class RuleFinding(BaseModel):
    kind: Literal["rule"] = "rule"
    rule_id: str
    severity: Severity
    target_field: Optional[str] = None
    message: str
    produced_by_node: Optional[NodeName] = None
```

All current rule-finding call sites are updated to populate `produced_by_node`. No existing test should change in spirit; a single new assertion verifies the field round-trips and is populated by the validators that actually run inside graph nodes.

---

## Test plan

PoC-level, not exhaustive. The frontend is verified manually on the audited primary path and by a small set of unit tests on pure functions.

### Manual acceptance

Run against a local backend with `LLM_PROVIDER=offline` and again with a real provider:

1. Load the page. Confirm: three columns visible at ≥1100px, IBM Plex Sans rendered, no layout shift, no console errors.
2. Select `Text-only PRD` from the template dropdown. Confirm the textarea is populated with the README example verbatim.
3. Click `Generate`. Confirm: button disables, 2px indeterminate bar appears, skeleton trace rows render with the six node names, elapsed timer ticks.
4. On response: confirm spec renders, six real trace rows replace the skeletons, total duration shows in the trace header.
5. Toggle `Rendered / JSON` in the spec header. Reload the page. Confirm the choice persisted.
6. Click the `critique` trace row. Confirm it expands inline, the full prompt text is shown line-numbered in mono, and the `Copy` button copies the text to clipboard.
7. Hover a `CritiqueFinding`. Confirm the `critique` trace row gets the accent left border and tint. Click to pin. Press `Escape`. Confirm the pinned state clears.
8. Submit a SpecScript that produces a `RuleFinding`. Hover the finding. Confirm the matching trace row (whichever node produced it) is highlighted.
9. Run the same SpecScript twice. Confirm `input_hash` values match node-by-node in the trace, and that pins/expansions don't carry over between submissions.
10. Stop the backend, click `Generate`. Confirm a single-line error appears in the Spec region; loading state resolves; no infinite spinner.

### Unit tests (frontend)

Pure-function tests, no DOM required:

1. **Linking map** — given a synthetic `SpecifyResponse`, `buildLinkMap(response)` returns a map where each `CritiqueFinding` resolves to the entry whose `prompts` matches its `critique_prompt_id`, and each `RuleFinding` resolves to the entry whose `node` matches its `produced_by_node`. Findings without a resolvable target return `undefined` rather than throwing.
2. **Duration formatter** — `formatDuration(12_148)` → `"12.1s"`, `formatDuration(240)` → `"240ms"`, `formatDuration(0)` → `"0ms"`. Single unit policy; no negative durations.
3. **Token-column visibility** — `shouldShowTokenColumn(entries)` returns `false` for entries all having `token_usage: null`, `true` when at least one has a numeric value, and `false` for an empty list.
4. **Spec JSON serialization** — `serializeSpec(spec)` produces stable, two-space-indented output with sorted keys at the top level, suitable for the `Copy` button.

### Backend test (additive)

In `tests/provenance/`, add one test asserting that every `RuleFinding` produced by the existing example input now has `produced_by_node` populated, and that the value is a member of `NodeName`. No other provenance test should change in semantics.

---

## Tasks

Ordered, atomic, executable.

### T-1. Add `produced_by_node` to `RuleFinding`

Update [`models/trace.py`](../models/trace.py) to add `produced_by_node: Optional[NodeName] = None` to `RuleFinding`. Update every validator call site in the graph nodes (search for `RuleFinding(` and for the `_dedupe_findings` paths in [`agents/nodes.py`](../agents/nodes.py)) to populate the field with the enclosing node's name. Where validators are invoked from a utility module, pass the node name in at the call site rather than letting the utility guess.

**Done when:**

- `RuleFinding.produced_by_node` is set on every rule finding produced by the existing example input.
- The existing provenance tests still pass.
- A new test asserts the field is populated and is a valid `NodeName`.

### T-2. Scaffold `web/` with Vite + React + TypeScript

Create a new `web/` directory at the repo root with a minimal Vite + React + TypeScript template. Add `.gitignore` for `node_modules` and `dist`. Add `web/README.md` covering install, dev server, build, and the `VITE_SPECSMITH_API_BASE_URL` environment variable. The root `README.md` gains a one-sentence pointer to `web/README.md`.

**Done when:**

- `npm install && npm run dev` from `web/` starts the dev server on a known port without errors.
- `npm run build` produces a working `dist/`.
- `npm run lint` and `npm run format` are wired but not blocking.

### T-3. Self-host IBM Plex Sans and Mono

Install `@fontsource/ibm-plex-sans` and `@fontsource/ibm-plex-mono`. Import only the weights 400, 500, 600 and only the latin subset. Configure `font-display: swap`. Verify no third-party font requests are made at runtime by inspecting the network panel on a cold load.

**Done when:**

- Both fonts render on first paint without falling back to system fonts beyond the swap window.
- The network panel shows no requests to `fonts.googleapis.com` or any third-party origin.
- Tabular numerals are active globally.

### T-4. Define semantic color and spacing tokens

In `web/src/styles/tokens.css`, define the semantic variables described in NFR-3 and NFR-4: surface, border, text-primary, text-secondary, accent, status-info / status-warn / status-error, spacing scale, radii. No component reads raw hex codes. Apply tokens via a single `:root` block.

**Done when:**

- A grep across `web/src/components/` finds no hex codes outside `tokens.css`.
- Switching one token (e.g. `--accent`) updates the CTA, the active row, the focus ring, and the cross-linking border together.

### T-5. Define TypeScript types for the `/specify` response

Create `web/src/types/specsmith.ts` with the types listed in the Data contracts section. Mark `RuleFinding.produced_by_node` as optional (the frontend tolerates older responses).

**Done when:**

- The types compile.
- A discriminated-union narrowing on `kind` works for `Finding` without casts.

### T-6. Implement the API client

Create `web/src/api/specify.ts` exporting a `submitSpecify({ specscript, files, target })` function that POSTs `multipart/form-data` to `${BASE_URL}/specify` and returns a typed `SpecifyResponse`. Non-2xx responses throw a typed error carrying the HTTP status, the parsed body (when JSON), and any `run_id` extracted from it.

**Done when:**

- A manual call against a running backend returns a parsed response.
- A failure case (backend down, 4xx, 5xx) produces a typed error consumable by the UI.

### T-7. Implement layout primitives

In `web/src/components/primitives/`, build: `Button`, `Field`, `Pill`, `Row`, `Section`, `Dropdown`, `Skeleton`, `Banner`. Each in its own file with co-located CSS. Each is a real semantic element (no `<div>` as button). All focusable elements expose the 2px accent focus ring.

**Done when:**

- A primitives demo page (gated behind a dev-only route or a query param) shows every primitive in every state (hover, focus, disabled).
- Axe DevTools reports no critical violations on the primitives demo.

### T-8. Implement the Input column

Build `web/src/components/input/InputColumn.tsx` covering: template dropdown, SpecScript textarea, file input with removable pills, target selector, `Generate` button. Wire to the API client. Local form state only.

**Done when:**

- All three README templates load on selection.
- File pills can be removed before submission.
- Submitting with empty SpecScript and zero files is disabled (the button greys out).
- Form state (textarea, target, file pills) is preserved across submissions per FR-12; only the response-derived UI is reset on resubmit.

### T-9. Implement templates module

Create `web/src/templates/index.ts` exporting an array of `{ id, label, specscript, expectsFiles }`. Populate from the README examples. The Input column reads from this module.

**Done when:**

- Adding a new template to the array adds an entry to the dropdown with no other changes.
- Templates expecting files show the inline hint described in FR-3.

### T-10. Implement the Spec column

Build `web/src/components/spec/SpecColumn.tsx` covering: the `Rendered / JSON` toggle (with `localStorage` persistence), the rendered view (title, type, prose sections, findings grouped by kind), and the JSON view (`<pre>` with mono font and a `Copy` button).

**Done when:**

- The JSON `Copy` button writes to clipboard.
- Findings render with their `kind` pill, severity dot, and either `rule_id` or `critique_prompt_id` in mono.
- The toggle choice persists across page loads.

### T-11. Implement the Trace column

Build `web/src/components/trace/TraceColumn.tsx`: the region header (node count, total duration, run id), the trace table with the columns described in FR-7, and the inline-expand behavior described in FR-8. Implement the token-column visibility rule from FR-9.

**Done when:**

- Six rows render for the existing example.
- Expanding the `critique` row reveals the prompt with line numbers and a working `Copy` button.
- Only one row can be expanded at a time.
- Keyboard interactions described in NFR-5 work.

### T-12. Implement cross-linking

Build `web/src/state/linking.tsx` with a small context provider, a `buildLinkMap(response)` pure function, and hover/pin state. Spec rows and trace rows consume the context to apply the accent border and tint. Pinning toggles on click; `Escape` clears.

**Done when:**

- Hovering any finding highlights the correct trace row, and vice versa, for both `RuleFinding` (via `produced_by_node`) and `CritiqueFinding` (via `critique_prompt_id`).
- Pinning survives mouse-out and is cleared by `Escape` or by clicking the pinned element again.
- Cross-linking is unit-tested via the linking-map test in the Test plan.

### T-13. Implement loading and error states

Wire the page-level state machine (`idle | submitting | success | error`). On `submitting`: button disables, 2px indeterminate bar appears, skeletons render in Spec and Trace columns, elapsed timer ticks in the Trace header. On `error`: render the error banner described in FR-11; render any partial trace returned with the error. On `success`: replace skeletons with real content together (no staggered fake animation).

**Done when:**

- Killing the backend mid-submission resolves the loading state to a visible error.
- `prefers-reduced-motion` disables skeleton shimmer and tint fades but keeps the elapsed timer ticking.

### T-14. Add unit tests for pure functions

In `web/src/__tests__/` (using `vitest`, installed as a dev dependency), add tests for `buildLinkMap`, `formatDuration`, `shouldShowTokenColumn`, and `serializeSpec` as described in the Test plan. Tests must run via `npm test`.

**Done when:**

- `npm test` runs green locally.
- Each test asserts the cases listed in the Test plan.

### T-15. Manual acceptance pass and README update

Run the manual acceptance checklist against a local backend. Update `web/README.md` to record any deviations from this brief and to link back to it. Update the repo-root `README.md` with a `Web frontend (PoC)` section pointing to `web/README.md`. Keep both short.

**Done when:**

- Every item in the manual acceptance checklist passes.
- An outside reader can run the frontend against a local backend by reading only `web/README.md`.

---

## Acceptance check

The work is complete when, against a running local backend and the existing example inputs:

1. The page renders three columns at ≥1100px, in IBM Plex Sans and Plex Mono, with no layout shift on cold load and no third-party network requests.
2. Selecting any README template populates the SpecScript textarea verbatim and shows the appropriate attachment hint.
3. Submitting a SpecScript produces a rendered spec and a six-row trace; the `critique` row, expanded, shows the full prompt text line-numbered with a working `Copy` button.
4. Hovering a `CritiqueFinding` highlights the `critique` row. Hovering a `RuleFinding` highlights the row of the node named in its `produced_by_node`. Pinning and `Escape` behave as specified.
5. The `Rendered / JSON` toggle persists across reloads and copies the JSON correctly.
6. The `tok in / out` column is present when at least one entry reports usage, and absent otherwise — never showing dashes.
7. Stopping the backend mid-submission resolves to a visible error with the HTTP status; any partial trace is rendered.
8. The audited primary path passes WCAG 2.2 AA on Axe DevTools with no critical or serious violations.
9. `npm test` passes with the unit tests described in the Test plan.
10. Production runtime `dependencies` count ≤ 10 and gzipped bundle (excluding fonts) is under 80KB, or a justification appears in the PR description.

Anything beyond this is out of scope for this PoC and should be opened as a follow-up issue. Dark mode, re-run-with-edits, per-node streaming, and a hosted demo are explicitly deferred.
