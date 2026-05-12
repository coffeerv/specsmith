import { useState } from "react";
import { InputColumn } from "./components/input/InputColumn";
import { SpecColumn } from "./components/spec/SpecColumn";
import { TraceColumn, useElapsed } from "./components/trace/TraceColumn";
import { LinkProvider } from "./state/linking";
import { submitSpecify, SpecifyError } from "./api/specify";
import type { SpecifyResponse } from "./types/specsmith";
import "./styles/app.css";

type Phase = "idle" | "submitting" | "success" | "error";
type ErrorState = {
  status: number;
  message: string;
  runId: string | null;
  partialTrace: SpecifyResponse["trace"] | null;
};

export default function App() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [response, setResponse] = useState<SpecifyResponse | null>(null);
  const [error, setError] = useState<ErrorState | null>(null);
  const elapsedMs = useElapsed(phase === "submitting");

  async function handleSubmit(payload: {
    specscript: string;
    files: File[];
    target: string;
  }) {
    setPhase("submitting");
    setResponse(null);
    setError(null);
    try {
      const res = await submitSpecify(payload);
      setResponse(res);
      setPhase("success");
    } catch (err) {
      if (err instanceof SpecifyError) {
        setError({
          status: err.status,
          message:
            typeof err.detail === "string"
              ? err.detail
              : err.detail
                ? JSON.stringify(err.detail)
                : err.message,
          runId: err.runId,
          partialTrace: err.partialTrace,
        });
      } else {
        setError({
          status: 0,
          message: err instanceof Error ? err.message : "Unknown error",
          runId: null,
          partialTrace: null,
        });
      }
      setPhase("error");
    }
  }

  const entries =
    response?.trace.entries ?? error?.partialTrace?.entries ?? [];
  const runId =
    response?.trace.run_id ?? error?.partialTrace?.run_id ?? null;
  const linkResponse = response
    ? { spec: response.spec, trace: response.trace }
    : null;

  return (
    <div className="app-shell">
      <header className="top-bar">
        <span className="brand">SpecSmith</span>
        {phase === "submitting" ? <div className="top-bar__progress" aria-hidden /> : null}
        {runId ? (
          <span className="top-bar__run mono" title={runId}>
            run {runId.slice(0, 8)}…
          </span>
        ) : null}
      </header>

      <LinkProvider response={linkResponse}>
        <main className="three-col">
          <div className="three-col__cell three-col__cell--input">
            <InputColumn submitting={phase === "submitting"} onSubmit={handleSubmit} />
          </div>
          <div className="three-col__cell three-col__cell--spec">
            <SpecColumn
              spec={response?.spec ?? null}
              loading={phase === "submitting"}
              error={
                error
                  ? {
                      status: error.status,
                      message: error.message,
                      runId: error.runId,
                    }
                  : null
              }
            />
          </div>
          <div className="three-col__cell three-col__cell--trace">
            <TraceColumn
              entries={entries}
              runId={runId}
              loading={phase === "submitting"}
              elapsedMs={elapsedMs}
            />
          </div>
        </main>
      </LinkProvider>
    </div>
  );
}
