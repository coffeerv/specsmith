import { useEffect, useState } from "react";
import clsx from "clsx";
import {
  Banner,
  Button,
  Pill,
  Section,
  Segmented,
  Skeleton,
} from "../primitives";
import type { Finding, Spec } from "../../types/specsmith";
import { findingKey, useLink } from "../../state/linking";
import { serializeSpec } from "../../utils/format";
import "./spec-column.css";

const STORAGE_KEY = "specsmith.spec-view";
type View = "rendered" | "json";

type Props = {
  spec: Spec | null;
  loading: boolean;
  error: { status: number; message: string; runId: string | null } | null;
};

export function SpecColumn({ spec, loading, error }: Props) {
  const [view, setView] = useState<View>(() => {
    const stored = typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    return stored === "json" ? "json" : "rendered";
  });

  useEffect(() => {
    if (typeof localStorage !== "undefined") localStorage.setItem(STORAGE_KEY, view);
  }, [view]);

  return (
    <Section
      className="spec-column"
      title="Spec"
      actions={
        <Segmented<View>
          ariaLabel="Spec view"
          value={view}
          onChange={setView}
          options={[
            { value: "rendered", label: "Rendered" },
            { value: "json", label: "JSON" },
          ]}
        />
      }
    >
      {error ? (
        <Banner
          title={`Request failed (${error.status || "network"})`}
          meta={error.runId ? `run ${error.runId}` : undefined}
        >
          {error.message}
        </Banner>
      ) : null}

      {loading && !spec ? <SpecSkeleton /> : null}

      {spec && view === "rendered" ? <RenderedSpec spec={spec} /> : null}
      {spec && view === "json" ? <JsonSpec spec={spec} /> : null}
    </Section>
  );
}

function SpecSkeleton() {
  return (
    <div className="spec-skeleton">
      <Skeleton height={24} width="60%" />
      <Skeleton height={14} width="40%" />
      <Skeleton height={14} width="90%" />
      <Skeleton height={14} width="80%" />
      <Skeleton height={14} width="70%" />
    </div>
  );
}

function RenderedSpec({ spec }: { spec: Spec }) {
  const findings = spec.findings ?? [];
  return (
    <div className="rendered-spec">
      {spec.title ? <h2 className="rendered-spec__title">{spec.title}</h2> : null}
      <div className="rendered-spec__meta">
        {spec.type ? <Pill>{String(spec.type)}</Pill> : null}
        {typeof spec.status === "string" ? <Pill>{spec.status}</Pill> : null}
      </div>

      {renderList("Objectives", spec.objectives)}
      {renderList("Functional requirements", spec.functional_requirements)}
      {renderList("Non-functional requirements", spec.non_functional_requirements)}
      {renderList("Metrics", spec.metrics)}
      {renderList("Risks", spec.risks)}
      {renderList("Open questions", spec.open_questions)}
      {renderStories(spec.user_stories)}

      {findings.length > 0 ? (
        <div className="findings">
          <h3 className="findings__title">Findings ({findings.length})</h3>
          <ul className="findings__list">
            {findings.map((f, idx) => (
              <FindingRow key={findingKey(f, idx)} finding={f} index={idx} />
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function renderList(label: string, items: unknown) {
  if (!Array.isArray(items) || items.length === 0) return null;
  return (
    <div className="rendered-section">
      <h3 className="rendered-section__title">{label}</h3>
      <ul className="rendered-section__list">
        {items.map((it, i) => (
          <li key={i}>{typeof it === "string" ? it : JSON.stringify(it)}</li>
        ))}
      </ul>
    </div>
  );
}

function renderStories(stories: unknown) {
  if (!Array.isArray(stories) || stories.length === 0) return null;
  return (
    <div className="rendered-section">
      <h3 className="rendered-section__title">User stories</h3>
      <ul className="rendered-section__list">
        {stories.map((s, i) => {
          if (typeof s !== "object" || s === null) {
            return <li key={i}>{String(s)}</li>;
          }
          const story = s as Record<string, unknown>;
          const as_a = String(story.as_a ?? "");
          const i_want = String(story.i_want ?? "");
          const so_that = String(story.so_that ?? "");
          const ac = Array.isArray(story.acceptance_criteria)
            ? (story.acceptance_criteria as unknown[])
            : [];
          return (
            <li key={i} className="story">
              <div>
                As a <em>{as_a}</em>, I want <em>{i_want}</em>, so that <em>{so_that}</em>.
              </div>
              {ac.length > 0 ? (
                <ul className="story__ac">
                  {ac.map((a, j) => (
                    <li key={j}>{String(a)}</li>
                  ))}
                </ul>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function FindingRow({ finding, index }: { finding: Finding; index: number }) {
  const key = findingKey(finding, index);
  const {
    setHoveredFinding,
    togglePinnedFinding,
    findingIsLinked,
    entryForFinding,
  } = useLink();
  const linked = findingIsLinked(key);
  const hasTarget = Boolean(entryForFinding(key));
  const severity = finding.severity;

  return (
    <li
      className={clsx(
        "finding",
        `finding--${finding.kind}`,
        linked && "finding--linked",
      )}
      onMouseEnter={() => setHoveredFinding(key)}
      onMouseLeave={() => setHoveredFinding(null)}
    >
      <button
        type="button"
        className="finding__hit"
        onClick={() => hasTarget && togglePinnedFinding(key)}
        aria-pressed={linked}
        disabled={!hasTarget}
        title={hasTarget ? "Click to pin link to trace" : "No linked trace entry"}
      >
        <span className={clsx("finding__dot", `finding__dot--${severity}`)} aria-hidden />
        <Pill mono tone={finding.kind}>
          {finding.kind === "rule" ? finding.rule_id : finding.critique_prompt_id}
        </Pill>
        <span className="finding__msg">{finding.message}</span>
        {finding.target_field ? (
          <span className="finding__target">{finding.target_field}</span>
        ) : null}
      </button>
    </li>
  );
}

function JsonSpec({ spec }: { spec: Spec }) {
  const text = serializeSpec(spec);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* no-op */
    }
  }
  return (
    <div className="json-spec">
      <div className="json-spec__bar">
        <Button onClick={copy}>Copy</Button>
      </div>
      <pre className="json-spec__pre">{text}</pre>
    </div>
  );
}
