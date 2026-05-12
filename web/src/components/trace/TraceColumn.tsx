import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import clsx from "clsx";
import { Button, Pill, Section, Skeleton } from "../primitives";
import { NODE_ORDER, type TraceEntry } from "../../types/specsmith";
import { useLink } from "../../state/linking";
import {
  formatDuration,
  formatTokens,
  shouldShowTokenColumn,
} from "../../utils/format";
import "./trace-column.css";

type Props = {
  entries: TraceEntry[];
  runId: string | null;
  loading: boolean;
  elapsedMs: number;
};

export function TraceColumn({ entries, runId, loading, elapsedMs }: Props) {
  const hasData = entries.length > 0;
  const totalMs = entries.reduce((acc, e) => acc + e.duration_ms, 0);
  const showTokens = shouldShowTokenColumn(entries);

  return (
    <Section
      className="trace-column"
      title="Trace"
      actions={
        <span className="trace-column__meta">
          {hasData ? (
            <>
              {entries.length} nodes · {formatDuration(totalMs)} total
              {runId ? (
                <>
                  {" · "}
                  <span className="mono">run {runId.slice(0, 8)}…</span>
                </>
              ) : null}
            </>
          ) : loading ? (
            <span className="mono">elapsed {formatDuration(elapsedMs)}</span>
          ) : (
            <span className="trace-column__placeholder">no run yet</span>
          )}
        </span>
      }
    >
      {hasData ? (
        <ol className="trace-list">
          {entries.map((entry) => (
            <TraceRow key={entry.entry_id} entry={entry} showTokens={showTokens} />
          ))}
        </ol>
      ) : loading ? (
        <ol className="trace-list trace-list--skeleton">
          {NODE_ORDER.map((node) => (
            <li key={node} className="trace-row trace-row--skeleton">
              <span className="trace-row__dot" aria-hidden />
              <span className="trace-row__node mono">{node}</span>
              <span className="trace-row__duration">
                <Skeleton height={12} width={48} />
              </span>
            </li>
          ))}
        </ol>
      ) : null}
    </Section>
  );
}

function TraceRow({
  entry,
  showTokens,
}: {
  entry: TraceEntry;
  showTokens: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const {
    setHoveredEntry,
    togglePinnedEntry,
    entryIsLinked,
  } = useLink();
  const rowRef = useRef<HTMLLIElement | null>(null);
  const linked = entryIsLinked(entry.entry_id);

  function onKey(e: KeyboardEvent<HTMLButtonElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const next = rowRef.current?.nextElementSibling;
      next?.querySelector<HTMLButtonElement>("button.trace-row__hit")?.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prev = rowRef.current?.previousElementSibling;
      prev?.querySelector<HTMLButtonElement>("button.trace-row__hit")?.focus();
    }
  }

  return (
    <li
      ref={rowRef}
      className={clsx(
        "trace-row",
        linked && "trace-row--linked",
        expanded && "trace-row--expanded",
      )}
      onMouseEnter={() => setHoveredEntry(entry.entry_id)}
      onMouseLeave={() => setHoveredEntry(null)}
    >
      <button
        type="button"
        className="trace-row__hit"
        aria-expanded={expanded}
        onClick={() => {
          setExpanded((v) => !v);
        }}
        onKeyDown={onKey}
        onDoubleClick={() => togglePinnedEntry(entry.entry_id)}
      >
        <span className="trace-row__dot trace-row__dot--success" aria-hidden />
        <span className="trace-row__node mono">{entry.node}</span>
        <span className="trace-row__duration mono">
          {formatDuration(entry.duration_ms)}
        </span>
        <span className="trace-row__hash mono" title={entry.input_hash}>
          {entry.input_hash.slice(0, 8)}
        </span>
        <span className="trace-row__keys">
          {entry.output_keys.slice(0, 3).join(", ")}
          {entry.output_keys.length > 3 ? "…" : ""}
        </span>
        {showTokens ? (
          <span className="trace-row__tokens mono">
            {formatTokens(entry.token_usage)}
          </span>
        ) : null}
        <span className="trace-row__chevron" aria-hidden>
          {expanded ? "▾" : "▸"}
        </span>
      </button>

      {expanded ? <TraceRowDetail entry={entry} /> : null}
    </li>
  );
}

function TraceRowDetail({ entry }: { entry: TraceEntry }) {
  const { togglePinnedEntry, pinnedEntry, findingCountForEntry } = useLink();
  const isPinned = pinnedEntry === entry.entry_id;
  const linkedCount = findingCountForEntry(entry.entry_id);

  async function copyHash() {
    try {
      await navigator.clipboard.writeText(entry.input_hash);
    } catch {
      /* no-op */
    }
  }

  return (
    <div className="trace-detail">
      <dl className="trace-detail__kv">
        <dt>entry_id</dt>
        <dd className="mono">{entry.entry_id}</dd>
        <dt>input_hash</dt>
        <dd className="mono">
          {entry.input_hash}{" "}
          <button type="button" className="link-btn" onClick={copyHash}>
            copy
          </button>
        </dd>
        <dt>output_keys</dt>
        <dd className="mono">{entry.output_keys.join(", ") || "—"}</dd>
        <dt>model</dt>
        <dd className="mono">{entry.model ?? "null"}</dd>
        {entry.token_usage ? (
          <>
            <dt>token_usage</dt>
            <dd className="mono">{JSON.stringify(entry.token_usage)}</dd>
          </>
        ) : null}
      </dl>

      <div className="trace-detail__actions">
        <Button
          onClick={() => togglePinnedEntry(entry.entry_id)}
          disabled={linkedCount === 0}
          title={
            linkedCount === 0
              ? "No findings were produced by this node"
              : `Highlights ${linkedCount} finding${linkedCount === 1 ? "" : "s"} in the Spec column`
          }
        >
          {isPinned
            ? `Unpin (${linkedCount})`
            : linkedCount === 0
              ? "No linked findings"
              : `Pin link to ${linkedCount} finding${linkedCount === 1 ? "" : "s"}`}
        </Button>
      </div>

      {entry.prompts.length > 0 ? (
        <div className="trace-detail__prompts">
          <h4 className="trace-detail__heading">Prompts</h4>
          {entry.prompts.map((p) => (
            <Prompt key={p.prompt_id} prompt={p} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function Prompt({
  prompt,
}: {
  prompt: { prompt_id: string; prompt_text: string };
}) {
  async function copy() {
    try {
      await navigator.clipboard.writeText(prompt.prompt_text);
    } catch {
      /* no-op */
    }
  }
  const lines = prompt.prompt_text.split("\n");
  return (
    <div className="prompt">
      <div className="prompt__header">
        <Pill mono>{prompt.prompt_id}</Pill>
        <Button onClick={copy}>Copy</Button>
      </div>
      <pre className="prompt__body">
        {lines.map((line, i) => (
          <span key={i} className="prompt__line">
            <span className="prompt__lineno">{i + 1}</span>
            <span className="prompt__text">{line || " "}</span>
          </span>
        ))}
      </pre>
    </div>
  );
}

// Elapsed timer hook used by the page-level container.
export function useElapsed(active: boolean): number {
  const [ms, setMs] = useState(0);
  useEffect(() => {
    if (!active) {
      setMs(0);
      return;
    }
    const start = performance.now();
    const id = setInterval(() => setMs(performance.now() - start), 100);
    return () => clearInterval(id);
  }, [active]);
  return ms;
}
