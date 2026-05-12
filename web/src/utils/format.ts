import type { TraceEntry } from "../types/specsmith";

export function formatDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return "0ms";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function shouldShowTokenColumn(entries: TraceEntry[]): boolean {
  if (!entries || entries.length === 0) return false;
  return entries.some(
    (e) =>
      e.token_usage !== null &&
      e.token_usage !== undefined &&
      Object.values(e.token_usage).some((v) => typeof v === "number"),
  );
}

export function serializeSpec(spec: unknown): string {
  return JSON.stringify(spec, null, 2);
}

function fmtNum(n: number | null): string {
  if (n === null) return "—";
  if (n < 1000) return String(n);
  return `${(n / 1000).toFixed(1)}k`;
}

export function formatTokens(tu: Record<string, number> | null): string {
  if (!tu) return "";
  const inTok = tu.input_tokens ?? tu.in ?? null;
  const outTok = tu.output_tokens ?? tu.out ?? null;
  const reasoning = tu.reasoning_tokens ?? null;
  if (reasoning && reasoning > 0) {
    return `${fmtNum(inTok)} / ${fmtNum(outTok)} +${fmtNum(reasoning)}r`;
  }
  return `${fmtNum(inTok)} / ${fmtNum(outTok)}`;
}
